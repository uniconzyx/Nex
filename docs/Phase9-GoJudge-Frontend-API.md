# Nex v2 前后端对接文档（Tauri v2 + go-judge Sidecar）

> 适用范围：`src-tauri/` 工程（Rust 宿主 + go-judge Sidecar + WebSocket 取消服务）。
> 前端（Vue/React + TypeScript）通过两条通道与宿主通信：
> 1. **Tauri `invoke`** —— 命令式调用（判题、环境检测、状态查询）。
> 2. **WebSocket `ws://127.0.0.1:14520/ws/run`** —— 长连接判题，支持「客户端掉线即强杀沙箱」防僵尸。

---

## 一、Tauri `invoke` 命令列表

所有命令通过 `@tauri-apps/api/core` 的 `invoke()` 调用（Tauri v2 起从 `api/core` 导入，
不再是 v1 的 `api/tauri`）。返回结构为 JSON。

### 1. `judge` —— 单词判题（命令式，内部含墙钟看门狗）

```ts
import { invoke } from '@tauri-apps/api/core';

const verdict: Verdict = await invoke('judge', {
  lang: 'python',        // 'python' | 'cpp' | 'c++' | 'c' | 'java'
  code: 'print(6*7)',     // 用户提交的源码
  stdin: '3 5\n',         // 可选：测试输入
});
```

- 参数：`lang: string`、`code: string`、`stdin?: string`
- 返回：`Verdict`（见第三节）
- 超时行为：宿主侧有墙钟看门狗（默认 5s，`AppConfig.wall_timeout_secs`），死循环/sleep 会被强杀并返回 `wall_timeout`。
- ⚠️ **多测试用例不要循环调它**：C++/Java 每次调用都会重新编译。请用下面的 `judge-batch`。

### 2. `judge-batch` —— 批量判题（编译产物复用）

```ts
const verdicts: Verdict[] = await invoke('judge-batch', {
  lang: 'cpp',
  code: sourceCode,
  stdins: ['3 5\n', '10 20\n'],   // 与测试用例等长、同序
});
```

- 参数：`lang: string`、`code: string`、`stdins?: string[]`（省略或空数组时按「一条空 stdin」处理）
- 返回：`Verdict[]`，与 `stdins` **等长同序**
- C++/Java 首用例编译并 `copyOutCached` 出 `fileId`，后续用例复用，**整个批次只编译一次**
- 现成的前端封装见 `frontend/src/lib/GoJudgeClient.ts`（`submitCode()` 即走此命令）

### 3. `judge-ws-url` —— 取 WebSocket 判题地址

```ts
const url: string = await invoke('judge-ws-url');
// => "ws://127.0.0.1:14520/ws/run"
```

### 4. `check-environment` —— 编译器/运行时环境检测

```ts
const env: EnvReport = await invoke('check-environment');
```

`EnvReport` 结构（见 `environment.rs`）：

```ts
interface EnvReport {
  languages: { name: string; available: boolean; path: string | null; version: string | null }[];
  go_judge: boolean;          // go-judge 二进制是否就绪
  go_judge_path: string | null;
}
```

### 5. `get-status` —— 判题服务运行时状态

```ts
const status: JudgeStatus = await invoke('get-status');
```

`JudgeStatus` 结构（见 `sandbox.rs::status_json`）：

```ts
interface JudgeStatus {
  go_judge_available: boolean;  // go-judge 是否在跑
  mock_mode: boolean;           // 是否处于本地直跑降级模式
  port: number;                 // go-judge 实际监听端口（动态分配）
  pid: number;                  // go-judge 进程 PID（0 = 未启动）
  enable_network: boolean;      // 沙箱是否允许联网
}
```

前端据此决定是否弹「缺少编译器」引导弹窗（见第五节）。

### 4. `get-status` —— 运行时状态

```ts
const st: {
  go_judge_available: boolean;
  mock_mode: boolean;
  port: number;
  pid: number;
  enable_network: boolean;
} = await invoke('get-status');
```

---

## 二、WebSocket `/ws/run` 消息格式

> 端口固定 `14520`（见 `AppConfig.ws_port`，也在 `tauri.conf.json` 注释中标注）。
> 仅监听本机回环 `127.0.0.1`，不暴露到网络（安全性）。

### 连接

```ts
const ws = new WebSocket('ws://127.0.0.1:14520/ws/run');
```

### 发送（请求）—— `WsJudgeReq`

