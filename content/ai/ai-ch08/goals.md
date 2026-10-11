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

## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 200724 | 深度学习框架官方仓库，量化/推理工程参考 |
| [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 189309 | 网页抓取到结构化数据：间接提示注入与输入净化的真实数据源 |
| [huggingface/transformers](https://github.com/huggingface/transformers) | 167014 | 量化与推理配置（GPTQ/AWQ/bitsandbytes）的标准入口 |
| [langgenius/dify](https://github.com/langgenius/dify) | 157994 | 生产级 LLM 应用平台：Trace、评测、成本面板的工程范例 |
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 147524 | 回调/追踪（callback & tracing）与 LLM-as-Judge 评测的工业实现 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at` 为准。


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 吴恩达 · 深度学习专项课程（中英字幕） | [视频](https://www.bilibili.com/video/BV164411b7dx/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 跟李沐学 AI · 动手学深度学习 v2 | [视频](https://space.bilibili.com/1567748478/lists/358497/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 炮哥带你学 · PyTorch 框架与经典 CNN 实战 | [视频](https://www.bilibili.com/video/BV1eP411w7Re/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 李宏毅 · 机器学习 2021 | [视频](https://www.bilibili.com/video/BV1JA411c7VT/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）

- **ai-ch06（RAG）**：本章的「上下文成本」「检索证据的注入风险」直接复用 RAG 的拼接与召回概念；间接提示注入的载体正是检索到的文档。
- **ai-ch07（Agent）**：Agent 步数、工具返回值的净化、最小权限都是本章可观测性与安全章节的延伸场景。
- 本线**独立自足**：若你熟悉 Transformer 推理的基本概念与 Python/numpy，可直接从本章开始；章内所有定量结论都有可离线复跑的示例托底。
