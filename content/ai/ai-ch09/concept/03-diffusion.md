# ai-ch09 · 核心概念（三）：扩散模型

> 视角覆盖：程序员（工程决策）/ 博士生（第一性原理）/ 考研者（笔面口径）。三者互补、不重复。
> 本章 `examples/ex07~ex11` 用 NumPy 从零实现加噪、反向单步、DDIM 与 CFG，输出与公式可逐项对账。

```text
前向：一步到位加噪（闭式，不用迭代）
    x_t = √ᾱ_t · x_0 + √(1-ᾱ_t) · ε ,  ε ~ N(0,I)
    t=0 ─────────────▶ t=T      ᾱ_t 单调递减，x_0 逐渐变纯噪声

训练：随机取 t，让网络从 x_t 预测 ε（本质是一个回归任务）
    loss = E‖ε - ε_θ(x_t, t)‖²

反向：从纯噪声逐步去噪
    x_T ─▶ x_{T-1} ─▶ … ─▶ x_0
    每步 x_{t-1} = (x_t - 系数·ε_θ)/√α_t + σ_t·z
    DDIM：跳步采样（T=1000 可只跑 20~50 步），确定性可复现
    CFG ：ε = ε_uncond + s·(ε_cond - ε_uncond)，s↑ 更贴提示词、多样性↓

账本：采样步数 × 每步一次 U-Net 前向 = 延迟，这就是少步采样/蒸馏是热点的原因
```

## 1. 前向过程：一条「闭式可算」的加噪链

扩散模型的前向过程是一个**固定的马尔可夫链**：每一步往数据里加一点高斯噪声，

$$q(x_t\mid x_{t-1})=\mathcal{N}\big(x_t;\sqrt{\alpha_t}\,x_{t-1},(1-\alpha_t)I\big),\qquad \alpha_t=1-\beta_t$$

记 $\bar\alpha_t=\prod_{s=1}^{t}\alpha_s$。关键结论是：**不需要逐步迭代**，任意时刻 $t$ 的加噪结果有闭式解

$$q(x_t\mid x_0)=\mathcal{N}\big(x_t;\sqrt{\bar\alpha_t}\,x_0,(1-\bar\alpha_t)I\big)\ \Longleftrightarrow\ x_t=\sqrt{\bar\alpha_t}\,x_0+\sqrt{1-\bar\alpha_t}\,\varepsilon,\quad \varepsilon\sim\mathcal{N}(0,I)$$

这条式子怎么来的：两个高斯相加仍是高斯，方差可加。设 $x_{t-1}=\sqrt{\bar\alpha_{t-1}}x_0+\sqrt{1-\bar\alpha_{t-1}}\varepsilon_1$，再加一步噪声得 $x_t=\sqrt{\alpha_t}x_{t-1}+\sqrt{1-\alpha_t}\varepsilon_2$，展开后 $x_0$ 的系数是 $\sqrt{\alpha_t\bar\alpha_{t-1}}=\sqrt{\bar\alpha_t}$，噪声项方差是 $\alpha_t(1-\bar\alpha_{t-1})+(1-\alpha_t)=1-\bar\alpha_t$。**训练能高效采样任意 $t$ 的原因就在于此**——一个 batch 里可以随机抽 $t$，不必跑完整条链。

$\beta_t$ 的选择（噪声调度）直接决定模型好不好训，工程上有三条主流曲线：

| 调度 | 形式 | 特点 |
|---|---|---|
| 线性（DDPM 原版） | $\beta_t$ 从 $10^{-4}$ 线性到 $0.02$ | 简单，但在高分辨率下末段噪声加得太快，$x_T$ 已近似纯噪声而信息全丢 |
| 余弦（improved DDPM） | $\bar\alpha_t=\cos^2\!\big(\frac{t/T+s}{1+s}\cdot\frac{\pi}{2}\big)$ | 前期降得更慢，保留结构更久，训练更稳 |
| Sigmoid / zero-terminal SNR | 对 SNR 做插值 | 保证 $t=T$ 时 SNR 精确为 0，避免「末步仍泄漏信息」 |

