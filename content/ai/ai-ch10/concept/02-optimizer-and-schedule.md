# ai-ch10 · 核心概念（二）：优化器、学习率与训练稳定性

> 视角覆盖：程序员（工程决策）/ 博士生（第一性原理）/ 考研者（笔面口径）。三者互补、不重复。

```text
优化器演进，每一步改的是什么：
    SGD        θ ← θ - lr·g                        只用一阶梯度
    Momentum   v ← βv + g ;  θ ← θ - lr·v          加惯性，平滑噪声方向
    Adam       m,v 是一阶/二阶矩的指数均值
               θ ← θ - lr·m̂/(√v̂+ε)                每参数自适应步长
    AdamW      把 weight decay 从梯度里挪出来
               θ ← θ - lr·(m̂/(√v̂+ε)) - lr·λ·θ      衰减不再被自适应缩放

学习率调度：
    lr ┤      ╭───╮
       │     ╱     ╲___
       │  __╱          ╲___             warmup：避开初期大梯度把参数带偏
       └─┴──┴──────────────┴──▶ step    decay：后期小步收敛
        warmup   decay
    Adam 的二阶矩估计在初期不准 -> warmup 不是玄学，是必需
```

## 1. 从 SGD 到 AdamW：优化器改的到底是什么

优化器的演化可以按「用了哪些信息」分三代：

**① SGD**：$\theta_{t+1}=\theta_t-\eta g_t$。只用当前梯度，方差大、对条件数敏感。

**② Momentum**：累积一个「速度」$v_t=\mu v_{t-1}+g_t$，$\theta\leftarrow\theta-\eta v_t$。它把「沿一致方向的梯度」放大、把「来回震荡的分量」抵消，等效于对梯度做低通滤波。在病态（条件数大）的损失面上，动量把有效步长按 $1/(1-\mu)$ 放大，这就是 $\mu=0.9$ 常见的原因。

**③ Adam**：同时估计一阶矩与二阶矩，做**逐参数自适应缩放**：

$$m_t=\beta_1m_{t-1}+(1-\beta_1)g_t,\qquad v_t=\beta_2v_{t-1}+(1-\beta_2)g_t^2$$
$$\hat m_t=\frac{m_t}{1-\beta_1^t},\qquad \hat v_t=\frac{v_t}{1-\beta_2^t},\qquad \theta_{t+1}=\theta_t-\eta\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}$$

偏差校正（$1-\beta^t$ 那一项）不是可选项：$m_0=v_0=0$ 会让前几步的估计**系统性偏小**，不校正相当于「前几步学习率被暗中缩小」。这也是「Adam 前期慢」的常见原因之一。

**AdamW 与 Adam（+L2）的差别是本章最容易被问倒的一个点。** 传统做法是把 L2 正则加进梯度（$g\leftarrow g+\lambda\theta$），但 Adam 会把这一项丢进 $v$ 里做归一化——**衰减强度被 $\sqrt{\hat v}$ 除掉了**，导致「梯度大的参数衰减少、梯度小的参数衰减多」，这不是我们想要的。

AdamW（Loshchilov & Hutter, 2019）把衰减**解耦**出来：

$$\theta_{t+1}=\theta_t-\eta\Big(\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}+\lambda\theta_t\Big)$$

衰减项直接作用在参数上、不参与自适应缩放。这个改动看起来只是「挪了个位置」，但在 Transformer 上能带来稳定的泛化提升，因此**今天所有 LLM 训练用的都是 AdamW 而非 Adam+L2**。

### 🧑‍💻 程序员视角

- 默认配方（可直接用）：`AdamW(lr=3e-4, betas=(0.9,0.95), eps=1e-8, weight_decay=0.1)`，**bias 与 LayerNorm 的 $\gamma$ 排除 weight decay**。LLM 的 `beta2=0.95`（而非 0.999）是为了对梯度尺度变化更快响应，长训练更稳。
- 学习率不是越小学越好：lr 太小会「看起来在学但永远到不了」，lr 太大会在前几百步就崩。判断手段是看 **loss 曲线的初始斜率**——健康训练在前 1% 步数内 loss 应有明显下降。
- **不要给 embedding 和输出层用同一个 weight decay**（embedding 常需要更小或 0），这是很多「小模型训不好」的隐藏原因。
- 优化器状态显存：Adam 每个参数要存 $m,v$ 两份 fp32，即 **8 字节/参数**（加上 fp32 master weight 再 4 字节 → 12 字节/参数）。7B 模型仅优化器状态就 84GB，这是「单卡训不动 7B」的直接原因（见第三节）。

