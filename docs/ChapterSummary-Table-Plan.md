# 章节完成总结表 · 完整方案（全学科覆盖 + 考研 408 / 复试 / 就业三专轨）

> 目标：把"每学完一章"的收尾升级为**结构化表格总结**，并建设三条专轨（**考研 408 初试 / 考研复试 / 就业八股**）；全部能力**覆盖所有学科**，且**场景化 = 工作中遇到的具体实例**、**逻辑链完整闭环**、**完工后自检**。
> 设计原则：复用 `progress.ts` / `logicChain.ts` / `content/*.json`；新增层纯函数、只读；**图表为独立资产**（DiagramsPage）。

## 一、方案目标与范围

| 项 | 说明 |
|---|---|
| 核心功能 | 章 `mastery===100` → 自动生成**单章总结表**；408 / 就业 / 复试 各生成专属视图 |
| **覆盖范围** | **全部学科**均启用单章总结表 + 场景化；考研 408 / 就业 / 复试 为叠加其上的**专轨**（不替代通用总结） |
| 复用资产 | `progress.ts`(状态) · `logicChain.ts`(`isUnlocked`/`done`) · `content/<s>/<ch>/*\.json` |
| 输出形态 | 应用内表格 + 一键**导出 Markdown 表格**（对齐 E 盘笔记习惯） |
| 非目标(本期) | 不重做状态机、不加后端接口、不改视觉品牌 |

## 二、触发时机

| 触发点 | 条件 | 动作 |
|---|---|---|
| 章节完成 | `doneChapters` 且 `mastery===100` | 渲染"本章总结"面板（仅本人达标后可见） |
| 408 章完成 | id∈`408.json` 且 `isUnlocked` | 更新 408 总表对应行 |
| 手动查看 | 任意已解锁章 | 可随时回看历史总结 |

> 不变量沿用 `Playability-Coherence-Plan`：三关是 `answers` 投影、`done⇔mastery100`，总结表统一走 `chapterStages()` + `masteryOfChapter()`。

## 三、单章总结表 schema（每学完一章 → 一张表，覆盖全部学科）

| 维度 | 数量/状态 | 你的完成度 | 关键条目（取内容前 3） |
|---|---|---|---|
| 目标 Goals | N 条 | — | 目标1 / 目标2 / 目标3 |
| 核心概念 Concepts | ≥3 | — | 概念1(ZWJ) / 概念2 / 概念3 |
| 易错点 Pitfalls | ≥3 | — | 坑1 / 坑2 / 坑3 |
| 例题 Exercises | X/Y 题 | 概念30+演练30 | 题id（未过红标） |
| 面试/真题 Interview | ≥3 | — | 面试题1 / 面试题2 |
| 实战 Project | 0/1 | 已通关/未 | 项目名 + `projectGate` |
| **总掌握度** | — | **100** | BOSS 通过、三关全绿 |

> 概念行单独附 **概念速查子表**（取自 `concept/*.md` 三视角标记）。**每一维均须带"工作场景"实例**（见第十三节）。

## 四、408 专轨设计（初试）

### 4.1 专轨元数据（`content/_tracks/408.json`，已写定，cross-walk 结果）

```json
{
  "trackId": "kaoyan-408",
  "name": "考研 408 计算机专业基础综合",
  "modules": [
    { "module": "数据结构",     "chapters": ["fund-ch01","fund-ch02","fund-ch03","fund-ch04","fund-ch05","fund-ch06","cpp-ch08","cpp-ch09"] },
    { "module": "计算机组成原理", "chapters": ["fund-ch07","fund-ch08"] },
    { "module": "操作系统",      "chapters": ["fund-ch09","fund-ch10","cpp-ch16"] },
    { "module": "计算机网络",    "chapters": ["fund-ch11","fund-ch12","mw-ch01","mw-ch02","mw-ch03","mw-ch04","mw-ch05","mw-ch06","mw-ch07","mw-ch08"] }
  ]
}
```

**学科进出 408 的边界（cross-walk 确认）**