**SNR（信噪比）** $\mathrm{SNR}(t)=\bar\alpha_t/(1-\bar\alpha_t)$ 是理解调度的正确坐标：线性 $\beta$ 在 SNR 的对数尺度上分布极不均匀，导致大量训练步落在「已经没信息」的区间，浪费容量。这是「换个调度就明显提升」的真实原因。

### 🧑‍💻 程序员视角

- **显存/计算的第一步不是模型，是调度**：把 $\bar\alpha$ 预计算成一张长度 $T$ 的表（float32/float64），训练时按索引取，别在 GPU 上现算累乘。
- 数值稳定：$\sqrt{1-\bar\alpha_t}$ 在 $t$ 很大时接近 1，$\sqrt{\bar\alpha_t}$ 接近 0，用 float32 做 $\sqrt{}$ 有精度问题，实践用 float64 建表再转 float32。
- 分辨率越高，线性调度越差；换 cosine 通常是「免费」的质量提升（不用改模型结构）。Stable Diffusion 系列用 scaled-linear（$\bar\alpha$ 的平方根线性插值）。
- **$t$ 的采样分布不要均匀**：均匀采 $t$ 会让大量算力花在「几乎纯噪声」的步上，且这些步的损失梯度对感知质量贡献小。工程上用 importance sampling（按损失方差加权）或直接对 $t$ 做 logit-normal 采样。
- 别把「加噪」写进 dataloader 的 normalizer 里：归一化必须是固定的（如 $[-1,1]$），噪声在模型内加，否则评估与推理的噪声尺度会对不上。

### 🎓 博士生视角

- 前向过程定义了**一族分布** $\{q_t\}$，扩散模型的本质是「学会这族分布之间的传输」。$\bar\alpha_t$ 曲线实际上定义了从数据流形到各向同性高斯的**路径形状**；不同调度就是不同路径，而采样质量对路径的曲率敏感（这解释了为什么换个 $\beta$ 调度会有系统性差异，而非随机波动）。
- 闭式解的另一种读法：$x_t$ 是 $x_0$ 与 $\varepsilon$ 的**球面插值**（系数平方和为 1），即 $x_t$ 落在以原点为球心、半径约 $\sqrt{\bar\alpha_t\|x_0\|^2+(1-\bar\alpha_t)d}$ 的球面上。这解释了「为什么扩散模型的隐空间是同心球壳」以及 spherical 采样（如 SDXL 的 EDICT 变体）为什么可行。
- $T\to\infty$ 的连续极限就是 SDE：$dx=-\frac{1}{2}\beta(t)x\,dt+\sqrt{\beta(t)}\,dw$（VP-SDE），其反向过程为 $dx=[-\frac{1}{2}\beta x-\beta\nabla_x\log q_t(x)]dt+\sqrt{\beta}\,d\bar w$。离散的 DDPM 是它的一阶 Euler-Maruyama 离散化。
- 另一个必须知道的等价类：**VE-SDE**（方差爆炸，$x_t=x_0+\sigma(t)\varepsilon$）。VP 与 VE 在理论上等价（差一个时间重参数化），但数值行为不同，score-based 论文用 VE、DDPM 用 VP，比较结果时必须说明用的是哪一套。

### 📚 考研者视角

- **必背**：$x_t=\sqrt{\bar\alpha_t}x_0+\sqrt{1-\bar\alpha_t}\varepsilon$；$\bar\alpha_t$ 的定义与递推；前向过程无参数（固定的，不学习）。
- **常考计算**：给定 $\beta_t=0.02$、$T=1000$，求 $\bar\alpha_{10}$ 或 SNR；给定 $x_0=1,\varepsilon=0.5,\bar\alpha_t=0.81$，求 $x_t$（$0.9\cdot1+0.4359\cdot0.5=1.118$）。
- **易混点**：$\alpha_t$ 与 $\bar\alpha_t$ 别搞混（前者单步、后者累积）；「加噪是加在 latent 上还是像素上」——取决于具体模型（像素扩散 / latent diffusion），概念题常设这个陷阱。

