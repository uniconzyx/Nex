# 阶段 17 · 前后端与客户端打通

## 1. 这一版要解决什么

上一阶段把考研题库的数据与接口做完了（395 题 / 73 份分类总结 / 89 套卷），
但**三层之间其实是各自跑通、彼此没接上**的：

```
React 前端 (frontend/)     ← fetch http://127.0.0.1:8000
      ↑                          地址写死在 api.ts，只能手改 localStorage
FastAPI 后端 (server/)      ← 起了才知道在哪个端口
      ↑
Tauri 客户端 (src-tauri/)   ← 完全不知道后端存在
```

具体表现为四个断点：

| # | 断点 | 用户看到什么 |
| --- | --- | --- |
| 1 | 客户端不知道后端在哪 | 换个端口/换台机器就「一直转圈」 |
| 2 | 前端地址写死 | 要手动改 localStorage，普通人找不到 |
| 3 | 「服务没起」与「接口报错」同一句文案 | 用户以为是 App 坏了 |
| 4 | 设置页把两个服务混成一个 | 「判题服务地址」实际改的是内容服务地址 |

这一版把这四条全接上，并给出**可复现的验收脚本**，让"打通"变成可断言的事实。

## 2. 后端：新增系统健康接口

`server/app/api/v1/system.py` → `GET /api/v1/system/health`

Nex 的数据源分两类，这个区分是整个阶段的基础：

| 类型 | 内容 | 依赖 |
| --- | --- | --- |
| **文件型** | 考研题库 / 指南 / 职业库 | 无（只读 `content/` 构建产物） |
| **数据库型** | 课程 / 练习 / 进度 / 账号 | Postgres + Redis |

所以「后端没起数据库」不该让整个 App 变砖。健康接口据此返回：

```json
{
  "backend":  { "name": "Nex API", "version": "0.1.0", "elapsed_ms": 3.1 },
  "exam":     { "ok": true, "questions": 435, "topics": 260, "summaries": 73, "papers": 89 },
  "database": { "ok": null, "checked": false },
  "features": { "exam": true, "guides": true, "content": false, "judge": null, ... }
}
```

三条硬约束：

1. **探测失败绝不 500**。数据库挂了，本接口仍返回 200，只是 `database.ok=false`；
   否则客户端连「后端是否活着」都判断不了。
2. **默认浅探测**，不连数据库——客户端首屏不该被 Postgres 拖住。
   需要深探测时带 `?deep=1`（1.5s 超时）。
3. `features` 是**逐功能**可用性，客户端据此只灰掉用不了的那部分入口，
   而不是整页报错。

## 3. 客户端：Rust 侧探测并下发基址

新增 `src-tauri/src/api_client.rs`，注册 Tauri 命令 `api_probe`：

| 优先级 | 候选地址 | 场景 |
| --- | --- | --- |
| 1 | `NEX_API_BASE` 环境变量 | 显式指定，最高优先 |
| 2 | `http://127.0.0.1:8000` | 桌面端本机后端 |
| 3 | `http://localhost:8000` | 同上，换个写法 |
| 4 | `http://<局域网IP>:8000` | 手机端连电脑上的后端 |
| 5 | 回落到 2 | 探测失败也返回，让前端有地址可显示 |

探测打 `/api/v1/system/health`（老后端退回 `/health`），返回
`{ baseUrl, reachable, candidates, backendVersion, elapsedMs }`。

> ⚠️ 所有 HTTP 请求必须 `.no_proxy()`：沙箱与 CI 会注入 `HTTP_PROXY`，
> 不绕过代理的话「自己连自己」都会被代理吞掉，表现成"后端明明在跑却连不上"。

配套改动：
- `permissions/allow-api-probe.toml` + `capabilities/default.json` 放行；
- `lib.rs` 的 `generate_handler!` 注册 `api_probe`。

## 4. 前端：API 层重构

`frontend/src/lib/api.ts` 重写，三件事：

### 4.1 基址三段式

```
客户端解析器 (Rust api_probe)  >  localStorage["nex.apiBaseUrl"]  >  http://127.0.0.1:8000
```

`registerBaseResolver(fn)` 让客户端注入自己探测到的地址，
`resolveApiBase()` 是所有请求的唯一入口。

**只有探测通了才注册**——探测不通时保持前端自身兜底，
免得把一个错的地址钉死、把用户手填的正确地址也盖掉。