| 学科 | 进 408? | 归到 408 哪块 | 说明 |
|---|---|---|---|
| `fundamentals` | ✅ | 四模块全覆盖 | ch01-06 数据结构；ch07-08 计组；ch09-10 OS；ch11-12 网络 |
| `cpp` | 部分 ✅ | 数据结构 / 操作系统 | 容器·算法(ch08/09)→数据结构；并发(ch16)→OS |
| `middleware` | 仅网络向 ✅ | 计算机网络（补充） | Redis/Kafka 属分布式，作 408 网络模块补充，非纯 OSI/TCP-IP |
| `data` | ❌ | — | NumPy/Pandas = 数据分析轨道，**非 408 数据结构** |
| `spring` | ❌ | — | Java 后端轨道，单列 |
| `tooling` | ❌ | — | Linux/Git/Docker 工程能力，非统考 |
| 其余 | ❌ | — | 不在 408 四门内 |

### 4.2 每章完成 → 408 考点总结表（单章表加一列）

| 章节 | 408 模块 | 对应考点 | 掌握度 | 关键图/公式 |
|---|---|---|---|---|
| fund-ch01 | 数据结构 | 线性表/链表 | 100 | 顺序表 vs 链表图 |
| fund-ch07 | 计算机组成 | 数据表示与运算 | 100 | 补码/浮点编码图 |
| fund-ch11 | 计算机网络 | TCP/IP 分层 | 100 | 协议栈图 |
| … | … | … | … | … |

### 4.3 408 总表（专轨视图，跨章汇总，备考用）

| 模块 | 章节数 | 已通关 | 平均掌握度 | 薄弱章(<60) | 冲刺建议 |
|---|---|---|---|---|---|
| 数据结构 | 8 | — | — | — | — |
| 计算机组成 | 2 | — | — | — | — |
| 操作系统 | 3 | — | — | — | — |
| 计算机网络 | 12 | — | — | — | — |

> "薄弱章"判定复用 `logicChain` + `mastery<60`，与首页 `nextAction` 同源。

## 五、数据来源与生成层

| 层 | 文件 | 职责 | 纯度 |
|---|---|---|---|
| 内容源 | `content/<s>/<ch>/{goals,concept,pitfalls,exercises,interview,project}.json` | 素材 | 只读 |
| 状态源 | `lib/progress.ts` → `ProgressState` | 完成度 | 只读 |
| 逻辑源 | `lib/logicChain.ts` | `isUnlocked`/`done` | 纯 |
| **新增** 生成 | `lib/chapterSummary.ts` | `buildChapterSummary` / `buildAllChapterSummaries` / `summaryToMarkdown` | 纯、无 dispatch |
| **新增** 轨道 | `lib/examTracks.ts` | 读 `TRACK_408` 按模块聚合 | 纯 |
| **新增** 内容切片 | `data/chapterContent.ts`（生成） | 章节正文切片（goals/pitfalls/concept/interview/project） | 只读，由 `scripts/gen_chapter_content.py` 生成 |
| **新增** 专轨数据 | `data/track408.ts`（生成） | 408 模块映射（前端不可直读 JSON） | 只读，由 `scripts/gen_tracks.py` 生成 |
| **新增** 就业 | `lib/employment.ts` | `buildInterviewGraph`（八股图） | 纯 |
| **新增** 复试 | `lib/reexam.ts` | `buildReexamView`（面试+机试） | 纯 |

> 纯函数层与 `logicChain.ts` 同构，便于 `verify_logic_chain.mjs` 扩展 `--check-*` 断言。

## 六、UI 落点

| 位置 | 形态 | 说明 |
|---|---|---|
| `LearnPage` 章节点 | "本章总结" 表格卡 | 仅 `mastery===100` 显示；沿用 `.km-node` |
| `#track/408` | 408 总表 + 逐章下钻 | 复用 `App.tsx` hash 深链 |
| `#employment` | 就业八股图谱 | 见第十节 |
| `#reexam` | 复试（面试 + 机试） | 见第十一/十二节 |
| 总结卡右上 | "复制为 Markdown 表格" 按钮 | 导出粘进 E 盘 `.ipynb` |

## 七、验收