```json
{
  "lang": "python",
  "code": "while True:\n    pass",
  "stdin": "optional input"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `lang` | string | 同 `judge` 命令 |
| `code` | string | 用户源码 |
| `stdin` | string? | 测试输入，缺省视为空 |

### 接收（响应）—— `Verdict`（单条 Text 消息即结束标记）

服务端对**每个请求只回一条** `Verdict` JSON（请求→响应一一对应）。收到该消息即代表本次判题结束，**无需额外 end 标记**。

```json
{ "verdict": "accepted", "stdout": "42\n", "time_ms": 0, "memory_kb": 0 }
```

`verdict` 枚举（snake_case，见 `judge_client::Verdict`）：

| `verdict` 值 | 含义 | 附加字段 |
|---|---|---|
| `accepted` | 通过 | `stdout`, `time_ms`, `memory_kb` |
| `compile_error` | 编译失败 | `stderr` |
| `runtime_error` | 运行错误 | `stderr`, `signal?` |
| `time_limit_exceeded` | go-judge CPU 超时 | — |
| `memory_limit_exceeded` | 内存超限 | — |
| `output_limit_exceeded` | 输出超限 | — |
| `illegal_syscall` | winc 拦截了非法系统调用 | `msg` |
| `wall_timeout` | **宿主墙钟看门狗触发**（死循环/sleep，cpuLimit 防不住） | — |
| `mock` | 降级模式本地直跑回显 | `stdout` |

### 客户端掉线 = 取消

- 前端关闭 `WebSocket`（关页面 / 切走 / `ws.close()`）→ 服务端 `tokio::select!` 监测到 `reader.next() == None` → 立即 `kill_current()` 强杀正在运行的沙箱进程树，**防止死循环代码在后台继续跑**。
- 因此前端无需显式发「取消」消息；**直接关闭连接即可取消**。

---

## 三、前端类型定义（TypeScript 建议）

> 完整可复用版本见 `frontend/src/lib/GoJudgeClient.ts`（含 `GoJudgeClient` 类、
> `JudgeClientError` 友好错误、`mapVerdictToUi()` UI 映射），React 调用示例见
> `frontend/src/components/JudgePanel.tsx`。

```ts
export type Verdict =
  | { verdict: 'accepted'; stdout: string; time_ms: number; memory_kb: number }
  | { verdict: 'compile_error'; stderr: string }
  | { verdict: 'runtime_error'; stderr: string; signal: string | null }
  | { verdict: 'time_limit_exceeded' }
  | { verdict: 'memory_limit_exceeded' }
  | { verdict: 'output_limit_exceeded' }
  | { verdict: 'illegal_syscall'; msg: string }
  | { verdict: 'wall_timeout' }
  | { verdict: 'mock'; stdout: string };

export interface WsJudgeReq {
  lang: 'python' | 'cpp' | 'c++' | 'c' | 'java';
  code: string;
  stdin?: string;
}
```

> 注意 `Verdict` 是 Rust 侧 `#[serde(tag="verdict", rename_all="snake_case")] 的
> **内部契约**，字段保持 snake_case；这与 `payload.rs`（迁就 go-judge 线格式的
> camelCase）是两套命名，不要混。

---

## 四、前端前置条件与依赖

1. **端口**：`judge_ws_url` 动态获取，默认 `ws://127.0.0.1:14520/ws/run`。不要硬编码，从命令取。
   - ⚠️ **代理陷阱**：若开发期 Vite dev server / 系统设置了 HTTP 代理，浏览器可能把
     `ws://127.0.0.1:*` 也交给代理而导致连不上。请把 `127.0.0.1` 加进 `no_proxy`。
2. **依赖库**（前端）：
   - `@tauri-apps/api`（invoke 调用，v2 从 `@tauri-apps/api/core` 导入）
   - 原生 `WebSocket`（浏览器/Tauri webview 自带，无需额外包）
   - 见 `frontend/package.json`
3. **能力权限**（宿主 `capabilities/default.json`）：
   - 调用 5 个命令需 `core:default` + `allow-judge` / `allow-judge-batch` /
     `allow-judge-ws-url` / `allow-check-environment` / `allow-get-status`。
   - 这些是**应用自身权限**，在 `src-tauri/permissions/allow-<cmd>.toml` 中定义，
     capabilities 里用**裸名**引用（不带 `nex:` 前缀）。配少了运行时报 permission 缺失。
4. **go-judge 二进制**：宿主在 `resources/binaries/go-judge(.exe)` 寻找；缺失时自动降级为「本地直跑（mock）」——`invoke('judge')` 仍可用，只是走本地进程而非沙箱，且**无网络/资源硬隔离**。生产环境须随包分发 go-judge。
5. **编译器**：`python`/`g++`/`java` 需在 PATH（或打进 Tauri 便携工具链 `bin/tools/`），否则 `check_environment` 会报缺失并引导安装。
6. **局域网端口**（移动端判题，见第八节）：桌面端 Axum 服务监听 `0.0.0.0:8080`，
   需 Windows 防火墙放行；Android 需 `usesCleartextTraffic="true"`。
