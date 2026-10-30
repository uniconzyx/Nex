# ai-ch09 · 生成模型：从自编码器到扩散

> 先修：ai-ch01（张量、反向传播、优化器）、ai-ch02（卷积/注意力）。
> 衔接：ai-ch11（自监督与多模态：CLIP 把「生成」与「理解」接起来）。
> 面试权重：★★★★★（AIGC/多模态/算法岗必考；「扩散的 ELBO 怎么推到 $\mathcal{L}_{\text{simple}}$」是分水岭题）
> 本机无 PyTorch/TensorFlow，全部示例用 **NumPy 从零实现并真实运行**（见 examples/），输出即公式的数值对账。

## 本章目标

学完你应该能：

1. **说清 AE / VAE / GAN / 扩散 / Flow 五类模型的目标函数差异**，并能从「显式密度 / 隐式密度 / 下界 / 精确」四个维度给它们定位。
2. **完整推导 VAE 的 ELBO**（Jensen 那一步 + 高斯 KL 闭式解），并解释重参数化为什么让梯度可回传、后验坍塌是什么信号。
3. **推出 GAN 的最优判别器** $D^*=\frac{p_{\text{data}}}{p_{\text{data}}+p_g}$，并代入得到 $2D_{\mathrm{JS}}-\log4$；解释为什么这时生成器在分布不重叠时会**梯度消失**，以及 WGAN 如何修好它。
4. **手算扩散的任意步加噪** $x_t=\sqrt{\bar\alpha_t}x_0+\sqrt{1-\bar\alpha_t}\varepsilon$，并把 ELBO 推到 $\mathcal{L}_{\text{simple}}=\|\varepsilon-\varepsilon_\theta\|^2$；说清「预测噪声 = 预测得分」这个恒等式。
5. **解释 DDIM 为什么能跳步、CFG 为什么能用两次前向换可控性**，并给出工业默认的采样配置（DPM-Solver++ / 20 步 / $s\approx7$）。
6. **判断一个 FID 数字可不可信**：说出四个已知偏差，并知道为什么要配 precision/recall 与 CLIPScore 三件套。

## 关键认知（本章最值钱的三句）

- **VAE 的 KL 项是「率」，重建项是「失真」**：β 就是两者的拉格朗日乘子。调 β 不是调玄学，是在率失真曲线上选点。
- **GAN 的最优判别器是一个密度比估计器**（$D^*/(1-D^*)=p_{\text{data}}/p_g$）；它只在一二阶统计意义上学到了「像不像」，因此既不保证覆盖、也不提供似然。
- **扩散 = 固定前向的层级 VAE，其去噪目标等价于得分匹配**：$\varepsilon_\theta=-\sqrt{1-\bar\alpha_t}\nabla\log q_t$。这一条把扩散、score-based、SDE/ODE、flow matching 全串起来了。
## 与相邻章节的边界

本章只回答两个问题：**这几类生成模型的目标函数差在哪、怎么训**（VAE/GAN/扩散/Flow/AR），
以及**怎么采样、怎么评**。工程侧的分工如下：

- **与 ai-ch01 / ai-ch02**：反向传播、卷积、注意力的前置知识不再重讲；
  本章出现的编码器/解码器只当黑箱用，需要回看时去 ch01（张量、链式法则）、ch02（卷积与注意力）。
- **与 ai-ch10（训练工程）**：扩散训练要多少卡、多少显存、怎么并行，是 ch10 的账；
  本章只讲 $L_{\text{simple}}$ 怎么来、怎么采样。需要把「从零训练一个 latent diffusion」落地时，读 ch10 的显存与并行三篇。
- **与 ai-ch11 / ai-ch13（服务化与推理部署）**：采样步数、CFG 的两次前向、VAE 解码的延迟，
  在 ch11 里是容量规划问题、在 ch13 里是 KV Cache 与 batching 问题；本章只给出工业默认配置（20 步、$s\approx7$）的来源。
- **与 ai-ch14（多模态落地）**：图像质量的 FID/CLIPScore 在本章讲；图文对齐质量、OCR→VLM 流水线的评测在 ch14。
- **与 ml 学科**：ml-ch06 的 GMM + EM 是隐变量模型的原型，VAE 就是把它换成神经网络参数化的编码器；
  差别在于「后验能不能解析求解」，这也是本章从 ELBO 讲起、而非从 EM 讲起的原因。


> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [huggingface/diffusers](https://github.com/huggingface/diffusers) | 34,819 | §3.1 前向过程 | 工业实现先看 `src/diffusers/schedulers/scheduling_ddpm.py`：`set_timesteps` 用 betas 累乘造出 $\bar\alpha_t$ 表（§3.1 的闭式），`step` 是单步反向（§3.2）；再看 `pipelines/stable_diffusion` 里 `guidance_scale` 如何落地 CFG（§3.3） |
| 2 | [CompVis/latent-diffusion](https://github.com/CompVis/latent-diffusion) | 14,180 | §3.2 反向过程与训练目标 | 潜空间扩散的原始实现：`ldm/models/diffusion/ddpm.py` 的 `p_losses` 是 $L_{simple}$（§3.2），`apply_model` 包住 U-Net 前向；潜空间压缩那部分回看 §1.2 的 VAE 编码器 |
| 3 | [ermongroup/ddim](https://github.com/ermongroup/ddim) | 1,855 | §3.3 采样 | DDIM 官方代码：`models/diffusion_utils.py` 的 `make_ddim_timesteps` 造跳步子序列、`ddim_step` 用 $\varepsilon_\theta$ 直接预测 $x_0$（§3.3 采样里的非马尔可夫边缘不变） |
| 4 | [openai/guided-diffusion](https://github.com/openai/guided-diffusion) | 7,442 | §3.2 反向过程与训练目标 | ADM 架构与 guidance：`guided_diffusion/gaussian_diffusion.py` 的 `p_mean_variance` 是反向均值/方差的标准写法（§3.2），`condition_mean` 的两个分支就是 CFG 的 $\varepsilon_{uncond}+s(\varepsilon_{cond}-\varepsilon_{uncond})$（§3.3） |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §1.2 VAE | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（自编码器前向与参数量）核对 |
| 2 | 扩散模型的原理是什么<br><sub>无限理论</sub> | [BV1fS7nznEUf](https://www.bilibili.com/video/BV1fS7nznEUf/) | §1.2 VAE | 36 分钟讲清加噪/去噪与「为什么可以从纯噪声生成」；先建立直觉，再回来看 ELBO 推导；看完回 `ex02`（重参数化与高斯 KL 闭式解对账）核对 |
| 3 | ViT / SAM / CLIP 多模态大模型详解<br><sub>人工智能AI大模型课程</sub> | [BV1AT411y7Zg](https://www.bilibili.com/video/BV1AT411y7Zg/) | 全章 | 把 ViT 的 patch 化、CLIP 的对比学习、SAM 的提示式分割串起来，补「视觉侧」的边界；看完回 `ex03`（ELBO 是似然的下界（数值验证））核对 |
| 4 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | §1.2 VAE | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex04`（GAN 最优判别器与 2*JSD-log）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Deep Learning》Goodfellow 第14章（自编码器）、第20章（深度生成模型） |
| 2 | Kingma & Welling, 2013 · Auto-Encoding Variational Bayes |
| 3 | Goodfellow et al., 2014 · Generative Adversarial Nets |
| 4 | Ho et al., 2020 · Denoising Diffusion Probabilistic Models |
| 5 | Song et al., 2021 · Score-Based Generative Modeling through SDEs |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、5 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