## 2. 反向过程与训练目标：把「去噪」变成回归

反向过程要学的是 $p_\theta(x_{t-1}\mid x_t)=\mathcal{N}(x_{t-1};\mu_\theta(x_t,t),\Sigma_\theta(x_t,t))$。用变分推断（对整条链求 ELBO），可以把它化成逐项之和：

$$\log p_\theta(x_0)\ \ge\ \mathbb{E}_q\Big[\log p_\theta(x_T)+\sum_{t=1}^{T}\log\frac{p_\theta(x_{t-1}\mid x_t)}{q(x_t\mid x_{t-1})}\Big]$$

逐项配平方后，第 $t$ 项等价于让 $\mu_\theta$ 逼近后验均值 $\tilde\mu_t$，而 $\tilde\mu_t$ 可写成

$$\tilde\mu_t=\frac{1}{\sqrt{\alpha_t}}\Big(x_t-\frac{\beta_t}{\sqrt{1-\bar\alpha_t}}\,\varepsilon\Big)$$

于是「预测均值」变成了「**预测噪声**」：把 $x_t$ 与 $\varepsilon_\theta(x_t,t)$ 代回，得反向一步

$$x_{t-1}=\frac{1}{\sqrt{\alpha_t}}\Big(x_t-\frac{\beta_t}{\sqrt{1-\bar\alpha_t}}\,\varepsilon_\theta(x_t,t)\Big)+\sigma_t z,\qquad \sigma_t^2=\tilde\beta_t=\frac{1-\bar\alpha_{t-1}}{1-\bar\alpha_t}\beta_t$$

DDPM 的第二个关键贡献是**把逐项加权系数丢掉**，得到极简目标

$$\mathcal{L}_{\text{simple}}=\mathbb{E}_{t,x_0,\varepsilon}\big\|\varepsilon-\varepsilon_\theta\big(\sqrt{\bar\alpha_t}x_0+\sqrt{1-\bar\alpha_t}\varepsilon,\ t\big)\big\|_2^2$$

丢掉系数是「有理论代价的工程选择」：理论上应该按 $t$ 的 SNR 加权（对应 ELBO 的真实各项），实践发现不加权反而生成质量更好——因为加权会过度强调低噪声步（那些步噪声小、损失小，但对细节/纹理最关键）。这是一个**理论正确 ≠ 效果最好**的经典案例。

**为什么预测 $\varepsilon$ 比预测 $x_0$ 好**：$\varepsilon$ 是标准正态、尺度与 $t$ 无关，回归目标始终是 $O(1)$ 量级；而 $x_0$ 的「可预测性」随 $t$ 剧变（$t$ 大时信息几乎全丢，预测 $x_0$ 相当于瞎猜），梯度尺度极不稳定。三种参数化（$\varepsilon$、$x_0$、$v=\sqrt{\bar\alpha}\varepsilon-\sqrt{1-\bar\alpha}x_0$）在数学上可互相换算，但**训练难度不同**；$v$-prediction 在高噪声区间更稳，是后来不少工作（progressive distillation）的选择。

### 🧑‍💻 程序员视角

- **一个 epoch 的训练伪码只有 5 行**：抽 $x_0$ → 抽 $t$ → 抽 $\varepsilon$ → 算 $x_t$ → 算 $\|\varepsilon-\varepsilon_\theta(x_t,t)\|^2$ 反传。**不需要**展开 $T$ 步链，这是扩散训练比自回归便宜的根本原因（每步是常数时间）。
- 时间步注入：正弦位置编码 → MLP → 加到每个残差块（FiLM 的 scale/shift）。别用小学习率的 embedding 表，正弦编码外推性更好。
- 采样默认用 $\sigma_t$ 的**下界**（DDPM 论文取 $\sigma_t^2=\beta_t$ 或 $\tilde\beta_t$，两者 FID 几乎一样）；想更快就换 DDIM（见下一节）。
- **训练不收敛的常见原因**：① $\bar\alpha$ 表精度不够（float16 建表会在末期崩）；② 残差块里 LayerNorm 的 eps 太小；③ 用 MSE 对比 $[-1,1]$ 归一化外的数据（范围错）；④ 学习率没 warmup（扩散对前期剧烈不稳定极敏感）。
- 定量检查：训练几百步后，用固定的 $x_T$ 采样，输出的**均值/方差**应接近数据集的统计量；若方差远小于真实数据，通常是过拟合或损失权重错。