7. **前端工程**：`frontend/` 已配好 Vite（`npm install` → `npm run dev`，端口 1420），
   产物输出 `../dist`，与 `tauri.conf.json` 的 `frontendDist` 对齐。

---

## 五、前端引导弹窗建议（环境缺失时）

`check_environment()` 返回某语言 `available:false` 时：

- **Python**：引导安装 [python.org](https://www.python.org) 并勾选「Add to PATH」；或提示「将使用应用内置便携 Python」。
- **C++ (g++)**：引导安装 MinGW-w64 / MSYS2；或提示内置便携工具链。
- **Java**：引导安装 JDK 17+；或提示内置便携 JDK。
- **go-judge**：若 `go_judge:false`，提示「当前为本地直跑模式，在线判题沙箱未启用（重新安装完整版以启用）」。

> 弹窗应为「非阻塞提示 + 重试按钮」，不要让缺失编译器卡死整个判题入口；降级模式至少保证 Python 题可本地跑。

---

## 六、典型调用时序

```
前端                          Rust 宿主                      go-judge Sidecar
  │                              │                                │
  │── invoke('judge', …) ──────>│  judge()                       │
  │                              │── /run (REST) ───────────────>│  编译+运行
  │                              │<── Verdict ───────────────────│
  │<── Verdict ─────────────────│                                │
  │                              │   (墙钟看门狗 5s 超时则        │
  │                              │    kill_tree 强杀整棵树)        │
  │                                                              │
  │── WebSocket 连接 /ws/run ──>│  start_ws_server              │
  │── {lang,code,stdin} ───────>│  judge() ── /run ────────────>│
  │<── Verdict (Text) ──────────│<── Verdict ───────────────────│
  │  (收到即结束，无需 end 标记)  │                                │
  │── ws.close() ──────────────>│  reader=None → kill_current()  │  (强杀沙箱)
```

---

## 七、安全要点（前端须知）

- **网络隔离**：go-judge 以 `--enable-network=false` 全局启动，沙箱不可联网。但 winc 实验性、隔离不彻底，**不可信用户提交的代码仍应回退到 Linux 服务端判题**（架构上保留该分支）。
- **墙钟看门狗**是最后一道闸：go-judge 的 `cpuLimit` 只计 CPU 时间，防不住 `sleep`/死循环；宿主机 5s 超时后强杀进程树。
- **WebSocket 掉线即取消**，前端不用发取消指令。

---

## 八、局域网模式（移动端瘦客户端，2026-10 新增）

Android APK **不跑 go-judge 沙箱**，而是作为瘦客户端，通过同一 Wi-Fi 请求
Windows 桌面端判题。桌面端在 Tauri invoke 之外额外开一个 Axum HTTP 服务。

### 8.1 服务端（Rust `src/lan_server.rs`）

| 项 | 值 |
|---|---|
| 监听地址 | `0.0.0.0:8080`（`lan_server::DEFAULT_LAN_PORT`） |
| 启动日志 | `[lan] 局域网判题服务: http://192.168.x.x:8080`（`guess_lan_ip()` 推测，UDP connect 技巧，不发包） |
| CORS | `CorsLayer` 放开 `Any`（手机端 WebView origin 是 `http(s)://tauri.localhost`，随版本变化） |
| 判题实现 | `judge_batch_core()` —— 与 invoke 的 `judge-batch` **同一份代码** |
| mock 模式 | 默认**拒绝** `/api/judge`（503 + `{error, hint}`）；降级路径无隔离，不对局域网开放 |

### 8.2 HTTP 接口

```http
GET /api/ping
200 OK
{
  "ok": true,
  "service": "nex-judge",
  "version": "0.1.0",
  "go_judge": true,      // 沙箱是否就绪
  "accepting": true      // 当前是否受理判题
}

POST /api/judge
Content-Type: application/json

{ "lang": "python", "code": "print(6*7)", "stdins": ["", "3 5"] }

200 OK
[ { "verdict": "accepted", "stdout": "42", "time_ms": 12, "memory_kb": 1024 }, ... ]
```

- 返回体是**裸 `Verdict[]`**，与 `invoke('judge-batch')` 逐字节一致，前端共用一套解析。
- `stdins` 为空数组 / 缺省 → 兜底为「一条空 stdin 的用例」（与 invoke 行为一致）。
- 非 2xx 时也是 JSON：`{ "error": "...", "hint": "..." }`，前端把 hint 直接展示给用户。
- `GET /api/environment` 为 bonus 接口，镜像 `check-environment`（探测的是**电脑端**环境）。

### 8.3 前端（`frontend/src/lib/GoJudgeClient.ts`）

`submitCode` / `submitCases` 自动选路，UI 层无感：

| 环境 | 判据 | 通道 |
|---|---|---|
| 桌面 Tauri | `window.__TAURI_INTERNALS__` 存在 **且** UA 非移动端 | `invoke('judge-batch')` |
| Android APK / 纯浏览器 | 其余情况 + 已配置局域网地址 | `fetch http://<IP>:8080/api/judge` |

```ts
import { goJudgeClient } from './lib/GoJudgeClient';

// 手机端首次使用：填入电脑端日志里打印的地址（可不带协议，自动补 http://）
goJudgeClient.setLanBaseUrl('192.168.1.5:8080');

// 填完先探测，比直接判题的报错友好得多
const ping = await goJudgeClient.probeLan();
if (!ping.accepting) console.warn('电脑端未启用沙箱：', ping);

// 之后正常调用即可，桌面/移动自动分流
const { allPassed, results } = await goJudgeClient.submitCode(code, 'cpp', testCases);
```

**为什么不能只用 `__TAURI_INTERNALS__` 判断桌面**：Android APK 也是 Tauri 应用，
WebView 里同样有该对象，但手机上没有 go-judge。误判会让 invoke 走进降级 mock 模式、
在手机上**无隔离地本地直跑**用户代码。因此判据必须叠加 UA 排除移动端。

局域网地址存在 `localStorage`（键 `nex.judge.lanBaseUrl`），模式存 `nex.judge.transportMode`
（`auto` / `invoke` / `lan`，设置页可强制指定）。

### 8.4 排障清单（fetch 失败时前端会给用户看）

1. 手机与电脑是否同一 Wi-Fi（注意路由器的 **AP 隔离 / 访客网络**）；
2. 电脑端日志是否有 `[lan] 局域网判题服务: http://<IP>:8080`；
3. Windows 防火墙是否放行 8080（首次启动弹窗选「允许」，或执行：
   `New-NetFirewallRule -DisplayName "Nex Judge LAN" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow`）；
4. 地址是否为 `http://<电脑IP>:8080`（不要带结尾斜杠）。

### 8.5 Android 明文 HTTP

Android 9+ 默认禁止明文流量，局域网 `http://` 请求会被 WebView 拦掉
（`net::ERR_CLEARTEXT_NOT_PERMITTED`）。已在
`src-tauri/gen/android/app/src/main/AndroidManifest.xml` 开启
`android:usesCleartextTraffic="true"`，并配 `res/xml/network_security_config.xml`。
详见 `src-tauri/gen/android/README.md`（含重新 `tauri android init` 后如何恢复改动）。

### 8.6 手机浏览器实测指南（30 秒版）

**原理**：判题全部发生在电脑端（go-judge 沙箱 + 本机编译器），手机只是
一个瘦客户端——发代码、收判定。所以手机浏览器访问的就是电脑上这个
Axum 服务（`0.0.0.0:8080`），打的还是同一条判题链路。

步骤：

1. **电脑端先跑起来**：`npm run tauri dev`（或装好的 Nex 桌面端）。
   日志里找这一行，记下 IP：
   `[lan] 局域网判题服务: http://192.168.43.17:8080  （手机端在同一 Wi-Fi 下填写此地址）`
   （IP 每次可能变，以日志为准；也可 `ipconfig` 看「WLAN/以太网适配器」的 IPv4。）
2. **手机连同一个 Wi-Fi**（或电脑开热点、手机连热点——实测 192.168.43.x
   就是热点网段）。注意别用访客网络/AP 隔离。
3. **手机浏览器直接开** `http://<上面日志里的IP>:8080/`。
   这是 Rust 内置的零依赖测试页（`lan_server.rs` 的 `LAN_TEST_PAGE`）：
   自动打 `/api/ping`，选语言、填代码、点「提交」即走 `/api/judge`。
4. **期望看到**：`go_judge: true`，Python `print("Hello Nex")` 返回
   `Accepted` + stdout；页面上的「测试连接」按钮可复诊。

防火墙：首次启动 Nex 时 Windows 弹窗要选「允许」（专用网络）；
没弹窗或之前拒了，管理员 PowerShell 执行：

```powershell
New-NetFirewallRule -DisplayName "Nex Judge LAN" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

已知边界（2026-10-17 实测）：

- 该页面是**链路自检**用途（验证 IP/防火墙/判题全链路），
  正式学习请用桌面端或 Android APK；
- 手机浏览器页面**不共享**桌面端的代码编辑态，两者是独立入口；
- 电脑睡眠/断网会直接断，手机端报「无法连接到电脑」属预期。

