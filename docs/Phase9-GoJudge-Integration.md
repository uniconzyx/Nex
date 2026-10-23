# Nex v2（原生脱离 Docker）— go-judge 集成方案设计

> 目标：用 **go-judge（winc 后端，JobObject + Restricted Token）** 替代 Judge0，作为 Tauri 桌面端的 Sidecar 进程，保住「在线判题 / 代码执行」核心功能。
> 适用框架：**Tauri v2（Rust 宿主 + React/TS 前端）**。数据存储走 SQLite + 本地文件系统（不在本文范围）。

---

## 0. 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  Nex 桌面端 (Tauri)                                            │
│                                                               │
│  ┌──────────────┐         HTTP (localhost)      ┌──────────┐  │
│  │ React/TS 前端 │ ───────────────────────────────▶│ go-judge │  │
│  └──────────────┘   POST /run :127.0.0.1:PORT     │ (Sidecar)│  │
│         │                  ▲                      │  winc    │  │
│         │ Tauri command    │ judge URL            │ 沙箱      │  │
│  ┌──────▼──────────────────┴──────────────┐       └──────────┘  │
│  │ Rust 宿主 (main.rs)                      │                    │
│  │  - JudgeManager：拉起/重启/清理 go-judge  │                    │
│  │  - FastAPI 宿主（可选，管内容/进度/AI）   │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

关键点：
- **go-judge 由 Rust 宿主直接 `std::process::Command` 拉起**（不用 Tauri 内置 sidecar，因为要自己控端口、崩溃重启、进程树清理）。
- 前端 **直连** go-judge（`127.0.0.1:PORT`），不走 Tauri 命令转发，延迟最低。
- 端口由宿主在启动时探测空闲端口并传给 go-judge，再通过 Tauri command 暴露给前端。

---

## 1. 进程生命周期管理（Sidecar 模式）

### 1.1 二进制放置与路径解析

`tauri.conf.json` 中声明外部二进制（Tauri 会自动加 target-triple 后缀）：

```json
{
  "bundle": {
    "externalBin": ["bin/go-judge"]
  }
}
```

Rust 端解析真实路径（Tauri v2 API）：

```rust
use tauri::Manager;
use std::path::PathBuf;

fn resolve_gojudge_path(app: &tauri::AppHandle) -> PathBuf {
    // Tauri 把 externalBin 放到 resources 目录，并按平台重命名
    // 例如 windows 上为 go-judge-x86_64-pc-windows-msvc.exe
    let dir = app.path().resource_dir().expect("resource_dir");
    // windows 下需补后缀；这里用运行时探测更稳
    let candidates = [
        dir.join("bin/go-judge-x86_64-pc-windows-msvc.exe"),
        dir.join("bin/go-judge.exe"),
    ];
    candidates.into_iter().find(|p| p.exists()).expect("go-judge 二进制缺失")
}
```

### 1.2 空闲端口探测 + 启动 + 就绪探测

```rust
use std::io;
use std::net::{TcpListener, TcpStream};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

/// 探测一个当前空闲的本地端口（TOCTOU 风险，靠就绪重试兜底）
fn find_free_port() -> io::Result<u16> {
    let l = TcpListener::bind("127.0.0.1:0")?;
    let port = l.local_addr()?.port();
    drop(l); // 立即释放，交给 go-judge 绑定
    Ok(port)
}

/// 拉起一次 go-judge（winc 后端在 Windows 上自动启用，无需额外 flag）
fn spawn_once(binary: &std::path::Path, port: u16) -> io::Result<Child> {
    Command::new(binary)
        .args([
            "--addr", &format!("127.0.0.1:{port}"),
            "--enable-network=false", // 关闭沙箱网络（见 §4 坑点）
            "--par", "4",             // 并发沙箱数，按机器核数调
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
}

/// HTTP 就绪探测：发一个无害的 /run 看是否 200（不引第三方依赖，手写最小 HTTP）
fn wait_ready(port: u16, timeout: Duration) -> bool {
    let start = Instant::now();
    let body = r#"{"cmd":[{"args":["cmd","/c","echo","ok"]}]}"#;
    let req = format!(
        "POST /run HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n\
         Content-Type: application/json\r\nContent-Length: {}\r\n\
         Connection: close\r\n\r\n{}",
        body.len(), body
    );
    use std::io::{Read, Write};
    while start.elapsed() < timeout {
        if let Ok(mut s) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = s.write_all(req.as_bytes());
            let mut buf = [0u8; 256];
            if let Ok(n) = s.read(&mut buf) {
                let head = String::from_utf8_lossy(&buf[..n]);
                if head.contains("200") {
                    return true;
                }
            }
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}
```