### 🎓 博士生视角

- Adam 可以看成**对角预条件的最速下降**：$\theta\leftarrow\theta-\eta\,\mathrm{diag}(\sqrt{\hat v})^{-1}\hat m$，即用梯度二阶矩的平方根近似 Hessian 的对角，做逐坐标缩放。这解释了它在「不同参数梯度尺度差异大」（如 embedding vs LayerNorm）时的优势，也解释了它为什么**不能纠正参数间的相关性**（非对角信息全丢）。
- Adam 不收敛的反例是真实存在的（Reddi et al., 2018）：某些凸问题上 $\hat v$ 的指数平均会「忘记」大的历史梯度，导致有效步长失控。AMSGrad 用 $v_t^{\max}=\max(v_{t-1}^{\max},v_t)$ 修补。实践中这个反例很少触发，所以 AMSGrad 不是默认。
- AdamW 的「解耦」在数学上等价于**在参数空间做 proximal 更新**（近端梯度）：$\theta\leftarrow\mathrm{prox}_{\eta\lambda\|\cdot\|}(\theta-\eta\,\mathrm{AdamStep})$，对 L2 而言 prox 就是按 $(1-\eta\lambda)$ 缩放。这把「正则」和「自适应缩放」彻底分开，是它泛化更好的理论解释方向。
- 「Adam 泛化不如 SGD」这个说法要加限定：在小视觉任务上 SGD+Momentum 常更好（平坦极小值假说），但在 Transformer/大模型上 AdamW 全面胜出。原因与「自适应缩放是否放大了噪声方向」有关，目前仍是开放问题。

### 📚 考研者视角

- **必背**：Momentum 的更新式、Adam 的 $m/v$ 与偏差校正、AdamW 与 Adam+L2 的差别。
- **常考计算**：给 $g_1=0.1,g_2=-0.2$、$\beta_1=0.9,\beta_2=0.999$，算 $t=2$ 时的 $\hat m,\hat v$ 与更新量；考「$\beta_2$ 越大对梯度尺度变化越不敏感」。
- **易混**：weight decay（直接衰减参数）≠ L2 正则（加在梯度里）——在 SGD 下两者近似等价，在 Adam 下**不等价**，这是标准辨析题。
- **口径提醒**：Adam 的「自适应」指**逐参数**学习率，不是「自动调学习率」（后者是 scheduler 的职责）。

## 2. 学习率调度：warmup 不是玄学

三个必须理解的现象：

**① 为什么需要 warmup。** Adam 在最初几步的 $\hat v$ 只由极少样本估计，方差巨大；此时若用大学习率，更新方向会被噪声主导。warmup 让前 $N$ 步用小学习率「把 $v$ 的估计跑稳」，之后再升到目标值。**Post-LN Transformer 对 warmup 极度敏感**（没有 warmup 几乎必然发散），Pre-LN 则宽容得多。

**② 为什么用 cosine 衰减。** 训练后期需要小学习率来「精修」（降低梯度的随机游走幅度）。cosine 的好处是**前期降得慢、后期降得快但不为零**，比 step decay 平滑（避免学习率突变引起的 loss 跳变）。线性衰减与 cosine 在现代配方里差别不大，cosine 更常用。

**③ batch size 与学习率的关系。** 小 batch 下梯度噪声大，等效于「隐式正则 + 温启动」；大 batch 下噪声小，可以走更大步。经验规则：

$$\eta\propto B\quad(\text{线性缩放，}B\le B_{\text{crit}}),\qquad \eta\propto\sqrt{B}\quad(B>B_{\text{crit}})$$

$B_{\text{crit}}$ 是「再增大 batch 也无法再增大学习率」的临界点（取决于任务与模型）。**实践建议**：batch 翻倍时 lr 翻倍，但要重新观察前 100 步是否稳定；超过临界 batch 后收益急剧递减（这是「大 batch 训练不划算」的定量依据）。

### 🧑‍💻 程序员视角

