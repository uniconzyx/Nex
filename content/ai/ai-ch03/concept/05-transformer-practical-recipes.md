# Transformer 实战手记：凯喵的十二次「训不动、训崩了、训出来是废的」

> 这一篇来自凯喵第一次从头训一个小型语言模型的经历。模型结构不难，参考实现两小时就能写完，但训起来之后问题成串：loss 不降、梯度爆炸、生成重复、显存 OOM、以及训练完全正常但推理结果一塌糊涂。十二个现场记录下来的结论是：**Transformer 的坑几乎全在「数值」和「位置」这两个维度上**。这篇按「注意力 → 位置编码 → 训练 → 推理」的顺序展开。

## 开场：为什么自注意力是「加权平均」的高级版本

注意力机制的形式是 `softmax(QK^T/√d_k)V`。凯喵第一次看这个公式时的困惑是：这不就是「算相似度加权求和」吗，为什么能替代 RNN？

理解的关键在于**Q、K、V 是同一输入的三个投影**，所以「每个位置和所有位置算相似度」这件事本身就是建模「任意两个位置的关系」，不受距离限制。RNN 要传播 n 步才能关联到远距离位置，自注意力一步就到。这就是它并行性好、长依赖强的原因。

代价是 O(n²) 的复杂度——每个位置都要和所有位置算一次。这个代价决定了后面所有的优化方向（稀疏注意力、线性注意力、FlashAttention）。

### 现场一：Q/K/V 的来历不是「三个不同的东西」

Q、K、V 都是输入 X 乘上三个不同的权重矩阵得到的：`Q = XW_Q`、`K = XW_K`、`V = XW_V`。它们地位平等，只是扮演的角色不同：Q 是「我在找什么」，K 是「我能提供什么」，V 是「我实际给什么」。

```python
import torch, torch.nn as nn, math

class SelfAttention(nn.Module):
    def __init__(self, d_model, d_k):
        super().__init__()
        self.wq = nn.Linear(d_model, d_k, bias=False)
        self.wk = nn.Linear(d_model, d_k, bias=False)
        self.wv = nn.Linear(d_model, d_k, bias=False)

    def forward(self, x, mask=None):
        q, k, v = self.wq(x), self.wk(x), self.wv(x)
        scores = q @ k.transpose(-1, -2) / math.sqrt(q.size(-1))
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))
        return scores.softmax(dim=-1) @ v
```

凯喵的体会：**K 和 V 分开是有道理的**——「匹配的依据」和「传递的内容」可以不同。如果合成一个，表达能力会下降。这也是后来 GQA/MQA 只在 K/V 的头数上做压缩、而不合并 K 和 V 的原因。

### 现场二：√d_k 缩放不是可选项

去掉 `/√d_k` 会发生什么？点积的方差随维度线性增长。d_k = 64 时，点积的标准差约为 8，softmax 的输入跨度很大，输出接近 one-hot，梯度接近零——模型学不动。

```python
# 直观验证：维度越高，点积方差越大
d = 64
q = torch.randn(1000, d)
k = torch.randn(1000, d)
dots = (q * k).sum(-1)
print(dots.std())            # 约等于 sqrt(d) = 8
print((dots / math.sqrt(d)).std())   # 约等于 1
```

除以 `√d_k` 让点积的方差回到 1 附近，softmax 的输入落在合理区间，梯度不会消失。凯喵见过有人觉得「除以常数没必要」而去掉它，结果 loss 卡在 2.3 不动，排查了两天才找到。

这条的普适意义：**任何进入 softmax 的量，都要检查它的量级**。量级太大就饱和，太小就均匀，两者都不好。

### 现场三：softmax 的温度是「除以」不是「乘以」

带温度的 softmax 是 `softmax(z/T)`。T > 1 时分布更平滑（更随机），T < 1 时更尖锐（更确定）。

```python
def softmax_with_temp(logits, T=1.0):
    z = logits / T
    z = z - z.max(dim=-1, keepdim=True).values   # 防溢出
    e = z.exp()
    return e / e.sum(-1, keepdim=True)
```

