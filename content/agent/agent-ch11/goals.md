# agent-ch11 · Agent 系统开发：工具、记忆、规划与多智能体

> 对应图片 DAY 35（一站式 AI 产品知识库）· 先修：agent-ch05（RAG 检索）、agent-ch08（Transformer 核心机理）· 面试权重：★★★★★
> 说明：这是本学科的重心章。面试官不问你「什么是 Agent」，而问「工具调用的幂等怎么设计、
> 上下文爆了怎么压缩、Agent 死循环怎么防、三个角色的多智能体为什么比一个 Agent 还贵」。
> 本章把「LLM 是大脑」补成能上线、能回放、能报价的完整系统。

## 本章目标

学完你应该能：

1. **设计工具层并对调用负责到底**：写出 function calling / MCP 工具的 schema（类型、必填、枚举、
   白名单字符），实现「语义等价修复 + 不可猜拒发」的参数校验，说清幂等键怎么算、副作用怎么抑制、
   权限怎么按最小化授予。
2. **搭记忆与状态层**：实现短期上下文的压缩（滑动窗口 vs 摘要，用同一批任务测成功率变化）、
   长期记忆的写入/检索/衰减打分，以及检查点序列化与断点续跑，并能解释「续跑结果必须与基线一致」。
3. **实现规划循环并防住失控**：把 ReAct（想-做-看）落成显式状态机，输出可回放的 trace；
   对比 Plan-and-Execute 的适用面；配齐死循环防护三检测器（步数上限/预算上限/无进展检测），
   并解释阈值 K 为什么不能取 2。
4. **组织多智能体并算清它的账**：设计角色分工与 handoff，用共享黑板减少跨角色上下文重复传递；
   能按角色拆成本账本，说出「返工第 N 轮的边际增益」与「角色错配的浪费」。
5. **交付带可观测性的多步 Agent**：一个含 3 个工具（其中 1 个是 MCP server）、检查点、
   人工介入、死循环防护、trace 回放的 Agent，失败样本能按归因标签分类并给出修复层。

## 关键认知（本章最值钱的三句）

- **工具是 Agent 的手，但手会重复劳动、会误操作、会被注入**：schema 校验拦形状错误，
  幂等键拦重复副作用，沙箱与权限最小化拦越权——三层少了任何一层，
  「重试一次」就可能变成「给客户发三封同样的邮件」。
- **记忆的本质是「丢什么」而不是「存多少」**：窗口滑动丢早期事实，摘要压缩丢细节，
  不衰减则新事实被旧记忆淹没。压缩前后必须用同一批任务测成功率——
  token 省了 70% 而任务成功率掉 20%，那不是优化是事故。
- **多智能体的每一跳 handoff 都是一次全额计费的调用**：成功率是用成本和交接次数买来的，
  返工轮次越深边际增益越薄；先用单 Agent + 好工具解决问题，
  上多智能体的理由必须是「角色上下文互相污染」或「并行刚需」，不是「看起来高级」。

## 技术交付物（来自 manifest.tech_load）

**LangGraph Agent：3 个工具（含 MCP server）、检查点、人工介入、死循环防护、trace 回放。**

验收口径（对应 project.json 的任务，逐条可核对）：

- 3 个工具各有 schema（类型/必填/枚举/字符白名单），参数校验器能拦形状错误、
  做语义等价修复、对不可猜参数拒发并回喂错误信息；其中至少 1 个工具按 MCP 工具
  协议暴露（本地 stdio server，工具发现/列表/调用三段可见）；
- 副作用工具带幂等键（工具名 + 归一化参数哈希，nonce/时间戳剔除），
  重复调用被抑制且返回首次结果；无幂等键时同样输入至少发出 2 次副作用的反证可复现；
- 每步成功后写检查点（trace + next_step 的 JSON 序列化），模拟崩溃后从检查点续跑，
  最终 trace 与一次跑完的基线逐元素一致；
- 人工介入：至少一个节点在「低置信度/校验失败/预算超阈值」时暂停等待人工指令，
  人工放行后能从断点继续，且暂停不丢已完成的副作用；
- 死循环防护三检测器（步数上限/预算上限/无进展检测）同时在跑，
  三类脚本化失控场景都在第 3 步被无进展检测拉闸，正常任务（含一次合法重试）零误杀；
- trace 可按 step 回放：每步记录 thought/action/args/observation + token + 双时延，
  能重放出任意一次任务的完整过程并按步汇总成本。
## 与 ai 学科的分界

`ai` 学科讲模型内部：注意力机理、推理优化、RAG 的向量检索实现、Agent 框架源码。
本章**只讲工程系统**：工具怎么接得安全、记忆怎么组织得可恢复、规划怎么防失控、
多智能体怎么算账、失败怎么归因。

需要理解「为什么上下文越长单步越贵」时回 `ai` 学科看注意力复杂度与 KV cache；
本章只给工程结论：上下文是预算、检查点是保险丝、handoff 是账单。
遇到「ReAct 为什么有效、反思的收益边界在哪」这类机理问题，
本章只给够用的解释与判据，推导在 `ai` 学科。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 44,248 | §02 检查点、断点续跑与状态机建模 | §03 终止条件与死循环防护：`libs/langgraph/` 的 graph + checkpointer 是本章「有状态编排」的直接实现，读 `checkpoint/` 的存储接口，就懂「断点续跑」靠什么落盘 |
| 2 | [microsoft/autogen](https://github.com/microsoft/autogen) | 61,505 | §03 角色分工 | §03 成本爆炸：`autogen-core/` 里 agent 之间的消息协议与终止条件都显式定义，对照本章「多智能体的成本随角色数超线性增长」 |
| 3 | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 59,947 | §03 共享黑板 | §03 多智能体的 handoff：`crew.py` 里 Task 的 `context` 参数就是「共享黑板」的落点，读它如何把上游产出注入下游，就懂本章「角色分工靠数据流而非提示词」 |
| 4 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 30,195 | §01 工具 schema 与参数校验 | §01 幂等与副作用：`openai-agents/` 的 handoff / guardrail / tracing 三个钩子各管一件事，其中 guardrail 是本章「重试不能让副作用叠加」的兜底层 |
| 5 | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | 24,629 | §01 权限最小化与沙箱 | §01 MCP 的工具发现：`src/mcp/server/` 里 `list_tools` 与 `call_tool` 是两个分离的 RPC，schema 校验发生在执行前——正是本章「把自由发挥拦在执行前」的协议证据 |
| 6 | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) | 71,000 | §03 多智能体：SOP 如何被编码进角色 | §03 终止条件：`metagpt/roles/` 每个角色类都带 `_observe` / `_think` / `_act` 三段，把本章「角色 = 职责 + 可用动作 + 终止条件」落成了类结构 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | 全章 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（ReAct 循环的状态机实现与 trac）核对 |
| 2 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | 全章 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex02`（工具 schema 校验与参数修复）核对 |
| 3 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex03`（工具调用的幂等键与重复调用抑制）核对 |
| 4 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | 全章 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex04`（上下文压缩前后任务成功率对比）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
