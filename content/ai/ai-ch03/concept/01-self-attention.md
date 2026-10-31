# ai-ch03 · 核心概念（一）：自注意力与多头注意力

> 视角覆盖：程序员（工程决策）/ 博士生（第一性原理）/ 考研者（笔面口径）。三者互补、不重复。

## 1. 自注意力：从序列到「集合加权」的映射

自注意力对输入矩阵 X（形状 n×d）先做线性投影得到 Q/K/V，再计算
$$Attention(Q,K,V)=softmax\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$
结果是每个位置对全体位置的加权求和。它最大的结构特性是**置换等变**：打乱输入顺序，输出同步重排但数值不变。

### 🧑‍💻 程序员视角
- 工程上 Decoder-only 自回归分两阶段：**prefill** 一次性算完所有已给 token 的 Q/K/V 并填满 KV Cache；**decode** 每步只新增 1 个 query，但要读全部历史 KV。decode 的瓶颈是**显存带宽**（小矩阵乘被 KV 读取拖住），不是算力。
- 长上下文要先估 KV Cache 显存再上量；上下文越长显存线性涨，超窗需截断 / 滑动窗口 / 层次压缩。

### 🎓 博士生视角
- 形式化置换等变：对任意置换矩阵 P，有 $Attention(XP^\top)=P\,Attention(X)$（Q/K/V 同步重排后结果同构重排）。这意味着**纯自注意力对词序盲目**，位置信息必须被显式注入——这是位置编码存在的根本动机。
- $\sqrt{d_k}$ 不是经验常数：Q、K 各分量独立时，$QK^\top$ 的方差随 $d_k$ 线性增长，除以 $\sqrt{d_k}$ 使 softmax 输入方差≈1、梯度尺度稳定；否则大 $d_k$ 下 softmax 饱和、梯度趋零。

### 📚 考研者视角
- 408/自命题常考 **Transformer 结构组成**：输入嵌入 + 位置编码 →（多头自注意力 + Add&Norm）×N →（前馈 + Add&Norm）×N → 输出层。
- **QKV 维度口径**：Q、K ∈ $\mathbb{R}^{n×d_k}$，V ∈ $\mathbb{R}^{n×d_v}$；标准实现 $d_k=d_v=d_{model}/h$。笔试常问「Q 和 K 维度为什么要一样」——点积注意力要求 Q、K 同维才能相乘。

## 2. 多头注意力：在子空间并行捕捉不同关系

把 d_model 切成 h 个 head，每个 head 在 d_k = d_model/h 的子空间独立算注意力，输出拼接后再投影回 d_model。

### 🧑‍💻 程序员视角
- **KV Cache 显存估算器**（工程必备）：单样本单 token 占 `layers × heads × head_dim × 2 × dtype_bytes` 字节（×2 指 K 与 V）。例：32 层 / 32 头 / head_dim=128 / fp16 / 4096 长 ≈ 2 GB；batch 放大、fp32 翻倍。MQA/GQA 通过减少 KV 头数直接砍这块。
- 头数越多并行关系越丰富，但**参数量与头数无关**（见考研者视角）；调头数主要换表达力而非容量。

### 🎓 博士生视角
- 缩放即温度：$\frac{QK^\top}{\sqrt{d_k}}$ 是 softmax 温度形式化的特例——缩放因子 $\sqrt{d_k}$ 等价于把 logits 除以 $\sqrt{d_k}$。这把「程序员调 temperature」与「理论家调 $\sqrt{d_k}$」统一到同一机制：softmax 对输入尺度极敏感。
- 多头把单一相似度空间拆成 h 个，使模型同时关注语法 / 语义 / 距离等不同子关系，是表示容量的关键来源。

