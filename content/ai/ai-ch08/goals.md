# ai-ch08 · LLM 应用工程：推理优化、评测、可观测性与安全

## 本章目标

学完本章，你应当能够：

1. **把「延迟」拆开**：说清 Prefill 决定 TTFT、Decode 决定 TPOT 的两阶段模型，并知道两阶段分别受算力还是带宽约束（见 ex03）。
2. **算清 KV Cache 的账**：用「2 × 层数 × KV 头数 × 头维 × 序列长 × 批 × 精度字节」估算显存，并解释 GQA/MQA 为什么能把它压到 1/4 甚至更低（见 ex01）。
3. **讲透批处理演进**：从静态批处理到连续批处理（continuous batching）再到投机解码，各自的吞吐收益来源与代价（见 ex04/ex05）。
4. **做量化的精度-内存取舍**：区分 FP16/INT8/GPTQ/AWQ/GGUF/NF4 的定位，用实测的舍入误差说明「NF4 省内存但小权重相对误差可接近 1」（见 ex02）。
5. **排对优化顺序**：先度量 → 砍上下文 → 分模型（路由）→ 加缓存（含语义缓存）→ 再谈推理加速，避免一上来就换推理框架（见 ex06/ex09）。
6. **搭起可观测性三件套**：Trace/Log/Metric 的分工，以及 AI 特有维度（幻觉率、格式合规率、单请求成本、Agent 步数）怎么上报。
7. **设计线上评测**：影子模式、A/B、离线回放、人工抽检的适用边界，用 z 检验判断显著性（见 ex12），并会给 LLM-as-Judge 做校准、用 Cohen's Kappa 量化一致性（见 ex07）。
8. **建立安全纵深**：对照 OWASP LLM Top 10，识别直接与间接提示注入，实施输入净化（见 ex08）、最小权限与输出校验，并落实数据最小化、脱敏与可删除（见 ex11）。

## 关键认知（本章最值钱的三句）

- **TTFT 和 TPOT 是两种病，得吃两种药。** Prefill 计算受限（冲 TTFT：批化 prefill、chunked prefill、前缀缓存）；Decode 带宽受限（冲 TPOT：量化权重、GQA、投机解码、连续批处理）。
- **优化顺序错了，努力全白费。** 先加推理加速框架往往只动了个位数百分比，而先砍上下文、加前缀缓存、做模型路由常常是数倍收益——所以第一步永远是度量。
- **AI 系统的可观测性必须多三个维度。** 传统 APM 只看延迟/错误/流量；LLM 还要看幻觉率、格式合规率、单请求成本、Agent 步数，否则「一切正常」的仪表盘下面藏着不断升高的账单和悄悄下降的答案质量。
## 软前置（可选，不阻断学习）

- **ai-ch06（RAG）**：本章的「上下文成本」「检索证据的注入风险」直接复用 RAG 的拼接与召回概念；间接提示注入的载体正是检索到的文档。
- **ai-ch07（Agent）**：Agent 步数、工具返回值的净化、最小权限都是本章可观测性与安全章节的延伸场景。
- 本线**独立自足**：若你熟悉 Transformer 推理的基本概念与 Python/numpy，可直接从本章开始；章内所有定量结论都有可离线复跑的示例托底。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,297 | 全章 | 深度学习框架官方仓库，工业级模型工程范例；本章先读与「主题一」「主题二」相关的部分 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 195,953 | 全章 | 为 AI Agent 提供网页数据：抓取到结构化数据的工程实现；本章先读与「主题一」「主题二」相关的部分 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,785 | 全章 | 自主 Agent 的开创性项目，Agent 架构与工具循环的经典参考；本章先读与「主题一」「主题二」相关的部分 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,266 | 全章 | Transformer 模型定义框架：从 BERT/GPT 到多模态的全量实现；本章先读与「主题一」「主题二」相关的部分 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 159,119 | 全章 | Agentic 工作流与 RAG 流水线平台：生产级 LLM 应用工程范例；本章先读与「主题一」「主题二」相关的部分 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,600 | 全章 | Agent 工程平台：工具、记忆、检索与编排的工业实现；本章先读与「主题一」「主题二」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §1.2 主题二 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（KV Cache 显存占用公式计算器（M）核对 |
| 2 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | 全章 | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex02`（量化精度损失数值模拟）核对 |
| 3 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex03`（TTFT / TPOT 两阶段延迟分解模）核对 |
| 4 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | 全章 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex04`（连续批处理 vs 静态批处理）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