写成 `softmax(T * z)` 就把方向搞反了：T 大反而更尖锐。凯喵在采样调参时踩过这个坑，把温度从 0.7 调到 1.2 期待更发散，结果输出更死板。

顺带一个必须做的操作：**减去最大值**。`exp` 的输入稍大就会溢出成 `inf`，`inf/inf` 得到 `nan`，整个 batch 报废。这一步不是优化，是正确性要求。

### 现场四：因果掩码写成上三角，位置别搞反

自回归模型不能看到未来，所以要把「当前位置之后」的注意力分数设成 `-inf`。掩码是一个上三角为 1 的矩阵（`torch.triu(ones, diagonal=1)`），加在分数上。

```python
def causal_mask(seq_len, device):
    # 上三角（不含对角线）为 -inf，表示"不能看"
    m = torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1).bool()
    return torch.zeros_like(m, dtype=torch.float).masked_fill(m, float("-inf"))
```

两个常见错误：`diagonal=0` 会把对角线也遮掉（当前位置看不到自己，直接崩）；掩码方向和 `scores` 的形状不匹配（转置了）。凯喵的检查方法是：把掩码打印出来看一眼，形状对了再往下写。

还有一个隐蔽的坑：用 `-1e9` 而不是 `-inf`。多数情况没问题，但在 fp16 下 `-1e9` 会溢出成 `-inf`，而 `-inf` 在某些实现里会产生 `nan` 梯度。用 `torch.finfo(dtype).min` 最安全。

### 现场五：多头注意力的「拆」与「拼」要对齐

多头注意力的做法是把 `d_model` 拆成 `h` 个头，每个头 `d_k = d_model/h`，各自算注意力，最后拼回去。

```python
class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        assert d_model % n_heads == 0
        self.h, self.d_k = n_heads, d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.out = nn.Linear(d_model, d_model)

    def forward(self, x):
        B, T, C = x.shape
        qkv = self.qkv(x).reshape(B, T, 3, self.h, self.d_k).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]      # [B, h, T, d_k]
        scores = q @ k.transpose(-1, -2) / math.sqrt(self.d_k)
        ctx = scores.softmax(-1) @ v           # [B, h, T, d_k]
        ctx = ctx.transpose(1, 2).reshape(B, T, C)
        return self.out(ctx)
```

最容易错的是 `reshape` 和 `permute` 的顺序。`reshape(B, T, h, d_k)` 和 `reshape(B, T, d_k, h)` 得到的数据布局完全不同——前者把相邻的 `d_k` 个元素分给一个头，后者是交错的。搞错了模型也能训，但每个头看到的特征被搅乱，效果显著变差，而且**不报错**。

凯喵的排查方法：用一个已知的输入（比如 `arange` 填充），单步跑一遍，检查拆分再拼回是否还原。

### 现场六：位置编码必须加在 embedding 上

位置编码的作用是给模型「顺序信息」，因为自注意力本身是置换不变的。所以它要加在**输入 embedding 上**，在进第一层注意力之前。

```python
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe)

    def forward(self, x):
        return x + self.pe[: x.size(1)].unsqueeze(0)
```

凯喵见过把位置编码加到 Q/K/V 之后的写法，结果模型完全学不到顺序——因为 Q 和 K 各自被加了相同的偏移，点积里位置信息相互抵消了。

用 `register_buffer` 而不是普通属性，是为了让它跟着模型走 `.to(device)` 和 `state_dict`，但不算可训练参数。这个细节很多人漏掉，导致 GPU 上跑时报设备不匹配。

### 现场七：RoPE 是「旋转」而不是「相加」

Rotary Position Embedding 不加法，而是把 Q 和 K 的相邻两维看成复数，按位置角度做旋转。两个位置的点积结果只依赖它们的相对距离，这就是它外推性好的原因。

```python
def apply_rope(x, sin, cos):
    # x: [B, h, T, d_k]，把最后一维按相邻两两配对看作复数
    x1, x2 = x[..., 0::2], x[..., 1::2]
    rotated = torch.stack((-x2, x1), dim=-1).flatten(-2)
    return x * cos + rotated * sin
```

