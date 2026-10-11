# ai-ch05 · 提示工程与上下文工程

## 本章目标

学完本章，你应当能够：

1. **把「提示工程」拆成可度量的四件事**：指令措辞、示例选择与排序、输出结构约束、上下文组织。它们各自的收益与代价不同，混在一起调就是在瞎调。
2. **讲清 CoT 为什么有效，以及它什么时候无效**：中间 token 是「额外的计算与上下文」，不是「让模型变聪明」；以及在什么任务上 CoT 反而掉点。
3. **建立结构化输出的四层防线**：Schema 约定 → 原生结构化输出 → Function Calling → 文法约束解码，逐层收紧、也逐层牺牲自由度；外层永远要配「校验-重试-降级」。
4. **像管理内存一样管理上下文**：分层组织（系统 / 记忆 / 证据 / 历史）、压缩（滚动摘要、状态槽）、位置策略（lost in the middle）、前缀缓存，以及 token 预算的显式分配。
5. **知道 prompt 注入为什么防不干净**：它是「数据与指令在同一信道」的结构性问题，只能做纵深防御。

## 关键认知（本章最值钱的三句）

- **上下文窗口不是「免费的记事本」**。它既是输入成本，也是干扰源：塞得越多，模型对**中间位置**信息的利用率越低（lost in the middle）。上下文工程的第一原则是**做减法**，不是做加法。
- **少样本示例的价值不在「教知识」，而在「定格式与定边界」**。示例的顺序、数量、标签分布都会系统性偏移模型行为——示例集本身就是一个需要评估的数据集。
- **结构化输出的可靠性来自「约束 + 校验 + 降级」三件套**，而不是「prompt 里写一句『请输出 JSON』」。只要没有解码期约束，就一定会有一定比例的不合法输出。

## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 147524 | prompt 模板、输出解析器与重试链的工业实现 |
| [langgenius/dify](https://github.com/langgenius/dify) | 157994 | 可视化 prompt 编排与上下文变量管理 |
| [huggingface/transformers](https://github.com/huggingface/transformers) | 167014 | 约束解码 / 结构化生成的底层实现入口 |
| [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187681 | ReAct 式工具循环与上下文压缩的经典工程范例 |

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

- **ai-ch03（Transformer 与 LLM 原理）**：本章反复引用「token 化」「注意力权重」「softmax 温度」这些概念，若已建立直觉，本章会顺畅很多。
- 本线**独立自足**：章内所有定量结论都有纯 Python / numpy 的可运行示例托底，不依赖任何外部 API。
