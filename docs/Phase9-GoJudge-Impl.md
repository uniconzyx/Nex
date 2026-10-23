# Nex v2 — go-judge 集成实现（Tauri v2 + Rust 工程级代码）

> 配套设计文档：`docs/Phase9-GoJudge-Integration.md`（架构/坑点总览）。本文件给**可直接粘贴到 `src-tauri/src/` 的代码**。
> go-judge 二进制由 `externalBin` 打包；Rust 宿主用 `std::process::Command` 直接托管（不用 Tauri 内置 shell sidecar，以便自管端口/重启/进程树）。

---

## 0. 工程文件结构

```
src-tauri/
├── Cargo.toml
├── build.rs
├── tauri.conf.json
├── bin/
│   └── go-judge-x86_64-pc-windows-msvc.exe      # externalBin（Tauri 按平台加后缀）
└── src/
    ├── main.rs          # 入口：setup 拉起 sidecar，ExitRequested 清理
    ├── lib.rs           # Tauri v2 标准入口（run() 在此）
    ├── commands.rs      # Tauri commands：check_environment / judge_*
    └── judge/
        ├── mod.rs
        ├── manager.rs   # 模块1：Sidecar 生命周期（端口/重启/杀树）
        ├── client.rs    # 模块3：reqwest 封装 + Payload + 判题判定
        ├── env.rs       # 模块2：编译器环境检测
        └── defender.rs  # 模块4：Defender 排除项
```

---

## 模块 1：Sidecar 进程管理与生命周期

### 1.1 `tauri.conf.json`（声明 externalBin）

```json
{
  "productName": "Nex",
  "version": "2.0.0",
  "identifier": "com.nex.app",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:1420",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [{ "title": "Nex", "width": 1100, "height": 760 }],
    "security": { "csp": null }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "externalBin": ["bin/go-judge"]
  }
}
```

> `externalBin` 只写 `bin/go-judge`，Tauri 在打包时会按目标三元组找 `bin/go-judge-<triple>.exe`；运行时通过 `resource_dir()` 解析真实路径（见 `manager.rs` 的 `resolve()`）。

### 1.2 `src/judge/manager.rs`（核心：端口探测 + 重启 + 杀树）

