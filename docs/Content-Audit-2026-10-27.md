# CppMind 内容与合作链路体检报告

> 体检时间：2026-10-27
> 范围：`content/`（15 个内容学科）、前端 13 学科呈现、AI 助手、登录与会话、考研/就业链路
> 口径：全部为**磁盘实扫**（`content/` 2917 个文件逐条解析 + 前端 `data/exercises.ts` / `data/bundle.ts` 解析），非引用文档结论。
> **结论先行：内容"骨架"完整（138 章 7 类内容齐备），但"可判题 + 可到达"两个环节严重缺失——344 道编程题只有 39 道能自动判分，agent/ml 两个学科 24 章 144 题完全没有入口，且既有文档声称的 53.8% 可判率与磁盘不符（实际 11.3%）。**

---

## 一、13 学科逐科体检

`SUBJECTS`（`frontend/src/lib/subject.ts`）定义 13 个学科；`BUNDLE.chapters` 只有 12 个键（`clang` 走 `clangUnits.ts` 特判）。
"有效题"= 能通过 `seed_and_import_bank.py` 的 `clean_items()`（编程题须有 `test_cases`；选择题答案须落在选项里）。

| 学科 | 章 | 题库 | 有效题 | 有效率 | 可判编程题 | 面试题 | 项目 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| C / C++ (cpp) | 20 | 130 | 100 | 77% | 2 / 27 | 82 | 20 | 章最全，**编程题几乎不可判** |
| C 语言 (clang) | 7 | 46 | 27 | 59% | 0 / 15 | 25 | 7 | **无 `_manifest.json`**，编程题 0 可判 |
| Java (java) | 9 | 66 | 56 | 85% | 10 / 20 | 45 | 9 | 相对健康 |
| Spring (spring) | 8 | 56 | 44 | 79% | 1 / 13 | 41 | 8 | 编程题基本不可判 |
| Python (python) | 8 | 60 | 26 | **43%** | 0 / 23 | 42 | 8 | **11 道选择题答案非法**，编程题 0 可判 |
| 全栈 (fullstack) | 8 | 64 | 38 | 59% | 0 / 26 | 45 | 8 | 编程题 0 可判 |
| 数据库 (database) | 8 | 58 | 51 | 88% | **18 / 25 (72%)** | 40 | 8 | **全库最健康** |
| 中间件 (middleware) | 8 | 58 | 32 | 55% | 0 / 20 | 40 | 8 | 6 道选择题非法 |
| AI / Agent (ai) | 8 | 63 | 33 | 52% | 0 / 20 | 48 | 8 | 10 道选择题非法 |
| 大数据 (bigdata) | 6 | 42 | 32 | 76% | 5 / 15 | 30 | 6 | 章数偏少 |
| 数据分析 (data) | 6 | 42 | 20 | **48%** | 0 / 15 | 32 | 6 | 7 道选择题非法，章数偏少 |
| 计算机基础 (fundamentals) | 12 | 87 | 49 | 56% | 0 / 32 | 59 | 12 | **32 道编程题全不可判**，量最大缺口 |
| 工具链 (tooling) | 6 | 46 | 14 | **30%** | 3 / 21 | 35 | 6 | **有效题最少**，14 道选择题非法 |
| **13 学科小计** | **114** | **818** | **522** | **63.8%** | **39 / 344** | **564** | **114** | — |
| *AI Agent 专项 (agent)* | *16* | *96* | *16* | *17%* | *0 / 48* | *64* | *16* | **有内容、无入口、几乎不可用** |
| *机器学习 (ml)* | *8* | *48* | *8* | *17%* | *0 / 24* | *32* | *8* | **有内容、无入口、几乎不可用** |
| **全库合计** | **138** | **962** | **546** | **56.8%** | **39 / 344** | **660** | **138** | — |

### 三个"结构性问题"（不是数量问题）

1. **可判率 11.3%，且 9 个学科为 0**
   `344` 道 coding 题里只有 `39` 道带 `test_cases`（database 18、java 10、bigdata 5、tooling 3、cpp 2、spring 1）。
   agent / ml / fundamentals / fullstack / python / ai / middleware / clang / data **一题都没有**。
   前端 `isJudgeReady()` 的降级是"只能自由运行"（不崩溃，但没有对错反馈）——
   **学生做完题得不到判定结果，练习闭环断裂**，这是"服务就业"最直接的硬伤。

2. **文档与磁盘严重脱节（虚报）**
   `docs/JUDGE-COVERAGE-2026-10-26.md` 写"含 test_cases 185 / 344，可判率 53.8%"，并称 native 补题写回 22 道。
   实测 `content/` 为 **39 / 344（11.3%）**，`git status` 干净 —— 那批成果**从未落盘或已丢失**。
   `content/_coverage.json` 同样过期：写 `total_chapters: 136 / incomplete 6 / missing agent-ch01、ch02、ch04、ml-ch04~08`，
   但磁盘上这些章节**全部存在且 7 类齐备**（实际 138 章 / 0 缺失）。

