# agent-ch03 · 模型接入与 DeepSeek 实操：第一次让程序真的说话

> 对应图片 DAY 5（DeepSeek 官方文档）· 先修：agent-ch02（Prompt 工程）· 面试权重：★★★★☆
> 说明：面试官不会问你「怎么发 HTTP」，而是问「超时了怎么办、重试几次、账单为什么涨了」。

## 本章目标

学完你应该能：

1. **把模型调用当一次外部依赖接入来设计**：写出带鉴权、超时、重试、限流、日志、成本统计的客户端，
   而不是在业务代码里裸调 `requests.post`。
2. **手写一个流式解析器**：处理 SSE 的跨包 JSON、多行 `data:`、`[DONE]` 与 usage，
   并解释为什么「按 chunk 解析」上线必坏。
3. **给错误码分类并落成策略表**：区分鉴权/入参/限流/过载/超时，决定哪些重试、哪些快速失败、
   哪些触发降级；能算出重试带来的 P95 放大倍数。
4. **做一次上下文与成本的账**：按输入/输出/缓存三档算单请求成本，说清前缀缓存生效的条件，
   并用 token 估算器做预算闸门而不是账单依据。
5. **给出本地与云端的选型结论**：用能力、成本、合规三条线对比 Ollama 与云端 API，
   设计「云端为主 + 本地降级」的混合路由，并说明熔断与半开探针的触发条件。

## 关键认知（本章最值钱的三句）

- **「兼容 OpenAI」只兼容了请求形状，没兼容语义**：tool call 的 id 长度、JSON 模式的强制程度、
  `reasoning_content` 是否回传、usage 字段是否齐全，各家都不同。接入层必须做**能力探测**，
  不能假设 `base_url` 一换就万事大吉。
- **重试是放大器，不是保险丝**：对不可重试错误重试，只是把 300ms 的失败拖成 3 秒；
  对非幂等写操作重试，会把一次下单变成三次。可重试的前提是**幂等 + 错误可恢复 + 有退避上限**。
- **成本的大头通常在输入侧**：输出单价是输入的数倍，但客服/RAG 类应用输入 token 常常是输出的 5~10 倍。
  先压输入（去冗余 few-shot、稳定前缀、缓存友好排序），再谈输出压缩。

## 技术交付物（来自 manifest.tech_load）

**可切换厂商的 LLM 客户端**：流式、超时、指数退避、令牌桶限流、结构化日志、按请求计费。

验收口径（对应 project.json 的任务）：

- 同一份业务代码通过配置切换至少 2 个厂商（真实厂商名可替换为 mock base_url），不改调用方；
- 流式接口能在 chunk 边界任意切分的情况下还原完整文本，且有首字超时与总超时两个阈值；
- 429/5xx/超时按策略表重试，401/400 快速失败；重试带抖动，P95 放大不超过设定上限；
- 每个请求落一条结构化日志：`request_id / vendor / model / prompt_tokens / cached_tokens /
  completion_tokens / cost / latency_first_token / latency_total / retry_count / fallback_reason`；
- 能用日志还原一次调用的 span 树，并算出各段 self time。
## 与 ai 学科的分界

`ai` 学科讲 Transformer 结构、注意力复杂度、推理优化与蒸馏；本章**不推导模型内部**，
只把模型当成一个有配额、有延迟分布、会失败的外部服务来接入。
需要理解「为什么长上下文更贵」时，回 `ai` 学科看注意力的 O(n²) 与 KV cache；
本章只给工程结论：上下文是预算，缓存是折扣，重试是风险。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [deepseek-ai/DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) | 104,539 | 全章 | DeepSeek 主力开源模型的技术报告与推理代码，理解成本为何能压这么低；本章先读与「鉴权与密钥管理」「错误码分类」相关的部分 |
| 2 | [deepseek-ai/DeepSeek-R1](https://github.com/deepseek-ai/DeepSeek-R1) | 91,920 | 全章 | 推理模型 RL 训练范式，面试问「为什么 R1 会思考」时的第一手材料；本章先读与「鉴权与密钥管理」「错误码分类」相关的部分 |
| 3 | [deepseek-ai/awesome-deepseek-integration](https://github.com/deepseek-ai/awesome-deepseek-integration) | 39,457 | 全章 | 官方集成清单：IDE/Agent/客服等落地形态，做选型时先看这里；本章先读与「鉴权与密钥管理」「错误码分类」相关的部分 |
| 4 | [ollama/ollama](https://github.com/ollama/ollama) | 185,510 | 全章 | 本地一键跑模型，验证「私有化」可行性最快的路径；本章先读与「鉴权与密钥管理」「错误码分类」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | 全章 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（令牌桶限流器）核对 |
| 2 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | §3.4 混合路由 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex02`（指数退避与抖动）核对 |
| 3 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex03`（SSE 流式解析器）核对 |
| 4 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | 全章 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex04`（错误码分类与降级决策表）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
