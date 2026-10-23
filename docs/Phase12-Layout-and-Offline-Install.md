# 阶段 12 · 布局重构与「装完即用」

> 目标：把外壳从「三栏挤在一起」改成能用的框架；把安装依赖收进安装包——
> 用户不需要开 Docker，也不需要登录，解压双击就能判题。

## 1. 结论先说

| 疑问 | 事实 |
| --- | --- |
| 安装要开 Docker？ | **不用**。Docker 只在 `server/`（可选后端）和 `deploy/`（云端部署）里。客户端数据全部来自打包的 `bundle.ts` + `localStorage`。 |
| 有登录页？ | **没有**。`App.tsx` 没有 auth 状态，启动不发任何后端请求。`api.ts` 里只有一个从不写入的 `nex.accessToken` 预留头。排行榜那句「接入登录后…」是空状态文案。 |
| 那之前判题为什么不可用？ | 发布目录里**没带 go-judge**，`resolve_go_judge` 找不到就静默降级成本地直跑；而且 Tauri 命令名与 ACL 不一致，批量判题直接 `Command judge-batch not found`。本轮两处都修了。 |

## 2. 布局：改了什么

### 2.1 桌面三栏

| 项 | 改前 | 改后 |
| --- | --- | --- |
| 正文上限 | 820px（1600 屏留白 200+） | **960px** |
| 右栏卡片 | 4 张，总高 877 > 756，末卡被切 105px | **3 张**（体量并入今日目标），756 = 756 |
| 凯喵立绘 | 190px 舞台 | 130px 舞台 / 128px 图 |
| 横向滚动条 | `.km-content` 因 `overflow-y:auto` 带上 x 轨道 | `overflow-x: hidden` |

右栏最终三张卡：凯喵（353px）→ 今日目标 + 内容体量（240px）→ 快捷入口（131px）。

### 2.2 断点降级（不再「隐藏 = 删功能」）

- **≤1180**：右栏收起，顶栏出现「目标」入口 → 右侧 340px 抽屉，
  抽屉里是同一份 `RightRail`（凯喵 / 今日目标 / 快捷），不是另写一套。
- **≤900**：导航变横条，右缘 `mask-image` 渐隐，末尾常驻「全部」按钮 →
  底部上滑面板，按原三组列出全部 15 项（2 列）。
- **≤560**：顶栏只留猫头 + 金币 + 目标 + 三图标；目标按钮收成 32px 图标。

### 2.3 判题台

内联样式全部迁到 `.jp-*` / `.lan-*`（这也是深色下白卡的根因）。

- 用例行：`120px 1fr 1fr`；≤560 变 `1fr 1fr` + 用例名独占一行。
- 宽 375 时：`scrollWidth` 从 **510 → 375**，「取消（强杀沙箱）」不再被压成三行。
- 深色下设置条 / 编辑器 / 结果条都跟随 `--km-*` 令牌。

### 2.4 深色

`.km-xp-text` 之前硬编码 `#1e3a5f`（深底深字）。现加 `[data-km-theme='dark']` 覆盖：
浅墨 `#e8f2fb` + 深色描边，实测 `rgb(232, 242, 251)`。

### 2.5 登录与帮助：收进页面，不挡启动

- **账号卡**放在「我的」顶部：头像 + 「本地游侠」+ 徽章「未登录 · 本地模式」，
  说明「进度只存在这台设备，不上传」。点「登录 / 注册」才展开邮箱/密码表单；
  提交时明确提示「账号服务尚未开放，本版本不收集账号信息」——不做假登录。
- **帮助页**（`HelpPage.tsx`，路由 `help`，不进侧栏）：
  五分钟上手 5 步（选学科 → 学一章 → 练一题 → 做项目 → 看笔记）、
  桌面/手机两栏判题说明、账号与数据、4 条常见问题。
- **入口**：「设置」第一张卡「第一次用？」→ 打开使用说明 / 去学习；
  「我的」账号卡 → 查看用法。
- 启动链路不读 token、不请求后端，因此安装后不会出现登录墙。

## 3. 安装：零外部依赖

### 3.1 go-judge 随包

- `src-tauri/binaries/go-judge.exe`（21MB）→ `tauri.conf.json`：
  `"bundle": { "resources": ["binaries/go-judge.exe"] }`
- `config.rs::resolve_go_judge` 增加 fallback：resource_dir 找不到时走 `detect_go_judge()`，
  因此**便携 zip**（exe 同级放 `binaries/go-judge.exe`）同样生效。

便携目录结构：

```
kaimao-code.exe
WebView2Loader.dll
binaries/go-judge.exe
```

### 3.2 实测

`GET /api/environment`：

```json
{"go_judge": true,
 "go_judge_path": "...\\release\\win64-portable\\binaries\\go-judge.exe",
 "languages": [{"name":"g++","available":true},{"name":"python","available":true},{"name":"java","available":true}]}
```

UI 判题：`结果：2 / 2 通过`，46ms / 15ms，0 console error。

## 4. 踩到的坑（这次新增）

### 4.1 Tauri 命令名：kebab 名根本不存在

```rust
#[tauri::command(name = "judge-batch")]   // 这个 name 不改注册名
async fn judge_batch(...)                  // 注册名仍是 judge_batch
```

ACL 写 `commands.allow = ["judge-batch"]` 时：

- 前端调 `judge-batch` → `Command judge-batch not found`（没这个命令）
- 前端调 `judge_batch` → `Command judge_batch not allowed by ACL`（名字对了，权限没放行）

正确做法：**命令注册名 = 函数名（下划线）**，ACL 的 `commands.allow` 也写下划线；
permission 的 `identifier`（`allow-judge-batch`）保持连字符，capabilities 引裸名。