### 4.2 401 自动续期

`apiGet/apiPost/apiPatch/apiPut` 收到 401 时调用 `refreshHandler`，
成功后**原样重放一次**原请求。钩子由 `session.ts` 注册
（`setRefreshHandler(refreshTokens)`），避免 `api.ts ← session.ts` 的 ESM 循环依赖。

续期接口自身 401 时跳过（否则无限递归）。

### 4.3 错误分级

新增 `ApiNetworkError`（请求根本没发出去）与既有 `ApiError`（后端回了错误）
区分开，文案才说得清「连不上」还是「请求被拒」。

## 5. 前端：连接状态可视化

| 文件 | 作用 |
| --- | --- |
| `lib/connection.ts` | 全局连接状态（unknown/online/offline）+ 60s 心跳 + 能力描述 |
| `components/ConnectionBadge.tsx` | 顶栏小圆点：绿=已连接 / 红=未连接（呼吸动画）/ 灰=检测中 |
| `lib/clientBridge.ts` | 调用 `invoke('api_probe')` 并把地址注册进 api.ts |

顶栏圆点点击直达设置页。

## 6. 设置页：两个服务彻底分开

这是原有的一处**真 bug**：设置页标题写「判题服务地址」，实际改的是
`nex.apiBaseUrl`（内容服务，8000）；而判题局域网地址用的是另一个键
`nex.judge.lanBaseUrl`（8080），设置页根本没入口。

现在拆成两张卡：

| 卡片 | 键 | 默认 | 说明 |
| --- | --- | --- | --- |
| **内容服务** | `nex.apiBaseUrl` | `http://127.0.0.1:8000` | 题库 / 指南 / 账号 / 进度；带实时状态卡 + 「检测连接」按钮 |
| **判题服务** | `nex.judge.lanBaseUrl` | 空（桌面端走本机 invoke） | 手机端填电脑局域网地址，如 `http://192.168.1.5:8080` |

内容服务卡片还展示：连接状态、后端版本、可用能力、题库规模、数据库状态。

## 7. 一键启动与验收

### 7.1 `scripts/dev_stack.py`

一条命令起全栈（含前置检查）：

```bash
python scripts/dev_stack.py              # 后端 + 前端 + 开浏览器
python scripts/dev_stack.py --check      # 只做前置检查与探活
python scripts/dev_stack.py --backend-only
```

设计约束（沿用项目既有铁律）：

- **不写 .sh 编排脚本**——本机 bash 会被路由到 wsl.exe 并被黑名单拦截，
  一切编排都用 Python；
- **不碰 Docker**——后端用本机 Python + uvicorn 直跑；
- 日志落 `scratch/logs/{backend,frontend}.log`；
- 端口探测用 socket connect，不用 ps/netstat（跨平台且无副作用）。

### 7.2 `scripts/verify_integration.py`

**这是"打通"的硬判据**，五组共 37 项：

| 组 | 验什么 |
| --- | --- |
| A 后端存活 | `/health` 返回 up；`/system/health` 统一信封；题库快照可用 |
| B 题库契约 | 目录/框架/知识点/总结/题目/详情/套卷/精读/判分 全部 200 + 统一信封 |
| C 字段透传 | `suggested_order` 存在且与 `question_ids` 同集合 |
| D 前端契约 | **从前端 `exam.ts` 里正则抽出每个端点，逐个打后端**——防止前端写了、后端没做 |
| E 客户端接线 | `api_probe` 已注册 / 在 handler 列表 / capabilities 放行 / 权限文件存在 / 前端确实调用了它 |

D 组是这版最有价值的检查：前端声明的路径由**前端源码自己提供**，
不是手抄清单，所以前端改了端点而忘了后端，验收会立刻红。

```bash
python scripts/verify_integration.py
# === 汇总：37 PASS / 0 FAIL / 0 WARN ===
```

### 7.3 `scripts/browser_acceptance.mjs` —— 真实浏览器验收

curl 只能证明「接口通」，证明不了「页面真的把数据画出来了」。
这一版打通的核心恰恰是**前端在浏览器里能不能渲染后端数据**，所以必须真跑一次 DOM。

用 `playwright-core`（装在 managed workspace）驱动真实 Chromium，13 项：

