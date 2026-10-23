# 阶段 11 · Windows EXE / Android APK 双端定版

> 日期：2026-10-19  
> 目标：**一份前端、一份 Rust 核心，产出 .exe 与 .apk 两个安装物，功能与内容完全一致，并逐项自检。**

---

## 1. 交付物

| 产物 | 路径 | 大小 | 说明 |
| --- | --- | --- | --- |
| Windows 绿色包 | `release/kaimao-code-0.1.0-win64.zip` | 11.5 MB | 解压即用，内含 exe + WebView2Loader.dll |
| Windows 可执行 | `release/kaimao-code-0.1.0-win64.exe` | 14.9 MB | 单独拷出时**必须**带上同目录 `WebView2Loader.dll` |
| Android 安装包 | `release/kaimao-code-0.1.0-arm64.apk` | 18.0 MB | 已 zipalign + v1/v2 签名，arm64-v8a |

- 包名 `com.nex.app`，应用名「凯喵Code试炼录」，minSdk 24 / targetSdk 36。
- 签名密钥：`src-tauri/gen/android/keystore/nex-release.jks`（alias `nex`，口令 `nex2026`）。
- 两端窗口/标题一致：`凯喵Code试炼录`；桌面默认 1280×820（最小 900×640），手机竖屏自适应。

## 2. 一致性如何保证

1. **同一份前端**：`frontend/` 构建出 `dist/`，被**同时**内嵌进 `nex.exe` 与 `libnex.so`。
   Vite 产物名带内容哈希，两端出现的资源名集合完全一致即证明字节一致（实测 19 个引用全等）。
2. **同一份 Rust 核心**：`src-tauri/src/lib.rs` 的 `run()` 同时是桌面 `main.rs` 与 Android `#[mobile_entry_point]` 的入口，
   判题命令、局域网服务、进度/学科逻辑不分叉；差异只在「谁来托管 WebView」。
3. **离线数据**：110 个项目 / 107 章节 / 18 篇考研笔记在构建期由 `frontend/scripts/gen_bundle_data.py`
   生成 `src/data/bundle.ts`，运行时不依赖 FastAPI/PostgreSQL。

## 3. 构建命令

### 3.1 Windows EXE

```bash
cd src-tauri
export PATH="$HOME/.cargo/bin:$PATH"
NO_PROXY="*" no_proxy="*" ../frontend/node_modules/.bin/tauri build --no-bundle
# 产物：src-tauri/target/release/nex.exe
# 必须同时分发：src-tauri/target/release/WebView2Loader.dll
```

### 3.2 Android APK

```bash
# ① 用 Tauri CLI 编 Rust 动态库（关键：只有 CLI 会嵌入 dist 资源）
cd src-tauri
export ANDROID_HOME="D:\\Sdk" ANDROID_SDK_ROOT="D:\\Sdk" \
       NDK_HOME="D:\\Sdk\\ndk\\android-ndk-r27c" JAVA_HOME="C:\\Program Files\\Java\\jdk-23" \
       NO_PROXY="*" no_proxy="*" CI=true
../frontend/node_modules/.bin/tauri android build --apk --target aarch64 --split-per-abi
# 该命令会在「创建符号链接」一步失败（Windows 未开开发者模式），属预期：
# 此时 libnex.so 已经编好，大小约 16.3 MB。

# ② 手动拷进 jniLibs
cp target/aarch64-linux-android/release/libnex.so \
   gen/android/app/src/main/jniLibs/arm64-v8a/libnex.so

# ③ Gradle 打包（跳过会重复调 node 的 rust 任务）
cd gen/android
./gradlew assembleRelease --no-daemon \
  -x rustBuildArm64Release -x rustBuildArmRelease \
  -x rustBuildX86Release -x rustBuildX86_64Release

# ④ 对齐 + 签名
"D:/Sdk/build-tools/35.0.0/zipalign.exe" -f -p 4 \
  app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk ../../../release/tmp.apk
"D:/Sdk/build-tools/35.0.0/apksigner.bat" sign \
  --ks keystore/nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 \
  --ks-key-alias nex --out ../../../release/kaimao-code-0.1.0-arm64.apk ../../../release/tmp.apk
```

## 4. 踩过的坑（都已在配置里固化）

1. **~~不要用 `cargo build --release` 出桌面包~~ → 根因已查明并修复（2026-10-20）**。
   直接 cargo 编出来的 exe 会把 `devUrl`（`http://localhost:1420`）当入口，双击就是白屏。
   **当初归因为"必须用 tauri build"，其实真正的原因是 `Cargo.toml` 的
   `default = []` 漏了 `tauri/custom-protocol`** —— 缺了它 `tauri-macros` 里
   `dev = cfg!(not(feature = "custom-protocol"))` 为真，codegen 走 dev 分支，
   既不嵌 `dist`，又把入口指向 devUrl。
   `tauri build` 能正常出包，只是因为它会自己加 `--features tauri/custom-protocol`。
   现在 `default` 已补上，裸 cargo 也能出正确产物。详见 `Phase14-Docker-Fix.md` §5。
   诊断方式：`nex-boot.log` 里看到 `page Started http://localhost:1420` 即为踩坑。
