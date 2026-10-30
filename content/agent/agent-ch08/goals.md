# agent-ch08 · Transformer 核心机理：能白板推一遍才算懂

> 对应图片 DAY 19（B 站王树森解析）· 先修：agent-ch03（模型接入与 DeepSeek 实操）· 面试权重：★★★★☆
> 说明：面试官不问你「Transformer 是什么」，而问「注意力为什么除 √d_k」、「KV Cache 显存怎么算」、
> 「Pre-LN 和 Post-LN 差在哪」。这一章的目标是**白板讲清 + 落到数字 + 能跑通代码**。

## 本章目标

学完你应该能：

1. **白板画出并讲清完整前向链路**：tokenizer → embedding → 位置编码 → 注意力（QKV）→
   残差与 LayerNorm → FFN → 输出层与采样，说清每一步张量形状怎么变、信息在哪一步被混合。
2. **用 numpy 手写单头与多头缩放点积注意力，以及 2 层 Transformer 前向**：验证注意力权重
   每行和为 1、缩放能抑制 softmax 饱和、多头在 `H=1` 时退化为单头（参数量不变）。
3. **用 nanoGPT 在玩具数据上跑通一次训练**：能读取 train/val loss 曲线，指出收敛点、
   val loss 最低点与过拟合拐点，能解释「为什么曲线初期陡降、后期平台」。
4. **算一遍参数量与 KV Cache 显存账本**：给定模型维度、层数、头数、序列长度、批量，
   把「长上下文为什么贵」落到具体 GB 数字，并比较 MHA / GQA / MQA 三者的显存差异。
5. **说清采样参数与学科边界**：给定 temperature / top-p，能预测其对输出多样性与稳定性的影响；
   能明确说出本章与 `ai` 学科的分工——本章只要求「白板讲清 + numpy 复现核心」。

## 关键认知（本章最值钱的三句）

- **注意力不是「相似度」，是「用相似度做加权求和」**：softmax 之前的点积只是**分数**，
  真正的信息流动发生在 `softmax(·)V` 这个加权和里。QK 决定「看哪里」，V 决定「取什么」。
  只盯着 QK 相似度理解注意力，会漏掉最关键的 V 投影。
- **缩放因子 √d_k 是为了救梯度**：点积的方差随维度 `d_k` 线性增长，维度一大，softmax 输入
  被推到饱和区，梯度趋近 0。除以 √d_k 把方差拉回 1，是「让训练不崩」而非「让结果更准」。
- **长上下文的贵来自两根曲线**：注意力计算的 O(n²) 与 KV Cache 显存的 O(n)（按层与头数放大）。
  所有工程优化（RoPE、GQA、MQA、FlashAttention）本质都是在给这两根曲线做减法，
  而不是提升「模型变聪明了」。

## 技术交付物（来自 manifest.tech_load）

**交付物一：numpy 手写单头 / 多头注意力与前向**
- 单头缩放点积注意力：输入 Q/K/V，输出加权 V，验证 `Σ_j α_ij = 1`。
- 多头：拆分 → 各头独立注意力 → 拼接 → 输出投影；验证 `H=1` 时退化为单头且参数量一致。
- 因果 mask：验证「遮住未来 token 后，前缀输出不变」。
- 对应示例 ex01 / ex02 / ex03。

**交付物二：用 nanoGPT 跑通一次训练并解释 loss 曲线**
- 在玩具语料上训练一个字符级 2 层模型，loss 从 `ln(V)` 附近下降；
- 能读取训练曲线，指出 train/val 收敛位置、val 最低点、过拟合拐点；
- 对应示例 ex10（受「禁止联网下载 nanoGPT」约束，示例用 numpy 复刻同构的训练循环，
  真实接入 nanoGPT 仓库见下方 GitHub 资源）。
- 验收口径：给出 loss 随 step 下降的曲线图（或文本折线），并写清楚每一段代表什么。
## 与 ai 学科的分界

`ai` 学科负责 Transformer 的**完整数学推导与源码级实现**：注意力复杂度的严格证明、
旋转位置编码的矩阵形式、LoRA 的低秩分解、各类 attention 变体的梯度推导。

本章**只要求「能白板讲清 + numpy 复现核心」**：你不必推导 RoPE 的等价旋转矩阵，
但要能在白板上写出 `softmax(QKᵀ/√d_k)V` 并解释每个符号；不必读通 FlashAttention 的
CUDA 实现，但要能算出 KV Cache 的显存账本。遇到「为什么这样设计」的深层机理，
回 `ai` 学科追推导；本章停在「够用即止的原理 + 工程判据 + 可运行产物」。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) | 64,145 | 全章 | 200 行级 GPT 训练脚本，把 Transformer 从公式变成可运行的张量；本章先读与「注意力在算什么」「为什么要缩放 √d_k」相关的部分 |
| 2 | [karpathy/build-nanogpt](https://github.com/karpathy/build-nanogpt) | 5,577 | 全章 | 逐行重写 GPT-2 的视频配套仓库，适合跟着敲一遍；本章先读与「注意力在算什么」「为什么要缩放 √d_k」相关的部分 |
| 3 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,241 | 全章 | 工业级模型库，读 modeling_*.py 看真实实现与论文的差异；本章先读与「注意力在算什么」「为什么要缩放 √d_k」相关的部分 |
| 4 | [jingyaogong/minimind](https://github.com/jingyaogong/minimind) | 64,067 | 全章 | 从零训练 26M 小模型的全流程，算力有限时最好的练手项目；本章先读与「注意力在算什么」「为什么要缩放 √d_k」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | 全章 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（手写单头缩放点积注意力）核对 |
| 2 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex02`（手写多头注意力）核对 |
| 3 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | 全章 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex03`（因果 mask 验证）核对 |
| 4 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | 全章 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex04`（位置编码对比）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
