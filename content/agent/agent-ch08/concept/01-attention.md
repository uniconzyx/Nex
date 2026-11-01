# 注意力机制：QKV 的几何意义、缩放、多头与因果 mask

> 注意力是 Transformer 唯一做「Token 间信息混合」的地方。其余组件（embedding、FFN、
> LayerNorm、残差）都在逐个 Token 独立处理。把这一节讲清，后面一切（位置编码、KV Cache、
> 长上下文成本）都挂在它上面。

```text
注意力 = Token 间唯一的信息混合处:
  Q·Kᵀ/√d ─softmax─▶ 注意力权重 ─▶ ×V ─▶ 输出
  QK 决定「看哪里」   V 决定「取什么」
  多头 = 在多个子空间并行看
```


## 1. 注意力在算什么：QK 决定「看哪里」，V 决定「取什么」

中立陈述：对第 `i` 个查询 Token，注意力先算它和所有 Key 的相似度（点积），softmax 归一化成
权重，再用这些权重对 Value 做加权求和。信息从 V 流入输出，QK 只决定「流多少」。

```
Attention(Q, K, V) = softmax( Q · Kᵀ / √d_k ) · V
                       └── 分数(行和=1) ──┘   └─ 取值 ─┘
```

几何意义：Q、K 在同一向量空间里比较方向，点积 `Q·K = |Q||K|cosθ`。两个 Token 语义越相关、
方向越一致，分数越高。但**分数只是权重，不是输出**；真正的语义内容由 V 携带。

| 矩阵 | 角色（在学什么） | 形状 | 类比 |
|---|---|---|---|
| Q (query) | 「我想从别人那里找什么信息」 | `(n, d_k)` | 检索的提问 |
| K (key) | 「我能提供什么信息的索引」 | `(n, d_k)` | 检索的标签 |
| V (value) | 「我实际携带的语义内容」 | `(n, d_v)` | 检索的原文 |

```python
import numpy as np

def single_head_attention(Q, K, V, scale=None):
    d_k = Q.shape[-1]
    scale = scale or np.sqrt(d_k)
    scores = Q @ K.T / scale          # (n, n) 分数矩阵
    # 数值稳定：减每行最大值再 exp，结果不变但防溢出
    scores -= scores.max(axis=-1, keepdims=True)
    w = np.exp(scores)                # 尚未归一化
    w /= w.sum(axis=-1, keepdims=True)  # 每行和为 1
    return w @ V, w                   # 输出与注意力权重

# 验证：权重每行和应为 1.0（示例 ex01 的判据）
out, w = single_head_attention(np.random.randn(4, 8),
                               np.random.randn(4, 8),
                               np.random.randn(4, 8))
assert np.allclose(w.sum(axis=-1), 1.0)
```

## 2. 为什么要缩放 √d_k：救梯度，不是救结果

中立陈述：点积 `Q·K` 的方差随维度 `d_k` 线性增长。假设 Q、K 各分量独立、均值 0、方差 1，
则单个点积的方差约为 `d_k`。维度一大，softmax 的输入被推到饱和区，`e^x` 巨大、梯度趋近 0，
训练起不来。除以 √d_k 把方差拉回 1，这是**工程上的稳定手段**，不是对「结果准确性」的修正。

```
Var(Q·K) ≈ d_k      →  除以 √d_k 后 Var = 1
饱和区：softmax 在 |x| 很大时梯度 ≈ 0，早期 token 学不动
```

```python
# 不缩放时，高维点积的方差随 d_k 爆炸，softmax 几乎 one-hot，梯度消失
for d in (8, 64, 512):
    s = np.random.randn(100, d) @ np.random.randn(100, d).T
    print(f"d_k={d:4d}  分数方差≈{s.var():.1f}  softmax熵≈{-(np.exp(s[0]-s[0].max())).sum() and 0:.2f}")
# d_k=8 时方差≈8；d_k=512 时方差≈512 → 进入饱和区
```

经验判断：业界主流实现默认缩放 √d_k；若你做维度很大的自定义注意力且观察到早期不收敛，
第一反应应检查「是不是忘了除以 √d_k」，而不是调学习率。

## 3. 多头在学什么：把表示空间切成多个子空间并行看

中立陈述：`h` 个头把 Q/K/V 投影到 `h` 个低维子空间（`d_k = d_model/h`），各自独立做注意力，
再拼接、过输出投影 `W_O`。多头不是「看更多 Token」，而是「在同一组 Token 上同时看不同的关系」：
一个头可能管句法依赖，另一个头管共指，再一个头管局部相邻。

