# CppMind / Nex 项目进展报告

> 生成时间：2026-10-23（基于磁盘 + git 实测，非仅靠记忆）
> 口径：已交付 = 已提交稳定；磁盘完成 = 文件已产出但未提交；缺口 = 待实现。

## 0. 一句话结论

内容平台 **Nex v1.0 已发布**（13 学科 114 章 + AI 助手 + 双来源 + 桌面/移动打包）；**Agent 16 章与考研题库已在磁盘产出但全部未提交**；考研**后端 API 已就绪、前端三视图仍未建**；服务端 20+ 文件处于未提交改动态，需尽快固化为提交。

---

## 一、已交付（git 已提交、稳定）

- **Nex v1.0 内容平台**：commit `03348f2`「13学科114章内容平台 + AI助手 + 双来源 + 打包链路」。
- **打包链路**：`Nex-Launcher`（Windows .exe 本地启动器 + Android .apk 云端构建 CI），已修 Dart/FVM/依赖声明等云构建错误。
- **AI 助手链路**：DeepSeek 调用 + 判题台（go-judge）+ Pyodide 前端沙箱 + 三件套（悬浮球 / 对话页 / 判题内嵌）。
- **学习路线图对标**：`docs/Roadmap-Alignment.md` —— 10 仓库基线 + 本轮新增「AI Agent 路线（Stage 0~6 逐级对标 16 章）」「考研大纲全科目 + B站资源」（8 仓库 GitHub API 实测、考研 B站 UP主 WebSearch 检索）。

---

## 二、磁盘已完成、尚未提交（风险项）

| 内容域 | 状态 | 规模 |
|--------|------|------|
| `content/agent/` | `??` 未跟踪 | 16 章全 complete（每章挂真实 GitHub + B站关键词） |
| `content/_exam/` | `??` 未跟踪 | 395 题 / 260 知识点 / 73 分类总结 / 89 套卷；磁盘 122 个 json |
| `content/ml/` | `??` 未跟踪 | 8 章 |
| `content/_guides/` `_projects/` 等 | `??` 未跟踪 | 指南 / 职业库 |
| 服务端 20+ 文件 | ` M` 已修改 | ai / progress / router / config / redis / main / models / schemas / docker-compose / init_db 等 |

> 说明：四科设计题已回填 id（`q-ds-design-01~12`、`q-os-design`、`q-cn-design`），属 `_exam` 未提交内容的一部分。

---

## 三、功能就绪但链路不完整

- **考研后端 API**：`server/app/api/v1/exam.py` 存在于代码树、`router.py` 已 `include_router(exam.router)`、`server/tests/test_exam_api.py` 存在（10 条）。读接口 12 端点 + 无状态判分已实现。**但前端消费链路缺失**（见缺口 P0）。

---

## 四、关键缺口 / 待办（按优先级）

| 优先级 | 事项 | 现状 |
|--------|------|------|
| **P0** | 考研前端三视图 | `ExamPage`、`gen_exam_bundle.py`、`exam.ts`、前端 exercises 接入 exam 数据——PRD 注明尚未创建。后端已就绪，**前端是阻塞点** |
| **P0** | 未提交工程固化 | agent / _exam / ml / guides / projects 内容 + 20+ 服务端文件未提交，存在丢失/冲突风险，建议分批改提交 |
| **P1** | 判题可判率 | Phase15 遗留：272 道编程题仅 39 道有 test_cases（14%），目标 40%+；JS/SQL/Shell 189 题两端无运行时（需 Node 沙箱 + 嵌入式 SQL 引擎） |
| **P1** | 分类总结加「建议做题顺序」 | 73 份分类总结已生成，缺做题顺序建议字段 |
| **P2** | Redis 生产 fail-closed | 生产 Redis 不可用应失败关闭，而非静默降级 |
| **P2** | CI 门禁 | 缺单测 / 集成门禁（阶段9 遗留） |
| **P3** | cpp 学科深度补齐 | 并发 / 工程化章节外部资料薄 |
| **P3** | AI Agent GAIA 评估实操 | ch15 项目未强制 GAIA 跑分（见 `Roadmap-Alignment.md` 9.3） |

---

## 五、下一步建议（落地顺序）

1. **立即**：把 `content/agent`、`content/_exam`、`content/ml` 内容先提交；再把 20+ 服务端 `M` 改动分批改提交（先内容后服务，降低冲突面）。
2. **接着**：实现 `gen_exam_bundle.py` → `exam.ts` → `ExamPage` 三视图（框架 / 套卷 / 训练），打通考研前端，释放已就绪的后端 API 价值。
3. **并行**：补 test_cases 提升可判率；引入 Node 沙箱 + 嵌入式 SQL 引擎补 JS/SQL 判题；分类总结加做题顺序；Redis fail-closed；补 CI 门禁。

---

*本报告的规模数字来自 2026-10-21 日志与 2026-10-23 磁盘/git 实测交叉核对。*