### 📚 考研者视角
- **多头注意力参数量 = $4\,d_{model}^2$**（Q/K/V/O 四个投影各 $d_{model}^2$），与头数 $h$ 无关；h 只决定每个头的子空间维度 $d_k=d_{model}/h$。
- 易错：以为「头数翻倍参数量翻倍」——错，翻倍的是并行度不是参数；翻倍 d_model 才翻倍参数。

---
### 三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 自注意力 | prefill/decode 差异、KV 显存 | 置换等变→位置编码必然、√d_k 缩放 | 结构组成、QKV 维度 |
| 多头 | KV Cache 估算、MQA/GQA | 缩放即温度、子空间并行 | 参数量 4d² 与头数无关 |

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 单头自注意力完整数值演算（含因果掩码）

```python
import numpy as np
rng = np.random.default_rng(42)
d = 4
T = 5
x = rng.standard_normal((T, d)).astype(np.float64)
Wq = rng.standard_normal((d, d))
Wk = rng.standard_normal((d, d))
Wv = rng.standard_normal((d, d))
Q = x @ Wq
K = x @ Wk
V = x @ Wv
scores = Q @ K.T / np.sqrt(d)
mask = np.triu(np.ones((T, T), dtype=bool), k=1)
masked = np.where(mask, -np.inf, scores)
def softmax(z):
    m = np.max(z, axis=-1, keepdims=True)
    e = np.exp(z - m)
    return e / e.sum(axis=-1, keepdims=True)
A = softmax(masked)
out = A @ V
print("scores shape:", scores.shape)
print("causal mask 上三角(未来)数:", int(mask.sum()))
print("A 每行和(应=1):", np.round(A.sum(axis=1), 6))
print("A[0] 只看位置0:", np.round(A[0], 6))
print("A[2] 后两位(应=0):", np.round(A[2, 3:], 6))
print("out shape:", out.shape)
print("out[0]:", np.round(out[0], 4))
```

实际输出：

```text
scores shape: (5, 5)
causal mask 上三角(未来)数: 10
A 每行和(应=1): [1. 1. 1. 1. 1.]
A[0] 只看位置0: [1. 0. 0. 0. 0.]
A[2] 后两位(应=0): [0. 0.]
out shape: (5, 4)
out[0]: [-0.7518 -1.1572  0.5513 -1.1966]
```

> 出处：`examples/ex01-single-head-attention.json`。改一处再看输出变没变，比读三遍解释有用。

### 多头注意力拆头/合并维度变换逐项验证

```python
import numpy as np
rng = np.random.default_rng(42)
T, d_model, n_heads = 6, 8, 2
x = rng.standard_normal((T, d_model))
Wq = rng.standard_normal((d_model, d_model))
Q = x @ Wq
head_dim = d_model // n_heads
Qh = Q.reshape(T, n_heads, head_dim)
Qht = Qh.transpose(1, 0, 2)
print("head_dim:", head_dim)
print("Q:", Q.shape, "-> Qh:", Qh.shape, "-> Qht:", Qht.shape)
ok = True
for h in range(n_heads):
    for t in range(T):
        if not np.allclose(Qht[h, t], Q[t, h * head_dim:(h + 1) * head_dim]):
            ok = False
print("拆头等价性(逐元素):", ok)
Oh = rng.standard_normal((n_heads, T, head_dim))
Oht = Oh.transpose(1, 0, 2).reshape(T, d_model)
ok2 = True
for h in range(n_heads):
    if not np.allclose(Oht[:, h * head_dim:(h + 1) * head_dim], Oh[h]):
        ok2 = False
print("合并等价性(逐元素):", ok2)
print("合并后 shape:", Oht.shape)
```

实际输出：

```text
head_dim: 4
Q: (6, 8) -> Qh: (6, 2, 4) -> Qht: (2, 6, 4)
拆头等价性(逐元素): True
合并等价性(逐元素): True
合并后 shape: (6, 8)
```

> 出处：`examples/ex02-multi-head-reshape.json`。改一处再看输出变没变，比读三遍解释有用。