```rust
// src/judge/manager.rs
use std::io;
use std::net::{TcpListener, TcpStream};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU16, AtomicU32, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

/// 托管 go-judge sidecar：自管端口、崩溃重启、进程树清理。
pub struct JudgeManager {
    inner: Mutex<Option<Child>>, // 当前子进程句柄（supervisor 线程持有并 wait）
    pid: AtomicU32,              // 当前子进程 PID（看门狗按 PID 强杀，避免与 supervisor 抢句柄）
    binary: std::path::PathBuf,
    port: AtomicU16,
    stop: AtomicBool,
}

impl JudgeManager {
    pub fn new(binary: std::path::PathBuf) -> Arc<Self> {
        Arc::new(Self {
            inner: Mutex::new(None),
            pid: AtomicU32::new(0),
            binary,
            port: AtomicU16::new(0),
            stop: AtomicBool::new(false),
        })
    }

    /// App 启动时调用：拉起一次，并起 supervisor 线程监督。
    pub fn launch(self: &Arc<Self>) {
        self.respawn();
        let m = self.clone();
        thread::spawn(move || m.supervisor_loop());
    }

    /// 探测空闲端口 → 拉起 → 就绪探测；失败重试 3 次。
    fn respawn(&self) {
        for _ in 0..3 {
            if self.stop.load(Ordering::Acquire) {
                return;
            }
            let port = match find_free_port() {
                Ok(p) => p,
                Err(_) => {
                    thread::sleep(Duration::from_millis(300));
                    continue;
                }
            };
            match spawn_once(&self.binary, port) {
                Ok(child) => {
                    // 端口探测存在 TOCTOU，用就绪轮询兜底：起得来但没就绪说明端口被抢，杀掉重来
                    if wait_ready(port, Duration::from_secs(10)) {
                        let pid = child.id();
                        *self.inner.lock().unwrap() = Some(child);
                        self.pid.store(pid, Ordering::SeqCst);
                        self.port.store(port, Ordering::SeqCst);
                        return;
                    }
                    kill_tree(child);
                }
                Err(e) => eprintln!("[judge] spawn failed: {e}"),
            }
            thread::sleep(Duration::from_millis(300));
        }
        eprintln!("[judge] go-judge 启动失败（多次重试）");
    }

    /// 监督循环：子进程退出则带退避重启；stop 置位则退出。
    fn supervisor_loop(self: Arc<Self>) {
        loop {
            if self.stop.load(Ordering::Acquire) {
                break;
            }
            // 持有句柄并等待（reap，防 Unix 僵尸进程）
            let exited = {
                let mut g = self.inner.lock().unwrap();
                if let Some(mut c) = g.take() {
                    drop(g);
                    let _ = c.wait();
                    true
                } else {
                    drop(g);
                    false
                }
            };
            if !exited {
                thread::sleep(Duration::from_millis(500));
                continue;
            }
            if self.stop.load(Ordering::Acquire) {
                break;
            }
            thread::sleep(Duration::from_millis(500)); // 退避，防崩溃循环打满 CPU
            self.respawn();
        }
    }

    /// App 退出时调用：置位 stop + 杀进程树（防僵尸/孤儿）。
    pub fn stop(&self) {
        self.stop.store(true, Ordering::Release);
        if let Some(mut c) = self.inner.lock().unwrap().take() {
            kill_tree(&mut c);
        }
    }

    /// 看门狗专用：杀掉当前 go-judge 进程树（含卡死沙箱），但不置 stop，
    /// supervisor 的 wait() 返回后会自动重启。
    pub fn kill_current(&self) {
        let pid = self.pid.load(Ordering::SeqCst);
        if pid == 0 {
            return;
        }
        #[cfg(windows)]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .output();
        }
        #[cfg(unix)]
        {
            unsafe {
                libc::kill(-(pid as i32), libc::SIGKILL);
            }
        }
    }

    pub fn url(&self) -> String {
        let p = self.port.load(Ordering::SeqCst);
        if p == 0 {
            String::new()
        } else {
            format!("http://127.0.0.1:{p}/")
        }
    }

    pub fn ready(&self) -> bool {
        self.port.load(Ordering::SeqCst) != 0
    }
}

/// 探测空闲本地端口（bind :0 让 OS 分配，读后立即释放交给 go-judge）。
fn find_free_port() -> io::Result<u16> {
    let l = TcpListener::bind("127.0.0.1:0")?;
    let p = l.local_addr()?.port();
    drop(l);
    Ok(p)
}

/// 拉起一次 go-judge。--enable-network=false 全局禁用沙箱网络（见模块4）。
fn spawn_once(binary: &std::path::Path, port: u16) -> io::Result<Child> {
    Command::new(binary)
        .args([
            "--addr",
            &format!("127.0.0.1:{port}"),
            "--enable-network=false", // ★ 强制禁用沙箱网络，防恶意代码外联
            "--par",
            "4", // 并发沙箱数，按机器核数调
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
}

/// 就绪探测：发一个无害的 /run，看 HTTP 是否 200（不引第三方依赖，手写最小 HTTP）。
fn wait_ready(port: u16, timeout: Duration) -> bool {
    let start = Instant::now();
    let body = r#"{"cmd":[{"args":["cmd","/c","echo","ok"]}]}"#;
    let req = format!(
        "POST /run HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\
         Content-Type: application/json\r\nContent-Length: {}\r\n\
         Connection: close\r\n\r\n{}",
        body.len(),
        body
    );
    use std::io::{Read, Write};
    while start.elapsed() < timeout {
        if let Ok(mut s) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = s.write_all(req.as_bytes());
            let mut buf = [0u8; 200];
            if let Ok(n) = s.read(&mut buf) {
                if String::from_utf8_lossy(&buf[..n]).contains("200") {
                    return true;
                }
            }
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}

/// 杀进程树：Windows 用 taskkill /T（winc 的 JobObject 会连带清掉沙箱子进程）；Unix 杀进程组。
#[cfg(windows)]
pub fn kill_tree(mut child: Child) {
    let pid = child.id();
    let _ = Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .output();
    let _ = child.kill();
}

#[cfg(unix)]
pub fn kill_tree(mut child: Child) {
    unsafe {
        libc::kill(-(child.id() as i32), libc::SIGKILL);
    }
    let _ = child.kill();
}
```