- 现代默认配方：**warmup 占总步数 1%-5%（LLM 常 2000 步）+ cosine 衰减到峰值的 10%**。别用「常数 lr + 手动降」，除非有明确的 plateau 检测需求。
- 出现 loss 尖峰（spike）时，第一反应不是「重启」，而是：① 回滚到 spike 前的 checkpoint；② 跳过引发 spike 的数据（数据里常有异常样本）；③ 降低 lr 或增大 warmup。**从 spike 前 1000 步的 checkpoint 重启并跳过该 batch** 是业界常用恢复手法。
- 学习率与 weight decay 的联动：AdamW 的 $\lambda$ 与 $\eta$ 耦合（有效衰减 $\approx\eta\lambda$），改 lr 时要同步检查 wd 是否需要缩放——这是「换 lr 后模型变差」的隐藏原因。
- 监控指标不要只看 loss：加 **grad norm** 与 **update/param ratio**（$\|\Delta\theta\|/\|\theta\|$，健康值约 $10^{-3}$ 量级）。后者是判断「学习率是否合理」的最直接信号。

### 🎓 博士生视角

- warmup 的必要性可以用「Adam 的二阶矩估计偏差」严格说明：$v_t$ 的估计在早期依赖初始化为 0，导致 $\sqrt{\hat v}$ 系统性偏小、有效步长偏大；warmup 相当于让 $\eta$ 与 $\sqrt{\hat v}$ 的收敛同步。
- 线性缩放规则的严格版本是「**梯度噪声尺度**」理论（McCandlish et al., 2018）：SGD 的稳态噪声由 $\eta/B$ 决定，保持 $\eta/B$ 不变就能在改变 batch 时维持相同的训练动力学——因此 $\eta\propto B$。超过临界 batch 后，梯度噪声的主导项从「采样噪声」变为「数据固有的标注/分布噪声」，此时再增大 $\eta$ 只会失稳，于是退化为 $\sqrt{B}$ 甚至更慢。
- cosine 的学习率积分是 $\int\eta\,dt$ 而非 $\eta$ 本身决定「总步长预算」；在固定总步数下，cosine 与 linear 的积分相近，因此效果差异不大——这是「调度选择不敏感」的解释。
- loss spike 的机制之一是**注意力 logit 爆炸**：softmax 前的分数过大使梯度进入极端区间，更新一步就把参数推到坏区。工程上用 QK-norm / logit soft-cap / z-loss 抑制，这是「架构层面的稳定性设计」而非优化器技巧。

### 📚 考研者视角

- **必背**：warmup + cosine 的分段公式（写得出函数即可）；线性缩放规则；梯度裁剪的公式。
- **常考问法**：① 为什么需要 warmup（$v$ 估计不稳、大模型初期梯度大）；② 学习率过大/过小的现象（发散/收敛慢）；③ 为什么大 batch 需要更大学习率（梯度噪声小）。
- **易混**：warmup（升）与 decay（降）是两个阶段，别只说「学习率衰减」；「学习率调度」不改优化器本身，只改步长。

## 3. 梯度裁剪与 loss 尖峰：怎么把「崩」变成「抖一下」

梯度裁剪最常见的实现是**按全局范数**（global norm）缩放：

$$g\leftarrow g\cdot\min\Big(1,\frac{c}{\|g\|_2}\Big)$$

注意它**只压范数大的方向，不改变方向**（整体等比缩放），因此不破坏动量的方向信息。$c$ 的常用值是 1.0（LLM）到 5.0（视觉）。

裁剪能防「一步炸掉」，但**不能修复结构性不稳定**：如果梯度持续超阈值，说明学习率/初始化/数据有问题，裁剪只是把发散变成缓慢漂移。

loss 尖峰（loss spike）是训练大模型的常态，成因大致四类：

| 成因 | 表现 | 处理 |
|---|---|---|
| 异常数据 | 单 batch loss 突然 ×10，之后的 batch 正常 | 跳过该 batch / 清洗数据 / 提高数据质量过滤 |
| 优化器状态污染 | spike 后 loss 持续高位，$v$ 被大梯度污染 | 回滚 checkpoint、重置优化器状态 |
| 数值溢出 | fp16 下出现 inf/nan | 用 bf16、开 loss scale、查 LayerNorm eps |
| 架构/超参临界 | 周期性 spike，与数据无关 | 降 lr、加 warmup、加 QK-norm/z-loss |

**回滚策略**是工程上的关键：保存「最近 N 个 checkpoint + 数据加载器状态」，spike 后回滚到前一个稳定点，跳过若干 batch 继续。没有这套机制，一次 spike 可能浪费数天算力。