```
head_i = Attention(Q·W_Qi, K·W_Ki, V·W_Vi),   i = 1..h
MultiHead = Concat(head_1..head_h) · W_O
```

退化检查（示例 ex02 的判据）：当 `h=1` 时，多头退化为单头，且总参数量与「单头直接用
`d_model` 维 QKV」完全一致——因为 `h·(d_model·d_k + d_k·d_model)` 在 `d_k=d_model/h` 时
恰好等于 `3·d_model² + d_model²`。多头的价值在 `h>1` 的并行多样性，不在参数量。

## 4. 因果 mask：推理时不能偷看未来

中立陈述：自回归生成中，第 `i` 个 Token 只能 attend 到 `≤i` 的位置。实现上在 softmax **之前**
把未来位置的分数置为 `-∞`（或加一个很大的负偏置），使 softmax 后对应权重为 0。

```
因果 mask（n=4）           softmax 之前加的偏置
[ 0 -∞ -∞ -∞ ]            [   0  -1e9 -1e9 -1e9 ]
[ 0  0 -∞ -∞ ]            [   0    0 -1e9 -1e9 ]
[ 0  0  0 -∞ ]            [   0    0    0 -1e9 ]
[ 0  0  0  0  ]            [   0    0    0    0 ]
```

**顺序的坑**：mask 必须在 softmax 之前加。先 softmax 再「把未来权重清零」是错的——
归一化已经被污染，前缀的输出会随未来 Token 变化（示例 ex03 验证：遮掉未来 token 后，
前缀输出应当完全不变；若变化就说明 mask 加晚了）。

---

## 三视角解析

### 🧑‍💻 程序员视角

- 用 numpy 手写时，**数值稳定先减行最大值**：`scores -= scores.max(-1, keepdims)`，
  否则 `exp(大数)` 直接溢出成 `inf`，整行变成 `nan`。这行不是优化，是必写。
- 因果 mask 用 `np.triu(ones, k=1)` 生成上三角布尔，乘以 `-1e9` 加到 scores；不要手动循环填。
- KV Cache 是因果注意力的推理优化：第 `i` 步只需计算新的 Q 与「已缓存的 K/V」做点积，
  而不是每步重算整段。没有因果 mask 就没有安全的 KV Cache（会泄露未来）。
- 多头投影矩阵 `W_Q/W_K/W_W_V/W_O` 建议一次性拼成 `(d_model, d_model)` 再 `reshape` 成头，
  比 h 次小矩阵乘快得多——这是 FlashAttention 之前最朴素的加速。

### 🎓 博士生视角

- 注意力的「低秩瓶颈」假说：单头在 `d_model` 维里被迫用同一个子空间同时表达 Q/K/V 关系；
  多头让每个头只在 `d_model/h` 的子空间里学一种关系，缓解表达冲突。这与「多核卷积」的直觉类似。
- 缩放因子与初始化强相关：若 Q/K 用 `std=1/√d_model` 初始化，点积方差已是 `d_model·(1/d_model)=1`，
  此时再除 √d_k 的必要性取决于 `d_k` 与 `d_model` 的关系；但标准约定统一除 √d_k 以覆盖最坏情况。
- softmax 的熵视角：`softmax(QKᵀ/√d_k)` 在分数方差大时趋近 one-hot（熵低、专注），
  方差小时趋近均匀（熵高、平均）。温度 `T` 等价于把 √d_k 换成 `T·√d_k`——这正是采样章节的伏笔。

### 📚 考研者视角

- 标准定义要能默写：`Attention(Q,K,V)=softmax(QKᵀ/√d_k)V`，并说明 Q/K/V 都来自同一输入的
  不同线性投影（自注意力时同源，交叉注意力时 K/V 来自编码器）。
- 常考计算：给定 `n=3, d_k=4`，写出分数矩阵形状 `(3,3)`、权重行和 `=1`、输出形状 `(3,d_v)`。
- 易混概念：**自注意力 vs 交叉注意力 vs 掩码注意力**。自注意力 K/V 来自自己；
  交叉注意力 K/V 来自另一序列（如解码器看编码器）；掩码注意力只是加了因果/填充 mask。
- 另一个易错点：**缩放除的是 √d_k，不是 √d_model**。当 `h` 个头时 `d_k=d_model/h`，
  缩放因子随头数变化，不要写错。