### 1.3 `src/lib.rs`（接入 Tauri 生命周期）

```rust
// src/lib.rs
mod commands;
mod judge;

use judge::manager::JudgeManager;
use std::sync::Arc;
use tauri::Manager;

/// 解析 externalBin 真实路径（Tauri 会按平台加三元组后缀）。
fn resolve_gojudge(app: &tauri::AppHandle) -> std::path::PathBuf {
    let dir = app.path().resource_dir().expect("resource_dir");
    let candidates = [
        dir.join("bin/go-judge-x86_64-pc-windows-msvc.exe"),
        dir.join("bin/go-judge-aarch64-pc-windows-msvc.exe"),
        dir.join("bin/go-judge.exe"),
    ];
    candidates.into_iter().find(|p| p.exists()).expect("go-judge 二进制缺失，请放入 src-tauri/bin/")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let binary = resolve_gojudge(app.handle());
            let manager = JudgeManager::new(binary);
            manager.launch();
            app.manage(manager); // 托管为状态，commands 通过 State 获取
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::check_environment,
            commands::judge_cpp,
            commands::judge_python
        ])
        .build(tauri::generate_context!())
        .expect("error while building Nex")
        .run(|_app, event| {
            // App 退出请求：彻底清理 sidecar，杜绝僵尸进程
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(m) = _app.try_state::<Arc<JudgeManager>>() {
                    m.stop();
                }
            }
        });
}
```

> `src/main.rs` 仅一行：`fn main() { nex_lib::run() }`（需在 `Cargo.toml` 把 lib 命名为 `nex_lib`，或直接把 `run()` 放 main.rs）。

---

## 模块 2：编译器环境检测与依赖管理

### 2.1 `src/judge/env.rs`（Rust 检测 g++/python/java）

```rust
// src/judge/env.rs
use std::process::Command;
use serde::Serialize;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EnvStatus {
    pub gpp: bool,
    pub python: bool,
    pub java: bool,
    pub gpp_path: Option<String>,
    pub python_path: Option<String>,
    pub java_path: Option<String>,
}

/// 依次尝试候选命令名，返回首个能成功执行的路径。
fn which(candidates: &[&str], arg: &str) -> Option<String> {
    for c in candidates {
        if let Ok(out) = Command::new(c).arg(arg).output() {
            if out.status.success() {
                return Some((*c).to_string());
            }
        }
    }
    None
}

/// Tauri command：检测编译器是否就绪。
#[tauri::command]
pub fn check_environment() -> EnvStatus {
    let gpp = which(&["g++.exe", "g++"], "--version");
    let python = which(&["python.exe", "python3.exe", "python"], "--version");
    let java = which(&["java.exe", "java"], "-version");
    EnvStatus {
        gpp: gpp.is_some(),
        python: python.is_some(),
        java: java.is_some(),
        gpp_path: gpp,
        python_path: python,
        java_path: java,
    }
}
```

### 2.2 便携编译器打包目录结构（推荐，避免强依赖用户环境）

```
src-tauri/bin/
├── go-judge-x86_64-pc-windows-msvc.exe
└── tools/                      # 便携工具链，随包分发
    ├── mingw64/                # 便携 g++/gcc（如 winlibs 版）
    │   └── bin/g++.exe
    ├── python/                 # 嵌入式 Python（python-3.12-embed-amd64）
    │   └── python.exe
    └── jdk/                    # 便携 JDK（Adoptium / Liberica）
        └── bin/java.exe
```

运行时优先用便携路径，找不到再回退系统 PATH：
```rust
// 在 client.rs 构造 Payload 时解析
fn resolve_tools(resource_dir: &std::path::Path) -> Tools {
    let tools = resource_dir.join("bin/tools");
    Tools {
        gpp: tools.join("mingw64/bin/g++.exe"),
        python: tools.join("python/python.exe"),
        java: tools.join("jdk/bin/java.exe"),
    }
}
```
> 把绝对路径直接写进 `CmdSpec.args` 与 `env`（如 `PATH=...`），用户无需预装任何编译器。

### 2.3 前端引导（TS，Vue/React 通用）