`judge` 命令没有分隔符，所以一直正常——只有带下划线的命令中招，排查时容易被误导。

### 4.2 包一层 .km-nav-shell 把整页撑到 1696px

grid item 的 `min-width` 默认 `auto`，nav 的 1644px 横滑内容把列宽顶开，
顶栏图标跑到视口外（390 宽下「搜索/主题/设置」直接消失，顶栏 98 → 136）。

修：`.km-main` / `.km-nav-shell` / `.km-nav-shell > .km-sidenav` 都设 `min-width: 0`，
shell 加 `overflow: hidden`。

### 4.3 层级

AI 浮球 `z-index: 100`，抽屉/面板原本 60-63，被浮球压在下面。
现改 110 / 111 / 112 / 113。

## 5. 自检表

| 检查 | 结果 |
| --- | --- |
| 1280×820 三栏几何 | 220 / 760 / 300，右栏 756=756，3 卡 |
| 1600×1000 正文 | 960（上限生效） |
| 1179 抽屉 | 宽 340，`document.scrollWidth = 1179`，无横向溢出 |
| 390 顶栏 | 98px（两行），无横向溢出 |
| 390 导航 | 1644px 横滑 + 渐隐 + 「全部」面板 15 项 |
| 390 判题台 | `scrollWidth 510 → 375`，无溢出 |
| 深色经验条 | `rgb(232, 242, 251)` + 深描边 |
| 深色判题台 | `.lan-bar` `rgba(28,43,64,.86)`、编辑器 `rgba(22,34,49,.66)` |
| exe 启动 | 15 导航 / 右栏 3 卡 / 0 console error |
| exe 判题 | go_judge=true，Python 2/2 accepted（46ms / 15ms） |
| 我的 · 账号卡 | 「本地游侠」+ 未登录徽章，登录表单展开 2 输入，不提交 |
| 帮助页 | 5 个步骤 / 4 条 FAQ / 903 字符，1280 与 390 均无横向溢出 |
| 前端构建 | `tsc --noEmit && vite build` 通过 |

## 6. 双端重出（2026-10-20）

两端产物已同步到同一份前端（`index-BhpwNIUq.js` + `index-C1GZl-Df.css`）。

| 步骤 | 命令要点 | 说明 |
| --- | --- | --- |
| ① 清旧哈希 | 先 `rm dist/assets/index-*` 再 `npm run build` | `emptyOutDir:false`，不清会残留 22 份旧产物，全被打进 `.so` |
| ② APK 原生库 | `tauri android build --apk --target aarch64 --split-per-abi` | 必带 `ANDROID_HOME=D:\Sdk` / `NDK_HOME=D:\Sdk\ndk\android-ndk-r27c`，否则直接报「SDK not found」；结尾符号链接报错属预期 |
| ③ 拷 so | `cp target/aarch64-linux-android/release/libnex.so gen/android/app/src/main/jniLibs/arm64-v8a/` | 15.6 MB |
| ④ 打包 | `./gradlew assembleRelease -x rustBuildArm64Release -x ...` | 15s |
| ⑤ 签名 | `apksigner --ks gen/android/keystore/nex-release.jks` | keystore 路径在 `gen/android/keystore/`，不在 `src-tauri/keystore/` |
| ⑥ exe | `tauri build --no-bundle` | 裸 cargo 会白屏 |

校验脚本：`.scratch/verify_so.cjs <bin>` 直接读 `dist/index.html` 的两个哈希，
确认二进制里真的嵌进了这版前端（PASS/FAIL 一目了然）。

APK 元信息：`com.nex.app` / 0.1.0 / versionCode 1000 / minSdk 24 / `arm64-v8a`，v2+v3 签名。

### 6.1 本轮补的两处

- **移动端导航自动滑入**：横滑条 1644px，靠后页面（设置/帮助）切过去时选中项在视野外，
  用户看不到「自己在哪」。`KaimaoShell` 加 `navRef` + `useEffect([active])`，
  `scrollTo({left: offsetLeft-14, behavior:'smooth'})`；同时横滑条两端渐隐
  （`mask-image` 左右各 14px / 26px）+ `scroll-snap-type: x proximity`。实测切到「冒险设置」后
  `scrollLeft = 1321`、按钮 100% 在可视区内，再切回首页 `scrollLeft = 0`。
- **Rust 警告清零**：`build_env` 的 `let mut env` 在非 Windows 构型下不需要 `mut`，
  加 `#[allow(unused_mut)]`（跨平台共用一份，不能直接删 `mut`）。

### 6.2 屏幕验收（375×812，headless Edge）

| 检查 | 结果 |
| --- | --- |
| 我的 · 账号卡 | 文案「本地游侠 · 未登录 · 本地模式」，点「登录/注册」展开邮箱/密码两栏 |
| 帮助页 | 4 卡，首卡「五分钟上手」5 步，无横向溢出 |
| 导航滑入 | home→settings→home 三次「visible: true」，`overflowX = 0` |
| 控制台 | 0 error |

## 7. 还没做

1. **空壳页**：图鉴 / 剧情 / 背包 / 支线 / 成就 / 衣柜仍是空状态（113–224 字符）。
2. **判题结果区**仍在编辑器下方，未做固定分栏；提交后要往下滚才能看到结果。
3. go-judge.exe 21MB 已进仓库工作区，尚未决定是否入 git（`.gitignore` 未排除）。
4. **「登录/注册」是空按钮**：点了只提示「账号服务尚未开放」。如果真要做多设备同步，
   得先有后端（账号 + 进度增量），当前架构是纯本地，别只补前端表单。
