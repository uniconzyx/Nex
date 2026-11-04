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
| 1 | [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 201,257 | §1.3 VJP（向量-雅可比积）：反向传播的真身 | 读 `tensorflow/python/eager/backprop.py`：`GradientTape` 记录前向的每个算子，反向时对每个算子调它注册的 `_vjp` 而不是拼整张雅可比矩阵——这正是本章「反向传播是逐算子 VJP 的链式叠加」那句的实现形态；先看 §1.2「计算图：前向建图，反向求导」再看这份源码，就明白「为什么不需要显式构造导数矩阵」 |
| 2 | [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 197,476 | §4.4 训练循环的标准骨架（含所有工程细节） | 读 `apps/api/src/index.ts`：抓取任务从「取种子 URL → 队列分发 → 抓取 → 落库」是一条带重试与限流的标准循环，与本章训练循环的「取 batch → 前向 → 反向 → step → 记录」是同构的骨架；对照 §4.5「梯度累积」，就能看出「一个 step 的边界」决定了重试与累积该放在哪层 |
| 3 | [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187,852 | §4.3 归一化：BatchNorm vs LayerNorm | 看 `classic/original_autogpt/autogpt/app`：Agent 主循环每一轮都要把「目标 + 历史 + 最近观察」重新拼成上下文再送模型，这个「每轮重新归约一次」的动作与 BN/LN 的「每层重新标准化一次输入」是同一个思路——稳定输入的分布，只是 Agent 里稳定的是文本分布 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.1 张量不是「多维数组」这么简单 | 读 `src/transformers/models/llama/modeling_llama.py` 的 `forward`：`(batch, seq, hidden)` 这条约定从 embedding 一路贯穿到 lm_head，中间所有的 `view`/`transpose` 都在维持它；配合 §1.2「计算图：前向建图」看，形状对不上时第一眼就该查这里 |
| 5 | [langgenius/dify](https://github.com/langgenius/dify) | 160,127 | §3.1 先明确问题：SGD 的三个痛点 | 读 `api/core/agent/cot_agent_runner.py` 与 `api/core/model_manager.py`：应用层把「策略（怎么想）」与「模型（谁来算）」写成两处，对应本章 §3.6「学习率调度」也是「更新规则」与「步长规则」两件事——混在一起写就会出现「换了优化器但调度还按旧步长」的错配 |
| 6 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §3.4 Adam = Momentum + RMSProp（加偏差修正） | 读 `libs/core/langchain_core/runnables/base.py`：`invoke`/`batch`/`stream` 三件套把一类调用抽象成统一协议，而具体实现各自不同——这与 §3.2 Momentum 与 §3.3 RMSProp 各自贡献一半、再由 §3.4 拼成 Adam 的分层方式一致；配合 §3.5「AdamW 修了什么」，就能看清「组合」与「修正」必须分开做 |

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