```typescript
// frontend/src/lib/env.ts
import { invoke } from "@tauri-apps/api/core";

type EnvStatus = {
  gpp: boolean; python: boolean; java: boolean;
  gppPath?: string; pythonPath?: string; javaPath?: string;
};

export async function ensureEnvironment(): Promise<boolean> {
  const env = (await invoke("check_environment")) as EnvStatus;
  const missing: string[] = [];
  if (!env.gpp) missing.push("C++ 编译器 (g++)");
  if (!env.python) missing.push("Python");
  if (!env.java) missing.push("Java (JDK)");

  if (missing.length === 0) return true;

  // 优雅引导：弹窗说明缺失项 + 两种解决路径
  showMissingModal(missing, {
    portable: "Nex 已内置便携编译器，将在设置中自动启用（推荐）",
    manual: "或自行安装：g++ (MinGW-w64) / Python 3.12 / JDK 17，并加入 PATH",
  });
  return false; // 调用方据此禁用对应语言的「提交」按钮
}
```

> 弹窗建议：列出缺失语言 + 「已内置便携版（自动启用）」勾选项 + 「我想自己装」折叠说明。若走便携版，前端不需要再做任何事（Rust 端用 `resolve_tools` 的绝对路径）。

---

## 模块 3：API 封装与高级判题请求

### 3.1 `src/judge/client.rs`（reqwest 封装 + Payload 类型 + 判定）

```rust
// src/judge/client.rs
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

// ---------- Payload 类型（字段名与 go-judge REST 对齐） ----------

#[derive(Serialize, Debug, Clone)]
pub struct FileSpec {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>, // 输入内容（base64 或明文由调用方定）
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>, // 命名输出：stdout / stderr
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max: Option<u32>, // 输出上限字节（防输出洪水）
}

/// files 数组按 fd 顺序：[stdin, stdout, stderr]，用 Option 表示 null（不捕获/继承）。
#[derive(Serialize, Debug, Clone)]
pub struct CmdSpec {
    pub args: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub files: Option<Vec<Option<FileSpec>>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cpu_limit: Option<u64>, // 纳秒
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_limit: Option<u64>, // 字节
    #[serde(skip_serializing_if = "Option::is_none")]
    pub proc_limit: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub copy_in: Option<HashMap<String, CopyIn>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub copy_out_cached: Option<Vec<String>>, // ★ 编译产物缓存成 fileId
}

#[derive(Serialize, Debug, Clone)]
pub struct CopyIn {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file_id: Option<String>, // ★ 引用上一步 copyOutCached 产出的 fileId
}

#[derive(Serialize, Debug)]
pub struct RunRequest {
    pub cmd: Vec<CmdSpec>,
}

// ---------- 响应类型 ----------

#[derive(Deserialize, Debug)]
pub struct CmdResult {
    pub status: String, // "Accepted" | "Time Limit Exceeded" | "Memory Limit Exceeded" | ...
    #[serde(default)]
    pub exit_status: Option<i32>,
    pub time: u64,   // ns
    pub memory: u64, // bytes
    #[serde(default)]
    pub files: Option<Vec<Option<String>>>, // 与请求 files 对应，内容为 base64
}

#[derive(Deserialize, Debug)]
pub struct RunResponse {
    #[serde(default)]
    pub run: Option<Vec<CmdResult>>, // cmd 为数组时，每项对应一个结果
    #[serde(default)]
    pub file_ids: Option<HashMap<String, String>>, // copyOutCached 产出的 id
}

// ---------- 给前端的统一结果 ----------

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JudgeOutput {
    pub verdict: String, // Accepted | CompileError | RuntimeError | TimeLimitExceeded | ...
    pub stdout: String,
    pub stderr: String,
    pub time_ms: f64,
    pub memory_kb: u64,
    pub message: Option<String>, // 编译错误详情等
}

pub struct JudgeClient {
    base: String,
    http: reqwest::Client,
}

impl JudgeClient {
    pub fn new(base: String) -> Self {
        Self {
            base,
            http: reqwest::Client::new(),
        }
    }

    pub async fn run(&self, req: &RunRequest) -> anyhow::Result<RunResponse> {
        let resp = self
            .http
            .post(format!("{}run", self.base))
            .json(req)
            .send()
            .await?
            .error_for_status()?;
        Ok(resp.json().await?)
    }
}

// ---------- 判题判定（CE / RE / TLE / MLE 映射） ----------

/// base64 解码（go-judge 的 files.content 是 base64）。
fn b64(s: &str) -> String {
    use base64::{engine::general_purpose::STANDARD, Engine};
    STANDARD
        .decode(s)
        .map(|b| String::from_utf8_lossy(&b).into_owned())
        .unwrap_or_else(|_| s.to_string())
}

fn fd(files: &Option<Vec<Option<String>>>, i: usize) -> String {
    files
        .as_ref()
        .and_then(|f| f.get(i).cloned().flatten())
        .map(|c| b64(&c))
        .unwrap_or_default()
}

/// 把 go-judge 的状态字符串映射成前端可识别的 verdict。
fn map_status(s: &str) -> &'static str {
    match s {
        "Accepted" => "Accepted",
        "Time Limit Exceeded" => "TimeLimitExceeded",
        "Memory Limit Exceeded" | "Out Of Memory" => "MemoryLimitExceeded",
        "Output Limit Exceeded" => "OutputLimitExceeded",
        "Illegal System Call" => "IllegalSystemCall",
        "Non Zero Exit Status" | "Runtime Error" => "RuntimeError",
        _ => "Other",
    }
}
```