3. **agent + ml 是孤儿内容**
   两个学科 24 章、144 题、96 条面试题、16 个项目章节，`_manifest.json` 与 7 类内容齐全，
   但 `SUBJECTS` 只有 13 个、`BUNDLE.chapters` 只有 12 个键、题库按 `useSubject()` 过滤 ——
   **这 144 题在 UI 上永远选不到**。且其有效率仅 17%（96→16、48→8），即使接入口也几乎不可用。

### 选择题数据 bug 可精确修复（111 道）

`bad_choice`（答案不在选项里 / 选项少于 2 个 / 无答案）共 **111** 道：
agent 32、ml 16、tooling 14、python 11、ai 10、data 7、middleware 6、fundamentals 6、cpp 5、clang 4。
这是**数据错误**而非内容缺口，补答案或修选项即可，修复成本低、收益立竿见影。

---

## 二、考研 / 就业链路

| 链路 | 资产 | 状态 |
|---|---|---|
| 考研题库 | 6 类考试（408 / 数学 / 英语 / 政治 / 离散 / 算法），11 个科目，**435 题** | ✅ 完整 |
| 模拟套卷 | **74 套**，498 个题位（344 引用题库 + 154 内联），**0 悬空 id** | ✅ 完整 |
| 考研入口 | `GuidesPage` 的「题库」tab 内嵌 `ExamPage`（框架 / 套卷 / 训练三视图） | ✅ 可达 |
| 就业面试 | **660 条**面试题（13 学科 564 + agent/ml 96） | ✅ 数量充足 |
| 就业项目 | **110 个**项目 / 4030 小时 / 13 条 track / T1–T4 梯度 | ✅ 完整 |
| 考研 ↔ 学科 | 两轴**各自独立**，学 `cpp` 时看不到本章对应的 408 考点 | ⚠️ 未打通（设计选择，非 bug） |

考研侧数据质量高（0 悬空引用、原创声明齐全、cover 每科 26–49 题），
问题不在"有没有"，而在**学科学习页与考研考点之间没有交叉跳转**——学生要自己意识到"学到指针了，该刷 408 的哪道题"。

---

## 三、AI 助手

| 环节 | 现状 |
|---|---|
| 后端 | ✅ **完整实装**：`POST /api/v1/ai/chat` SSE 流式（meta/delta/error/done）、RAG 课程检索锚定、会话落库、每日配额、6 模式 PROMPTS、DeepSeek/OpenAI/Claude 三 provider |
| 密钥 | ✅ `server/.env` 已配 `deepseek_api_key`，默认 `ai_provider=deepseek` |
| 前端（修前） | ❌ **纯本地桩**：`send()` 只回一段`【本地引导兜底】`文案，从未发请求 |
| 一级入口（修前） | ❌ `AiPage.tsx` 存在但**未被 `App.tsx` 引用**，`NAV_GROUPS` 也没有 `ai` 项 → 死页面 |
| 契约隐患 | ⚠️ 前端 UI 用 `dl`，后端 `AIMode` 枚举是 `dl_guide` → 直接传会 `ValueError`（500） |

**本次已修**：新增 `lib/aiChat.ts`（SSE 解析 + 模式映射 + 错误分类）、`AiPanel` 改为真实流式、
`AiPage` 接入 `App.tsx` 与侧导航、未登录/离线/配额三种态分别提示、失败回退本地引导、支持中断。

---

## 四、登录与会话

| 环节 | 现状 |
|---|---|
| 后端 | ✅ `/auth/register`、`/auth/login`、`/auth/refresh`、`/users/me` 完整；限流 Redis **fail-open**（无 Redis 也能登录） |
| 前端逻辑 | ✅ `lib/session.ts` 完整：令牌持久化、401 自动续期并重放、离线态、`probe` 启动探测 |
| 入口形态 | ✅ 内嵌在「个人闯关档案」，展开式表单（登录/注册切换），符合"登录是可选增强、不登录也能用"的设计 |
| 缺陷① | 登录成功后 `pullProgress()` 被调 **两次**（`session.login` 的 `onSignedIn` 钩子 + `ProfilePage.submit` 各一次）→ 已修 |
| 缺陷② | 输入框写"邮箱或手机号"，但注册**只写 email、从不写 phone** → 手机号永远登不上。已改为"邮箱"（诚实文案） |
| 缺陷③ | 无「忘记密码/重置」流程（后端也无对应接口） |
| 缺陷④ | AI 需要登录，但登录入口在「我的」页深处，AI 面板原先无引导 → 已加"去登录"按钮 |

---

## 五、其他缺陷

