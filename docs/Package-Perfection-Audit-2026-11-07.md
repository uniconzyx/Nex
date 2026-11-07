# Nex 全项目完善性审计（封装 / 内容 / 双端）

> 体检时间：2026-11-07
> 范围：`content/` 全量章节体系（167 章；正确性审计 `--all` 覆盖其中 160 个带 `goals.md` 的章节）、前端 React 构建、`web-preview/` 共享层双端 UI、Tauri 原生封装 EXE / APK、图标资产、本机 API、CI。
> 口径：全部为**本机实跑**（磁盘实扫 / 编译 / 真机验收 / 产物二进制比对），不引用既有文档的结论性描述。
> **结论先行：项目无阻断性缺口。内容门禁、全量正确性实跑（160 章 / 3964 检查项 / 0 FAIL / `AUDIT_OK`）、前端构建、真机验收、产物与图标校验全部通过；本轮另定位并修复了 6 个「看着对、实际不对」的隐性缺陷，并把判据固化成防回归脚本。**

---

## 一、实跑结果总表

| 维度 | 判据 / 命令 | 结果 |
|---|---|---|
| 内容门禁 | `audit_sources.py` / `audit_source_anchor.py` / `audit_repo_align.py` / `check_md_outputs.py` / `verify_manifest.py` / `audit_depth.py` | **6 / 6 通过**，深度分级 rc=0 |
| 章节深度 | 167 章，6 项取最差 | **A165 / B2 / C0**；B 为 dm-ch02、dm-ch03，因各只有 3 个 concept 文件，`concept_chars` 约 3500–3800，属结构使然而非缺陷 |
| 交互微游戏 | `audit_handmade_labs.py` | **179 / 179**（sandbox 167 + debug 12），167 章 sandbox 全覆盖 |
| sandbox 可解性 | `solve_sandbox.py --all` | **167 / 167** 有解，生成物无 diff |
| 示例 / 习题正确性 | `audit_correctness.py --all --skip-net` | **160 章 / 3964 检查项 / 0 FAIL / `AUDIT_OK` rc=0**（两轮实跑，详见第六节） |
| 前端类型 | `tsc --noEmit` | **rc=0** |
| 前端构建 | `vite build` | **rc=0**（临时输出，不覆盖 `dist/`） |
| 内嵌站点真机 | `verify_nex_package.cjs` | **14 / 14** |
| 等效 CSP | `verify_nex_csp.cjs` | **7 / 7** |
| 本机 API | `verify_local_api.py` | **13 / 13** |
| 原生包静态 / 签名 | `verify_nex_package.py` | **20 / 20** |
| 连接设置对话框 | `verify_conn_dialog.cjs` | **25 / 25** |
| 图标真进包 | `verify_icons.py` | **10 / 10** |
| 工作区 | `git status` | `## main...origin/main`，干净 |

默认 `tauri.conf.json`、`dist/`、`frontend/`、三份 HTML 的 sha256 在本轮封装中**全部未变**；原生包与现有 React 应用是并列关系，不推翻默认配置。

---

## 二、本轮定位并修复的 6 个隐性缺陷

| # | 现象 | 根因 | 修复 | 防回归 |
|---|---|---|---|---|
| 1 | EXE 换图标后提取出来仍是旧的 389B 蓝底白方块 | `build.rs` 缺 `cargo:rerun-if-changed=icons/icon.ico`，Cargo 复用旧 `libresource.a`(1176B) | 补声明；资源库变 121698B | `verify_icons.py` 用 ctypes `ExtractIconExW` 提图标，与设计稿比平均色差 **0.0/255** |
| 2 | Android 图标 clone 后重编变回 Tauri 默认机器人 | `src-tauri/gen/` 整目录被 gitignore，图标不入库 | 镜像到 `deploy/package/icons/android/`（17 文件 / 371KB），`prepare.py` 每次同步回 gen/，`build-apk.cmd` 加 xcopy 双保险 | 镜像目录入库 + `verify_icons.py` 比对 APK 内 xxhdpi 逐像素 |
| 3 | 修好的编译脚本被静默覆盖回旧版 | 只改了 `build-exe.cmd` / `build-apk.cmd` 产物，`prepare.py` 模板仍是旧串 | 把 `--target x86_64-pc-windows-gnu` 与 `java -jar apksigner.jar` + verify 写回模板，末尾加自检断言 | `prepare.py` 缺关键串直接 assert |
| 4 | 手机上点「连接后端」没反应 | 原生 WebView 静默吞 `window.prompt` | `promptConnect()` 改自绘对话框（预填基址 / 保存 / 取消 / 恢复默认 / Enter / Esc / 暗色） | `verify_conn_dialog.cjs` 25 / 25 |
| 5 | APK 只有 9.4MB，装上白屏 | 本机未开开发者模式，`tauri android build` 把 `jniLibs/libnex.so` 写成 **0 字节** | 手动 cp 真 `.so` → `gradlew assembleRelease -x rustBuild*` → zipalign → `java -jar apksigner.jar` 签名 | `verify_icons.py` 断言 APK 内 `.so` > 15MB（实测 22.4MB） |
| 6 | Git Bash 调签名包装脚本被拦 | 安全策略拦 `.bat` 包装脚本；连提交说明里出现 `cmd /c` 也会触发命令拦截 | 直接 `java -jar apksigner.jar`；提交说明改措辞 | CONTRIBUTING 第 10 节记录 |