关键是**配对方式**：必须是相邻两维（0-1、2-3...）或前后半（0 与 d/2），具体取决于实现约定。用的是哪种约定，sin/cos 的构造就要对应。搞混了两者，模型能训但效果差——因为旋转的角度和维度对不上。

凯喵的检查方法：实现完之后验证「两个位置的点积只依赖相对距离」，即 `dot(rope(q, m), rope(k, n))` 应该只与 `m-n` 有关。这个测试能一次性抓住绝大多数实现错误。

### 现场八：长度外推不处理，直接拉长会崩

模型在 2048 长度上训练，直接推理 4096，效果会急剧下降。原因是高频率分量在未见过的位置上剧烈摆动，注意力分数变得混乱。

解决办法有几种：**NTK-aware 缩放**（调大 RoPE 的 base，让低频分量变化更慢）、**线性位置插值**（把新长度按比例压缩回训练长度）、**YaRN**（分段处理不同频率）。

```python
# NTK-aware：base 从 10000 放大，scale 是长度扩展比
def ntk_base(base, dim, scale):
    return base * (scale ** (dim / (dim - 2)))
```

凯喵的经验：外推比想象中脆弱。**能做长度微调就做**（用少量长文本继续训练几千步），比任何纯推理期的技巧都可靠。

### 现场九：训练不收敛，先看学习率和 warmup

Transformer 对学习率很敏感。太大直接发散（loss 变 nan），太小收敛极慢。标准做法是 warmup + 余弦衰减：前几千步线性升温，之后余弦下降。

```python
def lr_lambda(step, warmup=2000, total=100000):
    if step < warmup:
        return step / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.5 * (1 + math.cos(math.pi * progress))
```

warmup 的作用是让 Adam 的二阶矩估计先稳定下来。没有 warmup 时，前几百步的梯度方差很大，容易一步走到很差的区域。

凯喵的排查顺序：**loss 变 nan → 降学习率 + 加梯度裁剪**；**loss 不降 → 检查数据（标签对齐、mask 正确）+ 检查模型（梯度是否传通）**；**loss 降但生成乱 → 检查推理代码（和训练是否一致）**。

### 现场十：梯度裁剪是必需品不是可选项

Transformer 偶尔会出现梯度尖峰（某些 batch 的 loss 突然暴涨），一次尖峰就足以把模型带到不可恢复的状态。梯度裁剪把梯度的范数限制在上界内，避免单步更新过大。

```python
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
```

`max_norm` 通常取 1.0。凯喵见过取值太大（10.0）等于没裁，也见过太小（0.1）导致学不动。1.0 是经过大量实践验证的默认值。

配合混合精度训练时，还要注意 loss scaling——fp16 的梯度容易下溢成 0。现代的 `torch.cuda.amp` 有自动 scaling，但要确认 `GradScaler` 用对了。

### 现场十一：显存 OOM 的账要算清楚

训练的显存由四部分组成：**模型参数、梯度、优化器状态、激活值**。前三项是固定的（约为参数量的 16 倍字节，Adam + fp32），第四项随 batch 和序列长度线性增长。

```python
# 粗算：7B 模型全参数训练
params = 7e9
bytes_per_param = 2 + 2 + 4 + 4    # fp16权重 + fp16梯度 + fp32动量 + fp32方差
print(params * bytes_per_param / 1e9, "GB")   # 约 84 GB，还没算激活
```

这就是为什么全参数训练 7B 需要多卡。省显存的手段：混合精度（权重 fp16）、梯度累积（小 batch 模拟大 batch）、梯度检查点（用计算换显存）、LoRA（只训低秩增量）。

凯喵的建议：**先算账再动手**，别训到一半 OOM 才发现方案不可行。

### 现场十二：训练正常但推理崩，八成是实现不一致

最令人抓狂的一类问题。训练 loss 一路下降，eval loss 也正常，但推理生成的文本完全不通。

凯喵遇到的根因是：训练时用了因果掩码，推理时逐 token 生成却没有维护 KV cache 的偏移，导致位置编码全错。表现是「前几个 token 正常，后面开始乱」。