### 1.3 管理器：崩溃自动重启 + 退出清理

```rust
pub struct JudgeManager {
    inner: Mutex<Option<Child>>,
    binary: PathBuf,
    port: AtomicU16,
    stop: AtomicBool,
}

impl JudgeManager {
    pub fn new(binary: PathBuf) -> Arc<Self> {
        Arc::new(Self {
            inner: Mutex::new(None),
            binary,
            port: AtomicU16::new(0),
            stop: AtomicBool::new(false),
        })
    }

    /// 启动并进入守护循环（在独立线程里监督子进程）
    pub fn launch(self: &Arc<Self>) {
        self.respawn(); // 首次拉起
        let m = self.clone();
        thread::spawn(move || m.supervisor_loop());
    }

    fn respawn(&self) {
        for _ in 0..3 {
            let port = match find_free_port() {
                Ok(p) => p,
                Err(_) => { thread::sleep(Duration::from_millis(300)); continue; }
            };
            match spawn_once(&self.binary, port) {
                Ok(child) => {
                    if wait_ready(port, Duration::from_secs(10)) {
                        *self.inner.lock().unwrap() = Some(child);
                        self.port.store(port, Ordering::SeqCst);
                        return;
                    }
                    // 起得来但没就绪（端口被抢）：杀掉重来
                    kill_tree(&child);
                }
                Err(e) => eprintln!("go-judge 拉起失败: {e}"),
            }
            thread::sleep(Duration::from_millis(300));
        }
        eprintln!("go-judge 多次重试仍失败，判题功能不可用");
    }

    /// 监督循环：子进程退出则带退避重启；stop 置位则退出
    fn supervisor_loop(self: Arc<Self>) {
        loop {
            if self.stop.load(Ordering::Acquire) {
                break;
            }
            // 等待当前子进程结束（reap，防 Unix 僵尸）
            let exited = {
                let mut g = self.inner.lock().unwrap();
                if let Some(mut c) = g.take() {
                    drop(g);
                    c.wait().ok();
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
            thread::sleep(Duration::from_millis(500)); // 退避，避免崩溃循环打满 CPU
            self.respawn();
        }
    }

    /// 应用退出时调用：置位 stop + 杀进程树（防僵尸/孤儿）
    pub fn stop(&self) {
        self.stop.store(true, Ordering::Release);
        if let Some(mut c) = self.inner.lock().unwrap().take() {
            kill_tree(&c);
        }
    }

    pub fn url(&self) -> String {
        format!("http://127.0.0.1:{}/", self.port.load(Ordering::SeqCst))
    }
}

/// 杀进程树：Windows 用 taskkill /T；winc 本身用 JobObject，杀掉 go-judge 即连带清掉沙箱子进程
#[cfg(windows)]
fn kill_tree(child: &mut Child) {
    let pid = child.id();
    let _ = Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .output();
    let _ = child.kill();
}

/// Unix：需用进程组才能杀树（spawn 时 pre_exec 里 setsid）
#[cfg(unix)]
fn kill_tree(child: &mut Child) {
    unsafe {
        libc::kill(-(child.id() as i32), libc::SIGKILL);
    }
    let _ = child.kill();
}
```

### 1.4 接入 Tauri 生命周期

```rust
// main.rs
struct JudgeState(Arc<JudgeManager>);

#[tauri::command]
fn get_judge_url(state: tauri::State<JudgeState>) -> String {
    state.0.url()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let binary = resolve_gojudge_path(&app_handle_placeholder()); // 见 1.1
    let manager = JudgeManager::new(binary);
    manager.launch();
    let mgr = manager.clone();

    tauri::Builder::default()
        .manage(JudgeState(manager))
        .invoke_handler(tauri::generate_handler![get_judge_url])
        .build(tauri::generate_context!())
        .expect("build error")
        .run(move |_app, event| {
            // 应用退出请求：清理 sidecar，杜绝僵尸进程
            if let tauri::RunEvent::ExitRequested { .. } = event {
                mgr.stop();
            }
        });
}
```

> 前端启动后先 `invoke('get_judge_url')` 拿到地址；若拿到空串说明 sidecar 还没就绪，UI 显示「判题引擎启动中…」并轮询。

---

## 2. API 通信与请求封装（TypeScript）

### 2.1 类型与客户端

