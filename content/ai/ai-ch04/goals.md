# ai-ch04 · 高效微调与对齐：LoRA、RLHF 与 DPO

## 本章目标

学完本章，你应当能够：

1. **算清一笔显存账**：给定模型规模与训练方式（全参 / LoRA / QLoRA），估出权重、梯度、优化器状态、激活四部分占用，并判断「单卡能不能训」。
2. **说清 LoRA 到底在做什么**：低秩假设从哪来、A/B 为什么一个高斯初始化一个置零、`rank` 与 `alpha` 分别控制什么、`target_modules` 该选谁。
3. **讲明白对齐的三条路线**：RLHF（奖励模型 + PPO）、DPO（跳过奖励模型的闭式解）、RLAIF/GRPO 等替代方案，以及各自要付的工程代价。
4. **避开奖励黑客（reward hacking）**：知道 KL 约束为什么不可省，以及它会带来什么副作用（alignment tax）。
5. **建立选型直觉**：**注知识用 RAG、改行为用微调**——别再拿微调去背文档。

## 关键认知（本章最值钱的三句）

- **微调改的是「怎么说」，RAG 改的是「说什么」。** 想让模型记住你公司的内部文档，微调是又贵又差的选择；想让它稳定输出某种语气/格式/决策偏好，微调才是对的工具。
- **LoRA 不是「小一号的全参微调」**。它的假设是「任务适配所需的权重改变量 ΔW 是低秩的」，因此只用 A(d×r)·B(r×k) 两个小矩阵去近似它。这个假设在「行为对齐」上通常成立，在「注入海量新知识」上往往不成立。
- **RLHF 的难点不在 PPO，在奖励模型。** 奖励模型是人类偏好的代理（proxy），而任何代理都会被优化器钻空子——KL 惩罚就是给这个代理上的保险栓。
## 软前置（可选，不阻断学习）

- **ai-ch02（注意力机制）**：理解 QKV 与多头注意力的维度变换，有助于看懂 LoRA 为什么只挂在 `q_proj`/`v_proj` 上。
- **ai-ch03（Transformer 与 LLM 原理）**：本章反复引用「参数量估算」「KV Cache」「logits 与 softmax」这些概念，若已在 ch03 建立直觉，本章会顺畅很多。
- 本线**独立自足**：若你熟悉 PyTorch 的张量运算与反向传播，可直接从本章开始；章内所有定量结论都有 numpy 从零实现的可运行示例托底。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §2.3 | 讲「RLHF 的奖励建模」时读 `tensorflow/python/keras/` 的自定义 loss 写法：奖励模型的训练目标是「偏好对排序」，loss 形式与本章的 Bradley-Terry 一致 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §4.1 | 讲「指令微调数据的来源」时读 `apps/api/src/` 的抓取与清洗：把网页转成 markdown 后还要做质量过滤，否则 SFT 会学到大量模板化噪声 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §3.3 | 讲「对齐后模型的行为边界」时看 agent 的工具权限控制：即便模型被对齐过，也要在工具层加白名单与确认，不能把「模型不会做坏事」当作安全边界 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.2 | 讲「LoRA 的低秩分解」时读 `src/peft/`（PEFT 已并入 transformers 生态）的 `LoraLayer`：`A` 随机初始化、`B` 零初始化让「训练开始时等价于原模型」，这是 LoRA 能即插即用的关键 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §3.3 对齐后模型的行为边界 | 看 `api/core/` 的模型配置与 `graph/` 的工作流节点：对齐只保证「模型倾向于不越界」，真正的边界写在这里的工具白名单与人工确认节点上——这正是本章「对齐不等于权限控制」那一条的工程落点 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §3.2 | 讲「DPO 与 RLHF 的差别」时读 `libs/langchain/langchain/chains/` 里的偏好优化封装：DPO 直接用偏好对做监督式优化，省掉「训练奖励模型 + PPO」两步 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §1.1 主题一 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（LoRA 参数量）核对 |
| 2 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex02`（LoRA 初始化）核对 |
| 3 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | 全章 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex03`（低秩假设）核对 |
| 4 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | 全章 | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex04`（NF4 与 INT8 的量化解量化误差对）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