### 3.2 C++ 高级 Payload（编译一次 + `copyOutCached` 复用，跑多组测试）

```rust
// 接 client.rs
impl JudgeClient {
    /// 编译一次（copyOutCached 拿 a.exe 的 fileId），失败返回编译错误；
    /// 成功则对每组 stdin 跑一次 copyIn fileId 的执行。
    pub async fn judge_cpp_multi(
        &self,
        code: &str,
        tests: &[String],
        gpp: &str,
    ) -> anyhow::Result<Vec<JudgeOutput>> {
        let limits = CmdSpec {
            cpu_limit: Some(10_000_000_000), // 10s CPU
            memory_limit: Some(256 << 20),   // 256MB
            proc_limit: Some(8),
            ..Default::default()
        };

        // 第 1 步：编译，缓存产物
        let compile = RunRequest {
            cmd: vec![CmdSpec {
                args: vec![gpp.into(), "-O2".into(), "-o".into(), "a.exe".into(), "main.cpp".into()],
                env: Some(vec![format!("PATH={}", std::path::Path::new(gpp).parent().unwrap().display())]),
                files: Some(vec![
                    None,
                    Some(FileSpec { name: Some("stdout".into()), max: Some(10240), ..Default::default() }),
                    Some(FileSpec { name: Some("stderr".into()), max: Some(10240), ..Default::default() }),
                ]),
                copy_in: Some(HashMap::from([(
                    "main.cpp".into(),
                    CopyIn { content: Some(code.into()), file_id: None },
                )])),
                copy_out_cached: Some(vec!["a.exe".into()]),
                ..limits.clone()
            }],
        };
        let compiled = self.run(&compile).await?;
        let c = compiled.run.as_ref().unwrap()[0].clone();
        if c.status != "Accepted" {
            // ★ 编译错误（CE）
            return Ok(vec![JudgeOutput {
                verdict: "CompileError".into(),
                stdout: fd(&c.files, 1),
                stderr: fd(&c.files, 2),
                time_ms: 0.0,
                memory_kb: 0,
                message: Some(fd(&c.files, 2)),
            }]);
        }
        let exe_id = compiled.file_ids.unwrap().get("a.exe").cloned().unwrap();

        // 第 2 步：每组测试复用 fileId（避免重复编译）
        let mut out = Vec::new();
        for input in tests {
            let run = RunRequest {
                cmd: vec![CmdSpec {
                    args: vec!["./a.exe".into()],
                    env: Some(vec![format!("PATH={}", std::path::Path::new(gpp).parent().unwrap().display())]),
                    files: Some(vec![
                        Some(FileSpec { content: Some(input.clone()), ..Default::default() }), // fd0 = 测试输入
                        Some(FileSpec { name: Some("stdout".into()), max: Some(10240), ..Default::default() }),
                        Some(FileSpec { name: Some("stderr".into()), max: Some(10240), ..Default::default() }),
                    ]),
                    copy_in: Some(HashMap::from([(
                        "a.exe".into(),
                        CopyIn { content: None, file_id: Some(exe_id.clone()) },
                    )])),
                    ..limits.clone()
                }],
            };
            let r = self.run(&run).await?;
            let e = &r.run.as_ref().unwrap()[0];
            out.push(JudgeOutput {
                verdict: map_status(&e.status).into(),
                stdout: fd(&e.files, 1),
                stderr: fd(&e.files, 2),
                time_ms: e.time as f64 / 1e6,
                memory_kb: e.memory / 1024,
                message: None,
            });
        }
        Ok(out)
    }
}
```