| 脚本 | 校验项 |
|---|---|
| `verify_logic_chain.mjs --check-summary` | `buildChapterSummary` 对 `done` 章产出 7 维非空；未 `done` 返回 null |
| `--check-employment` | 八股图节点均来自 `interview.json`，无悬空 |
| `--check-reexam` | 机试题均有 `exam:机试` 标签；复试引用章均 `done` |
| `audit_graph.py` | **全部学科**依赖图无环/无悬空/无自环 |
| `validate_content.py` | **全部学科**内容满足"场景化(工作实例)"标准 |
| `tsc --noEmit` + `vite build` | 新增层零错误 |

## 八、实施分期（基础）

| 阶段 | 内容 | 产出 |
|---|---|---|
| P1 | 写 `408.json`（cross-walk） | ✅ 已落地 |
| P2 | `chapterSummary.ts` + `examTracks.ts` + 生成数据层（`chapterContent.ts`/`track408.ts`/`gen_*.py`/`summary_checks.ts`） | ✅ 已落地（`--check-summary` 全绿、`tsc` 零错） |
| P3 | `LearnPage` 接"本章总结" + 导出 | ✅ 已落地（仅 mastery===100 解锁，7 维表 + 一键导出 Markdown + 全量条目折叠） |
| P4 | `#track/408` 路由 + 四模块总表 + 单章下钻 | ✅ 已落地（路由 #track408 + Track408Page + 深链 #track408/<章>） |
| P5 | `#employment` 就业板块 + 八股图 | ✅ 已落地（路由 #employment + EmploymentPage + buildInterviewGraph + `--check-employment` 全绿） |

## 九、与"可玩性第 3 项（丰富化）"的关系

本方案是**第 3 项的具体切片**：章节总结表 = "修炼路线"可视化收尾；408/就业/复试三链路 = "学科轨道依赖 / BOSS 章与学科大关 / 图鉴挂钩"的备考形态。其余切片（项目链、跨章连携奖励）按 `Playability-Coherence-Plan` 推进，不在本方案范围。**全学科覆盖**与**场景化**同时反哺内容标准（见第十三节）。

## 十、就业板块（含八股面试题图表化）★ 八股归就业，不归考研

> 需求：八股面试题（tech interview Q&A）归属**就业板块**，以**图表**呈现。**区别于考研**：考研复试面试 ≠ 八股。

| 图表形态 | 结构 | 数据 | 用途 |
|---|---|---|---|
| A 八股矩阵图（主视图） | 行=主题域（语言/框架/DB/OS/网络/计组/数据结构），列=题型（概念/手写/场景/陷阱/源码），格=题量+已答率 | `interview.json` + `answers` | 一眼看薄弱题型 |
| B 知识图谱 | 节点=八股题，按主题域聚类，色=掌握度，点开跳章 | 同上 + `chapterDeps` | 关联记忆、查漏 |
| C 思维导图 | 主题域→章→题 三级 | 同上 | 系统复盘 |

- **数据源**：`lib/employment.ts` → `buildInterviewGraph(st)` 纯函数。
- **UI 落点**：`#employment` 路由；或 `DiagramsPage` 增"面试题图"分组（复用图渲染基建）。
- **与单章表关系**：单章"面试/真题"行点"展开图表"即跳 B/C。

### 10.1 八股资源分区与专轨映射（分区整理 ★ 就业专属）

> 八股归就业（不归考研）。以下资源按「底层学科 → 语言/框架专轨 → AI 叠加层 → 导航工具」四区组织；Agent 八股单列专项（见 10.2）。所有资源经 `content/_tracks/employment.json`（新增，与 408.json 并列）登记，星数走**三级兜底**（API→manifest→`_star_snapshot.json`），作为八股图节点与 `github_notes` 来源；与 408 的 `attach_all_sources.py` 走**并行注册表**（408 仓库不混入就业区）。

**四区总览**

