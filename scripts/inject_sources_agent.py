# -*- coding: utf-8 -*-
"""批次一 · 来源颗粒度补齐：agent 16 章

背景
----
`scripts/audit_sources.py` 只能查出「同一学科内 github_notes 完全相同的章」
（=`route_key` 重复），查不出**内容泛泛**的情况。agent 16 章的 notes 都是
「这是什么」型：比如「12 周 24 课的 AI 通识课，用来补齐术语」——
读者看完仍不知道该打开哪个文件、读哪一段、能验证本章哪条结论。

对照已合格的章（cpp-ch01/03/04、fullstack-ch02/03）的写法：

    §2.2 box-sizing 规范原文：`css-box-3/Overview.bs` 里 box-sizing 与
    margin 合并的定义——「margin 为什么穿透父元素」在这里是写死的

三要素齐全：
  1. **§小节号**：指向本章 concept 的真实小节（可被 audit 的 RE_SECTION 识别）
  2. **入口文件/目录**：反引号包住，读者能直接去仓库里找到
  3. **证明什么**：这一处能验证本章哪条结论，而不是这个仓库大概讲什么

要改**两个地方**（漏一个就等于没改）
------------------------------------
1. `content/agent/_manifest.json` 的 `resources.github_notes`
   —— 机器可读的事实来源，`route_key` 用它判重。
2. `content/agent/<ch>/goals.md` 的「## 本章 GitHub」表格
   —— 读者真正看到的页面。原表格「对应本章」一列全填「全章」，
   且「读什么」末尾机械追加「；本章先读与「X」「Y」相关的部分」，
   同一句在两个仓库上重复——这就是学科级复制的指纹。

表结构（agent 16 章一致）：
    | # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |

改写后：
    对应本章 ← 该 repo 那条 note 的 §小节号部分（note 里 ` · ` 之后是第二节小节号，取第一个）
    读什么   ← 该 repo 那条 note 的「`文件` + 证明什么」部分

实现上不硬拆字符串，而是让 NOTES 的每条写成
    "<对应本章> · <读什么>"
脚本按 ` · ` 切开，前半进「对应本章」，后半进「读什么」。
这样两处永远同源，不会各写一套而对不上。

写盘格式
--------
`_manifest.json` 是 `indent=2` + **CRLF**（实测 1509 个 `\r\n`），
与 `labs.json` 的 `indent=1` + LF 完全不同。用错会让 1500 行文件整份假 diff。
`goals.md` 是普通 LF 文本，逐行替换，不动其他内容。
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
AGENT_DIR = os.path.join(ROOT, "content", "agent")
MANIFEST = os.path.join(AGENT_DIR, "_manifest.json")

# GitHub 资源表行：| n | [owner/repo](url) | 12,345 | 对应本章 | 读什么 |
RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

NOTES = {
    # ── ch01 行业价值链与岗位地图 ────────────────────────────────────────
    "agent-ch01": [
        "§1.四层结构（算力→模型→推理服务→应用） · §4.一次请求的钱怎么分："
        "`lessons/` 里每课都有可跑的 notebook，重点看「成本/延迟」那几课的账单表格——"
        "把「一次请求的钱如何在四层之间分」算成算式，而不是记结论",
        "§1.四层结构 · §3.为什么应用层岗位最多却存活率最低："
        "`README.md` 的 Train / Inference / Evaluation 分区就是价值链分层的索引，"
        "顺着分区看每个方向有哪些在维护的仓库，能判断「这个方向还有没有坑」",
        "§2.JD 拆解成四层信号 · §5.把岗位地图变成可验证的表："
        "`docs/` 下有部署与微调的完整命令（vllm/llama-factory 两条线），"
        "按它的步骤跑通一次私有化，才知道「推理服务层」岗位在交付什么",
        "§5.把岗位地图变成可验证的表 · §5.用代码验证而不是背结论：`docs/` 收录了评估、监控、组织协作的工业案例，"
        "看它「模型之外」的衡量口径，正好补本章「岗位不只考模型」那一条",
    ],
    # ── ch02 Prompt 工程 ────────────────────────────────────────────────
    "agent-ch02": [
        "§1.四段式（角色/任务/约束/示例） · §3.少样本怎么选："
        "`pages/techniques/` 每个技巧一页，页面底部都挂着原论文链接——"
        "「这个技巧凭什么有效」去论文里找，别只背模板名",
        "§2.结构化输出的三种机制 · §2.输出契约怎么写才不容易坏："
        "`examples/` 下 function calling / structured outputs 的 notebook 直接可跑，"
        "照它的 schema 写一遍，就看懂「JSON mode / 函数调用 / 严格 schema」三者的差别",
        "§2.流式输出不要等最后一个括号 · §1.上下文预算："
        "`misc/` 里有 streaming 与 prompt caching 的 notebook，"
        "运行一遍能看清「流式解析为什么要在最后一个括号前就开始处理」",
        "§1.四段式与指令优先级 · §1.Prompt 也是代码（版本/测试/回滚）：`promptflow/` 目录把 prompt 当节点做"
        "版本与批量评测，这正是本章「把 prompt 纳入 CI」那一条的工程实现",
    ],
    # ── ch03 模型接入 ──────────────────────────────────────────────────
    "agent-ch03": [
        "§2.前缀缓存（唯一条件是前缀逐字节稳定） · §3.按请求计费三档单价："
        "`README.md` 的 API 参数表里 `cache_hit` / `cache_miss` 两个单价是分开列的，"
        "把命中率代进去算一遍，就明白本章「缓存命中省的是哪一笔」",
        "§3.推理能力从哪来 · §5.单位成本的三个杠杆："
        "`inference/` 目录下的推理代码与技术报告里的训练/推理成本拆分，是「MoE 为何能把成本压下来」的第一手依据，"
        "别只看二手解读",
        "§3.错误码分类（先决定能不能重试） · §6.兼容层形状兼容≠语义兼容："
        "`README` 的「OpenAI 兼容」一节列了哪些字段对齐、哪些没对齐，"
        "这正好是本章「换一家 API 不是改个 base_url」的证据",
        "§5.混合路由 · §5.降级链路（逐级退到可用）："
        "`README` 的模型列表带参数量与量化格式，对照本章的「本地能替到哪一步」"
        "逐档验证：哪一档是 7B-Q4 跑得动的，哪一档必须上云",
    ],
    # ── ch04 需求与产品定义 ────────────────────────────────────────────
    "agent-ch04": [
        "§1.用户故事三段式是责任链 · §4.范围冻结："
        "`docs/` 的 case study 每篇都写了「做了什么 / 没做什么」，"
        "拿它对照本章「不做什么清单」，能看到真实项目是怎么砍范围的",
        "§3.AI 适用性四档 · §5.需求-能力匹配矩阵："
        "`app/backend/approaches/` 下并排放着 chat / ask / one-shot 三种实现，"
        "同一个问题三种答法，正好用来标「这件事属于哪一档」",
        "§5.指标三层不要混在一起 · §3.失败模式设计："
        "`notebooks/` 从数据校验到部署监控逐段推进，"
        "它的监控指标分层就是本章「离线/线上/护栏」的落地版",
        "§2.画布九格 · §4.人工接管触发条件："
        "`lessons/` 每课末尾的「进一步学习」与练习，是在逼你想「这个功能失败时用户看到什么」，"
        "与画布的「失败兜底」格一一对应",
    ],
    # ── ch05 RAG ──────────────────────────────────────────────────────
    "agent-ch05": [
        "§数据·主题二 切块策略（固定长度/语义块/父子块） · §检索·主题二 RRF 融合："
        "`libs/text-splitters/` 里每种切块器都是独立类且带参数说明，"
        "把它和 `libs/retrievers/` 的 ensemble retriever（RRF）接起来跑，"
        "就能实测「重叠多少、块多大」对召回的影响",
        "§数据·主题一 文档解析三道坎 · §检索·主题三 查询改写："
        "`llama-index-core/` 的 node parser 与 query transform 是分开的两层，"
        "读这两层的接口边界，就看懂「解析/切块」与「改写/召回」为什么不该耦合",
        "§检索·主题一 BM25 与向量为什么必须混合 · §评估·主题一 Recall@K/MRR："
        "`rag/app/` 里每种 RAG 流都带可视化，直接调参对照「纯向量 vs 混合」的召回差异，"
        "比看论文曲线直观",
        "§检索·主题三 多跳与图增强 · §评估·主题三 引用溯源："
        "`LightRAG` 的实体关系抽取与 chunk 溯源字段，是本章「实体关系补向量短板」"
        "和「引用必须可回溯到块」两条的同时落地",
    ],
    # ── ch06 推理部署 ─────────────────────────────────────────────────
    "agent-ch06": [
        "§01 显存四笔账 · §02 PagedAttention："
        "`vllm/core/` 里 block_manager 把 KV Cache 切成固定块管理，"
        "读它就知道「显存碎片」为什么能被 PagedAttention 吃掉——"
        "这是本章显存账本最后一笔账的代码证据",
        "§02 连续批处理 · §02 TTFT/TPOT/吞吐是三件事："
        "`benchmarks/` 下的脚本同时输出 TTFT、TPOT 与吞吐，"
        "换 batch size 跑两轮，就能看到本章「三者互相牵制」的实测曲线",
        "§01 量化省的是权重那笔账 · §01 显存的四笔账："
        "`ggml/src/` 里各量化类型的反量化 kernel 一目了然，"
        "对照本章「Q4 省 4 倍但激活不变」，就明白为什么长上下文量化救不了",
        "§03 多租户配额 · §03 容器化与灰度："
        "`README` 的部署矩阵列出各后端与硬件组合，"
        "按它跑一次本地服务，能实测本章「显存是第一约束」这句话",
    ],
    # ── ch07 微调 ─────────────────────────────────────────────────────
    "agent-ch07": [
        "§02 LoRA 低秩分解 ΔW=BA · §02 rank/alpha 怎么选："
        "`src/peft/tuners/lora/layer.py` 里 `scaling = alpha / r` 是写死的，"
        "读这一行就懂本章「只翻 rank 不调 alpha 等于改了有效学习率」——"
        "不是经验，是代码",
        "§03 数据配比与去重 · §03 对话模板与 loss mask："
        "`examples/` 下每种任务都有数据格式样板，`data/` 里 dataset_info 标了字段含义，"
        "照它的格式准备一份，就知道「只让 assistant 段产生梯度」在数据层怎么表达",
        "§02 QLoRA 4bit NF4 + 双重量化 · §02 显存账本："
        "`src/` 里 NF4 量化与双重量化的实现集中在 quant 相关模块，"
        "对照本章显存账本逐项核对，能算出「单卡 24G 能微调多大的模型」",
        "§03 过拟合识别与失败归因 · §01 什么时候不该微调："
        "`trl` 的 trainer 默认就带 eval 与早停钩子，"
        "看它记录哪些曲线，正好对应本章「过拟合怎么被发现」",
    ],
    # ── ch08 Transformer 内部 ─────────────────────────────────────────
    "agent-ch08": [
        "§03 FFN 是键值记忆 · §03 参数量账本："
        "`model.py` 全文不到 300 行，`CausalSelfAttention` 与 `MLP` 两个类把"
        "「QK 决定看哪里、V 决定取什么」和「FFN 两层线性之间塞词典」写成了可跑的张量",
        "§01 注意力在算什么 · §02 为什么要缩放 √d_k："
        "`model.py` 里 `att / math.sqrt(self.head_dim)` 这一行就是本章缩放那节的答案，"
        "注释里直接写了「不缩放 logits 会饱和」",
        "§02 Pre-LN vs Post-LN · §04 因果 mask："
        "`model.py` 的 forward 里先 `ln_1` 再 attention（Pre-LN），"
        "`bias` 用上三角 -inf 做 causal mask，两处都是本章结论的逐行实现",
        "§03 KV Cache 显存账本 · §03 采样参数："
        "`modeling_*.py` 里 `past_key_value` 的拼接逻辑与 generate 的 temperature/top_p"
        "处理，是本章「长上下文贵在哪」与「采样参数只调分布不改模型」的工业版对照",
    ],
    # ── ch09 多模态 ───────────────────────────────────────────────────
    "agent-ch09": [
        "§01 图像分块与 patch embedding · §01 token/显存账本："
        "`src/diffusers/pipelines/` 下每个 pipeline 都把「分块→编码→解码」拆成独立步骤，"
        "对照本章 patch 数公式，能算出「分辨率翻倍 token 翻四倍」",
        "§03 CLIP 双塔与跨模态检索 · §03 对齐空间里检索为什么成立："
        "`model.py` 里 `encode_image` / `encode_text` 两个独立塔 + 末尾归一化后的点积，"
        "整个「对齐空间里检索为什么成立」就这几十行",
        "§03 扩散生成可控性 · §03 两个工程接口（scheduler / guidance）："
        "`modules/` 下 scheduler 与 guidance 是分开的插件，"
        "换 scheduler 不改模型、调 guidance_scale 不改权重——"
        "这就是本章「两个工程接口」的分界",
        "§02 OCR 两条路线 · §02 字段级准确率（混淆矩阵）："
        "`README.md` 的模型卡标了各尺寸在文档理解类基准上的分数，"
        "拿它对照本章「字符对不等于字段对」，就知道该看哪个指标",
    ],
    # ── ch10 评估 ─────────────────────────────────────────────────────
    "agent-ch10": [
        "§01 黄金集分层抽样 · §01 指标分层（离线/线上/护栏）："
        "`evals/elsuite/` 下每个 suite 都是一套可复现的评分器，"
        "把本章「黄金集要版本化」落成 registry 里的固定条目",
        "§02 judge 的偏差谱系 · §02 两种口径与 kappa 校准："
        "`lm_eval/tasks/` 里每个任务都写了 metric 与 fewshot 口径，"
        "换口径重跑同一条目得到不同分数——这就是「口径必须随分数一起记录」的证据",
        "§01 指标分层 · §02 忠实度/答案完整率："
        "`ragas/metrics/` 里 faithfulness 被拆成「拆句→逐句验证→比例」三步，"
        "读源码比记定义更能理解「为什么忠实度可以自动化」",
        "§03 A/B 样本量先算后跑 · §03 不确定性与错误可恢复："
        "`lessons/` 每课的评测小节都把「这个结论基于什么样本」写清楚，"
        "正可用于本章「没有样本量说明的结论不可信」",
    ],
    # ── ch11 Agent 编排 ───────────────────────────────────────────────
    "agent-ch11": [
        "§02 检查点、断点续跑与状态机建模 · §03 终止条件与死循环防护："
        "`libs/langgraph/` 的 graph + checkpointer 是本章「有状态编排」的直接实现，"
        "读 `checkpoint/` 的存储接口，就懂「断点续跑」靠什么落盘",
        "§03 角色分工 · §03 成本爆炸："
        "`autogen-core/` 里 agent 之间的消息协议与终止条件都显式定义，"
        "对照本章「多智能体的成本随角色数超线性增长」",
        "§03 共享黑板 · §03 多智能体的 handoff："
        "`crew.py` 里 Task 的 `context` 参数就是「共享黑板」的落点，"
        "读它如何把上游产出注入下游，就懂本章「角色分工靠数据流而非提示词」",
        "§01 工具 schema 与参数校验 · §01 幂等与副作用："
        "`openai-agents/` 的 handoff / guardrail / tracing 三个钩子各管一件事，"
        "其中 guardrail 是本章「重试不能让副作用叠加」的兜底层",
        "§01 权限最小化与沙箱 · §01 MCP 的工具发现："
        "`src/mcp/server/` 里 `list_tools` 与 `call_tool` 是两个分离的 RPC，"
        "schema 校验发生在执行前——正是本章「把自由发挥拦在执行前」的协议证据",
        "§03 多智能体：SOP 如何被编码进角色 · §03 终止条件："
        "`metagpt/roles/` 每个角色类都带 `_observe` / `_think` / `_act` 三段，"
        "把本章「角色 = 职责 + 可用动作 + 终止条件」落成了类结构",
    ],
    # ── ch12 商业化 ───────────────────────────────────────────────────
    "agent-ch12": [
        "§01 三种计费模式 · §02 单次任务成本四元组与报价下限："
        "`api/` 目录里 workflow 的节点即计费单元，"
        "把一次运行的节点数 × 单节点 token 算一遍，就是本章「报价下限」的算式",
        "§03 POC→试点→推广三段式 · §03 竞品对比矩阵："
        "`packages/` 里每家集成（模型/存储/工具）都是可替换的适配器，"
        "这正好支撑本章「交付时按客户预算换供应商而不改架构」",
        "§02 固定成本与规模效应 · §02 超支归因："
        "`app/backend/approaches/` 三种答案生成策略的成本差异很大，"
        "对照本章「同一功能选不同策略，毛利差一个量级」",
        "§01 毛利率不是净利率 · §01 毛利诊断三个误判："
        "`azd up` 脚本把 RAG 应用从数据到部署全链路串了一遍，"
        "跟着算一遍自己的账单，就会发现本章「按 token 计价的幻觉」",
    ],
    # ── ch13 论文阅读与技术雷达 ──────────────────────────────────────
    "agent-ch13": [
        "§01 信息源分层与可信度排序 · §01 三遍读法："
        "`README` 按会议/年份归档的精读列表就是「可信度分层」的现成样本，"
        "跟着它的顺序读三篇，能校准本章「先读什么后读什么」的节奏",
        "§01 三遍读法带止损 · §02 指标对齐与差异归因："
        "`README.md` 每周榜单里的论文都附一句话结论，"
        "拿它对照自己三遍读完的判断，就知道「摘要骗人」具体骗在哪",
        "§03 四象限与打分 · §03 把雷达变成团队语言："
        "`README` 的训练/推理/应用/评测四个分区正好对应本章四象限，"
        "把分区里的仓库挪到象限里，雷达就不是画着好看的图",
    ],
    # ── ch14 能力矩阵与路径 ──────────────────────────────────────────
    "agent-ch14": [
        "§01 BARS 行为锚定等级 · §02 JD 关键词反推能力要求："
        "`README` 的面试题按主题归档，每道题背后就是一条能力要求，"
        "把题翻成「矩阵里的哪一格」，本章的方法就有了练习对象",
        "§03 作品集 STAR-R 结构 · §03 量化指标三要素："
        "`behavioral/` 与 `system-design/` 两卷的答题范例都带「结果如何量化」，"
        "照它的写法改自己的项目描述，能立刻看出缺的是基线还是归因",
        "§02 四条路径的技能栈 · §01 自评的证据要求："
        "`ML-Interviews` 里按岗位分的章节直接给出各路径的考点集合，"
        "对照本章四条路径，能判断自己缺的是「知识」还是「证据」",
        "§01 自评为什么人人偏高 · §03 用一张表判 STAR-R 强弱："
        "`chiphuyen` 的面试书把「你是否真的做过」拆成可追问的层级，"
        "拿它的追问链自测一遍，就等于做了一次本章的强弱判定",
    ],
    # ── ch15 项目实战 ────────────────────────────────────────────────
    "agent-ch15": [
        "§01 选题评分卡（真实用户/明确痛点/3 周可完成） · §01 关键路径拆解："
        "`docs/` 的案例都标了实现周期与团队规模，"
        "对照本章「3 周可完成性」判定，能校准自己对工作量的估计",
        "§02 基线的意义 · §02 错误分析驱动迭代（按损失排序）："
        "`app/backend/approaches/` 的三种策略天然构成 A/B 对照，"
        "先跑一份最简基线再迭代，这就是本章「回归安全带」",
        "§03 监控面板四指标 · §03 成本看板与预算告警："
        "`infra/` 下的 Application Insights 指标与告警模板，"
        "正是本章「把烧钱速度变成数字」的现成实现",
        "§03 容器化与一键启动 · §03 文档四件套："
        "`azd` 一键部署脚本与 README 的架构图，"
        "是本章「可复现是交付的定义」最省事的范本",
    ],
    # ── ch16 求职冲刺 ────────────────────────────────────────────────
    "agent-ch16": [
        "§02 系统设计：知识库 Agent 的容量账本与分层架构 · §01 STAR-R 一页纸："
        "`system-design-primer` 里容量估算章节给出了「先算 QPS 与存储再画图」的模板，"
        "套到本章的知识库 Agent 上，容量账本就不是凭感觉写的",
        "§02 八股高频题从背定义到给判断 · §03 三道手写题："
        "`technical-interview-handbook` 的追问链把「背了定义」和「能下判断」分开，"
        "拿它的追问自测，就知道自己停在哪一层",
        "§02 系统设计手写题 · §02 行为面："
        "`ML-Questions` 按 LLM/ML 岗位分类，每类都带系统设计题，"
        "与本章「三道手写题 + 行为面」正好对得上",
        "§03 前 30 天读代码与小切口 · §03 转正答辩证据链："
        "`chiphuyen` 把「入职后如何证明价值」拆成可执行动作，"
        "是本章「把试用期讲成留任理由」的对照读物",
    ],
}


def split_note(note: str) -> tuple[str, str]:
    """把 "<对应本章> · <读什么>" 拆成两栏。

    note 形如：
        §1.四层结构（算力→模型→推理服务→应用） · §4.一次请求的钱怎么分：
        `lessons/` 里每课都有可跑的 notebook，……

    以第一个 " · " 为界：前半进「对应本章」列，后半进「读什么」列。
    找不到分隔符就整条当「读什么」，对应本章写「全章」（退化为旧格式，
    但脚本会打印警告，方便发现写错的条目）。
    """
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(ch_dir: str, cid: str) -> tuple[bool, str]:
    """重写一章 goals.md 里「## 本章 GitHub」小节下连续的 `| n |` 表格行。

    只动 GitHub 小节：B 站小节的行格式与 GitHub 表一模一样（同样 5 列），
    全文件扫会把视频说明也覆盖掉——这是先前踩过的坑。
    """
    path = os.path.join(ch_dir, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"

    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    notes = NOTES.get(cid) or []
    n_hit = 0
    # 定位「## 本章 GitHub」小节的范围：从该标题行到下一个 "## " 标题
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = 0
    for i in range(start, end):
        m = RE_GH_ROW.match(lines[i])
        if not m:
            continue
        num, name, url, star, _old_corner, _old_read = m.groups()
        if row_idx >= len(notes):
            # 表格行比 notes 多，后面的保持原样（正常不会发生）
            row_idx += 1
            continue
        corner, read = split_note(notes[row_idx])
        lines[i] = f"| {num} | [{name}]({url}) | {star} | {corner} | {read} |"
        n_hit += 1
        row_idx += 1

    if n_hit == 0:
        return False, "GitHub 表格没匹配到任何行"

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return True, f"表格 {n_hit} 行"


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)

    chapters = data.get("chapters") or []
    by_id = {c.get("id"): c for c in chapters}

    n = 0
    for cid, notes in NOTES.items():
        c = by_id.get(cid)
        if not c:
            print(f"!! 找不到章节 {cid}")
            continue
        res = c.setdefault("resources", {})
        repos = res.get("github") or []
        if len(repos) != len(notes):
            # 条数与仓库数必须一致，否则读者会把 note 对错仓库
            print(f"!! {cid} 仓库 {len(repos)} 个、notes {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        n += 1

        # 同步 goals.md 的表格：机器源与读者看到的页面必须同源，
        # 只改 manifest 不改 md 的话，页面上还是「全章 + 机械追加句」
        ok, msg = rewrite_goals_table(os.path.join(AGENT_DIR, cid), cid)
        mark = "✓" if ok else "✗"
        print(f"  {cid:<12} {len(notes)} 条 · {mark} {msg:<12} · 首条 {notes[0][:26]}…")

    # 换行格式**按学科探测**：agent/ml/cpp 是 CRLF，其余 11 个学科是 LF。
    # 写死任一种都会让另一种学科整份假 diff，这里统一读一次原文件判断。
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {os.path.normpath(MANIFEST)}，共更新 {n} 章")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
