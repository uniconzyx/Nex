use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicBool, AtomicU16, AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Duration;

use tokio::process::{Child, Command as TokioCommand};
use tokio::sync::Mutex;

use crate::config::AppConfig;
use crate::error::{NexError, Result};
use crate::judge_client::{build_request, JudgeClient, Verdict};

/// go-judge 进程管理器（Sidecar 模式）。
///
/// 关键设计：
/// - 用 `std::process`/`tokio::process` 直接拉起 go-judge，自己控制端口协商 / 崩溃重启 / 进程树清理，
///   而不是用 Tauri 内置 shell sidecar（后者拿不到 PID，无法做看门狗强杀）。
/// - `pid: AtomicU32` 保存 PID，看门狗按 PID 强杀整棵进程树（含卡死沙箱），supervisor 再重启。
/// - 无 go-judge 时自动降级为本地直跑（run_direct），保证 `cargo build` 后就能跑通 mock 数据。
pub struct JudgeManager {
    cfg: AppConfig,
    port: Arc<AtomicU16>,
    pid: Arc<AtomicU32>,
    child: Arc<Mutex<Option<Child>>>,
    stopping: Arc<AtomicBool>,
}

impl JudgeManager {
    pub fn new(cfg: AppConfig) -> Self {
        Self {
            cfg,
            port: Arc::new(AtomicU16::new(0)),
            pid: Arc::new(AtomicU32::new(0)),
            child: Arc::new(Mutex::new(None)),
            stopping: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn ws_url(&self) -> String {
        format!("ws://127.0.0.1:{}/ws/run", self.cfg.ws_port)
    }

    pub fn status_json(&self) -> serde_json::Value {
        serde_json::json!({
            "go_judge_available": self.cfg.go_judge_path.is_some(),
            "mock_mode": self.cfg.mock_mode,
            "port": self.port.load(Ordering::Relaxed),
            "pid": self.pid.load(Ordering::Relaxed),
            "enable_network": self.cfg.enable_network,
        })
    }

    // ---------------- 启动 / 生命周期 ----------------

    /// 探测一个空闲端口（TOCTOU 兜底：随后显式把端口传给 go-judge）
    fn find_free_port() -> Result<u16> {
        let l = std::net::TcpListener::bind("127.0.0.1:0").map_err(NexError::Io)?;
        Ok(l.local_addr().map_err(NexError::Io)?.port())
    }

    /// App 启动时调用：拉起 go-judge（无则进降级模式），启动 supervisor
    pub async fn start(&self) -> Result<()> {
        let Some(path) = self.cfg.go_judge_path.clone() else {
            eprintln!("[judge] go-judge 未找到 -> 进入本地直跑降级模式（mock）");
            return Ok(());
        };
        let port = Self::find_free_port()?;
        self.port.store(port, Ordering::Relaxed);
        self.stopping.store(false, Ordering::Relaxed);

        let child = self.spawn_go_judge(path.clone(), port).await?;
        self.pid.store(child.id().unwrap_or(0), Ordering::Relaxed);
        *self.child.lock().await = Some(child);

        self.wait_ready(port).await?;
        eprintln!("[judge] go-judge 就绪 @ 127.0.0.1:{port}");
        self.supervise(path, port);
        Ok(())
    }

    async fn spawn_go_judge(&self, path: PathBuf, port: u16) -> Result<Child> {
        let addr = format!("127.0.0.1:{port}");
        let mut cmd = TokioCommand::new(path);
        // v1.13.3：HTTP 地址旗标名是 `-http-addr`（旧版 `-addr` 已被上游移除）。
        // 传错名字的后果极难排查：go-judge 打印 usage 后退出，supervisor 每 500ms
        // 重启刷屏，wait_ready 超时后又静默降级 mock 模式。
        cmd.arg("-http-addr").arg(addr);
        // Windows：go-judge 是控制台子系统程序，直接 spawn 会弹出一个黑色 cmd 窗口，
        // 盖在 app 主界面上（截图里那串 GIN-debug / Starting http server 就是它）。
        // CREATE_NO_WINDOW = 0x08000000，隐藏控制台但保留 stdout/stderr 管道。
        #[cfg(windows)]
        cmd.creation_flags(0x0800_0000);
        // v1.13.3 已无 `-enable-network` / `-enable-unsafe` 旗标：
        //  * 网络策略改为「默认隔离，要共享宿主网络才显式加 -net-share」——
        //    不加即是 enable_network=false 的语义；
        //  * Windows 上 winc（JobObject + Restricted Token）后端自动启用，无需开关
        //    （实验性；不可信用户判题仍应回退 Linux 服务端）。
        // cfg.enable_network 字段保留：恒 false，与上游默认一致；上游若恢复旗标再接回。
        debug_assert!(
            !self.cfg.enable_network,
            "v1.13.3 无网络旗标可传，enable_network 暂无法在沙箱侧生效"
        );
        cmd.kill_on_drop(true).spawn().map_err(NexError::Io)
    }

    /// 就绪轮询：go-judge 起来后 `/` 会响应（即使 404 也代表端口已监听）
    async fn wait_ready(&self, port: u16) -> Result<()> {
        let url = format!("http://127.0.0.1:{port}/");
        let client = reqwest::Client::new();
        for _ in 0..50 {
            if client
                .get(&url)
                .timeout(Duration::from_millis(200))
                .send()
                .await
                .is_ok()
            {
                return Ok(());
            }
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
        Err(NexError::Sidecar("go-judge 未在预期时间内就绪".into()))
    }

    /// 崩溃重启 supervisor（独立任务，不阻塞 start）
    fn supervise(&self, path: PathBuf, port: u16) {
        let child_arc = self.child.clone();
        let pid_arc = self.pid.clone();
        let stopping = self.stopping.clone();
        let addr = format!("127.0.0.1:{port}");
        // drop 显式丢弃 JoinHandle：supervisor 是有意分离（detach）的后台常驻任务
        drop(tauri::async_runtime::spawn(async move {
            loop {
                // 等待当前 child 退出
                let exit = {
                    let mut g = child_arc.lock().await;
                    match g.take() {
                        Some(mut c) => c.wait().await,
                        None => break,
                    }
                };
                eprintln!("[judge] go-judge 退出: {exit:?}");
                if stopping.load(Ordering::Relaxed) {
                    break;
                }
                // 退避后重启（v1.13.3：只传 -http-addr，见 spawn_go_judge 注释）
                tokio::time::sleep(Duration::from_millis(500)).await;
                // 与 spawn_go_judge 同口径：Windows 下隐藏 go-judge 控制台窗口，
                // 否则每次守护重启都会再弹一个黑框盖住 app。
                #[cfg(windows)]
                const CREATE_NO_WINDOW: u32 = 0x0800_0000;
                let mut restart_cmd = TokioCommand::new(path.clone());
                restart_cmd.arg("-http-addr").arg(&addr).kill_on_drop(true);
                #[cfg(windows)]
                restart_cmd.creation_flags(CREATE_NO_WINDOW);
                let nc = match restart_cmd.spawn() {
                    Ok(c) => c,
                    Err(e) => {
                        eprintln!("[judge] 重启失败: {e}");
                        break;
                    }
                };
                pid_arc.store(nc.id().unwrap_or(0), Ordering::Relaxed);
                *child_arc.lock().await = Some(nc);
            }
        }));
    }

    // ---------------- 判题入口 ----------------

    /// 单测试用例判题（命令层调用）
    pub async fn judge(&self, lang: &str, code: &str, stdin: Option<&str>) -> Verdict {
        let v = self.judge_batch(lang, code, vec![stdin]).await;
        v.into_iter().next().unwrap_or(Verdict::Mock {
            stdout: String::new(),
        })
    }

    /// 批量判题：C++/Java 首用例编译并 `copyOutCached` 出 fileId，后续用例复用，避免重复编译。
    pub async fn judge_batch(&self, lang: &str, code: &str, stdins: Vec<Option<&str>>) -> Vec<Verdict> {
        // 降级模式：本地直跑
        if self.cfg.go_judge_path.is_none() {
            let mut out = Vec::with_capacity(stdins.len());
            for s in &stdins {
                out.push(self.run_direct(lang, code, *s).await);
            }
            return out;
        }

        let client = JudgeClient::new(format!("http://127.0.0.1:{}", self.port.load(Ordering::Relaxed)));
        let compiled = matches!(lang, "cpp" | "c++" | "c" | "java");

        if compiled {
            // 第一步：独立编译请求（单 cmd + copyOutCached）→ fileId。
            // **不能**把「编译+运行」塞进同一请求：go-judge v1.13.3 的
            // worker 对 group 内每个 cmd 单独分配 Environment（独立 root），
            // run cmd 的沙箱里没有编译产物，实测直接
            // `Internal Error: The system cannot find the file specified.`。
            let creq = match build_request(lang, code, None, &self.cfg, None) {
                Ok(r) => r,
                Err(e) => return vec![Verdict::CompileError { stderr: format!("payload build: {e}") }; stdins.len()],
            };
            let (cv, fid) = match tokio::time::timeout(
                Duration::from_secs(self.cfg.wall_timeout_secs),
                client.run_cached(&creq),
            )
            .await
            {
                Ok(Ok(pair)) => pair,
                Ok(Err(e)) => return vec![Verdict::RuntimeError {
                    stderr: e.to_string(),
                    signal: None,
                }; stdins.len()],
                Err(_) => {
                    // 墙钟超时：强杀整棵进程树（含卡死沙箱），supervisor 会重启
                    let _ = self.kill_tree().await;
                    return vec![Verdict::WallTimeout; stdins.len()];
                }
            };
            // 编译失败：所有用例同一编译错误（带真实 stderr，见 map_compile_result）
            if !matches!(cv, Verdict::Accepted { .. }) {
                return vec![cv; stdins.len()];
            }
            let fid = match fid {
                Some(f) => f,
                None => {
                    // 编译成功却没回传 fileId：copyOutCached 契约被破坏，属平台故障
                    return vec![Verdict::CompileError {
                        stderr: "编译缓存缺失（go-judge 未回传 fileId）".into(),
                    }; stdins.len()];
                }
            };
            // 第二步：逐用例运行缓存产物（含第一个 stdin）。
            // run cmd 用裸名 `a.exe` / `Main`：winc 的 Execve 会把 Args[0]
            // 用 joinExeDirAndFName 解析到沙箱 root 内的绝对路径，而 copyIn
            // 恰好把 fileId 产物放在 root 里——实测该路径 Accepted 且
            // stdout 正常回收。
            let mut out = Vec::with_capacity(stdins.len());
            for s in &stdins {
                let req = match build_request(lang, code, *s, &self.cfg, Some(&fid)) {
                    Ok(r) => r,
                    Err(e) => {
                        out.push(Verdict::CompileError { stderr: e.to_string() });
                        continue;
                    }
                };
                out.push(self.run_one(&client, &req).await);
            }
            out
        } else {
            // Python：逐用例单 cmd
            let mut out = Vec::with_capacity(stdins.len());
            for s in &stdins {
                let req = match build_request(lang, code, *s, &self.cfg, None) {
                    Ok(r) => r,
                    Err(e) => {
                        out.push(Verdict::CompileError { stderr: e.to_string() });
                        continue;
                    }
                };
                out.push(self.run_one(&client, &req).await);
            }
            out
        }
    }

    /// 带墙钟看门狗的单词判题调用
    async fn run_one(&self, client: &JudgeClient, req: &crate::payload::RunRequest) -> Verdict {
        let wall = Duration::from_secs(self.cfg.wall_timeout_secs);
        match tokio::time::timeout(wall, client.run(req)).await {
            Ok(Ok(v)) => v,
            Ok(Err(e)) => Verdict::RuntimeError {
                stderr: e.to_string(),
                signal: None,
            },
            Err(_) => {
                // 墙钟超时（用户写了死循环 / sleep，go-judge 的 cpuLimit 防不住）：强杀整棵树
                let _ = self.kill_tree().await;
                Verdict::WallTimeout
            }
        }
    }

    // ---------------- 进程树清理（防僵尸） ----------------

    /// WS 断开时调用：强杀当前沙箱（按 PID 杀整棵树）
    pub async fn kill_current(&self) -> Result<()> {
        self.kill_tree().await
    }

    /// 按 PID 强杀整棵进程树（Windows 走 taskkill /F /T，最终调用 TerminateProcess）
    pub async fn kill_tree(&self) -> Result<()> {
        let pid = self.pid.load(Ordering::Relaxed);
        if pid == 0 {
            return Ok(());
        }
        kill_pid_tree(pid);
        Ok(())
    }

    /// App 退出时彻底清理
    pub async fn stop(&self) -> Result<()> {
        self.stopping.store(true, Ordering::Relaxed);
        if let Some(mut c) = self.child.lock().await.take() {
            let _ = c.kill().await;
        }
        self.kill_tree().await
    }

    // ---------------- 降级：本地直跑（无 go-judge 时使用） ----------------

    async fn run_direct(&self, lang: &str, code: &str, stdin: Option<&str>) -> Verdict {
        self.run_direct_tagged("run", lang, code, stdin).await
    }

    /// 与 `run_direct` 相同，但临时目录 tag 可指定。
    /// 生产走 `run_direct`（tag="run"）；测试传入各自唯一的 tag，
    /// 即可在并发跑测的环境下**确定性地**断言「没有残留目录」。
    async fn run_direct_tagged(&self, tag: &str, lang: &str, code: &str, stdin: Option<&str>) -> Verdict {
        match lang {
            "python" | "py" => {
                // RAII 守卫：正常返回 / 墙钟超时 / panic 都会递归回收该目录。
                // 必须在内层 spawn 之前声明——局部变量逆序析构，保证子进程先被杀、目录后被删。
                let guard = TempDirGuard::create(&format!("{tag}_py"));
                let f = guard.path().join("sol.py");
                let _ = std::fs::write(&f, code);
                let mut cmd = TokioCommand::new(find_exe("python"));
                cmd.arg(&f);
                match self.spawn_capture(cmd, stdin).await {
                    Ok((0, out, _)) => Verdict::Accepted {
                        stdout: out,
                        time_ms: 0,
                        memory_kb: 0,
                    },
                    Ok((_, _, err)) => Verdict::RuntimeError {
                        stderr: err,
                        signal: None,
                    },
                    Err(NexError::Watchdog) => Verdict::WallTimeout,
                    Err(e) => Verdict::RuntimeError {
                        stderr: e.to_string(),
                        signal: None,
                    },
                }
            }
            "cpp" | "c++" | "c" => {
                let guard = TempDirGuard::create(&format!("{tag}_cpp"));
                let src = guard.path().join("main.cpp");
                let _ = std::fs::write(&src, code);
                let exe = guard.path().join(if cfg!(windows) { "a.exe" } else { "a.out" });
                let mut cc = TokioCommand::new(find_exe("g++"));
                cc.arg(&src).arg("-O2").arg("-o").arg(&exe);
                match self.spawn_capture(cc, None).await {
                    Ok((0, _, _)) => {}
                    Ok((_, _, err)) => return Verdict::CompileError { stderr: err },
                    Err(NexError::Watchdog) => return Verdict::WallTimeout,
                    Err(e) => return Verdict::CompileError { stderr: e.to_string() },
                }
                let run = TokioCommand::new(exe);
                match self.spawn_capture(run, stdin).await {
                    Ok((0, out, _)) => Verdict::Accepted {
                        stdout: out,
                        time_ms: 0,
                        memory_kb: 0,
                    },
                    Ok((_, _, err)) => Verdict::RuntimeError {
                        stderr: err,
                        signal: None,
                    },
                    Err(NexError::Watchdog) => Verdict::WallTimeout,
                    Err(e) => Verdict::RuntimeError {
                        stderr: e.to_string(),
                        signal: None,
                    },
                }
            }
            "java" => {
                let guard = TempDirGuard::create(&format!("{tag}_java"));
                let src = guard.path().join("Main.java");
                let _ = std::fs::write(&src, code);
                let mut jc = TokioCommand::new(find_exe("javac"));
                jc.arg(&src);
                match self.spawn_capture(jc, None).await {
                    Ok((0, _, _)) => {}
                    Ok((_, _, err)) => return Verdict::CompileError { stderr: err },
                    Err(NexError::Watchdog) => return Verdict::WallTimeout,
                    Err(e) => return Verdict::CompileError { stderr: e.to_string() },
                }
                let mut run = TokioCommand::new(find_exe("java"));
                run.arg("Main").current_dir(guard.path());
                match self.spawn_capture(run, stdin).await {
                    Ok((0, out, _)) => Verdict::Accepted {
                        stdout: out,
                        time_ms: 0,
                        memory_kb: 0,
                    },
                    Ok((_, _, err)) => Verdict::RuntimeError {
                        stderr: err,
                        signal: None,
                    },
                    Err(NexError::Watchdog) => Verdict::WallTimeout,
                    Err(e) => Verdict::RuntimeError {
                        stderr: e.to_string(),
                        signal: None,
                    },
                }
            }
            other => Verdict::RuntimeError {
                stderr: format!("本地直跑模式不支持语言: {other}"),
                signal: None,
            },
        }
    }

    /// 通用子进程捕获：kill_on_drop 防僵尸 + Unix pre_exec RLIMIT_CPU 硬保底 + 墙钟看门狗
    async fn spawn_capture(
        &self,
        mut cmd: TokioCommand,
        stdin_data: Option<&str>,
    ) -> std::result::Result<(i32, String, String), NexError> {
        cmd.kill_on_drop(true);
        #[cfg(unix)]
        {
            // pre_exec 是 unsafe：回调在 fork 之后、exec 之前的子进程上下文执行，
            // 只允许 async-signal-safe 的操作（这里只调 setrlimit，满足要求）。
            unsafe {
                let _ = cmd.pre_exec(set_cpu_rlimit);
            }
        }
        cmd.stdout(Stdio::piped()).stderr(Stdio::piped());
        if stdin_data.is_some() {
            cmd.stdin(Stdio::piped());
        }
        let mut child = cmd.spawn().map_err(NexError::Io)?;
        if let Some(s) = stdin_data {
            if let Some(mut sin) = child.stdin.take() {
                use tokio::io::AsyncWriteExt;
                let _ = sin.write_all(s.as_bytes()).await;
                let _ = sin.shutdown().await;
            }
        }
        let wall = Duration::from_secs(self.cfg.wall_timeout_secs);
        match tokio::time::timeout(wall, child.wait_with_output()).await {
            Ok(Ok(out)) => {
                let code = out.status.code().unwrap_or(-1);
                Ok((
                    code,
                    String::from_utf8_lossy(&out.stdout).into_owned(),
                    String::from_utf8_lossy(&out.stderr).into_owned(),
                ))
            }
            Ok(Err(e)) => Err(NexError::Io(e)),
            Err(_) => Err(NexError::Watchdog), // 超时：kill_on_drop 已杀掉进程树
        }
    }
}

// ---------------- 自由函数 / 跨平台辅助 ----------------

fn find_exe(name: &str) -> String {
    // 交给 PATH 解析；环境检测见 environment.rs
    name.to_string()
}

/// 每次判题分配**唯一**临时目录。
///
/// 修正记录（2026-10-17）：旧实现只按 `pid + tag` 建目录，导致同一进程内
/// **并发判题共用同一个文件夹、同一个 sol.py / main.cpp**——后提交的代码会被
/// 前一个请求读到，出现「A 提交跑出 B 的输出」这类串号事故（桌面端是常驻
/// 单进程，必然触发）。这里改为 pid + 纳秒时间戳 + 原子序号三重标识。
///
/// 调用方应通过 [`TempDirGuard::create`] 间接使用，由 `Drop` 负责回收；
/// 直接调用本函数会泄漏目录（仅测试用）。
fn temp_dir(tag: &str) -> PathBuf {
    use std::sync::atomic::{AtomicU64, Ordering};

    static SEQ: AtomicU64 = AtomicU64::new(0);

    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);

    let p = std::env::temp_dir()
        .join("nex")
        .join(tag)
        .join(format!("{}_{}_{}", std::process::id(), nanos, seq));
    let _ = std::fs::create_dir_all(&p);
    p
}

/// nex 临时目录根：`<系统临时目录>/nex`。所有判题工作目录都必须位于它下面。
fn nex_temp_root() -> PathBuf {
    std::env::temp_dir().join("nex")
}

/// 判题临时目录的 RAII 守卫。
///
/// # 设计要点
/// - **任何退出路径都回收**：`Drop` 在正常返回、墙钟看门狗 `timeout` 丢弃 future、
///   乃至 panic 展开时都会运行，因此临时目录不会在 `%TEMP%/nex` 里堆积。
///   （`tokio::time::timeout` 超时是「丢弃 future」，future 内部局部的 `Drop`
///   一样会执行，所以这条保证对看门狗路径同样成立。）
/// - **绝不会误删 `copyOutCached` 的缓存文件**，双保险：
///   1. **语义隔离**：go-judge 模式下编译产物的缓存是 go-judge **自身 store 里的
///      fileId**（由 `POST /run` 的 `copyOutCached` 回传，见 `judge_client::run_cached`），
///      从来不落到本机临时目录；本 guard 只覆盖 `run_direct`（无 go-judge 时的
///      本地直跑降级路径）。
///   2. **路径硬闸**：只允许删除 `<tmp>/nex/<tag>/<...>`，且拒绝等于 nex 根本身；
///      任何 nex 之外的路径（go-judge 缓存目录、用户目录……）一律不删。
/// - **Windows 句柄延迟**：子进程刚被 `kill_on_drop` 杀掉时文件句柄可能有极小延迟，
///   `Drop` 内做有界重试（最多 5 次 × 20ms，仅失败路径发生）。
pub struct TempDirGuard {
    path: PathBuf,
}

impl TempDirGuard {
    /// 为本次判题分配**唯一**临时目录（pid + 纳秒 + 原子序号）并返回其守卫。
    pub fn create(tag: &str) -> Self {
        Self::new(temp_dir(tag))
    }

    /// 直接包裹一个已存在的目录。调用方需保证该目录是本次判题**独享**的工作目录。
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    /// 工作目录路径（用于写源码 / 设 `current_dir`）。
    pub fn path(&self) -> &std::path::Path {
        &self.path
    }

    /// 主动回收（等价于 `drop`）。一般无需显式调用，`Drop` 会自动兜底。
    #[allow(dead_code)]
    pub fn cleanup(self) {
        drop(self);
    }
}

impl std::fmt::Debug for TempDirGuard {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TempDirGuard").field("path", &self.path).finish()
    }
}

impl Drop for TempDirGuard {
    fn drop(&mut self) {
        let root = nex_temp_root();
        // 安全闸：只删 nex 临时根下的判题工作目录；绝不碰根目录本身或外部路径。
        if self.path == root || !self.path.starts_with(&root) {
            eprintln!(
                "[judge] TempDirGuard 拒绝删除非判题临时目录: {}",
                self.path.display()
            );
            return;
        }
        for attempt in 0..5 {
            match std::fs::remove_dir_all(&self.path) {
                Ok(()) => return,
                Err(e) => {
                    if !self.path.exists() {
                        return; // 已被回收，视为成功
                    }
                    if attempt == 4 {
                        eprintln!(
                            "[judge] 临时目录回收失败({}/5): {} -> {e}",
                            attempt + 1,
                            self.path.display()
                        );
                        return;
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }
            }
        }
    }
}

/// 按 PID 杀整棵进程树（跨平台）。Windows 的 taskkill /F /T 最终对每个节点调用 TerminateProcess。
fn kill_pid_tree(pid: u32) {
    #[cfg(windows)]
    {
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .status();
    }
    #[cfg(not(windows))]
    {
        let _ = std::process::Command::new("kill")
            .args(["-9", &pid.to_string()])
            .status();
        let _ = std::process::Command::new("pkill")
            .args(["-9", "-P", &pid.to_string()])
            .status();
    }
}

/// Unix 下在子进程 pre_exec 设置 RLIMIT_CPU（2 秒 CPU 硬保底），即便 cpuLimit 失效也能兜底。
///
/// 注意：nix 0.29 起 `setrlimit` 的签名是 (resource, soft, hard)，
/// 不再接收 `&Rlimit`（旧 0.27 写法）。此处同时把 soft/hard 都设为 2 秒。
#[cfg(unix)]
fn set_cpu_rlimit() -> std::io::Result<()> {
    use nix::sys::resource::{setrlimit, Resource};
    setrlimit(Resource::RLIMIT_CPU, 2, 2)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))
}