### 🎓 博士生视角

- 三种参数化统一在「**预测信噪比相关的分量**」这一视角下：$\varepsilon$、$x_0$、$v$ 是同一个二维空间（$x_t$ 与 $x_0$ 张成的平面）的三组正交/斜交基。$v$-prediction 的优势来自它在 $\bar\alpha_t\to0.5$ 附近的条件数最好。
- $\mathcal{L}_{\text{simple}}$ 与 ELBO 的差异可以精确写出：ELBO 的第 $t$ 项权重是 $\frac{\beta_t^2}{2\sigma_t^2\alpha_t(1-\bar\alpha_t)}$，它在 $t$ 小（低噪声）时很大、$t$ 大时趋于常数。丢掉它 = 降低低噪声步的权重，等于**把建模容量从「精确还原细节」转向「生成结构」**。
- 去噪目标与 score matching 的关系是恒等式：$q(x_t\mid x_0)$ 的对数梯度为 $\nabla_{x_t}\log q=-\varepsilon/\sqrt{1-\bar\alpha_t}$，故

$$\varepsilon_\theta(x_t,t)=-\sqrt{1-\bar\alpha_t}\,\nabla_{x_t}\log q_t(x_t)$$

即**预测噪声 = 预测得分函数**（差一个已知缩放）。这条式子把扩散与 score-based 生成模型（Song & Ermon）接上了，也是「扩散能借用所有 score 估计技术」的原因。

- 从 ELBO 到 $\mathcal{L}_{\text{simple}}$ 的「丢弃权重」在理论上其实是**换了一个散度**：加权 ELBO 对应（近似）前向 KL，而等权对应一种 SNR 重加权的目标。因此「$\mathcal{L}_{\text{simple}}$ 更优」不是玄学，而是目标变了。

### 📚 考研者视角

- **必背推导链**：ELBO → 逐项高斯 KL → 后验均值 $\tilde\mu_t$ → 重参数化成 $\varepsilon$ 预测 → $\mathcal{L}_{\text{simple}}$。这条链是「扩散模型」大题的标准答案骨架，漏掉「为什么可以预测噪声」会丢分。
- **常考**：$\mathcal{L}_{\text{simple}}$ 的形式与含义；反向一步的均值公式；$\sigma_t$ 的两个可选值（$\beta_t$ 或 $\tilde\beta_t$）；DDPM 与 VAE 的关系（层级 VAE）。
- **易错**：把反向过程说成「一次去噪到清晰」——它是 $T$ 步迭代；把 $\mathcal{L}_{\text{simple}}$ 说成「ELBO 的等价形式」——它是**去掉权重的简化版**，不严格等价。

```python
import torch

def q_sample(x0, t, betas):
    """前向一步到位：x_t = sqrt(ᾱ_t)·x0 + sqrt(1-ᾱ_t)·ε，不必真的循环 t 次。"""
    abar = torch.cumprod(1 - betas, dim=0)[t].view(-1, 1, 1, 1)
    eps = torch.randn_like(x0)
    return abar.sqrt() * x0 + (1 - abar).sqrt() * eps, eps

def diffusion_loss(eps_net, x0, t, betas):
    """训练目标就是「猜噪声」：预测 ε 与真实 ε 的 MSE。"""
    xt, eps = q_sample(x0, t, betas)
    return ((eps_net(xt, t) - eps) ** 2).mean()
```

「闭式可算」是扩散模型能落地的根本原因：若前向必须迭代 t 次才能得到 `x_t`，
训练一个 batch 就要几百次前向，成本高到不可接受。重参数化把这个 O(T) 变成 O(1)。


