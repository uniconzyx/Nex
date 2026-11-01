# ai-ch06 · RAG：向量检索与知识增强

## 本章目标

学完本章，你应当能够：

1. **说清 RAG 的两条链路**：离线索引（解析 → 分块 → 向量化 → 入库）与在线查询（query 向量化 → 召回 → 重排 → 拼接 → 生成），并理解「检索质量决定上限」。
2. **算清相似度的账**：余弦 / 内积 / L2 三者在「向量归一化后」的等价关系，能解释为什么工程上先归一化再只算内积（见 ex01/ex02）。
3. **设计分块策略**：固定长度 + 重叠、结构感知、语义分块、父子块各自的取舍，以及重叠为什么会缓解边界切断（见 ex03）。
4. **搭起混合检索**：向量检索补语义、BM25 补关键词，用 RRF 把多路排名融合（见 ex04/ex05），并知道 BM25 的 IDF 符号与 TF 饱和。
5. **读懂两阶段召回 + 重排**：双塔粗排与交叉编码器精排的分工，以及 top-k 该怎么定。
6. **选对向量索引**：HNSW / IVF / PQ 在「召回-延迟-内存」三角里的取舍，能按数据规模估算存储与召回损失（见 ex07/ex08/ex09）。
7. **建立分层评估观**：Recall@k / MRR / NDCG@k 与 Faithfulness / 引用准确率，并用「换检索器」对照实验证明 RAG 有用（见 ex06）。

## 关键认知（本章最值钱的三句）

- **RAG 改的是「说什么」，微调改的是「怎么说」。** 想让模型稳定引用你公司的内部/实时文档，RAG 是对的工具；想让它稳定输出某种语气/格式/决策偏好，才轮到微调。
- **检索质量决定 RAG 上限，生成质量决定下限。** 召回不到，再强的 LLM 也只能「编造」；召回到了却没用上，是重排与拼接的问题。
- **向量检索不是银弹。** 对精确字符串、ID、专有名词，稀疏检索（BM25）常常更准——混合检索 + RRF 才是生产标配。
## 软前置（可选，不阻断学习）

- **ai-ch05（提示与上下文工程）**：本章的「拼接 evidence 进 prompt」「上下文预算」直接复用 ch05 的分层组织与位置策略。
- 本线**独立自足**：若你熟悉向量/矩阵运算与基本的概率检索概念，可直接从本章开始；章内所有定量结论都有 numpy 从零实现的可运行示例托底。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | 全章 | 深度学习框架官方仓库，工业级模型工程范例；本章先读与「主题一」「主题二」相关的部分 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | 全章 | 为 AI Agent 提供网页数据：抓取到结构化数据的工程实现；本章先读与「主题一」「主题二」相关的部分 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | 全章 | 自主 Agent 的开创性项目，Agent 架构与工具循环的经典参考；本章先读与「主题一」「主题二」相关的部分 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | 全章 | Transformer 模型定义框架：从 BERT/GPT 到多模态的全量实现；本章先读与「主题一」「主题二」相关的部分 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | 全章 | Agentic 工作流与 RAG 流水线平台：生产级 LLM 应用工程范例；本章先读与「主题一」「主题二」相关的部分 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | 全章 | Agent 工程平台：工具、记忆、检索与编排的工业实现；本章先读与「主题一」「主题二」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | 全章 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（相似度度量对比）核对 |
| 2 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex02`（余弦相似度手算）核对 |
| 3 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | 全章 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex03`（chunk 切分器）核对 |
| 4 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | 全章 | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex04`（BM25 手写实现）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
