//! backend_supervisor.rs —— 桌面端自动拉起本机 FastAPI 后端
//!
//! 背景（11-09 / 11-10 两次「连不上内容服务」）：Tauri EXE 只起自己 + go-judge，
//! FastAPI(:8000) 需要单独跑 uvicorn。以前靠人工双击 .cmd 或会话后台任务，
//! 关机 / 会话回收就掉，主人一登录就报「无法连接后端」。
//!
//! 现在：桌面 app 在 setup 阶段后台检查 :8000/health，不通就按 exe 同目录的
//! `nex-backend.json` 起一个隐藏窗口的 uvicorn，并轮询到就绪。
//! 配置里是本机绝对路径（python.exe / cwd），换机器只改这一个文件。
//!
//! 设计约束：
//!   * 不阻塞 UI —— ensure 跑在 detached 后台任务；
//!   * 不重复起 —— 先做健康检查，且 spawn 只发生一次；
//!   * 不改前端 —— api_probe 只多等一小会儿，等不到仍按原逻辑回落默认地址；
//!   * 只在 Windows 生效 —— Android 瘦客户端连的是电脑上已有的后端。

use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use serde::Deserialize;

use crate::boot_log;

const HEALTH_URL: &str = "http://127.0.0.1:8000/health";
const CONFIG_FILE: &str = "nex-backend.json";
const LOG_FILE: &str = "nex-backend.log";

/// 后端已确认就绪
static READY: AtomicBool = AtomicBool::new(false);
/// ensure 已跑完（成功或失败），避免 api_probe 白等满超时
static DONE: AtomicBool = AtomicBool::new(false);
/// 只 spawn 一次后台任务
static SPAWNED: AtomicBool = AtomicBool::new(false);
/// 探测窗口：spawn 之后、25s 就绪窗口之内的这段时间，允许 api_probe 多次来问。
/// api_probe 自己也只等 6s，单次等不到不代表后端不会起来。
static PROBING: AtomicBool = AtomicBool::new(false);

/// 就绪超时：uvicorn 冷启动 + 加载题库的时间（实测 3~10s，慢机器更久）。
const READY_TIMEOUT_SECS: u64 = 40;

#[derive(Debug, Deserialize)]
struct BackendSpec {
    /// 绝对路径：server/.venv/Scripts/python.exe
    python: String,
    /// 工作目录：server/
    cwd: Option<String>,
    /// 传给 python 的参数
    #[serde(default = "default_args")]
    args: Vec<String>,
}

fn default_args() -> Vec<String> {
    [
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
}

fn exe_dir() -> PathBuf {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."))
}

/// 允许用环境变量覆盖配置路径：方便 CI / 冒烟测试指向别处的配置。
fn config_path() -> PathBuf {
    if let Ok(p) = std::env::var("NEX_BACKEND_CONFIG") {
        if !p.trim().is_empty() {
            return PathBuf::from(p);
        }
    }
    exe_dir().join(CONFIG_FILE)
}

fn health_client() -> reqwest::Client {
    // .no_proxy() 是必须的：全局 HTTP_PROXY 会把 127.0.0.1 请求丢给代理，
    // 表现成「后端明明在跑却连不上」（见 api_client.rs 同款注释）。
    reqwest::Client::builder()
        .no_proxy()
        .timeout(Duration::from_millis(700))
        .connect_timeout(Duration::from_millis(400))
        .build()
        .unwrap_or_default()
}

async fn health_ok(client: &reqwest::Client) -> bool {
    matches!(
        client.get(HEALTH_URL).send().await,
        Ok(resp) if resp.status().is_success()
    )
}

fn load_spec() -> Result<BackendSpec, String> {
    let path = config_path();
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("{} 读取失败: {e}", path.display()))?;
    let spec: BackendSpec = serde_json::from_str(&text)
        .map_err(|e| format!("{} 解析失败: {e}", path.display()))?;
    if !std::path::Path::new(&spec.python).exists() {
        return Err(format!("python 不存在: {}", spec.python));
    }
    Ok(spec)
}

fn spawn_backend(spec: &BackendSpec) -> Result<(), String> {
    let log_path = exe_dir().join(LOG_FILE);
    let log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .map_err(|e| format!("{} 打不开: {e}", log_path.display()))?;
    let log2 = log.try_clone().map_err(|e| e.to_string())?;

    let mut cmd = Command::new(&spec.python);
    cmd.args(&spec.args);
    if let Some(cwd) = &spec.cwd {
        cmd.current_dir(cwd);
    }
    cmd.stdin(Stdio::null())
        .stdout(Stdio::from(log))
        .stderr(Stdio::from(log2))
        // 让子进程的内网/回环一律直连，不受全局代理劫持；
        // 不移除 HTTP_PROXY，后端若要访问外网仍可走代理。
        .env("NO_PROXY", "*")
        .env("no_proxy", "*");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NO_WINDOW：uvicorn 是控制台程序，不隐藏会弹黑框盖住界面
        cmd.creation_flags(0x0800_0000);
    }
    cmd.spawn().map_err(|e| format!("spawn 失败: {e}"))?;
    Ok(())
}