## 3. 采样：DDPM → DDIM → 引导

采样是扩散模型最大的工程成本：DDPM 要跑 $T$（通常 1000）次前向。三条加速路线：

**① DDIM：把随机链改成确定性 ODE。** DDIM 构造了一个非马尔可夫的「同一前向边缘」的生成过程，令 $\sigma_t=0$ 得到确定性映射：

$$x_{t-1}=\sqrt{\bar\alpha_{t-1}}\,\hat{x}_0+\sqrt{1-\bar\alpha_{t-1}}\,\varepsilon_\theta(x_t,t),\qquad \hat{x}_0=\frac{x_t-\sqrt{1-\bar\alpha_t}\varepsilon_\theta}{\sqrt{\bar\alpha_t}}$$

因为它不依赖马尔可夫性，可以**跳步**（只取 $t$ 的一个子序列，如 50 步甚至 20 步）。代价：步数太少时细节丢失、多样性略降（确定性采样不探索）。$\eta=1$ 退回 DDPM，$\eta=0$ 是纯 DDIM，中间值插值。

**② 无分类器引导（CFG）：用两次前向换可控性。** 训练时以一定概率丢掉条件（10%-20%），得到无条件模型；采样时把两者外推：

$$\tilde\varepsilon=\varepsilon_\theta(x_t,t,\varnothing)+s\cdot\big(\varepsilon_\theta(x_t,t,c)-\varepsilon_\theta(x_t,t,\varnothing)\big)$$

$s=1$ 是无引导，$s>1$ 增强条件一致性但牺牲多样性（$s$ 太大出现「过饱和/烧焦」伪影）。$s$ 是产品里最常调的旋钮，代价是每次采样两倍前向（工程上用 batch 拼接或对 $s$ 做动态调度来省）。

**③ 蒸馏与高阶求解器。** 一致性模型（Consistency Models）、渐进蒸馏（Progressive Distillation）、对抗蒸馏（SDXL-Turbo / LCM）能把 50 步压到 1-4 步；DPM-Solver 系列用二阶/三阶 ODE 求解器，在不改模型的前提下把 50 步压到 10-20 步。**工业默认组合**：DPM-Solver++ / UniPC + CFG + 20 步。

### 🧑‍💻 程序员视角

- **采样参数的实际影响排序**：步数（20→50 明显提升）> CFG scale（$s$ 在 4-9 之间调）> 调度器（DPM-Solver++ 普遍优于 Euler）> 随机种子。调参按这个顺序，别一上来换模型。
- 采样器与 sigmas 表必须匹配：`karras sigmas` 与 DDIM 混用会得到灰蒙/过曝结果，这类问题占了「模型出图糊」故障的一半。
- 批量采样时同一 batch 内不同 prompt 长度会拖慢（padding 浪费），工程上用 token bucketing 或 sequential CFG 批处理。
- 生产部署必看 **latent 空间的一致性**：图像 VAE 的缩放因子（SD 1.5 是 0.18215）必须与训练时一致，混用不同 VAE 会得到偏色/糊图。
- 采样可复现性：固定 seed + 固定 scheduler + 固定 CFG + 固定 precision（fp16 与 fp32 结果不同），四个都固定才可复现，缺一不可。

### 🎓 博士生视角