```typescript
// judgeClient.ts
export interface FileSpec {
  content?: string;   // 输入内容（base64 由调用方决定；go-judge 接受明文或 base64）
  name?: string;      // 命名输出，如 "stdout"
  max?: number;       // 输出上限字节
}

export interface CmdSpec {
  args: string[];
  env?: string[];
  // files 数组按 fd 顺序： [stdin, stdout, stderr]
  // 用 null 表示不捕获/继承
  files?: (FileSpec | null)[];
  cpuLimit?: number;     // ns
  memoryLimit?: number;  // bytes
  procLimit?: number;    // 进程数上限
  copyIn?: Record<string, { content?: string; fileId?: string }>;
  copyOut?: string[];
  copyOutCached?: string[];
}

export interface RunRequest {
  cmd: CmdSpec[];
  // pipe?: boolean;
}

export interface CmdResult {
  status: string;   // "Accepted" | "Time Limit Exceeded" | "Memory Limit Exceeded"
                     // | "Non Zero Exit Status" | "Out Of Memory" | "Illegal System Call"
  exitStatus?: number;
  time: number;     // ns
  memory: number;   // bytes
  files?: (string | null)[]; // 与请求 files 对应，内容为 base64
  fileError?: (string | null)[];
}

export interface RunResponse {
  run?: CmdResult[];        // cmd 为数组时，每项对应一个结果
  status?: string;
  time?: number;
  memory?: number;
  fileIds?: Record<string, string>; // copyOutCached 产出的文件 id，供后续 copyIn 引用
}

export class GoJudgeClient {
  constructor(private base: string) {}

  async run(req: RunRequest): Promise<RunResponse> {
    const r = await fetch(`${this.base}run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!r.ok) throw new Error(`go-judge HTTP ${r.status}`);
    return (await r.json()) as RunResponse;
  }

  /** go-judge 返回的 files.content 是 base64，统一解码 */
  static b64dec(s: string): string {
    return decodeURIComponent(escape(atob(s)));
  }
}
```

### 2.2 封装用户代码 + 测试数据（Payload 构造）

判题 = 编译 + 运行两步。go-judge 的 `/run` 中 **`cmd` 数组里的命令共享同一沙箱文件系统、顺序执行**——所以编译产物能直接被下一步运行，无需文件搬运（最简洁路径，见 §3）。

```typescript
// 通用：单测试用例，编译+运行一次性提交（共享 fs）
async function judgeCpp(
  client: GoJudgeClient,
  code: string,
  stdin: string,
  limits = { cpu: 1e10, mem: 256 << 20, proc: 8 }
): Promise<CmdResult> {
  const res = await client.run({
    cmd: [
      {
        args: ["g++.exe", "-O2", "-o", "a.exe", "main.cpp"],
        env: ["PATH=C:/mingw64/bin"],
        // fd0 不喂（null），fd1/fd2 捕获，max 限幅
        files: [null, { name: "stdout", max: 10240 }, { name: "stderr", max: 10240 }],
        copyIn: { "main.cpp": { content: code } },
        cpuLimit: limits.cpu,
        memoryLimit: limits.mem,
        procLimit: limits.proc,
      },
      {
        args: ["./a.exe"],
        env: ["PATH=C:/mingw64/bin"],
        files: [
          { content: stdin },                 // fd0 = 测试输入
          { name: "stdout", max: 10240 },     // fd1
          { name: "stderr", max: 10240 },     // fd2
        ],
        cpuLimit: limits.cpu,
        memoryLimit: limits.mem,
        procLimit: limits.proc,
      },
    ],
  });
  // 取第二步（运行）的结果
  const run = res.run?.[1];
  if (!run) throw new Error("判题响应缺少运行结果");
  return run;
}

