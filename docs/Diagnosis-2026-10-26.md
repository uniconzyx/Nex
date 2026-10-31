# CppMind / Nex 可运行应用诊断与框架评估

> 诊断时间：2026-10-26
> 范围：FastAPI 后端 + React/Vite 前端 + Tauri v2 桌面端 + Flutter 移动端 + go-judge 判题侧车
> 结论先行：**技术框架选型合理，不需要推翻重写；当前阻塞点是“可运行产品链路”没有闭环——依赖未安装、数据库未初始化、客户端主线未收敛、端到端未验收。**

---

## 一、当前已具备的正确资产（不要动）

- **前端连接层**（`frontend/src/lib/api.ts` + `clientBridge.ts`）：统一基址（客户端探测 > localStorage > 默认 `127.0.0.1:8000`）、401 自动续期、健康探测、离线主动上报，设计完整。
- **考研三视图**（框架/套卷/训练）前端已通过 `tsc --noEmit` 与 `vite build`。
- **Redis 生产 fail-closed**（进度报告 P2）已实现并提交。
- **判题可判率** Python 题已补至 **47.4%（163/344）**，`test_cases` 结构全部合法。
- **分类总结** 73 个 group 的 `suggestedOrder` 已填真实题号、0 悬空 id。
- **内容 11 学科文件就绪**；go-judge 侧车二进制已在 `src-tauri/binaries`。

---

## 二、问题诊断表（按优先级）

| # | 问题 | 影响 | 优先级 | 根因 | 纠正动作 | 验收标准 |
|---|---|---|---|---|---|---|
| 1 | 后端依赖未装在 venv | 后端起不来，`dev_stack --check` 报缺 fastapi | **P0** | 无 `server/.venv`，依赖从未安装 | 增加 setup 脚本装 `requirements.txt` 到 venv；`dev_stack` 自动建/用 venv | `dev_stack --check` 通过；`uvicorn` 能起且 `/health` 返回 200 |
| 2 | 数据库未初始化 | 登录/进度/判题接口 500 | **P0** | PG 表未建，缺迁移或 init 未接启动链 | `init_db.py` 或 Alembic；`dev_stack` 启动时自动 init | `/health?deep=1` 通过；能注册/登录 |
| 3 | 客户端主线未收敛 | 不知道“哪个才是可运行产品” | **P1** | 并存 React / Tauri / Flutter / web-preview 四条线 | 明确：桌面主线 = Tauri 内嵌 React；移动 = Flutter 另线；web-preview = 调试沙箱（不入库） | README 写明每条线启动命令与产物 |
| 4 | C/Java 补题未落盘 | 可判率停在 47.4%，`cpp`/`clang` 0 题 | **P1** | 生成脚本写回解包 bug，实际 0 文件写入（content 无改动） | 修复 `_gen_test_cases_native.py` 重跑；提交 content | content 改动提交；覆盖率上升 |
| 5 | 判题侧车未入库 | 打包/CI 缺二进制 | **P1** | `.gitignore` 忽略 `src-tauri/binaries/` | CI 增加拉取/构建 go-judge 步骤 | release 流程能产出 sidecar |
| 6 | 端到端验收缺失 | 不知道真能跑通 | **P1** | 没从 0 跑过“后端+前端+Tauri”全链路 | 写 e2e / browser 验收脚本并固化 | 启动→登录→做题→判题 全过 |
| 7 | 进度报告文档过时 | 误导后续开发 | **P2** | 多处与代码现状不符（如“分类总结缺顺序字段”实际已完成） | 同步实际状态 | 文档与代码一致 |
| 8 | 仓库根误建 `x` 文件 | 工作树脏 | **P2** | 调试期间误建（1 字节） | 删除 | `git status` 干净 |

---

## 三、框架合理性评估

**结论：选型合理，建议沿用，问题在工程化闭环而非架构。**

- **FastAPI + React/Vite + Tauri v2 + Flutter**：成熟组合。Tauri 比 Electron 轻、用系统 WebView；React 生态成熟；Flutter 覆盖移动端；FastAPI 异步高性能。
- **判题走 go-judge sidecar（沙箱隔离）**：正确架构——代码执行必须在隔离沙箱，不能进主进程。
- **内容双轨**：文件型（考研题库，静态可版本化）+ DB 型（用户/进度，动态）——合理，前者零运维、后者支持多端同步。
- **前端连接层**：基址解析优先级、401 续期、离线感知，工程成熟度高于一般个人项目。

**需要补的工程化（非架构问题）**：依赖安装闭环、DB 迁移、客户端主线文档、CI 门禁、端到端验收。

---

## 四、打通“可实际运行应用”的实施顺序

- **Phase A — 依赖与数据闭环（P0）**：装 server 依赖到 venv；确认 PG/Redis 本地可用（docker 或本机）；`dev_stack` 一键起后端+DB；`/health?deep=1` 通过。
- **Phase B — 桌面客户端主线（P1）**：以 Tauri 内嵌 React 为桌面主线；本地 `tauri dev` 起；确认 go-judge sidecar 被拉起、`api_probe` 探测到后端。
- **Phase C — 端到端验收（P1）**：浏览器/桌面跑通 登录 → 浏览题库 → 做题 → 判题得反馈 全链路；固化 `browser_acceptance`。
- **Phase D — 补题完整化（P1）**：修复并重跑 C/Java 补题脚本，把可判率再推高，提交 content。
- **Phase E — 移动端另线（P3）**：Flutter 接同一后端 API（`api.ts` 已支持回环/局域网地址），独立排期。

---

## 五、建议下一步

建议从 **Phase A** 开始，先把“后端能一键起来 + 数据库可用”这关过掉——这是后面一切的地基。是否开始执行？