| 区 | 定位 | 数据源 | 覆盖 |
|---|---|---|---|
| A 底层学科 | 跨专轨通用地基 | 小林coding（图解计算机基础）、面试鸭 Mianshiya | 计算机基础全栈 + 综合刷题（Java/C++/Python/Go/前端） |
| B 语言/框架专轨 | 按技术栈切片 | Alessandro-Pang/fe-interview（前端）、itwanger/baguwen-wiki + CoderLeixiaoshuai/java-eight-part（Java 后端）、vikrant-d1/fullstack-interview-resources（Node/全栈） | 前端 1000+ / Java 基础·集合·JVM·Spring·MySQL·Redis / 现代全栈工程 |
| C AI 叠加层 | 前沿题库 | yugef3h/interview-yuge（AI 全栈/字节企业库）、Agent 八股专项（见 10.2） | LLM 应用、Agent 工程、RAG/MCP |
| D 导航与工具 | 顺藤摸瓜 + 多端刷题 | interviewMap（八股导航站）、面试鸭 Mianshiya | 检索入口、模拟刷题 |

**资源 → 分区映射表**

| 资源 | 类型 | 区 | 角色 / 特色 |
|---|---|---|---|
| 小林coding | 仓库 | A | 计算机基础图解，408 总结与八股底层双向复用 |
| 面试鸭 Mianshiya | 网站/开源 | A·D | 综合题库，Java/C++/Python/Go/前端/基础，多端同步 |
| Alessandro-Pang/fe-interview | 仓库 | B | 1000+ 前端真题，每题含参考答案/考点分析/关联题 |
| itwanger/baguwen-wiki | 仓库 | B | Java 后端八股（基础/集合/JVM/Spring/MySQL/Redis） |
| CoderLeixiaoshuai/java-eight-part | 仓库 | B | Java 八股合集 |
| vikrant-d1/fullstack-interview-resources | 仓库 | B | React/Node/JWT/Docker/CI-CD/AWS 全栈工程化 |
| yugef3h/interview-yuge | 仓库 | C | 2026-AI 全栈，含字节企业题库 + AI/LLM 深度追问 |
| interviewMap | 网站 | D | 八股文导航站，顺藤摸瓜找方向资料 |
| isboyjc/Interview | 仓库 | B（知识框架） | 结构化知识图谱，覆盖 90%+ IT 知识点 |

### 10.2 Agent 八股专项（独立体系：工程落地 / 系统设计 / 生产实践）

> Agent 八股已成独立体系，核心是「工程落地 + 系统设计 + 生产实践」，不混进通用语言专轨。以 **Prompt→Context→Agent→Harness** 四层工程骨架为底层学科，RAG/LangGraph/MCP 为专项模块，SuperGODOG 的 1-5 级深度分级生成「虚拟试卷」。

**四层工程骨架（基础学科）**

| 层 | 含义 | 参考 |
|---|---|---|
| Prompt | 提示词工程 | harrisliangsu/ai-agent-engineer-handbook |
| Context | 上下文管理 | 同上 |
| Agent | 智能体本体 | 同上 |
| Harness | 工程化承载（调度/沙箱/评测） | 同上 |

**专项模块 → 题库映射**

| 模块 | 题库来源 | 规模/特色 |
|---|---|---|
| 基础概念 / ReAct / LangGraph / RAG / 工具调用 / MCP | bcefghj/ai-agent-interview-guide（9 大模块） | 按模块专项突破 |
| RAG 基础 / Agent 基础 / MCP & A2A | ombharatiya/ai-system-design-guide（英文） | 128 题 + 系统设计 |
| 核心题库 | ranxi2001/zero2Agent（《Agent面试800问》828+ 大厂真题，"新手答 vs 高手答"对比） | 绿皮书 PDF |
| 公共真题 + 模拟面试引擎 | SuperGODOG/ai-agent-interview-240（477 题，含秒杀/Redis/MQ 后端，1-5 级深度） | 分级刷 |
| 图文/视频向 | itwanger/ai-better（369 题，Agent/RAG/MCP 等 12 分类） | 视觉型 |
| 工程化与系统设计 | cdavid817/agent-interview（1820 题，工程边界/失败处理/验证指标，多 Agent 协作） | 架构向 |

**模拟考卷（虚拟试卷）**