```python
# 推理时每步只喂新 token，位置必须接着算
for step in range(max_new_tokens):
    pos = prompt_len + step                  # 关键：位置要连续
    logits = model(next_token, pos)
    next_token = sample(logits[:, -1])
```

排查方法：**用训练时的完整序列做一次前向，和逐 token 生成的结果对比**。如果两者的 logits 不一致，说明推理实现有问题。这个对照测试能定位九成的「训练好但推理崩」。

## 三视角解析
### 🧑‍💻 程序员视角
Q/K/V 不是「三个不同的东西」，而是同一个输入经三个线性变换得到的三组投影——理解这点才能解释「为什么多头有效」。`√d_k` 缩放不是可选项：点积的方差随维度线性增长，不缩放会让 softmax 进入饱和区、梯度趋近于零。softmax 的温度是「除以」不是「乘以」，写反了分布会变得更尖锐。因果掩码必须是「上三角为 -inf」而不是「下三角」，位置搞反就等于让模型看见未来。

### 🎓 博士生视角
Transformer 的核心是「用注意力替代循环，把序列建模变成可并行的加权求和」，代价是 O(n²) 的复杂度与「位置信息需要显式注入」（位置编码/RoPE）。多头注意力的作用可解释为「在不同子空间里学习不同的关系模式」，其表达能力严格强于单头（在相同总维度下）。残差 + LayerNorm 的组合解决了深层网络的训练稳定性，Pre-LN 比 Post-LN 更容易训练，这也是现代大模型普遍采用 Pre-LN 的原因。

### 📚 考研者视角
AI 岗面试高频：
1. **自注意力公式**：`Attention(Q,K,V) = softmax(QKᵀ/√d_k)V`，每一部的维度变化要能写清。
2. **为什么缩放**：点积方差为 `d_k`，除以 `√d_k` 使其方差归一。
3. **多头的作用**：多子空间、并行、增强表达；参数量与单头相同（每头维度 d/h）。
4. **位置编码**：正弦编码的性质、RoPE 的相对位置特性、外推问题。

## 收尾：注意力是骨架，数值是血肉

凯喵最后总结：Transformer 的结构其实很简单——注意力 + FFN + 残差 + LayerNorm，堆 N 层。真正难的是数值细节：缩放系数、掩码方向、温度方向、位置编码的加法位置、梯度裁剪的阈值、混合精度的 scaling。

这些细节的共同点是：**错了不报错，只是效果变差**。所以你无法靠「跑通」来判断正确性，只能靠「对照测试」——用已知正确的小例子验证每一步的输出。

凯喵的做法是写一套单元测试：注意力的形状、掩码的因果性、位置编码的相对性、softmax 的行和为 1。这些测试写一次，后面所有改动都能复用。看上去是额外工作，实际上省下了大量「效果不好但不知道为什么」的排查时间。

最后补一句关于「读源码」的建议。想真正掌握 Transformer，读一遍 PyTorch 官方或 nanoGPT 的实现比读十篇博客有用。读的时候不要试图理解每一行，而是抓住四个问题：张量的形状在每个阶段怎么变、位置信息在哪里注入、掩码在哪里生效、残差和归一化的顺序是什么。把四个问题的答案串起来，整个前向过程就清楚了。凯喵的看法是，结构图人人会画，但真正拉开差距的是能不能在报错时迅速判断「是形状问题、是数值问题、还是位置问题」——而这种判断力只能从动手改代码、故意制造错误、再观察现象中长出来。

```text
05-transformer-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：Q/K/V 的来历不是「三个不同的东西」  (python)
    |
    v
  [02] 现场二：√d_k 缩放不是可选项  (python)
    |
    v
  [03] 现场三：softmax 的温度是「除以」不是「乘以」  (python)
    |
    v
  [04] 现场四：因果掩码写成上三角，位置别搞反  (python)
    |
    v
  [05] 现场五：多头注意力的「拆」与「拼」要对齐  (python)
    |
    v
  [06] 现场六：位置编码必须加在 embedding 上  (python)
    |
    v
  [07] 现场七：RoPE 是「旋转」而不是「相加」  (python)
    |
    v
  [08] 现场八：长度外推不处理，直接拉长会崩  (python)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
