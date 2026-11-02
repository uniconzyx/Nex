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
## 软前置（可选，不阻断学习）

- **ai-ch03（Transformer 与 LLM 原理）**：本章反复引用「token 化」「注意力权重」「softmax 温度」这些概念，若已建立直觉，本章会顺畅很多。
- 本线**独立自足**：章内所有定量结论都有纯 Python / numpy 的可运行示例托底，不依赖任何外部 API。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §2.3 | 讲「温度与采样的影响」时读 `tensorflow/python/ops/` 的 `top_k`/`top_p` 实现：它们改的是分布形状，不是「准确性」——低温更确定但不一定更对 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §4.2 | 讲「提示注入的防护」时读 `apps/api/src/` 的内容清洗：抓来的网页文本可能含指令，必须与系统提示隔离，否则「数据」会被当成「命令」 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §3.1 | 讲「CoT 与自洽性」时看 agent 的思考链：它把「先计划再执行」写进提示，与 CoT 的「显式中间步骤」是同一机制在不同尺度上的应用 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §4.1 | 讲「结构化输出的可靠性」时读 `src/transformers/generation/` 的约束解码相关实现：用语法约束 token 采样，比「请在 JSON 里回答」可靠得多 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §2.2 | 讲「少样本示例的组织」时读 `api/core/` 下的 prompt 编排模块：示例与指令分段存放、按场景组装，本章「例子要覆盖边界」在这里变成「示例集合的维护」 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §1.1 | 讲「提示模板的工程化」时读 `libs/core/langchain_core/prompts/`：`PromptTemplate` 把变量槽位与格式约束分开，避免「字符串拼接到处飞」 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | 全章 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（token 计数估算器）核对 |
| 2 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | 全章 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex02`（上下文窗口预算分配与溢出判定）核对 |
| 3 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | 全章 | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex03`（三种截断策略）核对 |
| 4 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex04`（few-shot 示例选择）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
