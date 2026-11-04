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
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §3.1 一、四层手段：从「约定」到「强制」 | 读 `tensorflow/python/ops/nn_ops.py` 的 `softmax` 与 argmax 相关实现：「在 logits 层直接屏蔽非法 token」这件事最终就落在这一步的算子链上，是本章四层手段里最强的一层；对照 §3.2「校验 - 重试 - 降级」就能看出，即便有约束解码也仍需要后置校验——语法合法不等于语义合法 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §4.5 五、Prompt 注入：结构性难题与纵深防御 | 读 `apps/api/src/index.ts`：抓来的网页正文与系统提示必须走不同通道，否则「数据」会被当成「命令」；这正是 §4.5 里「注入是结构性问题、不能靠提示词解决」的具体场景 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §2.3 三、CoT 什么时候反而有害 | 看 `classic/original_autogpt/autogpt/app` 的主循环：它每一步都强制输出思考再行动，在简单任务上就是纯浪费 token 与延迟；这正好印证本章「CoT 在任务本身不需要分步时有害」；对照 §2.1「CoT 为什么有效」，就能划出该不该强制思考的分界线 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §3.2 二、校验 - 重试 - 降级：唯一的健壮架构 | 读 `src/transformers/generation/logits_process.py`：`LogitsProcessor` 链按顺序改写 logits，每一步都可能把整段概率压没，所以即便加了约束解码，也必须在上层做「解析失败 → 重试 → 降级」；与 §3.3「约束解码的边界」并读，就能说清为什么约束不是银弹 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §2.1 一、CoT 为什么有效 | 读 `api/core/agent/cot_agent_runner.py`：它把「思考 → 行动 → 观察」写成显式状态循环，与 CoT 的「把中间步骤写出来」是同一机制在不同尺度上的实现；配合 §2.2「CoT 家族的主要变体」，就能看出 self-consistency 只是在同一个循环里采样多次再表决 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §4.3 三、位置策略：lost in the middle | 读 `libs/core/langchain_core/prompts/chat.py`：`ChatPromptTemplate` 把system / human / ai 拆成独立消息槽，顺序由模板决定而不是拼接顺序；这给了「把关键信息固定放在首尾」一个可执行的落点；配合 §4.4「前缀缓存与 token 预算」，就能权衡「省钱的顺序」与「模型实际读到的顺序」为什么冲突 |

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
