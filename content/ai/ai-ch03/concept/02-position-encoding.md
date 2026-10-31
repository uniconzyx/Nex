# ai-ch03 · 核心概念（二）：位置编码与 RoPE

> 视角覆盖：程序员（外推工程）/ 博士生（相对位置性质）/ 考研者（演进口径）。三者互补、不重复。

## 1. 为什么需要位置编码 & 正弦式

自注意力本身置换等变（见概念一），对词序盲目。要保留顺序信息，必须在输入里注入位置信号。
正弦式：$PE_{(pos,2i)}=\sin(pos/10000^{2i/d})$，$PE_{(pos,2i+1)}=\cos(pos/10000^{2i/d})$。

### 🧑‍💻 程序员视角
- 正弦式外推性差：推理位置超过训练最大长度时，对应频率的向量从未见过，分布漂移。工程上改用 **RoPE / ALiBi**，并对长上下文做 NTK-aware base 调整或继续微调。
- 可学习位置编码把位置向量当参数训，但同样难外推；推理长度变化时要插值（position interpolation）。

### 🎓 博士生视角
- 从置换等变出发：纯注意力 $Attn(XP^\top)=P\,Attn(X)$，顺序信息在注意力里被「洗掉」，所以位置必须被编码进 token 表示本身，否则模型把「猫 追 狗」与「狗 追 猫」视为同一集合。
- 正弦式提供平滑、可外推的频率信号（低频管长距、高频管邻近），但它编码的是**绝对位置**，长上下文泛化仍弱于相对位置方案。

### 📚 考研者视角
- 位置编码演进标准口径（笔试常考）：**正弦（Vaswani）→ 可学习（BERT）→ 相对位置（Transformer-XL / T5）→ RoPE（GPT-NeoX / LLaMA）/ ALiBi（MPT）**。
- 常考「为什么需要位置编码」「绝对 vs 相对位置的区别」。

## 可运行代码：正弦编码与 RoPE 的对照

两种方案都能给出「位置信息」，差别在于正弦编码是**加到**向量上，RoPE 是**旋转**向量，
后者天然保范：

```python
import torch

def sinusoidal(max_len: int, d_model: int) -> torch.Tensor:
    pos = torch.arange(max_len).unsqueeze(1).float()            # [L, 1]
    i = torch.arange(0, d_model, 2).float()                     # [d/2]
    div = torch.exp(-torch.log(torch.tensor(10000.0)) * i / d_model)
    pe = torch.zeros(max_len, d_model)
    pe[:, 0::2] = torch.sin(pos * div)
    pe[:, 1::2] = torch.cos(pos * div)
    return pe

def rope(x: torch.Tensor, base: float = 10000.0) -> torch.Tensor:
    L, d = x.shape
    inv = base ** (-torch.arange(0, d, 2).float() / d)          # [d/2]
    ang = torch.arange(L).float().unsqueeze(1) * inv            # [L, d/2]
    cos, sin = ang.cos(), ang.sin()
    x1, x2 = x[:, 0::2], x[:, 1::2]
    out = torch.empty_like(x)
    out[:, 0::2] = x1 * cos - x2 * sin
    out[:, 1::2] = x1 * sin + x2 * cos
    return out

pe = sinusoidal(8, 16)
print(pe[0, :6].tolist())                     # 位置 0 是 [0, 1, 0, 1, 0, 1]
print("相邻位置内积:", round(float(pe[0] @ pe[1]), 4))   # 距离越远，内积越小

x = torch.randn(8, 16)
print("RoPE 后每行范数:", torch.norm(rope(x), dim=1)[:3].tolist())
print("原向量每行范数  :", torch.norm(x, dim=1)[:3].tolist())   # 两行数值相同
```

最后两行数值相同，正是 RoPE 的关键性质：旋转矩阵是正交矩阵，`||R·x|| = ||x||`，
注意力打分只受**相对角度**影响。这也是它比「加性位置编码」更适合外推的原因——
长度变了，范数与尺度不变，只是角度继续增大。

## 2. RoPE：把位置「旋转」进隐空间

RoPE 不为每个位置存一个向量，而是用旋转矩阵把位置信息编码进 Q、K 的方向：对每个 2 维子空间按角度 pos·θ_i 旋转。

### 🧑‍💻 程序员视角
- RoPE 外推：长上下文时提高 base 频率或做 NTK-aware 线性缩放（Yang et al. 2023），让低频在更长的 pos 上仍平滑；这是「LLaMA-2 7B 扩展到 32K/100K」的常用手段。
- 相比可学习 PE，RoPE 在训练长度内学的是旋转关系，外推只需调频率，无需重训位置向量。

### 🎓 博士生视角
- **相对位置性质（核心）**：设 $R_m$ 为位置 m 的旋转矩阵，则 $RoPE(q,m)^\top RoPE(k,n)=q^\top R_{n-m}\,k$，即旋转后内积只依赖**相对距离 $m-n$**，与绝对位置无关。证明：旋转矩阵正交且 $R_m^\top R_n = R_{n-m}$，故 $(R_m q)^\top(R_n k)=q^\top R_m^\top R_n k=q^\top R_{n-m}k$。
- 这意味着注意力分数天然是「相对位置」的函数，与绝对位置解耦——这正是相对位置注意力想要的性质，且无需显式相对位置偏置项。

### 📚 考研者视角
- RoPE 是什么（旋转位置编码）：把位置编码成旋转，Q、K 在各自位置旋转后再做点积；为什么相对位置好：外推性、长度泛化优于绝对位置。
- ALiBi 用「距离越远的 query-key 加越大负偏置」替代旋转，训练即带外推偏置，推理长度外推性更好，是另一主流路线。

---
### 三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 为何需要 PE | 正弦外推差、NTK-aware | 置换等变→必须注入位置 | 演进口径、绝对vs相对 |
| RoPE | base 调整、长上下文外推 | 内积只依赖 m−n（证明） | RoPE 定义、相对位置优势 |