| 试卷难度 | 分级来源 | 生成规则 |
|---|---|---|
| L1-L2 概念定义 | SuperGODOG 1-5 级 | 每模块抽 N 道低分级题组卷 |
| L3-L4 落地权衡 | 同上 | 中分级 + 场景题 |
| L5 生产实践 | 同上 + cdavid817 | 高分级 + 失败处理/验证指标 |

- **接入方式**：就业专轨资源登记进 `content/_tracks/employment.json`（新增，与 408.json 并列）；星数走三级兜底；`lib/employment.ts` 的 `buildInterviewGraph` 把这些节点并入八股图，并按「区/专轨/模块」着色。
- **与单章表关系**：单章"面试/真题"行点"展开图表"即跳八股图对应节点。

## 十一、考研复试板块（面试问题[复试专属] + 机试）

> 复试 ≠ 八股。复试面试是**复试专属问题**（研究计划、项目陈述、英语口语、专业素养）；机试是编码测试。

| 维度 | 初试（408 专轨） | 复试（本板块） |
|---|---|---|
| 性质 | 笔试 / 四模块 | 面试 + 机试 |
| 路由 | `#track/408` | 新增 `#reexam` |
| 内容 | DS/计组/OS/网络 总结表 | 复试面试问题 + 机试题 |
| 数据 | `408.json` + 各章总结 | 见下 |

**复试板块内部结构**

| 子面板 | 内容 | 数据来源 |
|---|---|---|
| 面试问题 | 复试专属（研究计划/项目陈述/英语/专业素养），**非八股** | 项目章 `project` 描述 + 新增 复试面试题库 |
| 机试 | 编码题，**置于复试内** | 见第十二节机试题库规范 |

- **机试归属**：明确在复试板块内（不在 408 笔试专轨），与"初试笔试 / 复试机试"真实结构一致。
- **架构**：`lib/reexam.ts` + `pages/ReexamPage.tsx`；机试题通过 `exam:机试` 标签从题库筛选。

## 十二、机试题库规范（各大高校真题 + 三层答案 + 场景）

> 来自需求：机试以**各大高校机试真题**为主；答案固定**三层**；代码全注释通俗；多形式；每题**附具体场景（工作中实例）**。

| 规范项 | 要求 |
|---|---|
| 来源 | 主要取自**各大高校机试真题**（如 浙大 PAT、北航、华科、统考机试等），标注高校+年份 |
| 答案结构 | ① **大框架**（问题拆解/输入输出/边界）② **核心算法思想**（关键思路，伪代码或文字）③ **完整代码**（全注释、通俗易懂） |
| 表示形式 | 代码 + 图（流程图/状态机）+ 表，**多种形式均可** |
| 场景 | 每题**附带工作场景实例**（样例输入输出、真实业务映射、易错点） |
| 落库 | 复用 `exercises` 的 coding 类型，打标签 `exam:机试`；或 `content/_tracks/reexam.json` |
| 与章节关系 | 可按 408 模块关联（如"图"章→机试"最短路径"），形成 学→练→考 闭环 |

**单道机试题答案骨架（示例）**

```
① 大框架：输入 N 与边集 → 建图 → Dijkstra → 输出最短路；边界 N=1 / 不连通返回 -1。
② 核心算法思想：优先队列维护 (dist, u)，仅当松弛后更小才入队，避免重复扩展。
③ 完整代码（全注释）：
   // 建邻接表
   vector<vector<pair<int,int>>> g(n+1);
   for (auto& e : edges) { g[e.u].emplace_back(e.v, e.w); }
   // ... 其余带注释
```

## 十三、全局内容标准（场景化 + 图表归类）★ 覆盖全部学科

| 标准 | 要求 |
|---|---|
| **场景化（定义）** | **场景 = 工作中遇到的具体实例**（真实业务场景 / 线上问题 / 踩坑复盘），**非教科书抽象举例**。概念 / 例题 / 项目 / 面试题 / 机试题 均须带此场景 |
| 标准守门 | 场景化列为**全局内容标准**，由 `validate_content.py` 校验；自检阶段统计各学科的"缺场景"章节 |
| 图表归类 | 图表是**独立内容资产**（DiagramsPage）；正式学习链路中"图"单独归类，不与文本混排 |
| 一致性 | 单章表、408 表、八股图、机试 均复用同一套纯函数层，数据唯一来源 |
| **全学科生效** | 上述标准与单章总结表对 **cpp / java / python / database / spring / middleware / bigdata / tooling / ml / agent / ai / fundamentals / fullstack / clang / data** 及考研数学英语政治 **全部学科**生效，不限于 408 相关学科 |