### 🧑‍💻 程序员视角

- 裁剪的位置：在 `backward()` 之后、`optimizer.step()` 之前，**所有参数的梯度一起裁**（不是逐层裁）。逐层裁会破坏层间梯度比例，效果通常更差。
- 判断「裁剪是否在长期生效」：统计被裁剪的步数比例。若 >10% 说明学习率偏大；若长期 0% 说明 $c$ 太大、裁剪没起作用（也不是好事，等于没保护）。
- 混合精度 + 裁剪要小心：`clip_grad_norm_` 在 fp16 梯度上会出现 overflow，应先用 `scaler.unscale_(optimizer)` 还原再裁。
- 记录「spike 前后」的完整现场：lr、grad norm、loss、该 batch 的数据 id、优化器状态范数。事后归因全靠这些。

### 🎓 博士生视角

- 全局范数裁剪等价于**信赖域约束**（trust region）：限制单步更新的最大长度，与「按比例缩放学习率」在单步层面等价，但保留了方向。这是它比「固定学习率上限」更好的原因。
- loss spike 与**损失面曲率突变**有关：某些 batch 的 Hessian 最大特征值骤增，导致稳定步长上限 $2/\lambda_{\max}$ 突然变小；裁剪是「事后」应对，真正的解法是让曲率有界（归一化、残差、QK-norm）。
- 「跳过 batch」在理论上等价于**重要性采样的一次纠正**：坏 batch 对梯度的贡献被置零，引入偏差但有方差收益；实践中偏差可忽略，因为坏 batch 占比极低。

### 📚 考研者视角

- **必背**：裁剪公式（等比缩放，不改方向）；裁剪阈值与学习率的关系（阈值小 ≈ 降低有效学习率）。
- **常考问法**：① 梯度裁剪解决什么问题（爆炸，不解决消失）；② 为什么按全局范数而不是逐元素（保持方向）；③ 裁剪与梯度消失的关系（对消失无效）。
- **易混**：梯度裁剪 ≠ 梯度正则（后者改损失）；裁剪 ≠ 归一化（后者改激活）。

## 4. 有效 batch：梯度累积、分布式与「等价性」的边界

当显存放不下大 batch 时，用**梯度累积**：

$$g_{\text{acc}}=\frac{1}{K}\sum_{k=1}^{K}g_k\quad(\text{对 }K\text{ 个 micro-batch 取平均})$$

在**无状态层**（Linear/Conv/LN/残差）下，这与直接跑 $K$ 倍 batch 的梯度**数学等价**（`ex12` 会数值验证）。但有三处不等价，必须知道：

1. **BatchNorm**：统计量来自 micro-batch，不同 micro-batch 的归一化不同 → 不等价。要么改用 SyncBN/GN，要么别用累积。
2. **Dropout**：随机掩码不同 → 期望相同、方差不同，实际训练曲线会有差异（影响很小）。
3. **学习率与调度**：按「优化器 step 数」还是「样本数」计步？累积时 step 数 = 总 batch / (micro × K)，调度必须按 step 计，否则等价学习率变了。

分布式数据并行（DDP）的本质是**梯度取平均**：每卡算局部梯度，做一次 AllReduce（ring 算法，通信量 $\approx2\times$ 参数量），再各自更新。因此 DDP 的「全局 batch」= 单卡 batch × 卡数，与梯度累积组合时要小心：**两者都增大有效 batch，但只有累积会改变 BN 统计量**。

### 🧑‍💻 程序员视角

- 排「大 batch 训不动」的顺序：先确认 **lr 是否按 batch 缩放**、再确认 **warmup 是否够长**、最后才怀疑优化器。80% 的问题是 lr 没跟着 batch 调。
- 梯度累积的正确写法：`loss = loss / K` 再 `backward()`（否则梯度被放大 K 倍，等效 lr × K）；且 `optimizer.step()` 只每 K 次调用一次，`scaler.step/update` 也要同频。
- 需要「真大 batch」的场景（对比学习、BN 网络）不能用累积替代，必须上 DDP + SyncBN；这是「小卡多机」与「大卡单机」的性能分水岭。
- 通信优化：DDP 的 AllReduce 与反向计算可以**重叠**（bucket + 梯度就绪即通信）；不开 `gradient_as_bucket_view` 会有额外拷贝，大模型能差 10%-20% 吞吐。

### 🎓 博士生视角

