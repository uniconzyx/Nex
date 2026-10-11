#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""新增 AI/Agent 学科大纲；并把全部学科的资源统一替换为 GitHub star 最高仓库。

star 数据来源：GitHub Search/Repos API，抓取日期 2026-09-21。
"""
import json
import pathlib

FETCHED_AT = "2026-09-21"

# 各学科「GitHub star 最高」的学习资源（star 降序），全部为真实仓库
GH = {
    "cpp": [
        ("practical-tutorials/project-based-learning", 286133, "项目驱动的多语言实战教程合集（含 C/C++ 专题）"),
        ("TheAlgorithms/C-Plus-Plus", 34742, "C++ 实现的经典算法与数据结构合集，可直接编译运行"),
        ("ssloy/tinyrenderer", 24335, "从零手写软件渲染器，C++ 底层与内存布局的极佳教材"),
    ],
    "clang": [
        ("practical-tutorials/project-based-learning", 286133, "项目驱动的实战教程合集（含 C 专题）"),
        ("TheAlgorithms/C", 22507, "C 语言实现的算法与数据结构合集"),
    ],
    "java": [
        ("Snailclimb/JavaGuide", 159056, "Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计"),
        ("macrozheng/mall", 84863, "SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例"),
        ("doocs/advanced-java", 79141, "互联网 Java 工程师进阶知识：高并发、分布式、微服务"),
        ("eugenp/tutorials", 37326, "Spring 官方生态的系统化代码教程仓库"),
    ],
    "python": [
        ("TheAlgorithms/Python", 225266, "Python 实现的全部经典算法，含详细注释"),
        ("jackfrued/Python-100-Days", 187118, "Python 100 天从新手到大师（中文系统教程）"),
        ("microsoft/ML-For-Beginners", 91310, "微软官方 12 周机器学习入门课程，含 26 课与测验"),
    ],
    "fullstack": [
        ("trekhleb/javascript-algorithms", 196855, "JavaScript 算法与数据结构，含英文详解"),
        ("Chalarangelo/30-seconds-of-code", 129326, "短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧"),
        ("yangshun/front-end-interview-handbook", 44008, "前端面试手册：HTML/CSS/JS/浏览器/性能"),
    ],
    "spring": [
        ("macrozheng/mall", 84863, "SpringBoot + MyBatis 完整电商项目，最佳工程范例"),
        ("spring-projects/spring-boot", 81563, "Spring Boot 官方仓库：源码、文档与示例"),
        ("YunaiV/ruoyi-vue-pro", 39566, "企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现"),
        ("eugenp/tutorials", 37326, "Spring 生态系统化教程代码"),
    ],
    "middleware": [
        ("Snailclimb/JavaGuide", 159056, "含 Redis 与消息队列的高频面试知识"),
        ("doocs/advanced-java", 79141, "高并发与分布式：缓存、消息队列、分库分表专题"),
        ("redis/redis", 76640, "Redis 官方源码仓库：数据结构与命令实现的权威来源"),
        ("apache/kafka", 33917, "Apache Kafka 官方仓库：架构与协议实现"),
    ],
    "database": [
        ("Snailclimb/JavaGuide", 159056, "含 MySQL 索引、事务、锁与调优的系统讲解"),
        ("macrozheng/mall", 84863, "真实业务库表设计范例与 SQL 实践"),
        ("doocs/advanced-java", 79141, "含分库分表、读写分离与分布式事务"),
    ],
    "bigdata": [
        ("DataTalksClub/data-engineering-zoomcamp", 46045, "免费 9 周数据工程课程：含 Hadoop/Spark/数仓实践"),
        ("apache/spark", 44136, "Apache Spark 官方仓库：RDD/SQL/调优权威来源"),
        ("heibaiying/BigData-Notes", 16979, "中文大数据入门指南：Hadoop/Hive/Spark/Flink 系统笔记"),
        ("apache/hadoop", 15681, "Apache Hadoop 官方仓库：HDFS/YARN/MapReduce 实现"),
    ],
    "fundamentals": [
        ("donnemartin/system-design-primer", 373461, "系统设计入门：性能、一致性、可用性与面试题（408 之上的系统视野）"),
        ("jwasham/coding-interview-university", 362479, "完整的计算机科学自学计划：数据结构、算法、OS、网络全覆盖"),
        ("CyC2018/CS-Notes", 186393, "中文技术面试必备：操作系统、计算机网络、组成原理、算法、数据库"),
    ],
    "tooling": [
        ("trimstray/the-book-of-secret-knowledge", 248407, "运维与工程工具知识合集：Linux、网络、排障命令速查"),
        ("ohmyzsh/ohmyzsh", 190209, "Shell 生产力框架（工程效率的入门必装）"),
        ("jlevy/the-art-of-command-line", 162576, "命令行艺术：Linux 命令的体系化进阶指南"),
        ("bregman-arie/devops-exercises", 84793, "DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖"),
    ],
    "data": [
        ("scikit-learn/scikit-learn", 67487, "经典机器学习库官方仓库：算法实现与最佳实践"),
        ("jakevdp/PythonDataScienceHandbook", 50114, "《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib）"),
        ("pandas-dev/pandas", 49928, "Pandas 官方仓库：API 与内部机制权威来源"),
        ("microsoft/Data-Science-For-Beginners", 37525, "微软官方 10 周数据科学课程"),
    ],
    "ai": [
        ("tensorflow/tensorflow", 200724, "深度学习框架官方仓库，工业级模型工程范例"),
        ("firecrawl/firecrawl", 189309, "为 AI Agent 提供网页数据：抓取到结构化数据的工程实现"),
        ("Significant-Gravitas/AutoGPT", 187681, "自主 Agent 的开创性项目，Agent 架构与工具循环的经典参考"),
        ("huggingface/transformers", 167014, "Transformer 模型定义框架：从 BERT/GPT 到多模态的全量实现"),
        ("langgenius/dify", 157994, "Agentic 工作流与 RAG 流水线平台：生产级 LLM 应用工程范例"),
        ("langchain-ai/langchain", 147524, "Agent 工程平台：工具、记忆、检索与编排的工业实现"),
        ("microsoft/ML-For-Beginners", 91310, "微软官方机器学习 12 周课程"),
    ],
}

AI_MANIFEST = {
    "schema_version": 1,
    "subject": "ai",
    "title": "CppMind · AI / Agent 开发课程体系",
    "note": "阶段7 技术栈扩展大纲（AI 方向）。覆盖深度学习基础 → 大模型原理 → 对齐与微调 → 提示/上下文工程 → RAG → Agent 开发 → 应用工程化，形成「能训练、能调优、能落地 Agent」的完整链路。每章须齐备 7 类内容（见 _template 规范）。resources 仅存元数据与链接，不存第三方题面/正文，符合合规红线。",
    "groups": {
        "A1": "深度学习基础",
        "A2": "大模型原理与训练",
        "A3": "提示与知识增强",
        "A4": "Agent 与工程化",
    },
    "chapters": [
        {
            "id": "ai-ch01",
            "order": 1,
            "group": "A1",
            "title": "深度学习基础：张量、前向与反向传播",
            "summary": "张量与计算图；全连接网络与激活函数的必要性（非线性的来源）；损失函数与梯度下降；反向传播的链式法则与自动微分的向量-雅可比积；梯度消失/爆炸的机制与对策（好初始化、归一化、残差、梯度裁剪）；优化器演进（SGD→Momentum→Adam→AdamW）与学习率调度（warmup + cosine）；过拟合与正则化（L1/L2、Dropout、早停）；训练循环的工程要点（zero_grad、混合精度与 loss scaling、梯度检查点）。",
            "prerequisites": [],
            "status": "planned",
        },
        {
            "id": "ai-ch02",
            "order": 2,
            "group": "A1",
            "title": "视觉与序列建模：CNN、RNN 到注意力机制",
            "summary": "卷积的局部连接与权值共享（参数量与平移等变的来源）；感受野、步长、池化与下采样；经典骨干（LeNet→ResNet 的残差动机）；序列建模的困境（RNN 的长程依赖与梯度消失）；LSTM/GRU 的门控机制；注意力机制的直觉与计算；从「对齐式注意力」到「自注意力」的演进——为 Transformer 铺路。",
            "prerequisites": ["ai-ch01"],
            "status": "planned",
        },
        {
            "id": "ai-ch03",
            "order": 3,
            "group": "A2",
            "title": "Transformer 与大语言模型原理",
            "summary": "自注意力的 Q/K/V 计算与 √d_k 缩放的必要性；多头注意力的子空间并行；位置编码演进（正弦→可学习→相对位置→RoPE/ALiBi）；编码器-解码器与仅解码器架构的取舍；Decoder-only 自回归生成与采样策略（贪心/温度/top-k/top-p/重复惩罚）；预训练目标与 Scaling Law（含 Chinchilla 最优）；Tokenizer（BPE/词表大小的影响）；注意力复杂度与 FlashAttention/MQA/GQA 的工程解法。",
            "prerequisites": ["ai-ch02"],
            "status": "planned",
        },
        {
            "id": "ai-ch04",
            "order": 4,
            "group": "A2",
            "title": "高效微调与对齐：LoRA、RLHF 与 DPO",
            "summary": "全量微调的显存构成（参数/梯度/优化器状态/激活）；LoRA 的低秩假设、初始化与 target_modules 选择；QLoRA 的 4bit 量化与分页优化器；Prefix/P-Tuning 与 Adapter 系；SFT 的数据构造与损失掩码（只对回答算 loss）；奖励模型与 PPO 的 KL 约束（防奖励黑客）；DPO 的闭式推导与工程优势；RLAIF/GRPO/Constitutional AI 等替代路线；**选型原则：注知识用 RAG、改行为用微调**。",
            "prerequisites": ["ai-ch03"],
            "status": "planned",
        },
        {
            "id": "ai-ch05",
            "order": 5,
            "group": "A3",
            "title": "提示工程与上下文工程",
            "summary": "零样本/少样本与示例选择（顺序与标签分布的影响）；思维链（CoT）为何有效与涌现特性；Self-Consistency 与 Least-to-Most；结构化输出的四层手段（Schema 约定→原生结构化输出→Function Calling→文法约束解码）；校验-重试-降级的容错架构；**上下文工程**：分层组织（系统/记忆/证据/历史）、压缩（滚动摘要、状态槽）、位置策略（lost in the middle）、前缀缓存；token 预算与可观测性。",
            "prerequisites": ["ai-ch03"],
            "status": "planned",
        },
        {
            "id": "ai-ch06",
            "order": 6,
            "group": "A3",
            "title": "RAG：向量检索与知识增强",
            "summary": "RAG 解决「知识过时/私有」与「幻觉」；索引链路（解析→分块→向量化→入库）与查询链路的完整拆解；分块策略（固定/结构/语义/父子块）与元数据增强；Embedding 模型选型（多语言、维度、Matryoshka、指令前缀）与「检索不到」的六类根因；混合检索（向量 + BM25）与 RRF 融合；两阶段「召回 + 重排」；查询改写（Multi-Query/HyDE/Step-back/对话式改写）；向量索引（HNSW/IVF/PQ）的召回-延迟-内存三角；分层评估（Recall@k、Faithfulness、引用准确率）与「换掉检索器」对照实验。",
            "prerequisites": ["ai-ch05"],
            "status": "planned",
        },
        {
            "id": "ai-ch07",
            "order": 7,
            "group": "A4",
            "title": "Agent 开发：工具调用、记忆与多智能体",
            "summary": "Agent 三要素（目标/工具/循环）与 ReAct 范式；四种架构模式（单次工具调用→ReAct→Plan-Execute→多智能体）与「能用工作流就别用 Agent」的判据；Function Calling 机制与工具设计的七条原则（描述即提示词、参数强类型、返回精简、错误可行动、幂等、最小权限、危险操作人工确认）；记忆三层（工作/短期/长期）与写入-检索-遗忘策略；多智能体的六种失败模式（错误级联、通信爆炸、责任不清、循环死锁、一致性漂移、成本失控）与「层级编排 + 显式状态机」的工程建议；MCP 标准化与提示注入的纵深防御。",
            "prerequisites": ["ai-ch06"],
            "status": "planned",
        },
        {
            "id": "ai-ch08",
            "order": 8,
            "group": "A4",
            "title": "LLM 应用工程：推理优化、评测、可观测性与安全",
            "summary": "推理两阶段（Prefill 决定 TTFT / Decode 决定 TPOT）与对应优化；KV Cache 与 PagedAttention、连续批处理、投机解码；量化（GPTQ/AWQ/GGUF/NF4）与精度取舍；模型路由与语义缓存；成本与延迟优化的正确顺序（先度量→砍上下文→分模型→加缓存→再谈推理加速）；可观测性三件套（Trace/Log/Metric）与 AI 特有维度（幻觉率、格式合规率、单请求成本、Agent 步数）；线上评测（影子模式、A/B、回放、人工抽检）与 LLM-as-Judge 的校准；OWASP LLM Top 10、提示注入的间接形态与纵深防御；数据合规（最小化、脱敏、可删除）。",
            "prerequisites": ["ai-ch07"],
            "status": "planned",
        },
    ],
}


def build_resources(subj: str, keep_books=None) -> dict:
    """按学科生成 resources（github 为 star 最高的真实仓库）。"""
    gh = GH.get(subj, [])
    return {
        "github": [r[0] for r in gh],
        "github_stars": [r[1] for r in gh],
        "github_notes": [r[2] for r in gh],
        "github_fetched_at": FETCHED_AT,
        "books": keep_books or [],
        "leetcode": [],
        "nowcoder": [],
    }


def main() -> None:
    base = pathlib.Path("content")

    # ---------- ① 新增 AI 学科 manifest ----------
    ai_path = base / "ai" / "_manifest.json"
    ai_data = dict(AI_MANIFEST)
    for ch in ai_data["chapters"]:
        ch["resources"] = build_resources("ai")
    ai_data["github_resources"] = [
        {"repo": r[0], "stars": r[1], "url": f"https://github.com/{r[0]}", "note": r[2]}
        for r in GH["ai"]
    ]
    ai_data["resources_fetched_at"] = FETCHED_AT
    ai_path.parent.mkdir(parents=True, exist_ok=True)
    if ai_path.exists():
        # 保留已有 status（可能已开工）
        old = json.loads(ai_path.read_text(encoding="utf-8"))
        old_status = {c["id"]: c.get("status") for c in old.get("chapters", [])}
        for ch in ai_data["chapters"]:
            if old_status.get(ch["id"]) == "complete":
                ch["status"] = "complete"
    ai_path.write_text(json.dumps(ai_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ai: 新建/更新 manifest，chapters={len(ai_data['chapters'])}")

    # ---------- ② 全部学科：resources 替换为 GitHub star 最高 ----------
    subjects = [p.name for p in sorted(base.iterdir())
                if p.is_dir() and not p.name.startswith("_") and p.name != "clang"]
    for subj in subjects:
        mf = base / subj / "_manifest.json"
        if not mf.exists():
            print(f"  [跳过] {subj} 无 manifest")
            continue
        d = json.loads(mf.read_text(encoding="utf-8"))
        changed = 0
        for ch in d.get("chapters", []):
            old_books = ((ch.get("resources") or {}).get("books")) or []
            ch["resources"] = build_resources(subj, keep_books=old_books)
            changed += 1
        # clang 模块（在 cpp 里）同步
        cm = d.get("clang_module")
        if isinstance(cm, dict):
            for u in cm.get("units", []):
                old_books = ((u.get("resources") or {}).get("books")) or []
                u["resources"] = build_resources("clang" if subj == "cpp" else subj, keep_books=old_books)
        d["github_resources"] = [
            {"repo": r[0], "stars": r[1], "url": f"https://github.com/{r[0]}", "note": r[2]}
            for r in GH.get(subj, [])
        ]
        d["resources_fetched_at"] = FETCHED_AT
        mf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        top = GH.get(subj, [])
        top_s = f"{top[0][0]} ({top[0][1]}★)" if top else "N/A"
        print(f"{subj:13s} 更新 {changed:2d} 章 | top={top_s}")

    print()
    print("=== 各学科 GitHub 最高 star 资源 ===")
    for subj in ["fundamentals", "tooling", "cpp", "python", "fullstack", "java",
                 "middleware", "spring", "database", "bigdata", "data", "ai", "clang"]:
        rs = GH.get(subj, [])
        if rs:
            print(f"  {subj:13s} {rs[0][1]:>7} ★ {rs[0][0]}")


if __name__ == "__main__":
    main()
