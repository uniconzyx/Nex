# ai-ch02 · 视觉与序列建模：CNN、RNN 到注意力机制

> 先修：ai-ch01（张量、前向与反向传播、梯度消失/爆炸、优化器）。
> 衔接：ai-ch03（Transformer 与大语言模型原理）。
> 面试权重：★★★★★（视觉岗/序列建模/大模型岗必考；理解注意力是读懂 LLM 的前提）
> 本机无 PyTorch/TensorFlow，全部示例用 **NumPy 从零实现并真实运行**（见 examples/）。

## 本章目标

学完你应该能：

1. **说清卷积的两个结构性质**：局部连接与权值共享，以及它们如何把参数量从 O(H_in·H_out) 降到 O(Cout·Cin·k²)，并带来**平移等变**而非不变。
2. **手算输出尺寸、参数量、感受野**：掌握 out = floor((n+2p−k)/s)+1、Params = Cout·Cin·k·k + Cout、感受野递推，并能解释「3 个 3×3 感受野 = 1 个 7×7」的 ResNet 论据。
3. **从数学上理解 RNN 的梯度消失**：用 BPTT 连乘 W_hh 与 tanh 导数，证明长程梯度按谱半径指数衰减；说清 LSTM/GRU 的门控如何缓解（而非根治）。
4. **完整推导并手写缩放点积注意力**：Q·K^T / sqrt(d_k) → softmax → 加权 V，含因果掩码；说清除以 sqrt(d_k) 防止 softmax 饱和的动机。
5. **讲透复杂度与位置编码**：自注意力 O(n²d) vs RNN O(nd²) 的适用分野；正弦位置编码为何相加、为何用不同频率。

## 关键认知（本章最值钱的三句）

- **卷积的「等变」不是「不变」**：权值共享让平移输入等价于平移输出（等变）；要平移**不变**需额外池化/全局池化。
- **梯度消失是连乘的谱半径衰减**：RNN 的反向传播把 W_hh 与 tanh 导数沿时间连乘，谱半径 < 1 即指数衰减——LSTM 用门控把「记忆」走恒等通路来缓解。
- **注意力的二次复杂度是它最大的软肋**：O(n²d) 让长序列昂贵，这正是后续 FlashAttention / 稀疏注意力 / MQA 要解决的工程问题。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §1.1 | 讲「卷积的计算量」时读 `tensorflow/python/keras/layers/convolutional/`：`Conv2D` 的 `call` 里就是「滑窗 + 乘加」，参数量 `k²·C_in·C_out` 与计算量 `k²·C_in·C_out·H·W` 的差别在这里能直接看出来 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §2.3 | 讲「图文数据的采集」时读 `apps/api/src/` 的抓取输出：markdown 里保留图片链接，是「图文对」最廉价的来源，也解释了为什么多模态数据质量参差 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §4.2 | 讲「序列决策」时看 agent 的「观察 → 思考 → 行动」循环：与 RNN 的「隐状态随步更新」结构同构，区别是隐状态换成了上下文窗口 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §2.2 | 讲「从 RNN 到注意力」时读 `src/transformers/models/bert/` 与任一 RNN 模型的实现对比：注意力没有递归、整段并行，这是「训练能规模化」的根本原因 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §4.1 | 讲「视觉模型在应用里的位置」时读 `api/core/model_runtime/model_providers/`：多模态 provider 把图片转成 base64 或 URL 再送模型，本章「视觉 token 数决定成本」在这里变成计费口径 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §3.2 | 讲「序列建模的输入表示」时读 `libs/core/langchain_core/messages/`：把对话压成 token 序列时「角色 + 内容」的拼接方式，决定了模型看到的是什么 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | §3.1 RNN 与 BPTT 的梯… | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（滑窗卷积）核对 |
| 2 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | §4.1 缩放点积注意力与缩放动机 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex02`（im2col 卷积）核对 |
| 3 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | §4.1 缩放点积注意力与缩放动机 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex03`（池化输出尺寸公式验证（多组参数））核对 |
| 4 | ViT / SAM / CLIP 多模态大模型详解<br><sub>人工智能AI大模型课程</sub> | [BV1AT411y7Zg](https://www.bilibili.com/video/BV1AT411y7Zg/) | §2.2 padding='same… | 把 ViT 的 patch 化、CLIP 的对比学习、SAM 的提示式分割串起来，补「视觉侧」的边界；看完回 `ex04`（padding=same/valid 卷）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
