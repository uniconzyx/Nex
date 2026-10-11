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

## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 147524 | 检索器、向量库、RAG 链路的工业实现参考 |
| [langgenius/dify](https://github.com/langgenius/dify) | 157994 | Agentic 工作流与 RAG 流水线平台范例 |
| [huggingface/transformers](https://github.com/huggingface/transformers) | 167014 | embedding 模型与 cross-encoder 的标准入口 |
| [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 200724 | 深度学习框架官方仓库，工业级模型工程范例 |

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

- **ai-ch05（提示与上下文工程）**：本章的「拼接 evidence 进 prompt」「上下文预算」直接复用 ch05 的分层组织与位置策略。
- 本线**独立自足**：若你熟悉向量/矩阵运算与基本的概率检索概念，可直接从本章开始；章内所有定量结论都有 numpy 从零实现的可运行示例托底。
