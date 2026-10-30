# agent-ch02 · Prompt 工程与结构化输出：把自然语言当接口设计

> 对应图片 DAY 3（B 站吴恩达）· 先修：agent-ch01 · 面试权重：★★★★★
> （几乎每一轮 Agent/应用岗面试都会让你现场改 prompt 或解释「为什么这么写」）

## 本章目标

1. **写出可维护的四段式模板**（角色/任务/约束/示例），并说明每一段解决的是哪一种不确定性；
   能对任意一条 prompt 指出「缺了哪一段、会导致什么故障」。
2. **处理指令冲突**：按 system > developer > user > 外部数据的优先级设计结构，
   把「谁优先」写进应用层逻辑，而不是指望模型自觉。
3. **设计并通过一个 JSON Schema 契约**：覆盖必填、枚举、类型、长度、额外字段；
   能区分语法/结构/语义三层失败，并给出各自的检测与处置。
4. **实现一条带修复与降级的解析链**：解析失败 → 错误信息回传 → 有限轮修复 →
   仍失败则降级；能算出修复轮的成本与延迟代价。
5. **对 20 条边界输入建立回归集**：覆盖注入、超长、编码、空值、冲突指令，
   输出召回率/误报率，并能说明单层防御的上限。

## 关键认知（本章最值钱的三句）

- **Prompt 是接口，不是咒语**。接口要有类型、必填、边界、版本、测试；
  没有回归集的 prompt 修改，等于在生产环境做实验。
- **「JSON 合法」≠「符合 schema」≠「答案正确」**。三层失败要用三种手段处理，
  用合法率掩盖准确率，是结构化输出最常见的自欺。
- **注入防不住，只能限制爆炸半径**。数据与指令共享同一个文本信道，
  所以真正的边界在工具权限与人工确认，不在 prompt 里的那句「请不要执行」。

## 技术交付物

对应 `manifest.tech_load`：**Python 提示模板库：Jinja 风格渲染 + JSON Schema 校验 +
失败自修复 + 20 条边界输入回归测试。**

验收口径：

| 交付物 | 必须包含 | 验收方式 |
|---|---|---|
| 模板库 | 变量声明（类型/必填/长度）、单次替换、版本号 | 缺变量/类型错/超长各返回明确错误码，不渲染 |
| Schema 校验器 | 类型、required、enum、范围、数组、额外字段 | 9 条用例全过，错误信息带字段路径 |
| 修复链 | 错误回传、最多 2 轮、截断修补、降级 | 能输出每轮的成功率与成本 |
| 回归集 | ≥20 条：注入 8 / 边界 6 / 正常难例 6 | 输出分类召回与误报率，可重复运行 |
| 流式解析 | 状态机 + 前缀修补 + 部分渲染 | 在 10 个截断点上给出可解析/不可解析 |

配套代码（`examples/`，全部可运行、无网络、无密钥）：

| 示例 | 解决什么问题 |
|---|---|
| `ex01-template_validation` | 模板渲染、变量校验、二次展开漏洞 |
| `ex02-fewshot_returns` | 少样本数量 vs 准确率的收益递减 |
| `ex03-cot_tradeoff` | CoT 在简单任务上的反噬与盈亏平衡错误成本 |
| `ex04-json_schema_check` | 手写 Schema 校验器（含 bool/int 坑） |
| `ex05-repair_loop` | 修复轮的成功率/成本/延迟权衡 |
| `ex06-stream_json` | 流式截断与增量解析 |
| `ex07-injection_scan` | 注入特征扫描的召回/误报与阈值扫描 |
| `ex08-context_budget` | 三种截断策略的金标保留率对比 |
| `ex09-ab_significance` | 提示版本 A/B 的显著性、样本量与边看边停偏差 |
| `ex10-tool_schema` | 宽参数 vs 枚举参数的工具选错率与副作用成本 |
## 与 ai 学科的分界

`ai` 学科讲模型内部：注意力如何计算、指令微调如何训练、约束解码的实现。
本章只讲**接口层的工程判据**：怎么定义契约、怎么校验、怎么修复、怎么防注入，
以及每一步的成本与失败模式。

判断标准：**本章的每个结论都要能变成一段可运行的校验/修复/回归代码**；
不能落地的机制讨论，留给 `ai` 学科。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | 79,402 | 全章 | 提示工程体系化教材：技巧分类 + 论文出处，适合建立方法论而不是背模板；本章先读与「四段式」「指令优先级」相关的部分 |
| 2 | [openai/openai-cookbook](https://github.com/openai/openai-cookbook) | 76,730 | 全章 | 官方 API 用法与结构化输出范例，照它写第一次 function calling；本章先读与「四段式」「指令优先级」相关的部分 |
| 3 | [anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) | 53,639 | 全章 | Claude 的工具调用、长上下文、评测 notebook，对照 OpenAI 的差异；本章先读与「四段式」「指令优先级」相关的部分 |
| 4 | [microsoft/promptflow](https://github.com/microsoft/promptflow) | 11,253 | 全章 | 提示流工程化：把 prompt 当代码做版本、测试、批量评测；本章先读与「四段式」「指令优先级」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | §1.6 Prompt 也是代码 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（提示模板渲染与变量校验）核对 |
| 2 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | §1.6 Prompt 也是代码 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex02`（少样本数量 vs 准确率）核对 |
| 3 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | §1.6 Prompt 也是代码 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex03`（CoT 的反噬）核对 |
| 4 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | §3.4 工具权限边界 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex04`（手写 JSON Schema 校验器）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
