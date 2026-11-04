# agent-ch07 · 轻量化微调：LoRA / QLoRA 与数据工程

> 对应图片 DAY 13（Hugging Face PEFT 教程）· 先修：agent-ch06（私有化部署与推理服务）· 面试权重：★★★★☆
> 说明：面试官不问「怎么跑通一个 LoRA」，而问「数据只有 500 条该不该微调、rank 怎么选、留出集 82→87 算不算提升、微调后旧能力掉了怎么救」。

## 本章目标（5 条，动词开头，可检验）

1. **用一张决策表判断「该不该微调」**：能按知识更新频率、是否需要溯源、是否只改行为/风格、月请求量与成本，给出「微调 / RAG / 两者组合」的结论，而不是凭感觉。
2. **跑通一次 LoRA 训练脚本并说清每个旋钮**：写出挂载层、rank、alpha、学习率、epoch 的选择依据；能用 ex02 的参数量计算器说明「rank 翻倍参数量涨几倍、有效学习率怎么变」。
3. **用显存账本把「24GB 单卡能不能跑」说清楚**：按「权重 / 适配器 / 优化器 / 激活」四项逐项算，先开梯度检查点与降 seq，再降 rank，给出 QLoRA 双重量化 vs 全参的对比（对应 ex03）。
4. **交付一条可复现的数据流水线**：覆盖数据配比（在可行域搜而非拍比例）、MinHash+LSH 去重、对话模板与 loss mask、留出集切分，且每个环节有可量化判据（对应 ex04/05/06）。
5. **用留出集做「微调前/后」对比并归因失败**：报告必须包含准确率 + Bootstrap 置信区间 + n（ex09），用 McNemar 判断提升是否显著；过拟合/灾难遗忘有早停与 replay 的应对（ex07/08）。

## 关键认知（本章最值钱的三句）

- **LoRA 省的是「增量 ΔW 的自由度」，不是「基座 W 的秩」**：真实微调增量常呈长尾谱，所以 r=8~16 往往够用（ex01）；若小 rank 怎么都学不会，先怀疑数据/任务定义，而不是盲目加 rank。
- **账本里最先爆的通常不是权重而是激活**：QLoRA 把 7B 权重从 13.5GB 压到 3.6GB，省下的空间全给了激活与 batch；所以救 OOM 的顺序是「先开梯度检查点 → 降 seq → 最后才降 rank」（ex03）。
- **留出集 82%→87% 在 200 条上往往只是噪声**：95% 区间约 ±5pp，2.5pp 的提升完全落在噪声里（ex09）。「模型变好了」必须用配对 Bootstrap / McNemar + 置信区间来证明，不能只报点估计。

## 技术交付物（来自 manifest.tech_load）

**LoRA/QLoRA 训练脚本 + 数据清洗 + 留出集前后对比 + 失败案例归因**。

验收口径（对应 project.json 的任务）：

- 一份可复现的训练脚本（挂载 q/k/v/o、rank=16、alpha=32、固定随机种子），在单卡 24GB 预算内跑通，显存峰值可解释；
- 一条数据流水线：配比在「来源×类别」可行域搜索（非来源比例拍脑袋）、MinHash+LSH 去重 + 精确 Jaccard 阈值校准、对话模板与 loss mask 正确（prompt 段不计入梯度）；
- 一个留出集（≥200 条，建议 700+）与「微调前/后」评估脚本，输出准确率 + 95% 置信区间 + 配对 McNemar 判定；
- 一份失败案例归因报告：过拟合（val/train 间距比）、灾难遗忘（旧任务掉分）、数据泄漏/重复导致的虚高，各给 1 个真实修复动作。
## 与 ai 学科的分界

`ai` 学科推导 LoRA 的矩阵分解、NF4 量化的舍入误差、反向传播的数值细节；本章**不推导这些内部**，只把 LoRA/QLoRA 当成「在已部署基座上追加一个低秩适配器的工程手段」来用。需要理解「为什么 r=16 通常够用」时，回 `ai` 学科看低秩近似的谱衰减；本章只给工程结论：增量是低秩的、显存要给激活留余地、留出集要带置信区间。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [huggingface/peft](https://github.com/huggingface/peft) | 21,852 | §02 LoRA 低秩分解 ΔW=BA | §02 rank/alpha 怎么选：`src/peft/tuners/lora/layer.py` 里 `scaling = alpha / r` 是写死的，读这一行就懂本章「只翻 rank 不调 alpha 等于改了有效学习率」——不是经验，是代码 |
| 2 | [hiyouga/LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) | 76,000 | §03 数据配比与去重 | §03 对话模板与 loss mask：`examples/` 下每种任务都有数据格式样板，`data/` 里 dataset_info 标了字段含义，照它的格式准备一份，就知道「只让 assistant 段产生梯度」在数据层怎么表达 |
| 3 | [unslothai/unsloth](https://github.com/unslothai/unsloth) | 78,352 | §02 QLoRA 4bit NF4 + 双重量化 | §02 显存账本：`src/` 里 NF4 量化与双重量化的实现集中在 quant 相关模块，对照本章显存账本逐项核对，能算出「单卡 24G 能微调多大的模型」 |
| 4 | [huggingface/trl](https://github.com/huggingface/trl) | 19,561 | §03 过拟合识别与失败归因 | §01 什么时候不该微调：`trl` 的 trainer 默认就带 eval 与早停钩子，看它记录哪些曲线，正好对应本章「过拟合怎么被发现」 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | §1.2 微调 vs RAG 判定树 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（低秩近似的参数量与误差）核对 |
| 2 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | §1.2 微调 vs RAG 判定树 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex02`（LoRA 参数量计算器）核对 |
| 3 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex03`（QLoRA 显存账本）核对 |
| 4 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | 全章 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex04`（MinHash + LSH 去重）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
