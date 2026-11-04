# agent-ch05 · RAG 技术精讲：检索质量决定回答上限

> 对应图片 DAY 9（LangChain 中文教程）· 先修：agent-ch03（模型接入与 DeepSeek 实操）· 面试权重：★★★★☆
> 说明：面试官不会问你「怎么调 LangChain」，而是问「召回率 90% 但答案错，你先改哪一层」——检索质量是回答的上限，生成只是放大器。

## 本章目标

学完你应该能：

1. **把 RAG 当成一条数据管线来设计**：说清「文档解析→切块→向量化→混合检索→重排→生成→引用」每一段丢什么、错什么，
   而不是把 LangChain 当黑盒串起来；能画出一条请求的端到端延迟与失败分布。
2. **为不同文档类型选切块策略**：对 PDF 版面/表格/扫描件分别给出解析与切块方案，
   解释固定长度、语义块、父子块各自的召回代价，并量化「重叠窗口」与「碎片率」的取舍。
3. **搭一个可解释的混合检索**：用 BM25 + 向量做召回，用 RRF 融合，再用 cross-encoder 重排，
   并说清双塔召回与 cross-encoder 重排的延迟/精度分工，以及为什么重排通常卡在 Top-20 以内。
4. **用指标而非体感评估 RAG**：定义并算对 Recall@K、MRR、nDCG、答案完整率、忠实度、拒答率，
   能区分「召回到了但模型没用上」与「压根没召回」两类失败，并据此决定改检索还是改提示。
5. **把权限过滤与拒答写进检索层**：实现权限前置过滤（pre-filter）、查询改写、引用对齐与拒答阈值，
   给出「误答比拒答更贵」的工程账，并设计一条可回放、可审计的检索-生成链路。

## 关键认知（本章最值钱的三句）

- **RAG 的收益 80% 来自数据侧**：同样的生成模型，切块与元数据设计差一档，召回率可能从 95% 掉到 60%；
  而把重排模型从 cross-encoder 换成更强的，上限通常只动几个点。先修数据，再修检索，最后才动模型。
- **召回率不能只看 Top-K 命中**：一条问答对的「黄金证据」若被切成 3 块、只命中 1 块，Top-5 命中率是 100%
  但可用上下文只有 1/3——这种「命中但不可用」比「完全没命中」更隐蔽，必须用片段级召回与答案完整率补刀。
- **知识更新与权限必须落在检索层**：把「谁能看什么」和「数据新鲜度」塞进生成提示词是治标；
  真正的做法是在向量索引里带租户/权限标签，检索时 pre-filter，过期文档不进索引，否则越权与 stale 答案迟早爆雷。

## 技术交付物（来自 manifest.tech_load）

**RAG 服务**：解析→切块→混合检索→重排→引用；30 条黄金集，输出 Recall@K / 忠实度 / 拒答率。

验收口径（对应 project.json 的任务）：

- 给定一批本地 PDF/文本，能跑通「解析→切块→建索引→问答→引用」全链路，不依赖任何外部 API；
- 切块策略可切换（固定长度 / 语义 / 父子块），并输出每种策略在 30 条黄金集上的 Recall@5 与答案完整率；
- 混合检索 = BM25 + 向量，用 RRF 融合；重排用 cross-encoder 风格的本地打分，仅作用于 Top-20；
- 检索层支持权限标签 pre-filter，租户 A 的查询不能返回租户 B 的片段；
- 输出每条问答的引用片段与对齐分数（Jaccard），并在无高置信证据时触发拒答；
- 提交一份 `report.md`：30 条黄金集的 Recall@K 曲线、忠实度、拒答率，以及一次「召回但答错」的归因。
## 与 ai 学科的分界

`ai` 学科讲 embedding 模型怎么训练、注意力怎么把 query 和 doc 对齐、对比学习的损失；本章**不训练也不推导编码器**，
只把 embedding 模型当成一个「给定文本返回定长向量」的黑盒服务来用。
需要理解「为什么向量检索召回率有上限」时，回 `ai` 学科看对比学习与表征空间；
本章只给工程结论：检索是预算，重排是精读，拒答是底线。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §数据·主题二 切块策略（固定长度/语义块/父子块） | §检索·主题二 RRF 融合：`libs/text-splitters/` 里每种切块器都是独立类且带参数说明，把它和 `libs/retrievers/` 的 ensemble retriever（RRF）接起来跑，就能实测「重叠多少、块多大」对召回的影响 |
| 2 | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 52,595 | §数据·主题一 文档解析三道坎 | §检索·主题三 查询改写：`llama-index-core/` 的 node parser 与 query transform 是分开的两层，读这两层的接口边界，就看懂「解析/切块」与「改写/召回」为什么不该耦合 |
| 3 | [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 92,592 | §检索·主题一 BM25 与向量为什么必须混合 | §评估·主题一 Recall@K/MRR：`rag/app/` 里每种 RAG 流都带可视化，直接调参对照「纯向量 vs 混合」的召回差异，比看论文曲线直观 |
| 4 | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | 40,252 | §检索·主题三 多跳与图增强 | §评估·主题三 引用溯源：`LightRAG` 的实体关系抽取与 chunk 溯源字段，是本章「实体关系补向量短板」和「引用必须可回溯到块」两条的同时落地 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · LangChain 入门与 Agent 实战<br><sub>尚硅谷</sub> | [BV1rv7A6oEeP](https://www.bilibili.com/video/BV1rv7A6oEeP/) | 全章 | 主线：模型接入 → Prompt 与结构化输出 → Chain/LangGraph 编排 → RAG → Agent 工具循环；看完回 `ex01`（两种切块的对照）核对 |
| 2 | 黑马程序员 · 大模型 RAG 与 Agent 智能体实战<br><sub>黑马程序员</sub> | [BV1yjz5BLEoY](https://www.bilibili.com/video/BV1yjz5BLEoY/) | 全章 | 工程视角：文档切分、向量化与召回、重排、评测；Agent 部分讲工具定义与失败重试；看完回 `ex02`（父子块）核对 |
| 3 | 吴恩达 · 大模型合集（Prompt 到 Agent）<br><sub>吴恩达大模型课程</sub> | [BV1nc31zzEa3](https://www.bilibili.com/video/BV1nc31zzEa3/) | 全章 | 方法论最正：Prompt 的四条原则、评估驱动开发、Agent 的反思与规划模式；看完回 `ex03`（手写 BM25）核对 |
| 4 | 提示词工程（Prompt Engineering）系统教程<br><sub>AIAgent开发</sub> | [BV1VEA8zYE6f](https://www.bilibili.com/video/BV1VEA8zYE6f/) | 全章 | 把 Prompt 当接口设计：角色/约束/示例/输出格式四要素，以及失败时的收敛手段；看完回 `ex04`（手写 TF-IDF 向量与余弦）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Prompt Engineering for LLMs》Berryman & Ziegler |
| 2 | 《Designing Machine Learning Systems》Chip Huyen |
| 3 | 《大语言模型应用开发》相关官方文档（OpenAI / DeepSeek API Docs） |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