### 3.3 Python Payload（无需编译，单次 cmd）

```rust
impl JudgeClient {
    pub async fn judge_python(
        &self,
        code: &str,
        input: &str,
        python: &str,
    ) -> anyhow::Result<JudgeOutput> {
        let run = RunRequest {
            cmd: vec![CmdSpec {
                args: vec![python.into(), "main.py".into()],
                files: Some(vec![
                    Some(FileSpec { content: Some(input.into()), ..Default::default() }),
                    Some(FileSpec { name: Some("stdout".into()), max: Some(10240), ..Default::default() }),
                    Some(FileSpec { name: Some("stderr".into()), max: Some(10240), ..Default::default() }),
                ]),
                copy_in: Some(HashMap::from([(
                    "main.py".into(),
                    CopyIn { content: Some(code.into()), file_id: None },
                )])),
                cpu_limit: Some(5_000_000_000),
                memory_limit: Some(256 << 20),
                proc_limit: Some(8),
                ..Default::default()
            }],
        };
        let r = self.run(&run).await?;
        let e = &r.run.as_ref().unwrap()[0];
        Ok(JudgeOutput {
            verdict: map_status(&e.status).into(),
            stdout: fd(&e.files, 1),
            stderr: fd(&e.files, 2),
            time_ms: e.time as f64 / 1e6,
            memory_kb: e.memory / 1024,
            message: None,
        })
    }
}
```

### 3.4 `src/commands.rs`（暴露给前端的命令 + 看门狗）

```rust
// src/commands.rs
use crate::judge::client::{JudgeClient, JudgeOutput};
use crate::judge::manager::JudgeManager;
use serde::Serialize;
use std::sync::Arc;
use tauri::State;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct JudgeResult {
    pub ok: bool,
    pub outputs: Option<Vec<JudgeOutput>>,
    pub error: Option<String>,
}

#[tauri::command]
pub async fn judge_cpp(
    manager: State<'_, Arc<JudgeManager>>,
    code: String,
    tests: Vec<String>,
    gpp: String,
) -> JudgeResult {
    let url = manager.url();
    if url.is_empty() {
        return JudgeResult { ok: false, outputs: None, error: Some("判题引擎尚未就绪".into()) };
    }
    let client = JudgeClient::new(url);
    // ★ 模块4 看门狗：5s 超时（go-judge 的 cpuLimit 算的是 CPU 时间，防不住 sleep/死循环）
    match tokio::time::timeout(std::time::Duration::from_secs(5), client.judge_cpp_multi(&code, &tests, &gpp)).await {
        Ok(Ok(out)) => JudgeResult { ok: true, outputs: Some(out), error: None },
        Ok(Err(e)) => JudgeResult { ok: false, outputs: None, error: Some(format!("判题失败: {e}")) },
        Err(_) => {
            // 超时：强制杀掉 go-judge 进程树（含卡死沙箱），supervisor 会自动重启
            manager.kill_current();
            JudgeResult { ok: false, outputs: None, error: Some("判题超时（疑似死循环/sleep），已强制终止沙箱".into()) }
        }
    }
}

#[tauri::command]
pub async fn judge_python(
    manager: State<'_, Arc<JudgeManager>>,
    code: String,
    input: String,
    python: String,
) -> JudgeResult {
    let url = manager.url();
    if url.is_empty() {
        return JudgeResult { ok: false, outputs: None, error: Some("判题引擎尚未就绪".into()) };
    }
    let client = JudgeClient::new(url);
    match tokio::time::timeout(std::time::Duration::from_secs(5), client.judge_python(&code, &input, &python)).await {
        Ok(Ok(out)) => JudgeResult { ok: true, outputs: Some(vec![out]), error: None },
        Ok(Err(e)) => JudgeResult { ok: false, outputs: None, error: Some(format!("判题失败: {e}")) },
        Err(_) => {
            manager.kill_current();
            JudgeResult { ok: false, outputs: None, error: Some("判题超时（疑似死循环/sleep），已强制终止沙箱".into()) }
        }
    }
}
```