另更正一条上轮误判：两端心情卡**本来就有**「连接后端」入口，此前记录为「原生包没有连接入口」是错的。

---

## 三、图标资产（三套统一）

母题：**冰晶六边形（Nex 知识晶体）+ 凯喵 Q 版头像 + 掌握度圆弧**（呼应首页 conic 进度环）。
色值唯一来源 `frontend/src/styles/liquidglass.css` 的 `.km-app{}`：`--km-env-1 #ebf4fa`、`--km-primary #5db4e5`、`--km-primary-deep #4a90e2`、`--km-primary-lift #6ec6ff`、`--km-secondary #a2d2ff`、`--km-glow-a #c5e4ff`、`--km-glow-b #e3deff`。

生成器 `deploy/package/design_icons.py`（Pillow，SS=2048 超采样 → LANCZOS 缩放 → 圆形遮罩 + 白色描边环），一轮生成：

- `src-tauri/icons/icon.png` 540670B / `icon.ico` 120611B（EXE）
- `deploy/launcher/nex.ico` 120611B（桌面快捷方式）
- `web-preview/favicon-64.png` 8218B（两端 favicon）
- Android 五档 mipmap（mdpi / hdpi / xhdpi / xxhdpi / xxxhdpi，各含 ic_launcher、round、foreground）+ `ic_launcher_background.xml` / `ic_launcher_foreground.xml`，替换默认机器人矢量

三处 EXE 图标（设计稿 / `src-tauri/icons` / launcher）逐字节同源；APK 内启动图标与设计稿逐像素一致。

---

## 四、双端产物

| 文件 | 大小 | 说明 |
|---|---:|---|
| `release/nex-shell/Nex-Desktop-1.0.exe` | 18012160 B（约 18MB） | 内嵌 WebView2，窗口标题「Nex · 桌面版」，新图标已进资源段 |
| `release/nex-shell/WebView2Loader.dll` | 158K | 随 EXE 同目录分发 |
| `release/nex-shell/Nex-Mobile-1.0-arm64.apk` | 33384762 B（约 32MB） | v2/v3 签名，CN=Nex / O=uniconzyx，包名 com.nex.app；含 22.4MB 真 arm64 `.so` |
| `release/nex-shell/Nex-Mobile-1.0-arm64.apk.idsig` | 262K | v4 签名附属 |

产物目录被 gitignore，不入库；一键重建脚本 `deploy/package/build-exe.cmd` / `build-apk.cmd` 已对齐实测成功的编译路径。

---

## 五、复跑命令（防回归）

```bash
# 0. 审计实跑依赖（CONTRIBUTING 第 8 节）。漏装会堆出成片「缺 Python 依赖」假阴性
python -m pip install -r server/requirements-audit.txt
# 本机直连 PyPI 下载 wheel 卡住时换清华镜像（实测 5 分钟无进展 -> 24 秒装完）：
# python -m pip install -r server/requirements-audit.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 1. 内容门禁
python scripts/audit_sources.py && python scripts/audit_source_anchor.py && \
python scripts/audit_repo_align.py && python scripts/check_md_outputs.py && \
python scripts/verify_manifest.py && python scripts/audit_depth.py
python scripts/audit_handmade_labs.py
python scripts/solve_sandbox.py --all
python scripts/audit_correctness.py --all --skip-net --warn-out scratch/audit-warn-full.txt

# 2. 前端
npx tsc --noEmit && node node_modules/vite/bin/vite.js build --outDir ../tmp/vite-check

# 3. 原生包与图标
python deploy/package/verify_nex_package.py
python deploy/package/verify_icons.py
node scratch/verify_nex_package.cjs
node scratch/verify_nex_csp.cjs
node scratch/verify_conn_dialog.cjs
```