// 取输出文本
const out = GoJudgeClient.b64dec(run.files?.[1] ?? "");
const err = GoJudgeClient.b64dec(run.files?.[2] ?? "");
```

### 2.3 标准 Payload 示例（C++，含 copyIn/copyOut/procLimit/cpuLimit/memoryLimit）

```json
{
  "cmd": [
    {
      "args": ["g++.exe", "-O2", "-o", "a.exe", "main.cpp"],
      "env": ["PATH=C:/mingw64/bin"],
      "files": [null, { "name": "stdout", "max": 10240 }, { "name": "stderr", "max": 10240 }],
      "copyIn": { "main.cpp": { "content": "int main(){return 0;}" } },
      "cpuLimit": 10000000000,
      "memoryLimit": 268435456,
      "procLimit": 8
    },
    {
      "args": ["./a.exe"],
      "env": ["PATH=C:/mingw64/bin"],
      "files": [
        { "content": "1 2 3\n" },
        { "name": "stdout", "max": 10240 },
        { "name": "stderr", "max": 10240 }
      ],
      "cpuLimit": 10000000000,
      "memoryLimit": 268435456,
      "procLimit": 8
    }
  ]
}
```

> 字段含义：`cpuLimit` 单位 **纳秒**（1e10 = 10s CPU 时间）；`memoryLimit` 单位 **字节**（256MB = 268435456）；`procLimit` 沙箱内允许的**进程/线程总数上限**（winc 用 JobObject 强制）；`copyIn` 把用户源码注入沙箱；`files` 的 `max` 防止输出炸内存。

---

## 3. 编译与执行逻辑处理

### 3.1 两种组织方式

**(A) 单测试用例：一次 `/run`，多 `cmd` 共享 fs（推荐，最简单）**

如 §2.2：cmd[0] 编译出 `a.exe`，cmd[1] 直接 `./a.exe`。因为同一 `/run` 的所有命令在**同一个沙箱容器**里、文件系统共享，编译产物天然可见，无需 `copyOut/CopyIn`。

**(B) 多测试用例：编译一次 + 复用「缓存文件」**

同一份代码要跑 N 组测试数据时，重复编译浪费。用 `copyOutCached` 把编译产物缓存成 fileId，后续每次运行只 `copyIn` 这个 fileId：

```typescript
// 1) 编译并缓存
const compiled = await client.run({
  cmd: [{
    args: ["g++.exe", "-O2", "-o", "a.exe", "main.cpp"],
    env: ["PATH=C:/mingw64/bin"],
    copyIn: { "main.cpp": { content } },
    copyOutCached: ["a.exe"],          // 关键：缓存到 fileId
    cpuLimit: 1e10, memoryLimit: 256 << 20, procLimit: 8,
  }],
});
const exeId = compiled.fileIds?.["a.exe"]; // 拿到缓存 id

