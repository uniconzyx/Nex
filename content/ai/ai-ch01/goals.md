# ai-ch01 · 深度学习基础：张量、前向与反向传播

> 先修：data-ch01（NumPy 与向量化）。衔接：ai-ch02（Transformer 与注意力）、ai-ch05（RAG）。
> 面试权重：★★★★★（AI/算法岗必考；后端岗也常问「反向传播到底是什么」）

## 本章目标

学完你应该能：

1. **说清反向传播不是「链式法则的套用」而是「反向模式自动微分」**：理解它为什么复杂度是
   O(一次前向) 而不是 O(参数量) 次前向，以及它和前向模式 AD 的适用分野。
2. **手写一个能跑的 autograd**：只用 NumPy 实现张量、计算图、VJP（向量-雅可比积）与拓扑排序反向。
   这是理解 PyTorch `backward()` 的最短路径。
3. **解释梯度消失/爆炸的机制并给出对策**：能从「雅可比连乘的谱半径」角度说清为什么深层
   sigmoid 会崩，以及好初始化（Xavier/He）、归一化、残差连接各自在修复什么。
4. **说清优化器演进的每一步动机**：SGD 的问题 → Momentum 的指数滑动平均 →
   RMSProp 的自适应步长 → Adam 的二者结合 → **AdamW 为什么要修正 L2 与权重衰减的耦合**。
5. **掌握数值稳定性写法**：Softmax 减最大值、交叉熵与 Softmax 融合、log-sum-exp trick。

## 关键认知（本章最值钱的三句）

- **反向传播 = 反向模式 AD**：一次前向 + 一次反向就得到**全部**参数的梯度，
  代价约为 2 倍前向，与参数量无关；这正是训练十亿参数模型在数学上可行的根本原因。
- **梯度消失的本质是雅可比连乘的谱半径 < 1**：不是「梯度变小」这么含糊，
  而是连乘矩阵的奇异值指数级衰减到 0。
- **AdamW vs Adam 的区别不是「加了 weight decay」这么简单**：Adam 里 L2 正则被自适应学习率
  缩放，导致大梯度参数受到的正则反而更弱；AdamW 把权重衰减从梯度里拿出来，直接作用在参数上。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §1.2 | 讲「反向传播」时读 `tensorflow/python/eager/backprop.py`：`GradientTape` 记录前向的每个算子、反向按链式法则逐层求导，本章公式里的「链式相乘」就是这里的 `gradient` 调用链 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §3.3 | 讲「训练数据的来源」时读 `apps/api/src/` 的抓取与转换逻辑：网页 → markdown → 文本块，这条链路就是「原始数据变成可训练文本」的最小实现 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §4.3 | 讲「端到端的 AI 应用长什么样」时看仓库里的 agent 主循环：它把「LLM 调用 + 工具执行 + 结果回填」串成 while 循环，是本章「前向一次」在应用层的放大版 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §2.1 | 讲「张量的形状语义」时读 `src/transformers/models/` 下任一模型的 `forward`：`(batch, seq, hidden)` 这条约定贯穿所有模型，形状对不上时第一眼看的就是这里 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §4.1 | 讲「模型接入的工程形态」时读 `api/core/model_runtime/`：把不同厂商的 API 统一成 `invoke` 接口，本章讲的「张量在前向里流动」到了应用层就变成「消息在 provider 之间转换」 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §3.1 | 讲「训练循环的骨架」时读 `libs/core/langchain_core/` 的 Runnable 接口：`invoke`/`batch`/`stream` 三件套是「推理调用」的抽象，对照本章的训练循环能看清「训练与推理的差异在哪一层 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 吴恩达 · 深度学习专项（双语字幕）<br><sub>mHarvey</sub> | [BV1FT4y1E74V](https://www.bilibili.com/video/BV1FT4y1E74V/) | 全章 | 主干：神经网络基础 → 优化与正则 → CNN → 序列模型，每节都配可复现的作业；看完回 `ex01`（张量的形状、strides 与广播（深度）核对 |
| 2 | 李沐 · Transformer 论文逐段精读<br><sub>跟李沐学AI</sub> | [BV1pu411o7BE](https://www.bilibili.com/video/BV1pu411o7BE/) | §4.3 归一化 | 逐段读原论文：多头注意力的形状变化、位置编码、残差与 LayerNorm 的位置，读完能自己写一遍；看完回 `ex02`（手写两层全连接网络的前向传播（无框架））核对 |
| 3 | 李宏毅 · 机器学习/深度学习 2021<br><sub>二次元的Datawhale</sub> | [BV1JA411c7VT](https://www.bilibili.com/video/BV1JA411c7VT/) | 全章 | 讲「为什么」最透的一套：自注意力、Transformer、GAN、自监督与元学习都有完整推导；看完回 `ex03`（手写反向传播（拓扑排序 + VJP））核对 |
| 4 | ViT / SAM / CLIP 多模态大模型详解<br><sub>人工智能AI大模型课程</sub> | [BV1AT411y7Zg](https://www.bilibili.com/video/BV1AT411y7Zg/) | 全章 | 把 ViT 的 patch 化、CLIP 的对比学习、SAM 的提示式分割串起来，补「视觉侧」的边界；看完回 `ex04`（实证梯度消失）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深度学习》Goodfellow 等（花书） |
| 2 | 《动手学深度学习》李沐 等 |
| 3 | 《Deep Learning with PyTorch》Stevens 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 6 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