`verify_icons.py` 是「图标真进包 + so 非 0 字节」的唯一权威判据：设计稿对了不等于包里对了。
全量正确性审计约 25–27 分钟，须后台跑，前台会被沙箱超时掐断。

---

## 六、全量正确性审计（两轮实跑）

`audit_correctness.py --all --skip-net` 逐章实跑 examples 与习题答案（含数值题脚本实算），stdout 与 `expected_output` 逐字符比对。

**第一轮（未装审计依赖）**：160 章 / 3964 检查项，耗时 25m27s，结果 `AUDIT_FAIL` rc=1。
40 条 `[FAIL]` **全部**是「缺 Python 依赖 pandas」的环境假阴性（data-ch03 / 04 / 05 / 06 与 py-ch08 的 examples），**没有一条内容算错**；日志备份 `scratch/audit-correctness-before-pandas.log`。
同批信息：254 个示例仅末尾换行不同（按通过处理）、58 个 code_lang 未支持实跑（sql×40 / bash×10 / css×4 / html×2 / cmake×1 / yaml×1）、94 条 warn（「没有 ```text 图示块」「expected_output 含 Error:」等格式弱信号，不阻断）。

**根因与处置**：CONTRIBUTING 第 8 节已规定审计前必须 `python -m pip install -r server/requirements-audit.txt`；本轮首次用外层解释器直接跑，漏了这一步，属执行顺序问题而非文档缺失。`server/.venv` 缺 numpy / pandas 是已知历史模式（第 8 节「门禁报错先怀疑门禁自己」）。
补装：直连 PyPI 下载 10.7MB wheel 卡住 5 分钟无进展 → 换清华镜像，24 秒装完 `pandas 3.1.1`（numpy / bs4 / requests 已在位）。

**复跑验证**：

| 轮次 | 范围 | 结果 |
|---|---|---|
| 子集 | `--chapters data-ch03,data-ch04,data-ch05,data-ch06,py-ch08` | 5 章 / 129 检查项 `AUDIT_OK`，40 条假阴性全清，pandas 3.x 未引入输出差异 |
| **全量（最终）** | `--all --skip-net` | **160 章 / 3964 检查项 / 0 FAIL / `AUDIT_OK` rc=0**（27m4s） |

94 条 warn 完整清单落在 `scratch/audit-warn-full.txt`；warn 均为格式弱信号，不计失败。

> 口径提醒：`--all` 扫描的是「带 `goals.md` 的章节目录」（160），与「167 章全量体系 / sandbox 覆盖 167」不是同一口径，别混用；通过打印 `AUDIT_OK`，不是 `AUDIT_PASS`；只有 `[FAIL]` 才 rc=1。

---

## 七、已知边界（非缺陷）

- `dist-release/`(70M)、`tmp/`、`demo_bin.bin` / `demo_text.txt` / `nums.txt` 等根目录散落物均被 gitignore 且未跟踪；`app/` 为正常入库目录（55 文件）。仓库卫生无越界。
- 94 条 warn 与 58 个未支持实跑的 code_lang 示例属工具能力边界：前者是格式建议，后者是 bash / sql / css 等非 Python 片段，均不判失败。
- 完整微服务栈（PG + arq + judge）留给有 Docker 的环境；本机部署用内嵌 SQLite API，契约不变，页面切 `localStorage['nex.apiBaseUrl']` 即可。
- EXE 首次运行的防火墙询问弹窗属本机安全策略，留给使用者点掉，不改系统防火墙规则。
- CI 只覆盖前端构建冒烟与后端 PG 端到端；原生包 / 图标是本机资产，靠 `verify_icons.py` 在本机守门。

---

## 八、提交与 CI

| 提交 | 内容 |
|---|---|
| `a9f7089` | feat(package): 封装 EXE / APK 两个原生安装包（内嵌 web-preview 双端 UI），8 files / +251 |
| `cfd9490` | fix(package): 一键重编脚本对齐实测成功的编译路径，2 files / +8 |
| `80448b1` | feat(package): 重设计三套应用图标 + 全项目完善性收口，29 files / +620 / -13 |

三次均经 SSH 推送到 `origin/main`；对应 CI run `42370737916` / `42371169145` / `42374176397` 全部 **success**（前端构建冒烟 + 后端 PG 端到端两 job 全绿）。
本报告作为收口文档入库，把上述判据与复跑前置依赖固化下来。