---

## 模块 4：看门狗与安全防护

### 4.1 超时控制（已在 3.4 命令里用 `tokio::time::timeout` 实现）

- 判题命令包在 `tokio::time::timeout(Duration::from_secs(5), ...)` 里。
- 超时分支调用 `manager.kill_current()`：按 PID `taskkill /F /T` 杀整棵进程树（go-judge + winc 沙箱 + 卡死的 `a.exe`）。
- supervisor 线程的 `wait()` 随即返回，自动重启 go-judge（端口不变或重探测）。
- **升级路径（多用户/高并发）**：改用 go-judge 的 **WebSocket `/ws/run`**——直接 drop 连接即可取消该次运行并杀沙箱，无需重启整个引擎。当前单用户本机场景用 tree-kill 足够。

### 4.2 Windows Defender 排除项（`src/judge/defender.rs`）

go-judge 在沙箱里生成/编译 `a.exe`，Defender 实时扫描可能误杀或拖慢。两种做法：

**(A) Rust 运行时尝试加排除（需管理员；失败则提示用户）：**
```rust
// src/judge/defender.rs
#[cfg(windows)]
pub fn add_defender_exclusion(dir: &std::path::Path) -> bool {
    let ps = format!("Add-MpPreference -ExclusionPath '{}'", dir.display());
    std::process::Command::new("powershell")
        .args(["-Command", &ps])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}
```
> 调用时机：App 首次启动时对 `resource_dir/bin` 与沙箱临时目录调一次；返回 false 时在前端提示「请以管理员身份运行一次以添加杀软排除」。

**(B) 安装脚本（推荐，在 NSIS/WiX 安装阶段以管理员权限加，最稳）：**
```nsis
; NSIS 片段（安装时管理员权限执行）
ExecWait 'powershell -Command "Add-MpPreference -ExclusionPath '\''$INSTDIR\resources\bin'\''"'
ExecWait 'powershell -Command "Add-MpPreference -ExclusionPath '\''$INSTDIR\resources\bin\tools'\''"'
```
> 也可对生成的 `*.exe` 加 `Add-MpPreference -ExclusionProcess`，但目录级排除更省事。

### 4.3 强制禁用网络（Payload 之外，启动参数层）

- **全局禁用**：`spawn_once` 已传 `--enable-network=false`（见模块1.2）。go-judge 的网络开关是**全局启动参数**，不是每请求字段——设 false 后所有沙箱都无法出网。
- 注意 winc 的网络隔离是**实验性、不彻底**的：仍可能在特定情况下漏网。因此：
  - 沙箱内**绝不放置任何密钥/凭证**；
  - 面向**不可信公开用户**的判题，生产环境仍应回退到 Linux 服务端（winc 仅用于本机/个人学习）。

---

## 5. Cargo.toml 依赖

```toml
[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
reqwest = { version = "0.12", features = ["json"] }
anyhow = "1"
base64 = "0.22"

[target.'cfg(unix)'.dependencies]
libc = "0.2"
```

---

## 6. 落地顺序

1. `Cargo.toml` + `build.rs` + `tauri.conf.json`（externalBin）+ 放入 `bin/go-judge-<triple>.exe`。
2. `judge/manager.rs` → 端口/重启/杀树；`lib.rs` 接入 setup/ExitRequested。
3. `judge/env.rs` + `commands.rs::check_environment` → 前端引导。
4. `judge/client.rs` + `commands.rs::judge_*` → reqwest 封装 + copyOutCached + verdict 映射。
5. `commands.rs` 包 `tokio::time::timeout` 看门狗 + `manager.kill_current()`。
6. `judge/defender.rs` 加排除项（安装脚本为主，运行时兜底）。
7. 便携工具链放进 `bin/tools/`，`resolve_tools` 优先用绝对路径。
