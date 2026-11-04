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
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §1.1 主题一：显存四件套——权重、梯度、优化器状态、激活 | 读 `tensorflow/python/keras/layers/core.py` 的自定义 `Layer` 写法：每一层在训练时除了权重还要存梯度和优化器槽位，前向的中间结果还要留着做反向——四件显存就是这样一层层堆出来的；带着这本账再读 §1.2「SFT 的数据构造与损失掩码」，就明白掩码省下的不只是损失、还有非 assistant 位置的激活 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §2.1 主题一：LoRA 的低秩假设、初始化与 target_modules | 读 `apps/api/src/index.ts` 的抓取管道：它把「抓取」与「清洗」两个职责拆成独立步骤、各自可替换，主流程只负责串起来——LoRA 的思路与此同构：不改主干（抓取器），只在旁边挂一个可训练的低秩增量（新步骤）；配合 §2.2「QLoRA 的四位量化与分页优化器」，就能说清「低秩」与「低比特」是省显存的两条独立轴 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §3.1 主题一：从人类偏好到奖励模型（Bradley-Terry） | 看 `classic/original_autogpt/autogpt/app`：Agent 用「这步好不好」的规则决定要不要重试，就是一个手写的奖励信号；本章要做的只是把这个手写规则换成训练出来的标量模型，差别在于 §3.2「PPO 的 KL 约束」——手写规则不会过拟合人类偏好，学出来的会 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §2.2 主题二：QLoRA 的四位量化与分页优化器 | 读 `src/transformers/models/llama/modeling_llama.py` 的 `LlamaDecoderLayer`：主干层结构固定、参数量占绝对大头，所以「量化冻结的主干 + 训练低秩增量」才划得来；配合 §2.1「LoRA 的低秩假设」，就知道 target_modules 为什么几乎只挑 `q_proj`/`v_proj` 这类方阵 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §4.2 主题二：选型原则——注知识用 RAG，改行为用微调 | 读 `api/core/rag/retrieval/dataset_retrieval.py`：检索层把外部知识按需拼进上下文、模型权重一点不动，这正是「注知识用 RAG」的工程形态；与 §4.1「DPO 的闭式推导与工程优势」并读，就形成「改行为才动权重」的完整判据 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §4.1 主题一：DPO 的闭式推导与工程优势 | 读 `libs/langchain_v1/langchain/chat_models/base.py`：同一套 chat 接口既能接「奖励模型 + PPO」的两段式，也能接「偏好对直接回归」的一段式，差别只在训练目标；对照 §3.2 里 PPO 需要的四个模型（策略/参考/奖励/价值），就能量化说明 DPO 省掉了哪两块显存 |

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
