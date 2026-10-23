# 位置编码与归一化：顺序怎么进模型，残差流怎么走

> 注意力对输入顺序是**置换等变**的——把句子里的词打乱，输出只是跟着打乱，模型本身「不知道」
> 谁在前谁在后。位置信息必须显式注入。另一根主线是归一化与残差的位置之争，它直接决定
> 深层网络能不能训得动、训得稳。

## 1. 为什么必须注入位置：注意力本身没有顺序感

中立陈述：自注意力对每个位置的计算只依赖「Token 之间的内容关系」，不依赖「Token 在句子里的
第几个」。`Attention(Permute(X)) = Permute(Attention(X))`。这意味着没有位置信号时，
「猫吃鱼」和「鱼吃猫」在模型眼里只是同一组词的两种排列。位置编码就是给每个位置一个
**与内容无关、只标识顺序**的向量，加到 embedding 上。

两种主流路线：

| 路线 | 做法 | 相对位置能力 | 外推到更长序列 |
|---|---|---|---|
| 绝对位置（正弦 / 可学习） | 每个位置 `pos` 一个向量，直接加到词向量 | 弱（绝对坐标） | 可学习式几乎不能；正弦式靠波长部分可外推 |
| 相对位置（RoPE） | 在 Q/K 上做**按位置旋转**，内积只依赖相对距离 | 强（内积含 `m-n`） | 旋转频率固定，超长需 NTK 缩放等技巧 |

## 2. 正弦绝对编码 vs RoPE：一个是「加标签」，一个是「转坐标系」

中立陈述：原始 Transformer 用正弦曲线 `PE(pos,2i)=sin(pos/10000^(2i/d))` 作为绝对位置，
直接逐位加到 embedding。它的好处是可外推、不占参数；坏处是位置是「绝对坐标」，两个 Token 的
相对关系要靠模型自己学。

RoPE（Rotary Position Embedding）换了个思路：不另加向量，而是把位置编码做成**旋转**——
对 Q、K 的每对相邻维度按角度 `θ·pos` 旋转，使得 `Q_m·K_n` 的内积天然含有 `(m-n)` 项，
相对位置直接「长」在注意力分数里。

```python
import numpy as np

def rope(x, pos):
    # x: (seq, d)，对相邻两维 (2i,2i+1) 按角度 theta*pos 旋转
    d = x.shape[-1]
    theta = 1.0 / (10000 ** (np.arange(0, d, 2) / d))   # 频率
    ang = np.outer(pos, theta)                          # (seq, d/2)
    cos, sin = np.cos(ang), np.sin(ang)
    x_even, x_odd = x[..., 0::2], x[..., 1::2]
    rot_even = x_even * cos - x_odd * sin
    rot_odd  = x_even * sin + x_odd * cos
    out = np.empty_like(x)
    out[..., 0::2], out[..., 1::2] = rot_even, rot_odd
    return out

# RoPE 的关键性质：相对位置只由 (m-n) 决定
q, k = rope(np.ones((2, 4)), np.array([5.0, 8.0]))
# <旋转后的 q_5, 旋转后的 k_8> 只依赖 8-5=3，不依赖绝对位置 5/8 本身（示例 ex04 验证）
```

经验判断：2023 年后的主流开源模型（Llama 系列、Qwen 等）几乎都用 RoPE，原因是相对位置
对长上下文与注意力泛化更友好；但 RoPE 的「完美外推」是误区——超出训练长度同样会退化，
需要 NTK-aware 缩放等补救（对应示例 ex04 的 RoPE 相对性验证）。

## 3. Pre-LN vs Post-LN：残差流为什么不能先归一化再走

中立陈述：每个子层（注意力 / FFN）外面包一个 `LayerNorm + 残差`：`x_{t+1} = x_t + Sublayer(Norm(x_t))`。
Norm 放子层**之前**（Pre-LN）还是**之后**（Post-LN）是 Transformer 训练稳定性最关键的设计选择。

```
Post-LN:  x ← x + Sublayer( x )      → 再 LayerNorm(x)         （原版 Transformer）
Pre-LN:   x ← x + Sublayer( LayerNorm(x) )                    （现代主流）
```

