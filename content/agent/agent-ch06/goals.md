# agent-ch06 · 私有化部署与推理服务：把模型放进自己的机房

> 对应图片 DAY 11（vLLM 部署指南）· 先修：agent-ch03（模型接入与 DeepSeek 实操）· 面试权重：★★★★☆
> 说明：面试官不问「怎么起容器」，而是问「一张 24GB 卡能开多少并发 8k 上下文、P99 为什么压不下来、坏构建怎么不炸线上」。

## 本章目标

学完你应该能：

1. **算清一张显存账本**：把显存拆成权重 + KV Cache + 激活 + 碎片，按「P99 上下文长度 × 目标并发」先算 KV，再判断权重放不放得下；说清 INT4 比 FP16 省下的空间才是并发成立的前提。
2. **完成一次推理引擎选型**：对比 vLLM（PagedAttention / 连续批处理）、SGLang（前缀缓存）、llama.cpp（GGUF / CPU）、Ollama（一键本地），给出一张「何时用哪个」的决策表，而不是背特性列表。
3. **部署并压测一个 7B/14B 模型**：容器化跑起 OpenAI 兼容服务，用压测脚本输出 TTFT、TPOT、P99、QPS 与显存峰值，并读懂长尾——知道均值达标不等于线上不超时。
4. **设计灰度与多租户护栏**：用健康检查 + 摘流 + 灰度把坏构建的爆炸半径压到个位数；用配额隔离多租户，用日志脱敏守住合规，而不是「全量直切」。
5. **给一份单位 token 成本账**：把卡租摊到「有效吞吐 × 利用率」，算出与云端 API 的打平点，能回答「这个流量到底该自建还是走云」。

## 关键认知（本章最值钱的三句）

- **显存瓶颈的第一优先级是 KV Cache，不是权重**：权重加载一次是常数，KV 随上下文长度线性、随并发线性；先按 P99 长度 × 目标并发算 KV，再看剩下的空间够不够放权重——很多 OOM 是因为漏算了 KV 按最大上下文预留的部分。
- **批处理把「算力利用率」和「延迟」绑成一对冤家**：连续批处理抬高吞吐但拉高 TPOT；TTFT 看 prefill、TPOT 看 decode，调一个常伤另一个，所以 SLO 必须分别给（如 TTFT-P99 < 800ms、TPOT-P99 < 50ms），只报一个均值会被长尾打脸。
- **私有化省的是固定成本摊薄后的边际成本，不是 token 单价**：低流量时云端按量计费更便宜；利用率过不了打平点就别自建——自托管决策看两个数：月 token 量是否过打平点、平均利用率能否 >50%。

## 技术交付物（来自 manifest.tech_load）

**容器化部署 7B/14B 模型，跑出一份压测报告**：脚本输出 TTFT、TPOT、P99、吞吐（QPS）与显存峰值，并附单位 token 成本账。

验收口径（对应 project.json 的任务）：

- 单卡容器内能拉起一个 7B（建议 INT4/AWQ）或 14B 模型的 OpenAI 兼容服务，启动参数与资源上限可复现；
- 压测脚本能产生分位延迟（P50/P95/P99）、错误率、长度分布、硬件与模型版本五列，且区分首字延迟与每 token 延迟；
- 报告能指出当前配置的显存峰值来自哪一项（权重 / KV / 激活 / 碎片），并给出「再开 N 并发会先撞哪条线」；
- 成本账给出满负载边际成本、利用率扫描、与云端 API 打平点三张表；
- 部署含健康检查与灰度描述，坏构建的爆炸半径被限制在一个可控比例内。
## 与 ai 学科的分界

`ai` 学科讲 Transformer 结构、注意力 O(n²) 与 KV cache 内部、量化算法（AWQ / GPTQ）的数学推导；本章**不推导模型内部**，只把模型当成一个有配额、有延迟分布、会失败、能报价的**服务**来部署。

需要理解「为什么长上下文更贵」时，回 `ai` 学科看注意力的 O(n²) 与 KV cache；本章只给工程结论：显存是硬约束、批处理是吞吐开关、利用率是成本杠杆。需要理解量化具体怎么做的，回 `ai` 学科；本章只给选型判据与损失经验值。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 96,022 | §01 显存四笔账 | §02 PagedAttention：`vllm/core/` 里 block_manager 把 KV Cache 切成固定块管理，读它就知道「显存碎片」为什么能被 PagedAttention 吃掉——这是本章显存账本最后一笔账的代码证据 |
| 2 | [sgl-project/sglang](https://github.com/sgl-project/sglang) | 37,561 | §02 连续批处理 | §02 TTFT/TPOT/吞吐是三件事：`benchmarks/` 下的脚本同时输出 TTFT、TPOT 与吞吐，换 batch size 跑两轮，就能看到本章「三者互相牵制」的实测曲线 |
| 3 | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | 133,016 | §01 量化省的是权重那笔账 | §01 显存的四笔账：`ggml/src/` 里各量化类型的反量化 kernel 一目了然，对照本章「Q4 省 4 倍但激活不变」，就明白为什么长上下文量化救不了 |
| 4 | [ollama/ollama](https://github.com/ollama/ollama) | 185,510 | §03 多租户配额 | §03 容器化与灰度：`README` 的部署矩阵列出各后端与硬件组合，按它跑一次本地服务，能实测本章「显存是第一约束」这句话 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | 全章 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（显存账本）核对 |
| 2 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex02`（KV Cache 增长曲线）核对 |
| 3 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | 全章 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex03`（量化收益）核对 |
| 4 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | 全章 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex04`（连续批处理 vs 静态批处理）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
