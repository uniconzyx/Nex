# go-judge 二进制放置说明

本目录用于存放 **go-judge** 可执行文件，编译/运行期由 `src/config.rs::detect_go_judge`
在以下位置查找（优先级从高到低）：

- `<exe_dir>/binaries/go-judge(.exe)`
- `<exe_dir>/resources/binaries/go-judge(.exe)`  （Tauri 打包后的资源目录）
- `<exe_dir>/go-judge(.exe)`

## 获取 go-judge

go-judge 是 @criyle 的开源项目（https://github.com/criyle/go-judge），
提供 Windows（winc 后端）/ Linux / macOS 预编译二进制。

### Windows（winc 实验性沙箱）

下载 `go-judge-windows-amd64.exe`，重命名为 **`go-judge.exe`** 放到本目录：

```
src-tauri/binaries/go-judge.exe
```

启动参数由 `src/sandbox.rs::spawn_go_judge` 构造：
`go-judge.exe --addr 127.0.0.1:<port> --enable-network=false --enable-unsafe`

- `--enable-unsafe`：启用 winc 实验性沙箱（Windows 必需）
- `--enable-network=false`：默认全局禁用网络（不可信用户仍应回退 Linux 运行时）

## 缺失时

若本目录没有 go-judge 二进制，`JudgeManager` 会自动进入 **本地直跑降级模式**
（`sandbox.rs::run_direct`）：用系统已装的 g++/python/java 直接执行代码。
此时无沙箱隔离，仅适合个人/本机场景；`cargo build` 后也能跑通判题（mock/真实直跑）。

## 便携工具链（可选）

若用户电脑没装编译器，可把便携版工具链随包分发到：

```
src-tauri/binaries/tools/mingw64/bin/g++.exe
src-tauri/binaries/tools/python/python.exe
src-tauri/binaries/tools/jdk/bin/java.exe
```

并在 `environment.rs` / `sandbox.rs` 中把绝对路径优先于系统 PATH。
（当前脚手架默认走系统 PATH 检测，见 `environment.rs::check_environment`。）