2. **exe 不能单文件拷贝**。mingw 工具链把 WebView2Loader 做成了动态依赖，
   只拷 exe 会报 `api-ms-win-core-winrt-error-l1-1-0.dll: cannot open shared object file`
   （报错名误导，真实原因是同目录缺 `WebView2Loader.dll`）。
3. **~~Android 的 `.so` 必须由 Tauri CLI 编译~~ → 根因已查明并修复（2026-10-20）**。
   裸 `cargo build --release --target aarch64-linux-android --lib` 原来只有 7.8 MB、
   **不含前端资源**（APK 能装但白屏），同样是 `custom-protocol` 特性缺失所致。
   补上 `default = ["tauri/custom-protocol"]` 后，裸 cargo 编出来就是 16,351,512 B
   且内含 `index-*.js`。判别方法不变：`grep -c "index-XXXX.js" libnex.so`，
   或者更直接地看大小（>15MB 才可能带前端）。**注意 exe 侧的同类现象有误导性**：
   `grep localhost:1420` 永远能命中（config 字段被原样编译进去），不能当作判据。
4. **Windows 建符号链接被拒** → CLI 报 `Creation symbolic link is not allowed`，
   不影响 `.so`，手动 `cp` 即可。
5. **Gradle 的 `rustBuild*` 任务会再调一次 node CLI 且路径写死**，直接 `-x` 掉。
6. **Vite `emptyOutDir` 已关**：会话内批量删除有配额，改成 hash 产物自然共存，
   定期手工清理即可（见 `.scratch/dist-stale/`）。
7. **Android 链接 OpenSSL** → `reqwest` 换成 `rustls-tls`，去掉 native-tls。
8. **crates 走代理不通** → `~/.cargo/config.toml` 切 `rsproxy.cn`，并用 `NO_PROXY=*`
   绕开失效的系统代理；Gradle 用阿里云镜像 + 腾讯 Gradle 发行版。

## 5. 自检结果（2026-10-19）

### 5.1 EXE 实机启动

- `release/kaimao-code-0.1.0-win64.exe` 在 `release/` 目录下直接运行：进程常驻，
  日志正常输出「mock 判题 / 局域网 8080 / WS 14520」。
- 通过 WebView2 远程调试抓取：入口 `http://tauri.localhost/`，标题「凯喵Code试炼录」，
  **15 个导航项全部渲染**，`#root` 非空，**控制台 0 错误**。
- 逐页截图：主城首页、知识试炼区（C/C++ 8 张章节卡）、BOSS 项目实战（110 项目分档）、
  考研手札（18 条笔记）、冒险设置（外观/判题/数据/关于）均正常。

### 5.2 APK 静态校验

- `apksigner verify` 通过，签名主体 `CN=Nex, O=uniconzyx`。
- `aapt2 dump badging`：label `凯喵Code试炼录`、activity `com.nex.app.MainActivity`、
  `native-code: 'arm64-v8a'`、`INTERNET` 权限在列。
- `lib/arm64-v8a/libnex.so` 16.3 MB，内含 `index-DRxZsffv.js`，
  与 exe 的资源引用集合**完全相同（19/19）**。

### 5.3 同一份 dist 的布局回归

用无头 Edge 直接加载 `dist/`（即两端内嵌的同一份文件）：

| 视口 | 结果 |
| --- | --- |
| 1280×820（桌面） | 三栏、右栏凯喵可见、浮动球已隐藏、经验条文字居中、无横向溢出、0 报错 |
| 390×844（手机） | 右栏隐藏、侧栏转顶部横向（390×52）、无横向溢出、0 报错 |

- 右栏凯喵立绘可点击 → 打开苏格拉底式 AI 面板（已用截图确认）。
- 首页「今日试炼」跟随当前学科：C/C++ 下给出 GoogleTest，不再是无关学科的 Python 项目。

## 6. 已知限制

- APK 只出 `arm64-v8a`（绝大多数在用机型）；如需 32 位/模拟器，按同法补 `armv7` / `x86_64` 的 `.so`。
- 本机没有可用的 Android 模拟器系统镜像（`system-images` 目录为空，需 ~2 GB 下载），
  因此 APK 未做真机启动截图；移动端布局已用同源 `dist` 在 390×844 视口验证。
- 「怪物图鉴 / 剧情日志」仍为空状态页——仓库里没有对应数据，等有错题记录后才会长出内容。
