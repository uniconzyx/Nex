# ai-ch03 · Transformer 与大语言模型原理

> 先修：ai-ch02（CNN/RNN/注意力演进）。衔接：ai-ch04（微调与对齐）、ai-ch05（提示工程）。
> 学科线：AI / Agent 开发 · A2 大模型原理与训练。面试权重：★★★★★（算法/大模型岗必考）

## 本章目标

学完你应该能：

1. **说清自注意力的计算与第一性原理**：Q/K/V 的来历、√d_k 缩放的必要性、softmax 的温度形式化，
   以及为什么纯自注意力是「置换等变」的——这正是位置编码存在的根本动机。
2. **手写多头注意力的维度变换**：reshape + transpose 拆头、拼接合并，并说出参数量
   `4·d_model²` 与头数无关这一常被误算的结论。
3. **讲清位置编码的演进与 RoPE 的相对位置性质**：正弦→可学习→相对位置→RoPE/ALiBi，
   并能形式化说明「RoPE 旋转后 Q·K 内积只依赖相对距离 m−n」。
4. **理解 Decoder-only 自回归的两阶段（prefill / decode）与 KV Cache 显存账**：
   能给定层数/头数/head_dim/序列长度/dtype 估算 KV Cache 字节数，说清 decode 是 memory-bound。
5. **掌握采样策略与生成控制**：greedy / temperature / top-k / top-p 在同一批 logits 上的差异，
   以及困惑度 PPL = exp(CE) 与交叉熵的关系。
6. **说清架构取舍、训练目标与 Scaling Law**：Encoder-Decoder vs Decoder-only、GPT 的 next-token 目标、
   LayerNorm vs BatchNorm、残差 + LayerNorm 的梯度路径、Scaling Law 与 Chinchilla 最优。

## 关键认知（本章最值钱的三句）

- **纯自注意力对词序盲目**：它置换等变，位置信息必须显式注入——这是一切位置编码的出发点。
- **√d_k 缩放 = softmax 温度**：把 logits 除以 √d_k 与「程序员调 temperature」是同一机制，
  softmax 对输入尺度极敏感，不缩放会在大 d_k 下饱和、梯度趋零。
- **decode 是显存带宽瓶颈不是算力瓶颈**：每步只算 1 个 query，却要读全部历史 KV Cache，
  所以长上下文的成本首先在 KV 显存，而非 FLOPs。
## 软前置（可选，不阻断学习）

- 线性代数（矩阵乘法、softmax、向量内积）与 `ai-ch01`（反向传播）有助于理解梯度路径；
  不掌握也可先学本章工程视角，机制视角留待回看。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §2.2 | 讲「缩放点积的数值行为」时读 `tensorflow/python/ops/nn_ops.py` 的 `softmax`：数值稳定实现会先减去最大值，这解释了「不缩放时 softmax 饱和」为什么会让梯度消失 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §2.1 | 讲「预处理对模型输入的影响」时读 `apps/api/src/` 的 markdown 清洗：去掉导航与广告后，进入上下文的 token 才是「有效信息」，这直接影响注意力的信噪比 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §4.1 | 讲「长上下文的工程约束」时看 agent 的记忆管理：历史太长就摘要、关键信息单独存，与本章「KV Cache 随序列线性增长」是同一个约束的两种应对 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.1 | 讲「自注意力的实现」时读 `src/transformers/models/bert/modeling_bert.py` 的 `BertSelfAttention`：`query/key/value` 三个线性层 + `softmax(QKᵀ/√d)V`，与本章公式逐行对应 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §4.3 | 讲「Transformer 在 RAG 里的位置」时读 `api/core/rag/`：检索出的片段被拼进 prompt，模型用注意力在这些片段上做「软对齐」——RAG 的效果上限由这一步决定 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §3.1 | 讲「上下文窗口的代价」时读 `libs/core/langchain_core/` 的消息裁剪逻辑：超长上下文要做截断或摘要，本质是「注意力 O(n²) 的成本」在应用层的体现 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §1.1 自注意力 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（单头自注意力完整数值演算（含因果掩码））核对 |
| 2 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | 全章 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex02`（多头注意力拆头/合并维度变换逐项验证）核对 |
| 3 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | §1.1 自注意力 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex03`（位置编码对比）核对 |
| 4 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | §4.1 采样策略 | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex04`（KV Cache 显存估算器（确定性数字）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
