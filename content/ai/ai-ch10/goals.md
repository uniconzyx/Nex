# ai-ch10 · 训练工程与规模化：从「能跑通」到「能训起来」

> 先修：ai-ch01（反向传播、优化器基础）、ai-ch03（Transformer 结构）。
> 衔接：ai-ch04（LoRA/对齐：本章讲「怎么把模型训起来」，ch04 讲「怎么低成本适配」）。
> 面试权重：★★★★★（大模型/训练框架岗的核心；「7B 单卡为什么训不动」是开场必问）
> 本机无 PyTorch/CUDA，全部示例用 **NumPy 从零实现并真实运行**（见 examples/），数值结论可直接复算。

## 本章目标

学完你应该能：

1. **推出初始化的方差公式**（Xavier $2/(n_{in}+n_{out})$、He $2/n_{in}$），并解释为什么「方差保持」是深网可训练的第一性条件。
2. **说清 BN/LN/RMSNorm 的统计维度差异**，以及 Pre-LN 为什么能省掉长 warmup、Post-LN 为什么不行。
3. **写出 Adam / AdamW 的完整更新式**，并解释「解耦 weight decay」为什么在 Transformer 上带来泛化提升。
4. **口算训练显存**：16 B/参数（混合精度 + Adam）的四个组成，7B/13B/70B 分别需要多少、要几卡。
5. **说清 ZeRO 三阶段各分片什么、通信代价如何变化**，并能针对「模型大小 + 卡数 + 拓扑」给出并行方案。
6. **解释 fp16 为什么溢出、bf16 为什么不用 loss scaling、fp32 主权重为什么必需**。
7. **用 Scaling Law 做预算规划**：给定算力求最优 $N/D$，并解释「过训练」为什么在产品里更划算。
8. **读 loss 曲线做诊断**：区分过拟合、平台化、双下降、grokking、loss spike，并给出排查顺序。

## 关键认知（本章最值钱的三句）

- **训练的第一性问题是「信号能不能穿过深度」**：初始化和归一化都在控制 Jacobian 谱，残差保证谱不退化到 0。三者是同一个目标的三个杠杆，不是三个独立技巧。
- **混合精度不省模型状态显存**：训练要 16 B/参数（含 fp32 主权重与两份优化器矩），省的是激活与带宽。把「推理 2 B/参数」的账套到训练上，是算力规划的经典错误。
- **Scaling Law 优化的是「训练成本」，产品优化的是「总成本」**：这正是 Chinchilla（20 tokens/参数）与工业界「过训练小模型」并存的解释。
## 与相邻章节的边界

用一句话划界：**前四章讲「模型是什么」，本章讲「怎么让它在真实规模下训得下去」**。
同一个 Transformer，ch03 关心表达能力，本章只关心梯度能不能稳定穿过 96 层、显存够不够放下一次 step。

- **与 ai-ch01**：ch01 讲反向传播**怎么算**（链式法则、计算图），本章讲算出来的梯度
  **怎么稳定地走完十万步**——初始化、归一化、残差、AdamW、混合精度，五个杠杆同一个目标。
- **与 ai-ch03**：结构（MHA、位置编码、层数/宽度配比）在 ch03，本章假定结构已定，只讨论该结构上的训练稳定性。
- **与 ai-ch04**：ch04 是「冻结主干、只训适配器」的低成本路线（LoRA/QLoRA/对齐）；
  本章是全参数训练的资源与并行问题，两者是两条不同预算下的策略，不能互相替代。
- **与 ai-ch13**：ch13 讲**推理**的量化与 KV Cache 分页，本章只讲**训练**的混合精度
  （fp16 溢出、bf16 免 loss scaling、fp32 主权重），两者的显存账完全不同，别混用。
- **与 ai-ch11（服务化）**：本章终点是一个可复现的 checkpoint 与训练日志；
  从 checkpoint 到线上不崩（灰度、回滚、监控）在 ch11。


> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [microsoft/DeepSpeed](https://github.com/microsoft/DeepSpeed) | 43,271 | §3.3 并行策略 | `deepspeed/runtime/zero/stage3.py` 是 ZeRO-3 的参数分片（§3.3 三阶段表的第三行）；`stage1.py`/`stage2.py` 分别是优化器状态与梯度分片，看 `_partition_param` 就懂「12 字节/参数」怎么摊 |
| 2 | [NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM) | 18,278 | §3.3 并行策略 | `megatron/core/tensor_parallel/layers.py` 里列并行/行并行两个 Linear 就是 §3.3 的 TP 原文；`pipeline_parallel/` 能对上 $(P-1)/(M+P-1)$ 的空泡推导 |
| 3 | [google-research/tuning_playbook](https://github.com/google-research/tuning_playbook) | 30,404 | §2.2 学习率调度 | 先读「Batch size」与「Learning rate schedule」两节：§2.2 的 warmup+cosine、§2.4 的线性缩放规则都在这里给了工程口径，可与 ex06 的学习率曲线对照 |
| 4 | [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) | 64,145 | §2.2 学习率调度 | 最小可训 GPT：`train.py` 的 `get_lr` 就是 warmup+cosine（§2.2），`model.py` 的 `Block` 是 Pre-LN 残差（§1.3），`estimate_loss` 是评估口径 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §2.1 从 SGD 到 AdamW | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（三种初始化下 50 层前向的激活方差）核对 |
| 2 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | §1.3 残差与梯度路径 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex02`（随机矩阵 vs 正交矩阵的谱半径）核对 |
| 3 | ViT / SAM / CLIP 多模态大模型详解<br><sub>人工智能AI大模型课程</sub> | [BV1AT411y7Zg](https://www.bilibili.com/video/BV1AT411y7Zg/) | 全章 | 把 ViT 的 patch 化、CLIP 的对比学习、SAM 的提示式分割串起来，补「视觉侧」的边界；看完回 `ex03`（LayerNorm 与 RMSNorm ）核对 |
| 4 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex04`（Pre-LN 与 Post-LN 的信号）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Deep Learning》Goodfellow 第7-8章（正则化、优化） |
| 2 | Rajbhandari et al., 2020 · ZeRO: Memory Optimizations Toward Training Trillion Parameter Models |
| 3 | Loshchilov & Hutter, 2019 · Decoupled Weight Decay Regularization |
| 4 | Hoffmann et al., 2022 · Training Compute-Optimal Large Language Models（Chinchilla） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、4 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