| # | 场景 | 判据 |
| --- | --- | --- |
| 1 | 首屏 | 顶栏出现连接指示灯 |
| 2 | 首屏 | 指示灯为「已连接」（`km-conn-badge online`） |
| 3 | 设置页 | 有「内容服务」卡片 |
| 4 | 设置页 | 有「判题服务」卡片（与内容服务分开） |
| 5 | 设置页 | 健康卡片显示「已连接」 |
| 6 | 设置页 | 显示后端名称与版本（`Nex API v0.1.0`） |
| 7 | 设置页 | 显示题库规模 |
| 8 | 考研手札 | 题库 Tab 加载出 408 考试 |
| 9 | 考研手札 | 题库 Tab 渲染出科目列表 |
| 10 | 分类总结 | 出现「建议刷题顺序」区块 |
| 11 | 分类总结 | 建议顺序渲染出题目条目（实测 98 项） |
| 12 | **断网** | 地址改成坏端口后指示灯变红（`km-conn-badge offline`） |
| 13 | **断网** | 设置页显示「未连接」并给出指引 |

第 12、13 项是**反向验收**——证明这套接线不是"永远显示绿灯"的假象。

```bash
node scripts/browser_acceptance.mjs
# === 浏览器验收：13 PASS / 0 FAIL ===
```

> 环境说明：本机 `npm` 被命令安全层路由到 `wsl.exe` 黑名单拦截，装不了包，
> 所以 `playwright-core` 与 Chromium 都放在 managed workspace
> （`C:/Users/zyx/.workbuddy/binaries/node/workspace`）与 `~/.agent-browser/browsers`。
> ESM 不认 `NODE_PATH`，脚本里用 `file://` 绝对路径导入。

## 8. 验收结果

| 项 | 结果 |
| --- | --- |
| `scripts/verify_integration.py` | **37 PASS / 0 FAIL / 0 WARN** |
| `scripts/browser_acceptance.mjs`（真实 Chromium） | **13 PASS / 0 FAIL** |
| `pytest server/tests/` | **61 + 6 = 67 passed**（新增 `test_system_health.py` 6 条） |
| `tsc --noEmit` | EXIT 0 |
| `vite build` | EXIT 0 |
| `cargo check`（src-tauri） | Finished，无警告 |
| `cargo test --lib`（src-tauri） | **32 passed / 0 failed**（含 `api_client` 7 条） |

## 9. 顺带修掉的 bug

| Bug | 位置 | 后果 |
| --- | --- | --- |
| `exam_bank.py` 括号多一层 | `server/app/services/exam_bank.py` | **后端整个起不来**（SyntaxError），上一阶段编辑残留 |
| 设置页标题与实际键不符 | `frontend/src/pages/SettingsPage.tsx` | 用户改「判题地址」其实改的是内容服务地址 |
| 设置页深探测拖慢首屏 | `frontend/src/pages/SettingsPage.tsx` | 打开设置页要等 2s（DB 超时）才出信息；改为浅探测，深探测只在点按钮时做 |
| **Windows 测试宿主缺应用清单** | `src-tauri/build.rs` | `cargo test --lib` 必崩（`STATUS_ENTRYPOINT_NOT_FOUND`），看着像代码挂了其实是清单缺失，详见下节 |

### 9.1 `cargo test --lib` 崩在加载阶段的根因（Windows 特有）

上一版文档里「Rust 侧没有单元测试」这一条，其实卡在一个**与业务代码无关**的
Windows 加载问题上，值得单独记一笔：

**现象**：`cargo test --lib` 编译通过，但一运行就报

```
error: test failed, to rerun pass `--lib`
Caused by: process didn't exit successfully: nex-<hash>.exe
  (exit code: 0xc0000139, STATUS_ENTRYPOINT_NOT_FOUND)
```

**排查过程**（每一步都排除了一个可能）：

1. `import app.main` 之类？—— 不是，Python 侧正常。
2. DLL 缺失？—— 补上 `WebView2Loader.dll`（`webview2-com-sys` 的 out/x64 里就有）、
   `libgcc_s_seh-1.dll` / `libwinpthread-1.dll`（rust 工具链 bin 里）后，**依旧**同样报错。
3. 直接解析 PE 导入表，看 exe 到底要哪些符号：

   ```
   WebView2Loader.dll ['GetAvailableCoreWebView2BrowserVersionString']   ← 补了，还是崩
   comctl32.dll      ['DefSubclassProc','RemoveWindowSubclass','SetWindowSubclass','TaskDialogIndirect']
   ```

