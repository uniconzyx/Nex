"""生成 AI Agent 学科的 _manifest.json（对齐图片「90 天 AI Agent 链路」18 个节点）。

设计原则
--------------------------------------------------------------------
1. **节点不丢**：图片里 DAY 1 / 3 / 5 / 7 / 9 / 11 / 13 / 19 / 24 / 30 / 35 / 40 /
   43 / 45 / 47 / 55 / 70 / 90 共 18 个节点，全部映射到 16 章（DAY 40+43、DAY 70+90
   各合并为一章，因为它们的产出物是同一份：行业方案 / 求职包）。
2. **项目来源是 GitHub**：每章 3-6 个仓库，star 数来自 `_agent_src/repos.json`
   （API 实测；6 个千位近似标 ≈）。不写 B 站 BV 号——视频会下架、BV 会变，
   统一用站内搜索入口 + 精确关键词，避免链接腐烂。
3. **与 ai 学科的边界**：ai 是技术纵深（Transformer 推导、微调原理、RAG 机制）；
   agent 是**交付链路**（怎么把能力变成能上线、能报价、能面试的项目）。
   同一主题在 agent 里只保留「够用即止 + 工程判据」，推导一律指回 ai。
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAP = ROOT / "server" / "scripts" / "_agent_src" / "repos.json"
OUT = ROOT / "content" / "agent" / "_manifest.json"

REPO_NOTES = {
    "microsoft/AI-For-Beginners": "12 周 24 课的 AI 通识课，用来快速补齐术语与全景，避免面试时概念串味",
    "Hannibal046/Awesome-LLM": "LLM 生态索引：训练/推理/应用/评测的仓库地图，用来判断「这个方向还有没有坑」",
    "datawhalechina/self-llm": "开源大模型部署与微调实战教程，中文、可复现，适合做第一个私有化 demo",
    "eugeneyan/applied-ml": "工业界 ML 落地案例合集，看「模型之外」的评估、监控、组织协作怎么写",
    "dair-ai/Prompt-Engineering-Guide": "提示工程体系化教材：技巧分类 + 论文出处，适合建立方法论而不是背模板",
    "openai/openai-cookbook": "官方 API 用法与结构化输出范例，照它写第一次 function calling",
    "anthropics/claude-cookbooks": "Claude 的工具调用、长上下文、评测 notebook，对照 OpenAI 的差异",
    "microsoft/promptflow": "提示流工程化：把 prompt 当代码做版本、测试、批量评测",
    "deepseek-ai/DeepSeek-V3": "DeepSeek 主力开源模型的技术报告与推理代码，理解成本为何能压这么低",
    "deepseek-ai/DeepSeek-R1": "推理模型 RL 训练范式，面试问「为什么 R1 会思考」时的第一手材料",
    "deepseek-ai/awesome-deepseek-integration": "官方集成清单：IDE/Agent/客服等落地形态，做选型时先看这里",
    "ollama/ollama": "本地一键跑模型，验证「私有化」可行性最快的路径",
    "Azure-Samples/azure-search-openai-demo": "RAG 端到端参考架构（含引用溯源），企业方案的常见骨架",
    "GokuMohandas/Made-With-ML": "从数据校验到部署监控的完整工程流水线，补「只会调 API」的短板",
    "langchain-ai/langchain": "RAG 组件全家桶，适合快速拼原型，也适合读源码理解抽象边界",
    "run-llama/llama_index": "以索引为中心的数据框架，文档解析与检索策略比 LangChain 更细",
    "infiniflow/ragflow": "带 UI 的 RAG 引擎，可直接对照「文档解析→切块→召回→重排」每一步的参数",
    "HKUDS/LightRAG": "轻量图增强 RAG，理解「实体关系」如何补向量检索的短板",
    "vllm-project/vllm": "生产级推理引擎：PagedAttention/连续批处理，部署章的性能基线",
    "sgl-project/sglang": "高吞吐推理框架，对比 vLLM 的调度与缓存策略",
    "ggml-org/llama.cpp": "CPU/量化推理的参考实现，理解 GGUF 与显存账本",
    "huggingface/peft": "LoRA/QLoRA 官方实现，微调章的核心工具",
    "hiyouga/LLaMA-Factory": "中文微调一站式工具，从数据格式到导出合并的完整链路",
    "unslothai/unsloth": "单卡微调加速，显存不够时的现实解",
    "huggingface/trl": "RLHF/DPO/GRPO 训练库，理解对齐阶段的工程接口",
    "karpathy/nanoGPT": "200 行级 GPT 训练脚本，把 Transformer 从公式变成可运行的张量",
    "karpathy/build-nanogpt": "逐行重写 GPT-2 的视频配套仓库，适合跟着敲一遍",
    "huggingface/transformers": "工业级模型库，读 modeling_*.py 看真实实现与论文的差异",
    "jingyaogong/minimind": "从零训练 26M 小模型的全流程，算力有限时最好的练手项目",
    "huggingface/diffusers": "扩散模型标准库，多模态章的图像生成基线",
    "openai/CLIP": "图文对齐的经典实现，理解「多模态检索」为什么能跨模态",
    "AUTOMATIC1111/stable-diffusion-webui": "最流行的 SD 前端，看插件生态如何把模型变成产品",
    "QwenLM/Qwen3-VL": "国产多模态模型，中文场景的视觉问答/文档理解首选",
    "openai/evals": "评测框架与题库结构，学会把「感觉不错」变成可回归的分数",
    "EleutherAI/lm-evaluation-harness": "学术基准评测标准，面试问 MMLU/GSM8K 口径时的依据",
    "explodinggradients/ragas": "RAG 专用评测：faithfulness/answer relevancy 的计算方式",
    "langchain-ai/langgraph": "有状态 Agent 编排：图、检查点、人工介入，Agent 章的主线",
    "microsoft/autogen": "多智能体对话框架，理解角色分工与终止条件",
    "crewAIInc/crewAI": "角色化多 Agent 框架，快速搭「调研-写作-审核」流水线",
    "openai/openai-agents-python": "官方 Agents SDK：handoff、guardrail、tracing 的最小实现",
    "modelcontextprotocol/python-sdk": "MCP 官方 SDK，工具生态的标准接口，写一个 server 就懂",
    "FoundationAgents/MetaGPT": "软件公司式多 Agent，看 SOP 如何被编码进角色",
    "langgenius/dify": "可视化 LLM 应用平台，商业化交付最常见的底座之一",
    "n8n-io/n8n": "工作流自动化，把 Agent 接进企业既有系统的最低成本方式",
    "mli/paper-reading": "李沐论文精读系列配套，建立「读一篇顶会」的节奏",
    "dair-ai/ML-Papers-of-the-Week": "每周论文榜，解决「不知道追什么」的问题",
    "donnemartin/system-design-primer": "系统设计面试基础，Agent 服务也要过容量与一致性这关",
    "yangshun/tech-interview-handbook": "技术面试通用题库与行为面框架",
    "alirezadir/Machine-Learning-Interviews": "ML/LLM 岗位面试题分类整理，含系统设计",
    "chiphuyen/ml-interviews-book": "《Machine Learning Interviews》开源书，面试官视角的评分逻辑",
    "datawhalechina/llm-universe": "中文 LLM 应用开发教程：API→RAG→Agent→评估的完整路径",
    "datawhalechina/happy-llm": "从零构建大模型的教学项目，补「模型内部发生了什么」",
}

BILIBILI = {
    "李沐": "https://search.bilibili.com/all?keyword=%E6%9D%8E%E6%B2%90%20AI",
    "吴恩达": "https://search.bilibili.com/all?keyword=%E5%90%B4%E6%81%A9%E8%BE%BE%20Prompt%20%E5%B7%A5%E7%A8%8B",
    "王树森": "https://search.bilibili.com/all?keyword=%E7%8E%8B%E6%A0%91%E6%A3%AE%20Transformer",
    "实战手册": "https://search.bilibili.com/all?keyword=AI%E4%BA%A7%E5%93%81%E7%BB%8F%E7%90%86%E5%AE%9E%E6%88%98%E6%89%8B%E5%86%8C",
    "论文精读": "https://search.bilibili.com/all?keyword=%E6%9D%8E%E6%B2%90%20%E8%AE%BA%E6%96%87%E7%B2%BE%E8%AF%BB",
}

# (id, group, day, title, summary, prerequisites, github_repos, bilibili_key)
CHAPTERS = [
    (
        "agent-ch01", "G1", "DAY 1",
        "AI 行业认知与岗位地图：从「会用」到「知道为什么值钱」",
        "对应图片 DAY 1（B 站李沐学 AI）。先建立三张地图：**技术地图**（模型层/推理层/应用层/工具层各自的钱从哪来）、"
        "**岗位地图**（算法、应用开发、Agent 工程、AI 产品、解决方案，各自考什么、实习做什么）、"
        "**能力地图**（本学科 16 章对应哪 6 项可验证能力）。核心判断：2026 年的岗位缺口不在「会调 API」，"
        "而在「能把不确定的模型能力包成稳定交付物」——后面 15 章都在练这一件事。产出：一页《岗位对标表》，"
        "把自己当前能力对到目标 JD 的每一条要求上，标出缺口。",
        [], ["microsoft/AI-For-Beginners", "Hannibal046/Awesome-LLM",
             "datawhalechina/self-llm", "eugeneyan/applied-ml"], "李沐",
    ),
    (
        "agent-ch02", "G1", "DAY 3",
        "Prompt 工程与结构化输出：把自然语言当接口设计",
        "对应图片 DAY 3（B 站吴恩达）。不讲「神奇咒语」，讲**接口设计**：角色/任务/约束/示例四段式的信息论依据、"
        "零样本与少样本的适用边界、思维链在什么任务上有效（以及为什么在推理模型上会反噬）、"
        "结构化输出（JSON Schema / function calling / 严格模式）的错误率与自修复策略、"
        "提示注入的攻击面与防御层次、token 成本与缓存命中。产出：一个带 schema 校验与重试的提示模板库，"
        "对 20 条边界输入有回归测试。",
        ["agent-ch01"], ["dair-ai/Prompt-Engineering-Guide", "openai/openai-cookbook",
                         "anthropics/claude-cookbooks", "microsoft/promptflow"], "吴恩达",
    ),
    (
        "agent-ch03", "G1", "DAY 5",
        "模型接入与 DeepSeek 实操：第一次让程序真的说话",
        "对应图片 DAY 5（DeepSeek 官方文档）。把「调模型」当一次**外部依赖接入**来做：鉴权与密钥管理、"
        "流式与超时、错误码与退避重试、限流与并发、上下文长度与截断策略、"
        "OpenAI 兼容层与厂商差异（tool call 格式、JSON 模式、reasoning_content）、"
        "本地 Ollama 与云端 API 的取舍、成本核算（每千次请求的 token 账单）。"
        "产出：一个可切换厂商的 LLM 客户端封装，含重试、限流、日志、成本统计四件套。",
        ["agent-ch02"], ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1",
                         "deepseek-ai/awesome-deepseek-integration", "ollama/ollama"], "李沐",
    ),
    (
        "agent-ch04", "G1", "DAY 7",
        "需求洞察：用户故事与 AI 产品画布",
        "对应图片 DAY 7（《AI 产品经理实战手册》）。AI 项目最常见的死法不是模型不行，是**需求不成立**。"
        "本章给三件工具：用户故事（As a… I want… so that…）与验收条件、AI 适用性判断（确定性规则 / 分类 / 生成 / "
        "Agent 四档，越往后越贵越不稳）、产品画布（用户-场景-输入输出-失败兜底-成本-指标）。"
        "再补**失败模式设计**：模型错了用户看到什么、置信度低时怎么降级、人工接管怎么触发。"
        "产出：一个真实场景的《AI 产品一页纸》，含 3 条可测指标与 3 条不做什么。",
        ["agent-ch01"], ["eugeneyan/applied-ml", "Azure-Samples/azure-search-openai-demo",
                         "GokuMohandas/Made-With-ML", "microsoft/AI-For-Beginners"], "实战手册",
    ),
    (
        "agent-ch05", "G2", "DAY 9",
        "RAG 技术精讲：检索质量决定回答上限",
        "对应图片 DAY 9（LangChain 中文教程）。RAG 的收益 80% 来自数据侧：文档解析（PDF 版面/表格/扫描件）、"
        "切块策略（固定长度/语义/父子块）与重叠、元数据设计、混合检索（BM25 + 向量）与融合排序、"
        "重排（cross-encoder）的性价比、查询改写与多跳、引用溯源与「拒答」策略。"
        "再补两个工程真相：**召回率不能只看 Top-K 命中**、**知识更新与权限过滤必须写进检索层**。"
        "产出：一个可评测的 RAG 服务，含 30 条问答对的召回率/忠实度基线。",
        ["agent-ch03"], ["langchain-ai/langchain", "run-llama/llama_index",
                         "infiniflow/ragflow", "HKUDS/LightRAG"], "李沐",
    ),
    (
        "agent-ch06", "G2", "DAY 11",
        "私有化部署与推理服务：把模型放进自己的机房",
        "对应图片 DAY 11（vLLM 部署指南）。先算账：显存 = 权重 + KV Cache + 激活，量化（FP16/INT8/AWQ/GPTQ）"
        "各自损失什么；再选型：vLLM 的 PagedAttention 与连续批处理、SGLang 的前缀缓存、llama.cpp 的 CPU/GGUF 路线；"
        "然后才是部署：容器化、健康检查、灰度、并发压测（TTFT/TPOT/吞吐三指标）、"
        "多租户与配额、日志脱敏。产出：单卡部署一个 7B/14B 模型，给出压测报告（QPS、P99 延迟、显存峰值）。",
        ["agent-ch03"], ["vllm-project/vllm", "sgl-project/sglang",
                         "ggml-org/llama.cpp", "ollama/ollama"], "李沐",
    ),
    (
        "agent-ch07", "G2", "DAY 13",
        "轻量化微调：LoRA / QLoRA 与数据工程",
        "对应图片 DAY 13（Hugging Face PEFT 教程）。先回答「什么时候不该微调」：知识注入优先 RAG、"
        "格式与风格才考虑微调、推理能力微调性价比最低。再讲方法：LoRA 的低秩分解与秩/alpha 选择、"
        "QLoRA 的 4bit 量化与显存账本、数据配比与去重、对话模板与 loss mask、过拟合识别、"
        "合并导出与部署。产出：用 500-2000 条自有数据完成一次 LoRA，给出「微调前/后」在留出集上的对比与失败案例分析。",
        ["agent-ch06"], ["huggingface/peft", "hiyouga/LLaMA-Factory",
                         "unslothai/unsloth", "huggingface/trl"], "李沐",
    ),
    (
        "agent-ch08", "G3", "DAY 19",
        "Transformer 核心机理：能白板推一遍才算懂",
        "对应图片 DAY 19（B 站王树森解析）。目标是**能白板讲清**：tokenizer→embedding→注意力（QKV 的几何意义、"
        "为什么要缩放、多头在学什么）→残差与 LayerNorm 的位置之争→FFN 是键值记忆→位置编码（绝对/ROPE）→"
        "输出层与采样（temperature/top-p）。再算一遍参数量与 KV Cache 显存，把「为什么长上下文贵」落到数字上。"
        "产出：手写一个 2 层注意力的 numpy 前向，并用 nanoGPT 跑通一次训练 loss 曲线。",
        ["agent-ch03"], ["karpathy/nanoGPT", "karpathy/build-nanogpt",
                         "huggingface/transformers", "jingyaogong/minimind"], "王树森",
    ),
    (
        "agent-ch09", "G3", "DAY 24",
        "多模态应用开发：图像、文档与语音的工程接口",
        "对应图片 DAY 24（Stable Diffusion Colab）。分清三条线：**理解**（VLM 做图表/文档/截图问答）、"
        "**生成**（扩散模型与文生图的可控性：ControlNet/Inpainting）、**检索**（CLIP 跨模态向量）。"
        "工程上要处理：图像预处理与分辨率、OCR 与版面还原、多图输入的 token 成本、生成内容的安全与版权、"
        "异步任务队列与进度反馈。产出：一个「发票/报表识别 + 结构化抽取」的小应用，含准确率评估与失败样本集。",
        ["agent-ch08"], ["huggingface/diffusers", "openai/CLIP",
                         "AUTOMATIC1111/stable-diffusion-webui", "QwenLM/Qwen3-VL"], "李沐",
    ),
    (
        "agent-ch10", "G4", "DAY 30",
        "AI 产品设计与评估方法论：把「感觉不错」变成分数",
        "对应图片 DAY 30（Google《AI 设计原则》）。两条主线：**设计**（能力边界外露、不确定性表达、"
        "错误可恢复、人机协作的分工与接管、渐进式授权）与**评估**（黄金集构建、LLM-as-judge 的偏差与校准、"
        "人工评审量表、离线指标到线上指标的映射、A/B 与护栏指标）。再讲 Responsible AI 的落地检查："
        "隐私、偏见、幻觉免责、审计日志。产出：一份《评估方案》，含 50 条黄金样本、3 个指标、1 套回归流程。",
        ["agent-ch04", "agent-ch05"], ["openai/evals", "EleutherAI/lm-evaluation-harness",
                                       "explodinggradients/ragas", "microsoft/AI-For-Beginners"], "实战手册",
    ),
    (
        "agent-ch11", "G4", "DAY 35",
        "Agent 系统开发：工具、记忆、规划与多智能体",
        "对应图片 DAY 35（一站式 AI 产品知识库）。本学科的重心章。从「LLM 是大脑」出发，补齐四件套："
        "**工具**（function calling / MCP 的 schema 设计、幂等与副作用、权限最小化）、"
        "**记忆**（短期上下文压缩、长期向量记忆、状态机与检查点）、"
        "**规划**（ReAct、Plan-and-Execute、反思与重试、终止条件与死循环防护）、"
        "**多智能体**（角色分工、handoff、共享黑板、成本爆炸）。再讲可观测性：trace、每步 token/时延、"
        "失败归因。产出：一个能完成多步任务的 Agent（含 3 个工具、检查点、人工介入、失败回放）。",
        ["agent-ch05", "agent-ch08"], ["langchain-ai/langgraph", "microsoft/autogen",
                                       "crewAIInc/crewAI", "openai/openai-agents-python",
                                       "modelcontextprotocol/python-sdk", "FoundationAgents/MetaGPT"], "实战手册",
    ),
    (
        "agent-ch12", "G4", "DAY 40-43",
        "商业化与行业解决方案：从 demo 到能签单",
        "对应图片 DAY 40（AI 产品变现指南）+ DAY 43（《实战手册》第四章）。先讲商业模式：按席位/按调用/按效果"
        "三种计费的毛利结构与风险转移；再讲成本模型：token、推理卡、向量库、人工兜底，算出单次任务成本与报价下限；"
        "然后讲行业方案：客服、知识管理、代码助手、营销内容四条常见赛道的现状与坑；"
        "最后讲交付：POC→试点→推广的验收口径、SLA、数据合规（等保/个人信息保护）、失败退出条款。"
        "产出：一份《行业方案书》，含成本测算表、竞品对比、POC 验收标准。",
        ["agent-ch04", "agent-ch10"], ["langgenius/dify", "n8n-io/n8n",
                                       "Azure-Samples/azure-search-openai-demo",
                                       "microsoft/AI-For-Beginners"], "实战手册",
    ),
    (
        "agent-ch13", "G5", "DAY 45",
        "前沿技术追踪：建立自己的信息过滤系统",
        "对应图片 DAY 45（B 站李沐每周论文精读）。目标不是「读完所有论文」，而是**建立过滤与复现习惯**："
        "信息源分层（顶会/实验室博客/工程博客/社区）、三遍读法（标题摘要→图表结论→方法与局限）、"
        "如何判断一篇论文值不值得复现、复现的最小闭环（数据→脚本→指标→差异归因）、"
        "技术雷达（Adopt/Trial/Assess/Hold）的维护。产出：一份个人技术雷达 + 3 篇精读笔记（含可运行的最小复现）。",
        ["agent-ch08"], ["mli/paper-reading", "dair-ai/ML-Papers-of-the-Week",
                         "Hannibal046/Awesome-LLM"], "论文精读",
    ),
    (
        "agent-ch14", "G5", "DAY 47",
        "职业发展框架：把能力翻译成岗位语言",
        "对应图片 DAY 47（《实战手册》第七章）。三件事：**能力矩阵**（工程/模型/产品/业务四维，每维 5 级行为锚点）、"
        "**路径选择**（应用开发 vs Agent 工程 vs 解决方案 vs AI 产品，实习与校招的考核差异）、"
        "**作品集结构**（问题-方案-指标-取舍-复盘，5 个项目里至少 1 个有真实用户）。"
        "再补职场基本盘：如何写周报、如何做技术评审、如何和产品/业务对齐指标。产出：个人能力矩阵自评 + 12 个月成长计划。",
        ["agent-ch01"], ["donnemartin/system-design-primer", "yangshun/tech-interview-handbook",
                         "alirezadir/Machine-Learning-Interviews", "chiphuyen/ml-interviews-book"], "实战手册",
    ),
    (
        "agent-ch15", "G6", "DAY 55",
        "项目实操：端到端交付一个可演示的 Agent 产品",
        "对应图片 DAY 55（专属项目实战）。不是再做一个聊天框，而是**完整交付**：选题（有真实用户/有明确痛点/"
        "能在 3 周内完成）、需求与范围冻结、数据与知识库准备、基线（先用最简单方案跑通）、"
        "迭代（按错误分析排序，不按感觉）、评测（黄金集 + 回归）、部署（容器 + 监控 + 成本面板）、"
        "文档（README/架构图/演示视频/复盘）。产出：一个可公开访问的 demo + 一份能讲 15 分钟的答辩材料。",
        ["agent-ch05", "agent-ch11", "agent-ch10"], ["datawhalechina/llm-universe",
                                                    "datawhalechina/happy-llm",
                                                    "langchain-ai/langgraph", "langgenius/dify"], "实战手册",
    ),
    (
        "agent-ch16", "G6", "DAY 70-90",
        "简历、模拟面试与入职答辩：把项目讲成录用理由",
        "对应图片 DAY 70（模拟面试简历辅导）+ DAY 90（面试入职）。简历层：一页纸结构、项目描述 STAR-R"
        "（Situation/Task/Action/Result/Reflection）、量化指标的写法、避免「参与了」式空话。"
        "面试层：八股（Transformer/RAG/Agent/部署）、系统设计（设计一个企业知识库 Agent）、"
        "手写题（检索打分、Agent 循环、限流器）、行为面（冲突/失败/优先级）。"
        "入职层：前 30 天怎么活下来（读代码、找小切口、建立信任）。产出：简历终稿 + 3 次模拟面试录像 + 入职 30 天计划。",
        ["agent-ch14", "agent-ch15"], ["alirezadir/Machine-Learning-Interviews",
                                       "chiphuyen/ml-interviews-book",
                                       "GokuMohandas/Made-With-ML",
                                       "donnemartin/system-design-primer"], "实战手册",
    ),
]

# 每章「技术承重」：图片只给了学习主题，这里补上程序员标准下必须交付的代码物。
# 没有这一列，章节就会退化成读书笔记——这是对图片链路最大的修正。
TECH_LOAD = {
    "agent-ch01": "读 4 个仓库的架构与目录，产出《技术分层表》；不写业务代码，但要能画出一次请求从 UI 到模型的完整路径",
    "agent-ch02": "Python 提示模板库：Jinja 风格渲染 + JSON Schema 校验 + 失败自修复 + 20 条边界输入回归测试",
    "agent-ch03": "可切换厂商的 LLM 客户端：流式、超时、指数退避、令牌桶限流、结构化日志、按请求计费",
    "agent-ch04": "需求→技术可行性评估表；附一个成本估算脚本（token × 单价 × 日活），算出「这个需求经济上成不成立」",
    "agent-ch05": "RAG 服务：解析→切块→混合检索→重排→引用；30 条黄金集，输出 Recall@K / 忠实度 / 拒答率",
    "agent-ch06": "容器化部署 7B/14B 模型；压测脚本输出 TTFT、TPOT、P99、显存峰值与单位 token 成本",
    "agent-ch07": "LoRA/QLoRA 训练脚本 + 数据清洗 + 留出集前后对比 + 失败案例归因",
    "agent-ch08": "numpy 手写单头/多头注意力与前向；用 nanoGPT 跑通一次训练并解释 loss 曲线",
    "agent-ch09": "文档/发票抽取应用：OCR→版面→VLM 结构化输出；50 条样本的字段级准确率",
    "agent-ch10": "评估框架：50 条黄金集 + LLM-as-judge 校准 + 回归脚本；指标能接进 CI",
    "agent-ch11": "LangGraph Agent：3 个工具（含 MCP server）、检查点、人工介入、死循环防护、trace 回放",
    "agent-ch12": "成本模型脚本（token/卡时/向量库/人工兜底）+ POC 验收清单 + 竞品对比矩阵",
    "agent-ch13": "3 篇论文的最小复现脚本（可跑、有指标、记录与原文差异）",
    "agent-ch14": "能力矩阵自评（行为锚点）+ 12 个月计划 + 作品集目录；非代码，但要可被面试官逐条追问",
    "agent-ch15": "端到端产品：可访问 demo + 容器部署 + 监控面板 + 成本看板 + 15 分钟答辩材料",
    "agent-ch16": "三道手写题（BM25 检索打分 / ReAct 循环 / 令牌桶限流）+ 3 次模拟面试录像 + 入职 30 天计划",
}

# B 站学习清单：图片只给了「B 站 XXX」这种模糊指向，这里落成可检索的关键词。
# 不写 BV 号是刻意的——视频会下架、合集会被重排，BV 链接的腐烂率极高。
BILI_KEYWORDS = {
    "agent-ch01": ["李沐 深度学习 课程", "大模型 应用开发 岗位", "AI 行业 产业链"],
    "agent-ch02": ["吴恩达 Prompt Engineering", "function calling 教程", "提示注入 防御"],
    "agent-ch03": ["DeepSeek API 教程", "Ollama 本地部署", "OpenAI 兼容 接口"],
    "agent-ch04": ["AI 产品经理 用户故事", "AI 产品 需求分析", "产品画布"],
    "agent-ch05": ["LangChain RAG 教程", "向量数据库 原理", "RAG 切块 重排"],
    "agent-ch06": ["vLLM 部署", "大模型 量化 显存", "推理 压测"],
    "agent-ch07": ["LoRA 微调 教程", "QLoRA 显存", "LLaMA-Factory 使用"],
    "agent-ch08": ["王树森 Transformer", "注意力机制 手推", "KV Cache 原理"],
    "agent-ch09": ["Stable Diffusion 教程", "多模态大模型", "VLM 文档识别"],
    "agent-ch10": ["LLM 评测 方法", "RAGAS 评估", "AI 产品 指标"],
    "agent-ch11": ["LangGraph 教程", "Agent 开发 实战", "MCP 协议", "多智能体"],
    "agent-ch12": ["大模型 商业化", "企业 知识库 方案", "AI 项目 报价"],
    "agent-ch13": ["李沐 论文精读", "如何读论文", "论文 复现"],
    "agent-ch14": ["AI 工程师 职业规划", "实习 面试 准备", "能力矩阵"],
    "agent-ch15": ["大模型 项目 实战", "从0到1 AI 产品", "Agent 项目 部署"],
    "agent-ch16": ["大模型 面试 题", "项目 介绍 STAR", "系统设计 面试"],
}

GROUPS = {
    "G1": "认知与基座（DAY 1-7）：先知道钱在哪，再让程序开口",
    "G2": "知识与部署（DAY 9-13）：把私有数据变成能力，把模型放进机房",
    "G3": "原理与多模态（DAY 19-24）：能白板推导，能处理图像与文档",
    "G4": "产品与系统（DAY 30-43）：评估、Agent、商业化，形成交付物",
    "G5": "前沿与职业（DAY 45-47）：信息过滤系统与能力矩阵",
    "G6": "交付与求职（DAY 55-90）：项目、简历、面试、入职",
}


def main() -> int:
    snap = json.loads(SNAP.read_text(encoding="utf-8"))
    repos = snap["repos"]

    chapters = []
    for order, (cid, group, day, title, summary, prereq, gh, bili_key) in enumerate(CHAPTERS, 1):
        stars, approx, notes = [], [], []
        for r in gh:
            item = repos.get(r)
            if not item or not item.get("ok"):
                raise SystemExit(f"{cid} 引用仓库缺失：{r}")
            stars.append(item["stars"])
            approx.append(bool(item.get("approx")))
            notes.append(REPO_NOTES.get(r, "参考实现与工程实践"))
        chapters.append({
            "id": cid,
            "order": order,
            "group": group,
            "course": f"{GROUPS[group]}",
            "week": day,
            "title": title,
            "summary": summary,
            "prerequisites": prereq,
            "books": [],
            "status": "planned",
            "tech_load": TECH_LOAD[cid],
            "resources": {
                "github": gh,
                "github_stars": stars,
                "github_approx": approx,
                "github_notes": notes,
                "github_fetched_at": snap.get("fetched_at", "2026-10-21"),
                "bilibili": BILIBILI[bili_key],
                "bilibili_keywords": BILI_KEYWORDS[cid],
                "bilibili_note": "站内搜索入口（关键词固定、视频会更新，故不写死 BV 号）",
                "books": [],
                "leetcode": [],
                "nowcoder": [],
            },
        })

    doc = {
        "schema_version": 1,
        "subject": "agent",
        "title": "CppMind · AI Agent 开发与交付（对齐 90 天 Agent 链路）",
        "note": (
            "章节骨架对齐图片「人生建议：今年死磕 AI Agent」的 18 个节点（DAY 1/3/5/7/9/11/13/19/24/30/35/"
            "40/43/45/47/55/70/90），合并为 16 章：DAY 40+43 合为「商业化与行业方案」，DAY 70+90 合为"
            "「简历面试与入职」。**与 ai 学科的分界**：ai 讲技术纵深（Transformer 推导、LoRA 原理、RAG 机制、"
            "Agent 框架内部实现），本学科讲**交付链路**——同一主题只保留「够用即止 + 工程判据 + 可验收产出」，"
            "推导与源码分析一律指回 ai。每章必须齐备 7 类内容，且必须挂真实 GitHub 项目作为实操来源；"
            "star 数由 API 实测（6 个千位近似标 ≈）。目标是达到「能独立交付一个 Agent 应用、能通过实习面试」的水平。"
        ),
        "source_course": {
            "name": "90 天 AI Agent 学习链路（图片版）",
            "nodes": [
                {"day": "DAY 1", "topic": "AI 行业认知", "chapter": "agent-ch01", "ref": "B 站李沐学 AI"},
                {"day": "DAY 3", "topic": "Prompt 工程", "chapter": "agent-ch02", "ref": "B 站吴恩达"},
                {"day": "DAY 5", "topic": "DeepSeek / 操作", "chapter": "agent-ch03", "ref": "DeepSeek 官方文档"},
                {"day": "DAY 7", "topic": "用户故事 产品画布", "chapter": "agent-ch04", "ref": "《AI 产品经理实战手册》"},
                {"day": "DAY 9", "topic": "RAG 技术精讲", "chapter": "agent-ch05", "ref": "LangChain 中文教程"},
                {"day": "DAY 11", "topic": "私有化部署方案", "chapter": "agent-ch06", "ref": "vLLM 部署指南"},
                {"day": "DAY 13", "topic": "轻量化模型微调", "chapter": "agent-ch07", "ref": "Hugging Face PEFT 教程"},
                {"day": "DAY 19", "topic": "Transformer 核心", "chapter": "agent-ch08", "ref": "B 站王树森解析"},
                {"day": "DAY 24", "topic": "多模态应用开发", "chapter": "agent-ch09", "ref": "Stable Diffusion Colab"},
                {"day": "DAY 30", "topic": "AI 产品设计方法论", "chapter": "agent-ch10", "ref": "Google《AI 设计原则》"},
                {"day": "DAY 35", "topic": "Agent 系统开发", "chapter": "agent-ch11", "ref": "一站式 AI 产品知识库"},
                {"day": "DAY 40", "topic": "AI 商业化实战", "chapter": "agent-ch12", "ref": "B 站 AI 产品变现指南"},
                {"day": "DAY 43", "topic": "行业解决方案", "chapter": "agent-ch12", "ref": "《实战手册》第四章"},
                {"day": "DAY 45", "topic": "前沿技术追踪", "chapter": "agent-ch13", "ref": "B 站李沐每周论文精读"},
                {"day": "DAY 47", "topic": "职业发展框架", "chapter": "agent-ch14", "ref": "《实战手册》第七章"},
                {"day": "DAY 55", "topic": "AI 产品项目实操带学", "chapter": "agent-ch15", "ref": "专属项目实战"},
                {"day": "DAY 70", "topic": "模拟面试简历辅导", "chapter": "agent-ch16", "ref": "重塑简历内容"},
                {"day": "DAY 90", "topic": "AI 产品经理面试入职", "chapter": "agent-ch16", "ref": "开启新职业旅途"},
            ],
            "bilibili_search": BILIBILI,
        },
        "groups": GROUPS,
        "chapters": chapters,
        "extensions": {
            "image_audit": {
                "verdict": "图片链路偏产品/商业化：18 个节点中，纯技术动作只有 7 个（DAY 5/9/11/13/19/24/35），"
                           "其余为行业认知、需求、产品设计、商业化、职业叙事。直接照做会得到「懂名词但写不出代码」的结果，"
                           "达不到实习门槛。",
                "missing": [
                    "编程与工程基础：Python 异步、HTTP/SSE、Git 协作、单元测试、容器化",
                    "评测工程：黄金集、LLM-as-judge、回归门禁（图片只在 DAY 30 提了方法论，没给做法）",
                    "可观测性与成本：trace、每步 token、P95 延迟、单次任务成本（图片完全缺失）",
                    "安全与合规：提示注入、权限最小化、数据脱敏、审计日志（图片完全缺失）",
                    "数据基础：SQL、向量库选型、文档解析与清洗（图片只提 RAG，没提数据准备）",
                ],
                "compensation": {
                    "编程与工程基础": "分散进 agent-ch02/ch03 的交付物（模板库、客户端封装）与 ch06 的容器化",
                    "评测工程": "agent-ch10 独立成章，要求 50 条黄金集 + 回归脚本",
                    "可观测性与成本": "agent-ch11 的 trace 与 agent-ch12 的成本模型脚本",
                    "安全与合规": "agent-ch02（注入防御）、agent-ch11（权限最小化）、agent-ch12（数据合规）",
                    "数据基础": "agent-ch05 的解析/切块/权限过滤，agent-ch09 的 OCR 与版面",
                },
                "node_level": {
                    "DAY 1": "认知", "DAY 3": "半技术", "DAY 5": "技术", "DAY 7": "产品",
                    "DAY 9": "技术", "DAY 11": "技术", "DAY 13": "技术", "DAY 19": "技术",
                    "DAY 24": "技术", "DAY 30": "半技术", "DAY 35": "技术", "DAY 40": "商业",
                    "DAY 43": "商业", "DAY 45": "半技术", "DAY 47": "职业", "DAY 55": "综合",
                    "DAY 70": "求职", "DAY 90": "求职",
                },
            },
            "internship_bar": [
                "能独立完成「需求 → 基线 → 迭代 → 评测 → 部署 → 复盘」全链路，至少 1 个可公开访问的项目",
                "能解释每个技术选型的取舍（为什么 RAG 不微调、为什么用 LangGraph 不用裸循环、为什么这个切块大小）",
                "能给出一份带数字的评估报告（召回率/忠实度/P95 延迟/单次任务成本）",
                "能白板推导 Transformer 注意力与 KV Cache 显存账本",
                "能在 45 分钟内完成一道 Agent 系统设计题并回答追问",
            ],
            "portfolio": [
                "agent-ch05 → RAG 服务（含 30 条黄金集基线）",
                "agent-ch11 → 多步 Agent（3 工具 + 检查点 + 人工介入）",
                "agent-ch15 → 端到端产品（可访问 demo + 答辩材料）",
            ],
        },
        "github_resources": [],
        "resources_fetched_at": snap.get("fetched_at", "2026-10-21"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    approx_n = sum(1 for c in chapters for a in c["resources"]["github_approx"] if a)
    print(f"写入 {OUT.relative_to(ROOT)}：{len(chapters)} 章 / "
          f"{sum(len(c['resources']['github']) for c in chapters)} 个仓库引用（≈ {approx_n} 个）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