## 十四、正式学习链路闭环（全学科 + 逻辑链完整）★

**14.1 学科内逻辑链完整（无悬空、无断点）**

| 检查项 | 要求 | 守门 |
|---|---|---|
| 依赖图完整 | 每学科 `chapterDeps` 形成 基础→进阶 连续链，无悬空前置、无断点 | `audit_graph.py` 全学科 |
| 解锁一致 | `isUnlocked` 与 `graph.ts` 单一事实来源，nextAction 推荐链闭合 | `logicChain.stateViolations` |
| 掌握闭环 | 章 `mastery===100` ⇔ `done`；达标章可生成总结并导出，未达标在 nextAction 被推荐 | `Playability-Coherence-Plan` 不变量 |

**14.2 跨轨道闭环（学→练→考→结→复盘）**

| 环节 | 内容形态 | 归口 | 覆盖 |
|---|---|---|---|
| 概念 | 图文（ASCII 图在 `concept/*.md`）+ **工作场景实例** | 图表资产 | 全学科 |
| 例题 | 带工作场景的练习题 | 章节 | 全学科 |
| 项目 | 实战项目（带工作场景） | 章节 | 全学科 |
| 章总结 | 7 维表格（每维带场景） | 本章总结面板 | 全学科 |
| 考研 408 | 四模块总表 + 考点表 | `#track/408` | 408 相关学科 |
| 考研复试 | 复试面试问题 + 机试（高校真题三层答案+场景） | `#reexam` | 考研向 |
| 就业 | 八股面试题图谱（工作场景） | `#employment` | 求职向 |

> "图表归为图表"：所有 ASCII/架构图统一走 `DiagramsPage`，学习主链路保持表格/文本，图作为可展开资产——链路完整且职责清晰。**闭环**：学完→生成总结→(应用：机试/面试/八股)→复盘→推荐下一章，无断裂。

## 十五、内容充实规范（王道/大纲 + 数学老师）★ 覆盖全部学科 + 详细完整

> 来自需求：408 整体内容以**考研大纲 + 王道**为主、须**丰富**；数学以**张宇/武忠祥（高数）、李永乐（线代）、方浩+其他（概率）**为主；内容要求**详细完整**。

### 15.1 408 四模块按王道章节结构充实

现有 `fundamentals` 已按王道标题组织（`fund-ch07~12` 对应 计组/OS/网络/DS），但每模块仅 1-2 章，远少于王道（每模块 6-8 章）。充实方向：按**王道/考研大纲**将每模块拆为完整章集，**内容详细完整 + 场景化（工作实例）**。

| 408 模块 | 王道章清单（目标） | 现状 | 充实动作 |
|---|---|---|---|
| 数据结构 | 绪论/复杂度、线性表、栈与队列、串、树与二叉树、图、查找、排序、散列、并查集 | `fund-ch01~06` 已覆盖主干 | 补 散列/并查集/串 等缺章 |
| 计算机组成原理 | 计算机系统概述、数据的表示与运算、存储系统(Cache/主存/虚存)、指令系统、中央处理器(数据通路/流水)、总线、输入输出(中断/DMA) | `fund-ch07`(数据表示)、`fund-ch08`(存储+CPU) 仅 2 章 | 拆为 **王道 7 章** |
| 操作系统 | 概述、进程与线程、处理机调度、同步与死锁、内存管理、文件管理、I/O 管理 | `fund-ch09`(进程调度)、`fund-ch10`(内存文件IO) 仅 2 章 + `cpp-ch16` | 拆为 **王道 6-7 章** |
| 计算机网络 | 体系结构、物理层、数据链路层、网络层、传输层、应用层、网络安全 | `fund-ch11`(分层TCP)、`fund-ch12`(应用层) 仅 2 章 | 拆为 **王道 6-7 章** |