4. 核对 System32 的 `comctl32.dll` 导出：只有 v5 那套，**没有 `TaskDialogIndirect`**；
   `TaskDialogIndirect` 只存在于 **Common-Controls v6**（WinSxS 里的 side-by-side 副本）。
5. 定位引用源：`grep -rl TaskDialogIndirect ~/.cargo/registry/src/` →
   `tauri-runtime-wry/src/dialog/windows.rs` 与 `muda`。

**根因**：Windows 应用清单里必须显式依赖 `Microsoft.Windows.Common-Controls` v6，
否则加载器只认 System32 的 v5，v5 又不导出 `TaskDialogIndirect` → 加载期就崩。
而 **Tauri 的清单只嵌进 `bin` 目标**（`tauri-winres` → `cargo:rustc-link-arg-bins`），
`cargo test --lib` 生成的**测试宿主是另一个 exe**，它没有清单。

**修法**（`src-tauri/build.rs`）：不再用 Tauri 自带的清单，改为自编一份
（内容等价 + `dpiAware`），用 `windres` 编成 COFF 资源对象后通过
`cargo:rustc-link-arg` 链给**所有**链接目标（bin / 测试宿主 / cdylib），
保证 test 与 build 的运行时行为一致。

> MSVC 工具链不需要这段：`mt.exe` 与链接器会自动生成外置 `.manifest`，
> 测试宿主同样能解析到 v6 控件。代码里已按 `CARGO_CFG_TARGET_ENV` 分支跳过。

**顺带收获**：`cargo test --lib` 一旦能跑，之前累积的 `payload` / `sandbox` /
`lan_server` 单测也全部复活——**32 条一次通过**，其中 `sandbox` 的看门狗、
临时目录清理、mock 降级等高风险路径现在有回归网了。

## 10. 自查：这一版还有什么没做

诚实列出来，不粉饰：

1. **没有真客户端（.exe / .apk）验收**。`api_probe` 这条链路的 Rust 侧经过
   `cargo check` 与静态断言，浏览器侧也验了完整的降级行为，
   但**没有实际跑起 .exe 点击一遍**——本机没有可交互的桌面会话。
   这是本版**最大的未验证面**：浏览器里 `isClient()` 为 false，走的是
   localStorage 分支，**Rust 探测分支只在 Tauri 里才走到**。
2. **Flutter 客户端（`app/`）仍是 v1 归档**，用的是 `api_client.dart` 的 dio，
   默认 `http://10.0.2.2:8000/api/v1`。它**没有**接 `api_probe`，
   也不走 `system/health`。本次打通覆盖的是 Tauri + React 这条主链。
3. **数据库型功能仍未实测**。本机没起 Postgres/Redis，`/system/health?deep=1`
   只验证了"连不上时返回 200 而不是 500"，没验证连上时的路径。
4. **心跳是固定 60s**，没有做「离线时加速重试」。当前实现里 `installConnectionWatch`
   两种状态同频；离线时其实该更快重试（后端可能正在启动）。
5. **没有断线重连的 UI 提示**。用户在后端重启期间操作，只会看到一次性报错。
   浏览器验收证明了断网后指示灯会变红，但页面内容本身没有「点击重试」入口。
6. **单文件脚本没进 CI**。`verify_integration.py` 需要后端在跑，
   CI 里要么加 service container，要么退化成静态检查。
7. **Rust 侧单测已补齐并跑通**（`cargo test --lib` 32 passed），
   但**仍未做真客户端（.exe / .apk）的人工验收**——见第 1 条。

## 11. 下一步建议

优先级从高到低：

1. **在有桌面会话的机器上跑一次真客户端验收**：起 `.exe` → 看顶栏圆点 →
   点设置看健康卡片 → 进「考研手札」看题库加载 → 判一道题。
   （Rust 单测已补齐，见第 9.1 节。）
2. **补离线加速重试 + 断线重试入口**（第 10 节第 4、5 条），这两条是真实用户最常撞的。
3. **Flutter 客户端接 `system/health`**，让 v1 客户端也能判断后端状态。
4. **`verify_integration.py` 进 CI**：起一个 uvicorn service container，
   把 37 项作为 PR 门禁。
5. 数据库型功能做一次带 Postgres 的完整走查（内容/练习/进度/账号四条线）。