数值实验（示例 ex07）的结论：Post-LN 在深层时梯度尺度极不稳定，需要很小心地学习率预热；
Pre-LN 把归一化放在残差分支的「输入侧」，使恒等路径 `x_t` 始终以无缩放形态流过，梯度不会
随层数指数放大或缩小——这正是现代大模型能堆到几十上百层的基础。代价是 Post-LN 理论上
「残差流」更干净，Pre-LN 的表示稍有冗余，但工程上稳定性压倒一切。

```python
def pre_ln_block(x, attn, ffn, gamma, beta):
    h = attn(layernorm(x, gamma, beta))   # 先归一化再做子层
    x = x + h                             # 恒等路径不被缩放
    h = ffn(layernorm(x, gamma, beta))
    return x + h

def post_ln_block(x, attn, ffn, gamma, beta):
    h = attn(x)
    x = layernorm(x + h, gamma, beta)     # 归一化在残差之后
    h = ffn(x)
    return layernorm(x + h, gamma, beta)  # 深层时梯度易爆炸/消失
```

> 经验判断：面试里「为什么现代都用 Pre-LN」的标准答法是「残差分支不受 LayerNorm 缩放，
> 深层梯度尺度稳定」。能接一句「Post-LN 需要 warmup 才稳」是加分项。

---

## 三视角解析

### 🧑‍💻 程序员视角

- 绝对正弦编码现在少用了，但 `pos / 10000^(2i/d)` 这串频率在你自己写位置编码时仍然是个好起点；
  可学习位置编码更简单，但序列一变长就哑火。
- RoPE 在推理时的便宜之处：旋转只依赖 `pos` 和频率，KV Cache 里存的是**已旋转**的 K/V，
  后续步直接拿缓存算点积，不必回算旋转（示例 ex08 的显存账本就基于此）。
- Pre-LN 的工程后果很实在：你几乎不用为「层数多了训崩」头疼，学习率预热可以短很多。
  接 HuggingFace 时看 `modeling_*.py` 里 `norm1 / norm2` 出现在 `attn/ffn` 之前还是之后，
  一眼能判断它是 Pre 还是 Post。
- 一个容易踩的坑：RoPE 的维度必须是偶数，且旋转是「两两配对」；奇数维度最后一位不参与旋转，
  写错形状会静默地让位置信号缺失。

### 🎓 博士生视角

- RoPE 的数学本质：把位置编码写成旋转矩阵 `R(pos)`，要求
  `R(m)Q_m · R(n)K_n = g(Q_m, K_n, m-n)`，即内积只依赖相对位移。这比可学习绝对编码的
  归纳偏置更契合「语言依赖的是相对顺序」这一先验。
- 残差流（residual stream）视角：把 `x_t` 看作一条贯穿各层、维度固定的「主干道」，
  每个子层只往主干上做小幅「增量写入」。Pre-LN 让写入前先归一化，主干自身始终保持稳定尺度，
  这也是后续「 mechanistic interpretability 」把模型当线路图分析的物理基础。
- Post-LN 的梯度爆炸可由「初始化 `γ`（LayerNorm 的缩放）为接近 0」缓解，使残差分支
  初始几乎为零，等于先训一个浅网络再慢慢放开——这是早期稳定训深层 Post-LN 的技巧。

### 📚 考研者视角

- 标准表述要能写出：**注意力对输入置换等变，因此需要位置编码**；并区分
  「绝对位置编码（加一个位置向量）」与「相对位置编码（让注意力分数依赖相对距离）」。
- 常考计算：正弦编码第 `i` 个维度频率 `1/10000^(2i/d)`，周期随维度升高而变长；
  低频维表达「大尺度位置」，高频维表达「细粒度顺序」。
- 易混概念：**LayerNorm vs BatchNorm**。BatchNorm 跨 batch 维归一化、训练推理行为不一致、
  不适合变长序列；LayerNorm 跨特征维、对每个样本独立、天然适配 NLP 变长输入。Transformer 用 LN。
- 另一个易错点：**Pre-LN 不是「不要归一化」，而是「把归一化挪到子层输入侧」**。
  答题时画出 `x + Sublayer(Norm(x))` 的表达式即可避免被追问时露怯。
