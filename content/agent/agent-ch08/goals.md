# agent-ch08 · Transformer 核心机理：能白板推一遍才算懂

> 对应图片 DAY 19（B 站王树森解析）· 先修：agent-ch03（模型接入与 DeepSeek 实操）· 面试权重：★★★★☆
> 说明：面试官不问你「Transformer 是什么」，而问「注意力为什么除 √d_k」、「KV Cache 显存怎么算」、
> 「Pre-LN 和 Post-LN 差在哪」。这一章的目标是**白板讲清 + 落到数字 + 能跑通代码**。

## 本章目标

学完你应该能：

1. **白板画出并讲清完整前向链路**：tokenizer → embedding → 位置编码 → 注意力（QKV）→
   残差与 LayerNorm → FFN → 输出层与采样，说清每一步张量形状怎么变、信息在哪一步被混合。
2. **用 numpy 手写单头与多头缩放点积注意力，以及 2 层 Transformer 前向**：验证注意力权重
   每行和为 1、缩放能抑制 softmax 饱和、多头在 `H=1` 时退化为单头（参数量不变）。
3. **用 nanoGPT 在玩具数据上跑通一次训练**：能读取 train/val loss 曲线，指出收敛点、
   val loss 最低点与过拟合拐点，能解释「为什么曲线初期陡降、后期平台」。
4. **算一遍参数量与 KV Cache 显存账本**：给定模型维度、层数、头数、序列长度、批量，
   把「长上下文为什么贵」落到具体 GB 数字，并比较 MHA / GQA / MQA 三者的显存差异。
5. **说清采样参数与学科边界**：给定 temperature / top-p，能预测其对输出多样性与稳定性的影响；
   能明确说出本章与 `ai` 学科的分工——本章只要求「白板讲清 + numpy 复现核心」。

## 关键认知（本章最值钱的三句）

- **注意力不是「相似度」，是「用相似度做加权求和」**：softmax 之前的点积只是**分数**，
  真正的信息流动发生在 `softmax(·)V` 这个加权和里。QK 决定「看哪里」，V 决定「取什么」。
  只盯着 QK 相似度理解注意力，会漏掉最关键的 V 投影。
- **缩放因子 √d_k 是为了救梯度**：点积的方差随维度 `d_k` 线性增长，维度一大，softmax 输入
  被推到饱和区，梯度趋近 0。除以 √d_k 把方差拉回 1，是「让训练不崩」而非「让结果更准」。
- **长上下文的贵来自两根曲线**：注意力计算的 O(n²) 与 KV Cache 显存的 O(n)（按层与头数放大）。
  所有工程优化（RoPE、GQA、MQA、FlashAttention）本质都是在给这两根曲线做减法，
  而不是提升「模型变聪明了」。

## 技术交付物（来自 manifest.tech_load）

**交付物一：numpy 手写单头 / 多头注意力与前向**
- 单头缩放点积注意力：输入 Q/K/V，输出加权 V，验证 `Σ_j α_ij = 1`。
- 多头：拆分 → 各头独立注意力 → 拼接 → 输出投影；验证 `H=1` 时退化为单头且参数量一致。
- 因果 mask：验证「遮住未来 token 后，前缀输出不变」。
- 对应示例 ex01 / ex02 / ex03。

**交付物二：用 nanoGPT 跑通一次训练并解释 loss 曲线**
- 在玩具语料上训练一个字符级 2 层模型，loss 从 `ln(V)` 附近下降；
- 能读取训练曲线，指出 train/val 收敛位置、val 最低点、过拟合拐点；
- 对应示例 ex10（受「禁止联网下载 nanoGPT」约束，示例用 numpy 复刻同构的训练循环，
  真实接入 nanoGPT 仓库见下方 GitHub 资源）。
- 验收口径：给出 loss 随 step 下降的曲线图（或文本折线），并写清楚每一段代表什么。

## 本章 GitHub 资源（star 数取自 manifest，GitHub API 实测 2026-10-21，均为精确值）

- `karpathy/nanoGPT` — 63967★：看 `train.py` 与 `model.py`，把 Transformer 从公式变成
  可运行的张量；交付物二「跑通一次训练」就是照它最小配置来。
- `karpathy/build-nanogpt` — 5577★：逐行重写 GPT-2 的视频配套仓库，适合跟着敲一遍，
  解决「论文看懂了但张量维度对不上」的问题。
- `huggingface/transformers` — 167942★：读 `models/gpt2/modeling_gpt2.py` 等文件，
  看工业级实现与论文的差异（如 attention 的 scaling、position_ids、cache 实现）。
- `jingyaogong/minimind` — 64067★：从零训练 26M 小模型的全流程，
  算力有限时最好的练手项目，能补齐「数据 → 训练 → 推理」的完整链路认知。

## 本章 B 站学习清单

入口（站内搜索，视频会更新，故不写死 BV 号）：
https://search.bilibili.com/all?keyword=%E7%8E%8B%E6%A0%91%E6%A3%AE%20Transformer

按 manifest 的 `bilibili_keywords` 看三组：

1. **王树森 Transformer**：看注意力、LayerNorm、残差的整体推导与数据流。看完要能回答：
   「QKV 各自在学什么？为什么先 LayerNorm 再算注意力（Pre-LN）成了主流？」
2. **注意力机制 手推**：看缩放点积、因果 mask、多头拆分的逐行推导。看完要能回答：
   「不除以 √d_k 会发生什么？因果 mask 在 softmax 之前还是之后加？」
3. **KV Cache 原理**：看推理时 K/V 为什么要缓存、显存怎么随序列长度涨。看完要能回答：
   「同样的模型，上下文从 2k 涨到 32k，显存为什么不是翻倍而是涨十几倍？」

## 与 ai 学科的分界

`ai` 学科负责 Transformer 的**完整数学推导与源码级实现**：注意力复杂度的严格证明、
旋转位置编码的矩阵形式、LoRA 的低秩分解、各类 attention 变体的梯度推导。

本章**只要求「能白板讲清 + numpy 复现核心」**：你不必推导 RoPE 的等价旋转矩阵，
但要能在白板上写出 `softmax(QKᵀ/√d_k)V` 并解释每个符号；不必读通 FlashAttention 的
CUDA 实现，但要能算出 KV Cache 的显存账本。遇到「为什么这样设计」的深层机理，
回 `ai` 学科追推导；本章停在「够用即止的原理 + 工程判据 + 可运行产物」。