- DDIM 的严格基础是「**非马尔可夫前向过程的边缘分布不变**」：只要 $q(x_t\mid x_{t-1},x_0)$ 设计成使 $q(x_t\mid x_0)$ 与 DDPM 相同，训练好的 $\varepsilon_\theta$ 就可复用，而生成过程可以自由选 $\sigma_t$。这是「训练与采样解耦」的一般化思想，也是后来 flow matching / consistency 系列的理论起点。
- DDIM 的确定性版本等价于**概率流 ODE**（PF-ODE）的一阶离散化：$dx/dt$ 由 score 决定，轨迹唯一，因此 $\eta=0$ 时「同一起点必得同一结果」，且支持隐空间插值（两张图的 latent 线性插值 → 语义插值）。这是 $\eta=1$（SDE 采样）做不到的。
- CFG 是一个**贝叶斯后验的锐化**：$\nabla\log p(x\mid c)=\nabla\log p(x)+\nabla\log p(c\mid x)$，而 $\varepsilon_{\text{cond}}-\varepsilon_{\text{uncond}}$ 近似 $\nabla\log p(c\mid x)$。$s>1$ 相当于把「条件似然」的指数抬到 $s$ 次方，于是后验更尖锐（更贴条件、更少多样性）。$s\to\infty$ 会退化成「最符合条件的单点」，多样性归零。
- 为什么 CFG 会导致过饱和：$s$ 放大的是整条 score，包括与条件无关的高频分量，等价于对图像做对比度增强，超出 $[-1,1]$ 后裁剪就产生色块伪影。

### 📚 考研者视角

- **必背**：DDIM 与 DDPM 的区别（非马尔可夫、确定性、可跳步）；CFG 的公式与 $s$ 的作用；扩散采样的复杂度（$T$ 次前向 vs 自回归 $n$ 次、GAN 1 次）。
- **高频问法**：① 为什么 DDIM 能减少步数而效果接近（同一前向边缘 + 确定性 ODE）；② CFG 为什么需要训练时丢条件（要同时有条件和无条件模型）；③ 扩散比 GAN 慢多少、怎么加速。
- **易混**：DDIM 不是「另一个模型」，它与 DDPM **共用同一套权重**，只是采样过程不同——这是最常见的错答。

```python
@torch.no_grad()
def ddim_sample(eps_net, shape, betas, steps=50):
    """DDIM：只在时间步子集上走，确定性（eta=0），50 步即可出图。"""
    abar = torch.cumprod(1 - betas, dim=0)
    ts = torch.linspace(len(betas) - 1, 0, steps).long()
    x = torch.randn(shape)
    for i, t in enumerate(ts):
        t_prev = ts[i + 1] if i + 1 < len(ts) else torch.tensor(0)
        eps = eps_net(x, t)
        x0 = (x - (1 - abar[t]).sqrt() * eps) / abar[t].sqrt()   # 反解出 x0 估计
        x = abar[t_prev].sqrt() * x0 + (1 - abar[t_prev]).sqrt() * eps
    return x
```

DDPM 需要 1000 步、DDIM 只要 20~50 步，差别不在「模型更好」而在**采样器换了**。
同一组权重配不同采样器是常见的性价比调节手段：先换采样器，再考虑蒸馏。


## 4. 统一视角：SDE、概率流 ODE 与 Flow Matching

把离散链推到连续时间，前向过程写成 SDE：

$$dx=f(x,t)\,dt+g(t)\,dw$$

其反向 SDE 为

$$dx=\Big[f(x,t)-g(t)^2\nabla_x\log q_t(x)\Big]dt+g(t)\,d\bar w$$

而与之**边缘分布完全相同**的确定性 ODE（概率流 ODE）为

$$\frac{dx}{dt}=f(x,t)-\frac{1}{2}g(t)^2\nabla_x\log q_t(x)$$

这三个式子的意义是：**SDE / ODE / 离散 DDPM 是同一个生成模型的三种数值实现**，采样器的选择（随机 vs 确定、几阶、几步）只是数值方法，不改变模型本身。

**Flow Matching（流匹配）** 是这条线的当代形态：不再「加噪去噪」，而是直接回归一个**速度场**。取最简单的线性插值路径 $x_t=(1-t)x_0+t\varepsilon$，目标速度为 $v=x_1-x_0=\varepsilon-x_0$，损失为

$$\mathcal{L}_{\text{CFM}}=\mathbb{E}_{t,x_0,\varepsilon}\big\|v_\theta(x_t,t)-(\varepsilon-x_0)\big\|^2$$

