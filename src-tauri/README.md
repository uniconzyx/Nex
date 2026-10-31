# Nex 原生桌面端（Tauri v2 + go-judge）

脱离 Docker 的第二个版本：用 **go-judge** 的 Windows `winc` 沙箱替代 Judge0，
由 Tauri v2 (Rust 宿主) 以 **Sidecar** 模式托管，前端用 TypeScript 调用。

## 目录结构

```
src-tauri/
├── Cargo.toml              # 依赖：tauri/tokio/reqwest/tokio-tungstenite/nix/sysinfo
├── build.rs                # tauri_build::build()
├── tauri.conf.json         # 应用/窗口/打包配置（NSIS + 全局禁用网络 CSP）
├── capabilities/
│   └── default.json        # 最小权限：仅本机回环
├── icons/                  # icon.png / icon.ico（已生成占位图）
├── binaries/
│   └── README.md           # 把 go-judge(.exe) 放这里；缺失则自动降级
├── installer/
│   └── installer.nsi       # NSIS 安装脚本（admin + Defender 排除项）
└── src/
    ├── main.rs             # 入口：setup 拉起 JudgeManager + WS 服务，退出清理
    ├── config.rs           # AppConfig + go-judge 路径解析
    ├── error.rs            # NexError 统一错误
    ├── payload.rs          # go-judge /run 请求/响应类型
    ├── judge_client.rs     # REST 封装 + Payload 构造 + Verdict 映射
    ├── sandbox.rs          # JudgeManager：Sidecar 生命周期 / 看门狗 / 本地直跑
    ├── ws_handler.rs       # WebSocket 取消服务（掉线强杀沙箱）
    ├── defender.rs         # Windows Defender 排除项
    └── environment.rs      # g++/python/java/go-judge 环境检测
```

## 依赖与工具链

- Rust ≥ 1.77（建议 `rustup` 安装 stable）
- 前端构建产物放到 `../dist`（已含占位 `index.html`，可替换）
- 可选：把 `go-judge(.exe)` 放到 `src-tauri/binaries/`

## 构建与运行

```bash
# 1) 安装 Rust（首次）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 2) 进入工程
cd CppMind/src-tauri
# 3) 编译（无需 go-judge 也能过；缺失时进 mock 模式）
cargo build
# 4) 开发运行（需先有前端 dev server，或临时用占位页）
cargo run
# 5) 打包（NSIS / MSI / app / dmg）
cargo tauri build
```

## 7 步落地顺序（对应需求优先级）

1. **资源限制 + 网络隔离**（优先级 1）
   - `sandbox.rs::spawn_go_judge` 启动参数 `--enable-network=false` + Windows `--enable-unsafe`。
   - `sandbox.rs::run_one` 用 `tokio::time::timeout` 做墙钟看门狗；超时即 `kill_tree()` 强杀整棵进程树（含卡死沙箱），supervisor 自动重启。
   - Unix：`sandbox.rs::set_cpu_rlimit` 在 `pre_exec` 设置 `RLIMIT_CPU` 作为 CPU 时间硬保底。
   - capabilities 仅放行本机回环；不可信用户回退 Linux 运行时的接口保留在 `config.enable_network` 与 `spawn_go_judge` 注释中。

2. **WebSocket 掉线强杀**（优先级 2）
   - `ws_handler.rs` 用 `tokio-tungstenite` 托管 `ws://127.0.0.1:14520/ws/run`。
   - `tokio::select!` 监听 `reader.next()`；客户端断开（`None`）立即 `manager.kill_current()`。
   - `sandbox.rs::spawn_capture` 对本地直跑子进程用 `kill_on_drop(true)` 防僵尸。

3. **Defender 排除 + NSIS**（优先级 3）
   - `defender.rs::ensure_exclusion` 运行时静默提权加排除项（路径末尾去反斜杠）。
   - `installer/installer.nsi` `RequestExecutionLevel admin`，安装期 `Add-MpPreference`，卸载期 `Remove-MpPreference`。

4. **脚手架化**（优先级 4）
   - 完整 `Cargo.toml` / `build.rs` / `main.rs` / 各 `.rs` 模块；`cargo build` 可编译。
   - 无 go-judge 时 `judge()` 走 `run_direct` 真实本地执行，跑通 mock/直跑数据。

5. **多语言 Payload**（模块 3）
   - `judge_client.rs::build_request` 构造 C++/Python/Java 的 `/run` 请求。
   - C++/Java 首用例 `copyOutCached` 出 `a.exe`/`Main.class` 的 `fileId`，后续用例 `copyIn` 复用，避免重复编译。

6. **CE/RE/TLE/MLE 映射**（模块 3）
   - `judge_client.rs::map_results` 把 go-judge 状态映射为前端 `Verdict`。

7. **环境检测引导**（模块 2）
   - `environment.rs::check_environment` 检测 g++/python/java/go-judge。
   - 前端可调用 `check_environment` 命令，缺失时引导安装或切换到便携工具链（见 `binaries/README.md`）。

## ⚠️ 编译前请确认的两点

- **能力(permission)命名**：`capabilities/default.json` 引用了 `nex:allow-judge` 等自定义命令权限。
  若 `cargo build` 报 “permission not found”，把那 4 行 `nex:allow-*` 删掉即可编译通过
  （运行时命令会需另行授权；不影响编译）。命名规则为 `<包名>:allow-<命令名>`。
- **go-judge 二进制**：缺失不影响 `cargo build`，会自动进入本地直跑降级模式。
  要启用沙箱判题，把 `go-judge(.exe)` 放到 `src-tauri/binaries/`。

## winc 已知坑点（务必留意）

- `--enable-network=false` 在 winc 下**网络隔离不彻底**，不可信用户判题仍应回退 Linux 服务端。
- `cpuLimit` 只算 **CPU 时间**，**防不住 `sleep`/死循环** → 必须靠宿主墙钟看门狗（已实现）。
- `procLimit` 只限进程数，**线程炸弹不计数**（靠 `cpuLimit` 兜底）。
- Java/Go 需显式给足 `memoryLimit`（JVM 自带开销）。
- Windows Defender 可能误报 go-judge/生成的 `a.exe` → 已加排除项逻辑（installer + 运行时）。