- 梯度累积的等价性可以严格写成：$\frac{1}{K}\sum_k\nabla L_k=\nabla\big(\frac{1}{K}\sum_k L_k\big)$，只要 $L_k$ 之间无跨样本耦合（BN 破坏了这一条）。这是「为什么 BN 与累积不兼容」的形式化表述。
- 分布式训练的**有效 batch** 与「梯度噪声尺度」直接相关：$\eta/B$ 决定噪声，因此「4 卡 × batch 8 + 累积 4」与「单卡 batch 128」在无状态层上等价，在有 BN 时不等价（统计量来源不同）。
- Ring AllReduce 的带宽最优性是 $\frac{2(N-1)}{N}\cdot S$（$S$ 为梯度大小），随卡数增大趋近 $2S$，因此**通信量不随卡数线性增长**——这是 DDP 能扩展的基础。ZeRO/FSDP 换的是「显存」而不是「通信量」，代价是通信次数增加（见第三节）。

### 📚 考研者视角

- **必背**：梯度累积的公式与「除以 K」的原因；DDP 是「梯度平均」不是「参数平均」（后者是模型平均/EMA）。
- **常考问法**：① 梯度累积与增大 batch 是否等价（无状态层等价、BN 不等价）；② DDP 与模型并行的区别（数据切分 vs 模型切分）；③ AllReduce 是什么（所有卡归约到相同结果）。
- **易混**：数据并行（每卡一份完整模型）≠ 模型并行（每卡一部分模型）；参数平均（联邦/模型平均）≠ 梯度平均（DDP）。

## 可运行代码：warmup 曲线与两种 weight decay

「warmup 不是玄学」可以看着学习率曲线说清楚——前 100 步线性升到峰值，之后余弦降到 0：

```python
import math
import torch

def lr_at(step, base=3e-4, warmup=100, total=1000):
    """线性 warmup + 余弦退火；step 从 0 计。"""
    if step < warmup:
        return base * (step + 1) / warmup           # 峰值出现在第 warmup 步
    t = (step - warmup) / max(1, total - warmup)
    return 0.5 * base * (1 + math.cos(math.pi * t))  # 平滑降到 ~0

print([round(lr_at(s), 7) for s in (0, 50, 99, 100, 550, 999)])

# Adam 的 weight_decay 与 AdamW 的衰减不是一回事
p1 = torch.nn.Parameter(torch.tensor([1.0, -2.0]))
p2 = torch.nn.Parameter(torch.tensor([1.0, -2.0]))
for p in (p1, p2):
    p.grad = torch.zeros_like(p)                   # 梯度置零，只剩衰减项在起作用
torch.optim.Adam([p1],  lr=0.1, weight_decay=0.1).step()
torch.optim.AdamW([p2], lr=0.1, weight_decay=0.1).step()
print("Adam :", [round(v, 4) for v in p1.data.tolist()])
print("AdamW:", [round(v, 4) for v in p2.data.tolist()])
```

第一行列表里，第 100 步是峰值且**不连续**——`step < warmup` 用线性、之后切余弦，接缝处
如果不专门处理就会有跳变，这也是很多实现把 warmup 写成 `min(1, step/warmup)` 再统一相乘的原因。

后半段的对比更值得记：梯度为 0 时，`Adam(weight_decay)` 的衰减项会**进入梯度再被二阶矩归一化**，
于是衰减幅度与参数大小脱钩，大参数反而衰减得更「慢」；`AdamW` 把 `lr * wd * p` 直接乘在参数上，
是**按比例**缩小。这就是「Adam + L2 正则」与「AdamW」在论文里被分开讨论的根本原因。

## 三视角小结

| 主题 | 程序员要会 | 博士生要会 | 考研/笔面要会 |
|---|---|---|---|
| 优化器 | AdamW 配方、排除 wd、显存 12B/参数 | 对角预条件、proximal 视角、反例 | 三种更新式、AdamW vs Adam+L2 |
| 学习率 | warmup 1-5% + cosine、update/param 比 | 噪声尺度理论、cosine 积分 | warmup 原因、线性缩放 |
| 稳定性 | 全局裁剪、回滚策略、spike 四类成因 | 信赖域、曲率突变、QK-norm | 裁剪公式与作用边界 |
| 有效 batch | 累积写法（除以 K）、DDP 重叠 | 等价性条件、AllReduce 带宽 | 累积 vs 大 batch、DDP vs 模型并行 |