// ============================================================================
//  测试：墙钟看门狗能否成功触发并杀死死循环进程（优先级 1 的核心担忧）
//  - 单元测试 kill_pid_tree：直接验证「按 PID 强杀整棵进程树」机制。
//  - 集成测试（模拟 WS 请求）：JudgeManager::judge 收到死循环代码后，
//    墙钟看门狗超时 -> 返回 WallTimeout，且 kill_on_drop 确保无残留子进程。
// ============================================================================
/// 测试专用配置：`go_judge_path: None` -> 走本地直跑（mock）路径。
///
/// `pub(crate)` + `#[cfg(test)]`：sandbox 与 lan_server 两个测试模块共用，
/// 避免两边各写一份、改字段时漏改。
#[cfg(test)]
pub(crate) fn mock_config(wall_secs: u64) -> AppConfig {
    AppConfig {
        go_judge_path: None,
        ws_port: 14520,
        enable_network: false, // 全局禁用网络
        cpu_limit_ns: 2_000_000_000,
        memory_limit_bytes: 256 * 1024 * 1024,
        proc_limit: 32,
        wall_timeout_secs: wall_secs,
        mock_mode: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::AppConfig;
    use crate::judge_client::Verdict;
    use tokio::process::Command as TokioCommand;

    /// 构造一个跨平台的「死循环」子进程（不依赖 go-judge / 特定语言）
    fn infinite_child() -> TokioCommand {
        let mut c = if cfg!(windows) {
            let mut c = TokioCommand::new("powershell");
            c.args(["-NoProfile", "-NoLogo", "-Command", "while($true){}"]);
            c
        } else {
            let mut c = TokioCommand::new("sh");
            c.args(["-c", "while true; do :; done"]);
            c
        };
        c.stdout(Stdio::null()).stderr(Stdio::null());
        c
    }

    /// 单元测试：kill_pid_tree 必须能杀掉一个正在运行的死循环（含其子孙）。
    #[tokio::test]
    async fn watchdog_kills_infinite_process_tree() {
        let mut child = infinite_child()
            .kill_on_drop(true)
            .spawn()
            .expect("spawn infinite process");
        let pid = child.id().expect("child pid");

        // 先确认它确实在跑（没在 sleep 期间就退出）
        tokio::time::sleep(Duration::from_millis(300)).await;
        assert!(
            child.try_wait().unwrap().is_none(),
            "死循环进程应当在运行，而非已退出"
        );

        // 触发墙钟看门狗的杀进程动作
        kill_pid_tree(pid);

        // 等待进程树被回收（taskkill /F /T 后应立即退出）
        let mut reaped = false;
        for _ in 0..50 {
            if child.try_wait().unwrap().is_some() {
                reaped = true;
                break;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        assert!(reaped, "墙钟看门狗应已强制杀掉死循环进程（含进程树）");
    }

    /// 构造本地直跑（降级）模式的配置：无 go-judge、墙钟设为 1 秒、python 可解析。
    /// 兼容别名：实现已上移为模块级 `mock_config`（与 lan_server 测试共用）。
    fn mock_cfg(wall_secs: u64) -> AppConfig {
        mock_config(wall_secs)
    }

    /// 集成测试（模拟 WebSocket 请求）：死循环代码 -> 墙钟看门狗 -> WallTimeout。
    /// 这正对应 WS handler 里的 `manager.judge(lang, code, stdin)` 调用路径。
    #[tokio::test]
    async fn ws_request_deadloop_triggers_wall_timeout() {
        // 确认 python 可用（run_direct 的 python 分支依赖它）
        let python_ok = TokioCommand::new("python")
            .arg("-c")
            .arg("print('ok')")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .await
            .map(|s| s.success())
            .unwrap_or(false);
        if !python_ok {
            eprintln!("跳过 ws_request_deadloop：本机未检测到 python");
            return;
        }

        let mgr = JudgeManager::new(mock_cfg(1)); // 1 秒墙钟
        let verdict = mgr
            .judge("python", "while True:\n    pass\n", None)
            .await;

        assert!(
            matches!(verdict, Verdict::WallTimeout),
            "死循环应触发墙钟看门狗返回 WallTimeout，实际得到: {verdict:?}"
        );
    }

    /// 快乐路径：正常代码在降级模式下也能跑到 Accepted（证明 mock 链路可用）。
    #[tokio::test]
    async fn mock_mode_runs_normal_code() {
        let python_ok = TokioCommand::new("python")
            .arg("-c")
            .arg("print('ok')")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .await
            .map(|s| s.success())
            .unwrap_or(false);
        if !python_ok {
            eprintln!("跳过 mock_mode_runs_normal_code：本机未检测到 python");
            return;
        }

        // 墙钟放宽到 20s（非延迟断言，只是避免偶发误判）：
        // cargo test 默认并发执行三个用例，前两个用例会故意起 CPU 打满的死循环
        // （powershell 忙等 + python 忙等），本机核心被抢占时 python 启动可能被拖慢。
        // 看门狗的严格性由上面那个 1 秒墙钟用例负责。
        let mgr = JudgeManager::new(mock_cfg(20));
        let verdict = mgr.judge("python", "print(6*7)", None).await;
        match verdict {
            Verdict::Accepted { stdout, .. } => {
                assert_eq!(stdout.trim(), "42", "正常 python 应输出 42");
            }
            other => panic!("正常代码应 Accepted，实际: {other:?}"),
        }
    }

    // ---------------- 临时目录 RAII 守卫 ----------------

    /// 正常路径：drop 后工作目录被递归删除。
    #[test]
    fn temp_dir_guard_removes_work_dir_on_drop() {
        let guard = TempDirGuard::create("guard_basic");
        let p = guard.path().to_path_buf();
        std::fs::write(p.join("sol.py"), b"print(1)").unwrap();
        assert!(p.exists(), "前置：目录应已创建");
        drop(guard);
        assert!(!p.exists(), "drop 后工作目录应被递归删除");
    }

    /// panic 路径：`Drop` 在栈展开时同样执行，目录必须被回收。
    #[test]
    fn temp_dir_guard_cleans_up_on_panic() {
        // 屏蔽 panic 回显，保持测试日志干净
        let hook = std::panic::take_hook();
        std::panic::set_hook(Box::new(|_| {}));
        let guard = TempDirGuard::create("guard_panic");
        let p = guard.path().to_path_buf();
        std::fs::write(p.join("x.txt"), b"boom").unwrap();

        let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            let _g = guard; // move 进闭包，panic 时在此作用域内析构
            panic!("模拟判题中途 panic");
        }));
        std::panic::set_hook(hook);

        assert!(r.is_err(), "catch_unwind 应捕获到 panic");
        assert!(!p.exists(), "panic 展开后临时目录也应被回收");
    }

    /// 安全路径：守卫绝不误删同级的 go-judge 缓存 store（模拟 copyOutCached 产物）。
    #[test]
    fn temp_dir_guard_preserves_go_judge_cache_store() {
        let root = nex_temp_root();
        std::fs::create_dir_all(&root).unwrap();
        // 模拟 go-judge 的缓存 store：与工作目录同在 nex 根下，但不是工作目录
        let cache = root.join("gojudge_store_sim");
        std::fs::create_dir_all(&cache).unwrap();
        std::fs::write(cache.join("cached_a_exe"), b"MZ fake exe").unwrap();

        // 注意：必须先把 guard 绑到变量上再取 path。
        // 若写成 `TempDirGuard::create("cpp").path()`，语句结束的瞬间临时 guard 就被
        // drop、目录立刻被删，下一行写文件会 NotFound（这正是 Drop 立即生效的证明）。
        let guard = TempDirGuard::create("cpp");
        let work = guard.path().to_path_buf();
        std::fs::write(work.join("main.cpp"), b"int main(){}").unwrap();
        drop(guard);

        assert!(!work.exists(), "工作目录应被回收");
        assert!(
            cache.join("cached_a_exe").exists(),
            "go-judge 缓存文件不得被误删"
        );
        let _ = std::fs::remove_dir_all(&cache);
    }

    /// 安全闸：任何不在 `<tmp>/nex` 下的路径一律拒绝删除（防误伤用户目录）。
    #[test]
    fn temp_dir_guard_refuses_paths_outside_nex_root() {
        // 注意：`Path::starts_with` 按**路径分量**比较，
        // `nex_guard_outside_probe` 与 `nex` 不是同一分量，故不会被误判为「根下」。
        let outside = std::env::temp_dir().join("nex_guard_outside_probe");
        std::fs::create_dir_all(&outside).unwrap();
        std::fs::write(outside.join("keep.txt"), b"1").unwrap();

        drop(TempDirGuard::new(outside.clone()));

        assert!(outside.exists(), "守卫不得删除 nex 临时根之外的目录");
        let _ = std::fs::remove_dir_all(&outside);
    }

    /// 并发路径：多个守卫同时存在时互不干扰、各自回收（防串号回归的看门测试）。
    #[test]
    fn temp_dir_guards_are_isolated_and_all_cleaned() {
        let guards: Vec<TempDirGuard> = (0..8).map(|_| TempDirGuard::create("guard_conc")).collect();
        let paths: Vec<PathBuf> = guards.iter().map(|g| g.path().to_path_buf()).collect();

        // 唯一性：并发场景下绝不允许两个 guard 指向同一目录
        let uniq: std::collections::HashSet<&PathBuf> = paths.iter().collect();
        assert_eq!(uniq.len(), paths.len(), "并发守卫必须拿到互不相同的目录");

        for (i, p) in paths.iter().enumerate() {
            std::fs::write(p.join(format!("sol{i}.py")), b"x").unwrap();
        }
        drop(guards);
        for p in &paths {
            assert!(!p.exists(), "每个守卫都应回收自己的目录: {}", p.display());
        }
    }

    /// 看门狗中断路径：`tokio::time::timeout` 超时会**丢弃 future**，
    /// 局部变量随之析构——guard 同样必须回收目录。
    #[tokio::test]
    async fn temp_dir_guard_cleans_up_on_watchdog_timeout() {
        let guard = TempDirGuard::create("guard_watchdog");
        let p = guard.path().to_path_buf();
        std::fs::write(p.join("sol.py"), b"while True:\n    pass\n").unwrap();

        // 起一个死循环子进程，并用 timeout 模拟墙钟看门狗触发
        let mut child = infinite_child().kill_on_drop(true).spawn().expect("spawn");
        let timed_out = tokio::time::timeout(Duration::from_millis(300), child.wait()).await;
        assert!(timed_out.is_err(), "300ms 内死循环不应退出（模拟看门狗超时）");

        // 看门狗语义：先强杀进程（kill_on_drop），再回收目录
        drop(child);
        drop(guard);
        assert!(!p.exists(), "看门狗中断后临时目录也应被回收");
    }

    /// Windows 真实场景：子进程被杀瞬间文件句柄可能未释放，
    /// `Drop` 的有界重试必须仍能把目录删掉。
    /// （holder 起不来时自动退化为普通回收路径，不影响断言成立。）
    #[tokio::test]
    async fn temp_dir_guard_cleans_up_when_file_handle_still_open() {
        let guard = TempDirGuard::create("guard_lock");
        let p = guard.path().to_path_buf();
        let lock = p.join("lock.bin");
        std::fs::write(&lock, b"").unwrap();

        // 起一个长时间持有 lock.bin 句柄的子进程（跨平台）
        let mut holder = if cfg!(windows) {
            let mut c = TokioCommand::new("powershell");
            c.args([
                "-NoProfile",
                "-NoLogo",
                "-Command",
                &format!(
                    "$f=[System.IO.File]::Open('{}','Open','ReadWrite'); Start-Sleep -Seconds 30; $f.Close()",
                    lock.display()
                ),
            ]);
            c
        } else {
            let mut c = TokioCommand::new("sh");
            c.args(["-c", &format!("exec 3<'{}'; sleep 30", lock.display())]);
            c
        };
        holder.stdout(Stdio::null()).stderr(Stdio::null()).kill_on_drop(true);
        let child = holder.spawn().ok(); // 起不来就跳过加锁场景

        tokio::time::sleep(Duration::from_millis(400)).await; // 给 holder 时间拿句柄
        drop(child); // kill_on_drop -> 进程被杀，句柄释放
        drop(guard); // 若句柄未立即释放，由有界重试兜底

        assert!(!p.exists(), "进程被杀后临时目录应被回收（含曾被占用的文件）");
    }

    // ---------------- 端到端：判题后不得残留临时目录 ----------------

    /// 统计某 tag 目录下的残留工作目录数。
    fn count_work_dirs(tag: &str) -> usize {
        let p = nex_temp_root().join(tag);
        std::fs::read_dir(p).map(|rd| rd.filter_map(|e| e.ok()).count()).unwrap_or(0)
    }

    /// 本机是否有可用 python（两个端到端用例都依赖它）。
    async fn python_available() -> bool {
        TokioCommand::new("python")
            .arg("-c")
            .arg("print('ok')")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .await
            .map(|s| s.success())
            .unwrap_or(false)
    }

    /// 端到端：正常跑完一次判题，临时目录必须被回收（0 残留）。
    /// 用独立 tag，与其它并发用例完全隔离，断言是确定性的。
    #[tokio::test]
    async fn run_direct_leaves_no_temp_dirs_behind() {
        if !python_available().await {
            eprintln!("跳过 run_direct_leaves_no_temp_dirs_behind：本机未检测到 python");
            return;
        }
        const TAG: &str = "e2e_ok";
        let _ = std::fs::remove_dir_all(nex_temp_root().join(format!("{TAG}_py")));
        assert_eq!(count_work_dirs(&format!("{TAG}_py")), 0, "前置：应无残留");

        let mgr = JudgeManager::new(mock_cfg(20));
        let v = mgr.run_direct_tagged(TAG, "python", "print(6*7)", None).await;
        assert!(matches!(v, Verdict::Accepted { .. }), "应正常跑完: {v:?}");

        assert_eq!(
            count_work_dirs(&format!("{TAG}_py")),
            0,
            "判题正常结束后不应残留任何临时目录"
        );
    }

    /// 端到端：**墙钟看门狗杀掉死循环进程后**，临时目录同样必须被回收。
    /// 这是最容易被忽略的路径——子进程刚被杀时可能仍持有 sol.py 句柄。
    #[tokio::test]
    async fn run_direct_leaves_no_temp_dirs_after_watchdog_kill() {
        if !python_available().await {
            eprintln!("跳过 run_direct_leaves_no_temp_dirs_after_watchdog_kill：本机未检测到 python");
            return;
        }
        const TAG: &str = "e2e_kill";
        let _ = std::fs::remove_dir_all(nex_temp_root().join(format!("{TAG}_py")));
        assert_eq!(count_work_dirs(&format!("{TAG}_py")), 0, "前置：应无残留");

        let mgr = JudgeManager::new(mock_cfg(1)); // 1 秒墙钟
        let v = mgr
            .run_direct_tagged(TAG, "python", "while True:\n    pass\n", None)
            .await;
        assert!(matches!(v, Verdict::WallTimeout), "死循环应被看门狗终结: {v:?}");

        assert_eq!(
            count_work_dirs(&format!("{TAG}_py")),
            0,
            "看门狗杀进程后也不应残留临时目录（句柄未释放？）"
        );
    }
}