### 15.1.1 权威参考仓库（408 总结 + 最后复习 + 八股 共用）

| 仓库 | 特点 | 覆盖 | 用途 |
|---|---|---|---|
| **CS-Four-Basics-Notes** | 数据结构/OS/网络/数据库 四大件；内容精简 + 可运行 Demo 代码 + 思维导图 | 四大件（含数据库） | 408 总结、最后复习速背、八股素材 |
| **小林coding（图解计算机基础）** | "图解"出名；1000+ 图 + 通俗语言讲透底层；覆盖 网络/OS/计组/数据库 | 网络/OS/计组/数据库 | 构建底层体系、408 图解总结、八股素材 |

- 二者均作为 **408 总结内容 + 最后复习阶段内容** 的权威来源，同时纳入**八股（就业）**素材池。
- 接入方式：经 `scripts/attach_all_sources.py` 的 `REPOS_OVERRIDE` / `NOTES_OVERRIDE`（或 `_cpp_sources.py` 同构表）登记，按章节 `github_notes` 标注 `§` 读法；星数走三级兜底（API→manifest→`_star_snapshot.json`），避免限流抹空。
- 与 王道/大纲 的关系：王道/大纲定**章节结构与考纲边界**，上述两仓库提供**图解/速背/八股**视角的补充素材，互不替代。

### 15.2 数学 track（老师主线）

新建 `content/math`，按老师主线组织，**内容详细完整 + 场景化（工作实例）**；老师主线体现在 `resources`/讲解视角标注，不替代内容严谨性。

| 数学分支 | 主线老师 | 章清单（目标） |
|---|---|---|
| 高等数学 | **张宇 + 武忠祥** | 函数极限连续、导数与微分、中值定理、不定积分、定积分、微分方程、多元微分、重积分、曲线曲面积分、级数 |
| 线性代数 | **李永乐** | 行列式、矩阵、向量、线性方程组、特征值与特征向量、二次型 |
| 概率论与数理统计 | **方浩 + 其他风评好老师** | 随机事件与概率、一维随机变量、多维随机变量、数字特征、大数定律与中心极限、统计量、参数估计、假设检验 |

### 15.3 内容守门

| 标准 | 要求 |
|---|---|
| 详细完整 | 每章 7 类内容（目标/概念/易错/例题/面试/项目/场景实例）齐备，复用单章总结表 schema |
| 场景化 | 同第十三节：场景 = 工作中遇到的具体实例 |
| 校验 | `validate_content.py` 扩 "详细完整" 校验（7 类齐备 + 场景化）；408/数学 充实进度纳入完工自检报告 |

## 十六、更新后的实施分期（全）

| 阶段 | 内容 | 产出 |
|---|---|---|
| P1 | 写 `408.json`（cross-walk） | ✅ 已落地 |
| P2 | `chapterSummary.ts` + `examTracks.ts` + 生成数据层（`chapterContent.ts`/`track408.ts`/`gen_*.py`/`summary_checks.ts`） | ✅ 已落地（`--check-summary` 全绿、`tsc` 零错） |
| P3 | `LearnPage` 本章总结 + 导出 | ✅ 已落地（仅 mastery===100 解锁，7 维表 + 一键导出 Markdown + 全量条目折叠） |
| P4 | `#track/408` 路由 + 四模块总表 + 单章下钻 | ✅ 已落地（路由 #track408 + Track408Page + 深链 #track408/<章>） |
| P5 | `#employment` 就业板块 + 八股图 | ✅ 已落地（路由 #employment + EmploymentPage + buildInterviewGraph + `--check-employment` 全绿） |
| P6 | `#reexam` 复试板块（面试 + 机试） | 复试链路 |
| P7 | 机试题库（高校真题 + 三层答案 + 工作场景）seed | 机试内容 |
| P8 | 场景化标准接入 `validate_content.py`（全学科） | 内容守门 |
| **P9** | **完工自检**：`--check-summary`/`--check-employment`/`--check-reexam` + `audit_graph.py`(全学科) + `validate_content.py`(场景覆盖) + `tsc`+`vite build`，出自检报告 | 全绿 + 覆盖报告 |