| # | 问题 | 级别 | 说明 |
|---|---|---|---|
| 1 | `components/SideNav.tsx` 是**死代码** | P2 | 定义了 `practice/resources/ai` 8 项导航，但无人 import；实际导航是 `lib/nav.ts`。两套定义易误导后续开发 |
| 2 | `clang` 缺 `_manifest.json` | P2 | 其余 14 学科都有；clang 靠 `clangUnits.ts` 前端特判，前后端数据结构不统一 |
| 3 | 每个学科只有 6–20 章，bigdata/data/tooling 仅 6 章 | P2 | 对"就业"而言 6 章偏薄（如大数据只有 6 章，覆盖不到 Spark/Flink 工程面） |
| 4 | `_coverage.json` / `JUDGE-COVERAGE` 文档过期或虚报 | **P1** | 会误导后续开发判断（本次即因此浪费了核查成本） |
| 5 | `content/` 中 8 处 `�` / `锟斤拷` | — | **假阳性**：全部位于"编码/解码"教学章节，是刻意的解码失败示例，无需修 |

---

## 六、修复优先级与建议路线

### P0（决定"能不能用"，建议本周）

1. **补编程题用例，先把 database/java 之外的 9 个学科从 0 拉起来**
   不是 344 道全补（纯函数型 C/Java 无 `main`，自动生成易污染基准），而是**按学科分批**：
   先 `cpp(27)` + `fundamentals(32)` + `python(23)` + `java 剩余(10)` = 92 道，覆盖最核心就业科目。
   建议方式：`reference_code` 缺失的先补参考实现 → 本地真实编译运行取 `expected_output`（绝不手工编造）。
2. **修 111 道非法选择题**（agent 32 / ml 16 / tooling 14 / python 11 / ai 10 / data 7 / middleware 6 / fundamentals 6 / cpp 5 / clang 4）
3. **决定 agent/ml 归属**（二选一，见下）
4. **重算 `_coverage.json` + 更正 `JUDGE-COVERAGE` 文档**，消除虚报

### agent/ml 的两个方案（需产品决策）

- **方案 A：并入 `ai` 学科**（推荐）
  `ai` 的 label 本就是「AI / Agent 开发」，项目库 track `ai` 的 12 个项目已含 agent 项目。
  做法：`BUNDLE.chapters.ai` 纳入 agent/ml 的 24 章（按 group 分层：AI 基础 / Agent 工程 / ML），
  `SUBJECTS` 保持 13 个不变。**代价：ai 变成 32 章 207 题，学习路径偏长。**
- **方案 B：扩成 15 学科**
  `SUBJECTS` 加 `agent`、`ml` 两项，题库与 bundle 同步。
  **代价：与"13 学科"的既定口径冲突，且这两科有效题只有 24 道，扩出去会更空。**

### P1（决定"好不好用"）

5. **学科 ↔ 考研交叉跳转**：章节页加「本章 408 考点」入口（`_exam/knowledge` 已有 11 份考点矩阵可直接映射）
6. **补 Python/tooling/data 的低有效率**（43% / 30% / 48%），主要是非法选择题
7. **忘记密码流程**（后端 `POST /auth/reset-request` + 邮件，或先做"管理员重置"）

### P2（工程整洁）

8. 删除 `SideNav.tsx` 死代码（或让它成为唯一导航源，与 `nav.ts` 二选一）
9. 给 `clang` 补 `_manifest.json`，与其余 14 学科结构对齐
10. 扩展 bigdata/data/tooling 到 8–10 章

---

## 七、本次已修复（代码层，`tsc --noEmit` 通过）

| 文件 | 改动 |
|---|---|
| `frontend/src/lib/nav.ts` | `KmPage` 增加 `'ai'`；`NAV_GROUPS` 增加「AI 助手」导航项 |
| `frontend/src/App.tsx` | 引入并在 `page === 'ai'` 渲染 `AiPage`；给 `AiPanel` 传 `onRequireLogin` |
| `frontend/src/lib/aiChat.ts` | **新增**：`/ai/chat` SSE 客户端，含 `dl → dl_guide` 模式映射、帧解析、错误分类（未登录/配额/离线） |
| `frontend/src/components/AiPanel.tsx` | 重写 `send()` 为真实流式；未登录提示 + 去登录；失败回退本地引导；支持"停止"中断；显示剩余配额 |
| `frontend/src/pages/AiPage.tsx` | 改为受控入口页，显示真实会话状态、提供去登录；移除"尚未接入后端"的过时文案 |
| `frontend/src/pages/ProfilePage.tsx` | 去掉登录后重复的 `pullProgress()`；"邮箱或手机号" 改为 "邮箱" |

---

## 八、口径说明（便于复现）

- 章节数 = `content/<subject>/<chapter>/` 目录数（`_manifest.json` 与磁盘 100% 一致，0 漂移）
- "7 类齐备" = `goals.md` + `pitfalls.md` + `exercises.json` + `interview.json` + `project.json` + `concept/` + `examples/` 全部存在
- 有效题 = 通过 `clean_items()`：coding 必须有非空 `test_cases`；choice 至少 2 个选项且答案 ∈ 选项
- 可判编程题 = coding 题中 `test_cases` 非空的数量（前端 `isJudgeReady` 还要求 `lang` ∈ JUDGE_LANGS）
- 模拟卷题位 = `papers/*.json` 的 `sections[].items` 展开数（字符串为题库引用、对象为内联题），0 悬空即全部可解析