它和扩散的关系：VP-SDE 用「保方差」的插值路径（系数 $\sqrt{\bar\alpha},\sqrt{1-\bar\alpha}$ 平方和为 1），Flow Matching 用「直线」路径（系数和为 1）。**路径不同，但训练目标结构相同**。直线路径的数值优势是轨迹更接近直线，用少步 Euler 就能积好，这是 SD3 / Flux 等新模型转向 flow matching 的主要动机。

### 🧑‍💻 程序员视角

- 选型时看**生态**而不是论文：先用社区采样器（diffusers 的 `DPMSolverMultistepScheduler`、ComfyUI 的 `dpmpp_2m`），别自己写积分器；自研只在有明确指标收益时做。
- 判断一个「新采样器」是否可信：看它是否**共用原模型权重**（改数值方法的可复用）、是否报告了相同步数下的 FID/CLIPScore、是否在多个分辨率上稳定。声称「10 步超过 50 步」但没有同口径指标的，基本是调了 CFG 或 cherry-pick。
- Flow matching 的工程差异：$t=0$ 是数据、$t=1$ 是噪声（与 DDPM 相反），采样时**别把时间方向搞反**，这是移植代码最常见的 off-by-direction 错误。
- 训练成本估计：以 512×512 latent 扩散为例，单卡 A100 训练数十万步是常态；这决定了「小团队做生成」几乎只能走微调 + LoRA，不从头训。

### 🎓 博士生视角

- SDE 与 ODE 的边缘等价性来自 **Fokker-Planck 方程**：前向 SDE 的 FPE 与 PF-ODE 的连续性方程描述同一族边缘密度。这是「同一个 $p_t$ 有无限多种实现路径」的严格表述。
- 扩散 = 连续时间的**层级变分推断**；Flow Matching = 连续时间的**回归**。二者的等价性（Gao et al., 2024 等）说明：在特定加权下，扩散的 ELBO 与 flow matching 的 CFM 目标可以互相转化，差别在**路径的参数化**与**损失权重**。
- 「直线路径更好」的严格说法是：直线路径的 ODE 解更接近直线，因而**离散化误差更小**（同样的步数下截断误差更低），而不是「模型更强」。这解释了为什么 flow matching 在少步采样上优势明显、在 100 步以上优势消失。
- 还有一个常被忽略的分野：扩散的**前向过程固定**（无参数），因此不存在「编码器塌陷」；flow matching 的路径也可以是学的（如 Rectified Flow 的 reflow），此时就引入了「路径优化」这一自由度。

### 📚 考研者视角

- **概念关系图（务必能画）**：AE → VAE（层级化）→ 扩散（$T$ 层 VAE + 固定前向）；GAN（隐式、对抗）；Flow（可逆变换、精确似然）；Flow Matching（速度场回归）。
- **高频问法**：① 扩散模型与 VAE 的关系（层级 VAE、ELBO 逐层分解、前向固定）；② 扩散与 score matching 的关系（$\varepsilon=-\sqrt{1-\bar\alpha}\nabla\log q$）；③ SDE/ODE 两种采样有什么区别（随机 vs 确定、可复现性、插值能力）。
- **易混**：概率流 ODE ≠ 前向 SDE（前者是反向确定性版本）；Flow Matching ≠ Normalizing Flow（前者是连续时间速度场、不要求可逆变换的 Jacobian）。

## 三视角小结

| 主题 | 程序员要会 | 博士生要会 | 考研/笔面要会 |
|---|---|---|---|
| 前向加噪 | $\bar\alpha$ 表、cosine 调度、$t$ 采样策略 | 球面插值、VP/VE 等价 | $x_t$ 闭式解与手算 |
| 训练目标 | 5 行伪码、$t$ 注入、数值坑 | ELBO 权重、$\varepsilon$/$x_0$/$v$ 参数化 | $\mathcal{L}_{\text{simple}}$ 推导链 |
| 采样 | DPM-Solver + CFG 20 步、参数影响排序 | DDIM ≡ PF-ODE、CFG 的后验锐化 | DDIM vs DDPM、CFG 公式 |
| 统一视角 | 生态优先、方向别搞反 | FPE 等价性、直线路径的离散误差 | 五类生成模型的关系图 |