// 2) 每组测试一个 /run，copyIn 复用
for (const input of testCases) {
  const r = await client.run({
    cmd: [{
      args: ["./a.exe"],
      env: ["PATH=C:/mingw64/bin"],
      copyIn: { "a.exe": { fileId: exeId } },
      files: [{ content: input }, { name: "stdout", max: 10240 }, { name: "stderr", max: 10240 }],
      cpuLimit: 1e10, memoryLimit: 256 << 20, procLimit: 8,
    }],
  });
  // r.run[0] 即该组结果
}
```

> 注意：`copyIn` 引用 `fileId` 只能跨**独立 `/run` 请求**使用；同一请求内 cmd 之间靠共享 fs，不用 fileId。

### 3.2 各语言编译/运行命令

| 语言 | 编译 cmd | 运行 cmd | 备注 |
|---|---|---|---|
| C++ | `g++.exe -O2 -o a.exe main.cpp` | `./a.exe` | MinGW 路径进 `env` |
| C | `gcc.exe -O2 -o a.exe main.c` | `./a.exe` | 同上 |
| Java | `javac.exe Main.java` | `java.exe Main` | `memoryLimit` 给足（JVM + `-Xmx`） |
| Python | 无需编译 | `python.exe main.py` | `copyIn: {"main.py": {content}}` |
| Go | `go.exe build -o a.exe main.go` | `./a.exe` | — |

Java 示例（compile + run 同一次请求）：

```typescript
const res = await client.run({
  cmd: [
    { args: ["javac.exe", "Main.java"], env: ["PATH=C:/jdk/bin"],
      copyIn: { "Main.java": { content } },
      files: [null, {name:"stdout",max:10240},{name:"stderr",max:10240}],
      cpuLimit: 1e10, memoryLimit: 512<<20, procLimit: 16 },
    { args: ["java.exe", "Main"], env: ["PATH=C:/jdk/bin"],
      files: [{content: stdin},{name:"stdout",max:10240},{name:"stderr",max:10240}],
      cpuLimit: 1e10, memoryLimit: 512<<20, procLimit: 16 },
  ],
});
```

### 3.3 输出与文件安全处理

- **输出一律经 `files[].max` 限幅**，超限 go-judge 截断，避免恶意巨量输出撑爆前端。
- 响应 `files[].content` 是 **base64**，前端 `atob` 后展示（见 §2.1 `b64dec`）。
- **绝不**把用户源码/输出写到宿主机的共享目录——所有 I/O 走 `copyIn`/`files`，由沙箱托管；go-judge 每次请求自动建/清临时目录。
- 判题结果（status/time/memory）直接来自响应，前端据此判定 AC / TLE / MLE / RE。

---

## 4. 坑点规避与安全建议（winc 实测向）

> winc 是 go-judge 的 **Windows 实验性后端**，基于 JobObject + Restricted Token。以下为已知点与规避手段。

### 4.1 winc 已知坑

1. **网络隔离不完善**：`--enable-network=false` 在 winc 下**不一定**能完全阻断网络访问（不像 Linux 的网络命名空间彻底）。
   - 规避：判题沙箱内**不要放任何密钥/凭证**；如面向不可信用户公开判题，**生产环境仍用 Linux 服务器**，winc 仅用于本机/个人学习场景。
   - 进阶：用 Windows 防火墙出站规则，对 go-judge 的低权限 Restricted Token 所在账户禁用出网。

2. **部分系统调用会失败/挂起**：winc 用 Restricted Token 降权，访问全局命名对象、网络共享、某些特权 API 会直接报错——属预期，不影响常规编译运行。

3. **`cpuLimit` 是 CPU 时间，不是墙钟时间**：`sleep(1000)` 不耗 CPU，**不会被 cpuLimit 杀掉**。
   - 规避：对单请求加**宿主级墙钟看门狗**——前端/后端对每次判题设硬超时（如 15s），超时直接杀掉该 `/run` 对应进程（或重启 sidecar）。

4. **fork/线程炸弹**：`procLimit` 限制进程数（winc 经 JobObject 强制），但**线程炸弹**不算进程。
   - 规避：`procLimit` 设紧（单线程题设 1，常规 8~16）；线程炸弹的 CPU 消耗由 `cpuLimit` 兜底。

5. **内存计量差异**：winc 的 `memoryLimit` 走 JobObject 提交内存上限；Java/Go 这类带运行时的语言要**显式给足**（Java 加 `-Xmx256m` 且 `memoryLimit ≥ 512MB`），否则误判 MLE。

6. **Anti-Cheat / Defender**：Windows Defender 可能误报 go-judge 或沙箱内生成的 `.exe`，导致冷启动慢甚至被杀。
   - 规避：对 go-judge 目录加 Windows Defender 排除项；生产分发时对二进制**代码签名**。

### 4.2 防恶意代码卡死宿主（硬性配置）

| 威胁 | 配置 | 机制 |
|---|---|---|
| 死循环（耗 CPU） | `cpuLimit` 10e9（10s CPU） + 宿主墙钟看门狗 15s | JobObject CPU 累计 + 超时强杀 |
| 内存爆炸 | `memoryLimit` 256~512MB | JobObject 提交内存上限 |
| fork 炸弹 | `procLimit` 8~16 | JobObject 进程数上限 |
| 输出洪水 | `files[].max` 10KB | 输出截断 |
| 网络外联 | `--enable-network=false` + 防火墙 | winc 降权 + 网络规则 |
| 文件逃逸 | `copyIn` key 校验（禁 `..`/绝对路径） | 沙箱根目录隔离 |
| 僵尸/孤儿进程 | 宿主 `stop()` 调 `taskkill /T` | 进程树清理 + JobObject 连带 |

### 4.3 运维与发布

- **架构匹配**：go-judge Windows 二进制需与宿主同架构（通常 amd64），跨架构要分别编译/分发。
- **并发上限**：`--par` 控制同时运行的沙箱数，按机器核数设（默认偏激进），避免多题并发压垮机器。
- **临时目录**：`--src-path` 指定到受控目录，监控其体积，防长时间高并发下临时文件堆积（go-judge 每请求清理，但极端情况下需兜底）。

---

## 5. 落地 checklist

- [ ] `go-judge.exe`（Windows amd64）放入 `src-tauri/bin/`，`tauri.conf.json` 配 `externalBin`。
- [ ] Rust 端实现 `JudgeManager`（端口探测 / 就绪探测 / 崩溃重启 / `stop` 清理）。
- [ ] `main.rs` 在 `setup` 拉起、`RunEvent::ExitRequested` 清理；暴露 `get_judge_url`。
- [ ] TS 端实现 `GoJudgeClient` + `judgeCpp/judgeJava/judgePy`，输出 base64 解码。
- [ ] 单测试用例走「一次 `/run` 多 cmd 共享 fs」；多测试用例走 `copyOutCached` + `copyIn`。
- [ ] 硬性 limits：`cpuLimit` + `memoryLimit` + `procLimit` + `files[].max` + 宿主墙钟看门狗。
- [ ] `--enable-network=false` + Defender 排除 + 代码签名。
- [ ] 面向不可信用户时，判题仍回退到 Linux 服务端（winc 仅本机/个人场景）。