/// setup 阶段调用：后台确保后端可用（不阻塞窗口创建）。
pub fn spawn_ensure() {
    if SPAWNED.swap(true, Ordering::SeqCst) {
        return;
    }
    drop(tauri::async_runtime::spawn(async move {
        ensure().await;
    }));
}

/// 真正的检查 + 拉起 + 等待。pub 是为了让冒烟测试二进制能直接调用。
pub async fn ensure() {
    DONE.store(false, Ordering::SeqCst);
    let client = health_client();

    // ── 关键（2026-11-11 修）────────────────────────────────────────
    // 以前这里是「一进来先 health_ok 一次，不通就 spawn」。问题在于：
    // ensure 是 detached 后台任务，而 api_probe 的 wait_ready 只等 6s；
    // 一旦冷启动时 uvicorn 起得慢（题库加载、杀软扫描），api_probe 先超时返回
    // reachable=false，前端就把兜底地址钉死了。后来即使后端起来了，
    // 前端也不会再问一次 —— 于是「后端明明在跑，登录页永远是红的」。
    //
    // 现在：spawn 出来的进程由 ensure 一直守着直到真就绪（最长 40s），
    // 期间任何一次 api_probe 都可以重新问你「好了吗」（见 wait_ready）。
    if health_ok(&client).await {
        READY.store(true, Ordering::SeqCst);
        DONE.store(true, Ordering::SeqCst);
        boot_log("[backend] already running on :8000");
        return;
    }

    let spec = match load_spec() {
        Ok(s) => s,
        Err(e) => {
            READY.store(false, Ordering::SeqCst);
            DONE.store(true, Ordering::SeqCst);
            boot_log(&format!("[backend] SKIP: {e}"));
            return;
        }
    };

    if let Err(e) = spawn_backend(&spec) {
        boot_log(&format!("[backend] FAIL: {e}"));
        DONE.store(true, Ordering::SeqCst);
        return;
    }
    boot_log(&format!("[backend] spawned uvicorn via {}", spec.python));
    // 从这一刻起进入「正在起」窗口：api_probe 每等完一轮都可以再来问
    PROBING.store(true, Ordering::SeqCst);

    let start = Instant::now();
    while start.elapsed() < Duration::from_secs(READY_TIMEOUT_SECS) {
        tokio::time::sleep(Duration::from_millis(400)).await;
        if health_ok(&client).await {
            READY.store(true, Ordering::SeqCst);
            DONE.store(true, Ordering::SeqCst);
            PROBING.store(false, Ordering::SeqCst);
            boot_log(&format!(
                "[backend] ready in {}ms",
                start.elapsed().as_millis()
            ));
            return;
        }
    }
    PROBING.store(false, Ordering::SeqCst);
    boot_log(&format!(
        "[backend] WARN: {}s 内未就绪，检查 nex-backend.log / PG5432 / Redis6379",
        READY_TIMEOUT_SECS
    ));
    DONE.store(true, Ordering::SeqCst);
}

/// api_probe 调用：后端正在被拉起时最多等 max。
///
/// 两个必须分清的情况：
///   * 已经 ready（或 ensure 已彻底结束）→ 立刻返回，不必等；
///   * 仍在「正在起」窗口内（PROBING）→ 等满 max 也值得，让前端这一次就能拿到地址。
///
/// 以前只判 DONE：ensure 里一旦 "spawned" 就把 DONE 置位的情况会让这里提前返回，
/// 前端拿到 reachable=false 后**再也不会重问**（App 里只在启动时调一次），
/// 这是冷启动「红字不消失」的直接成因。
pub async fn wait_ready(max: Duration) {
    let start = Instant::now();
    while start.elapsed() < max {
        if READY.load(Ordering::SeqCst) {
            return;
        }
        // ensure 已结束（无论成功失败）且不在探测窗口 → 没得等了
        if DONE.load(Ordering::SeqCst) && !PROBING.load(Ordering::SeqCst) {
            return;
        }
        tokio::time::sleep(Duration::from_millis(120)).await;
    }
}

/// 最近一次 ensure 是否确认后端就绪（冒烟测试用）。
pub fn is_ready() -> bool {
    READY.load(Ordering::SeqCst)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_args_start_uvicorn_on_8000() {
        let a = default_args();
        assert_eq!(a.first().map(String::as_str), Some("-m"));
        assert!(a.iter().any(|s| s == "uvicorn"));
        assert!(a.windows(2).any(|w| w[0] == "--port" && w[1] == "8000"));
    }

    #[test]
    fn spec_parses_without_optional_fields() {
        let s: BackendSpec = serde_json::from_str(r#"{"python":"C:/py.exe"}"#).unwrap();
        assert_eq!(s.python, "C:/py.exe");
        assert!(s.cwd.is_none());
        assert!(s.args.iter().any(|x| x == "uvicorn"));
    }

    #[test]
    fn health_client_bypasses_proxy() {
        // 构造不 panic 即可；真正的 .no_proxy() 行为由集成冒烟覆盖
        let _ = health_client();
    }
}
