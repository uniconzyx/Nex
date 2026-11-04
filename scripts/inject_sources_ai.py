# -*- coding: utf-8 -*-
"""ai 学科来源锚点重写（批次 A1，14 章 62 条）。

依据：逐章 dump 出 concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
每条格式：`§x.y 小节标题 · 读什么`（分隔符为前后各一空格的中间点）。

本批除编号错位外，还清掉三类历史问题：
  1) 跑题：ai-ch01#2 原指 §3.3「训练数据的来源」，但该章 §3 是「优化器与调度」；
     ai-ch01#3 原指 §4.3「端到端的 AI 应用」，该章 §4 是「正则化与训练」；
     ai-ch02#2 原指 §2.3「图文数据采集」，该章 §2 是「池化与下采样」。
     → 全部改挂到真实小节（优化器 / 正则化 / 池化）。
  2) 编号越界：ai-ch04 只有 4 个 concept 文件，原 notes 引用 §2.3 / §3.3；
     ai-ch12 只有 3 个文件，原 notes 引用 §3.2 / §4.1；
     ai-ch13 只有 4 个文件，原 notes 引用 §1.1/§2.2/§3.1/§4.2 但标题全错；
     ai-ch14 只有 3 个文件，原 notes 引用 §1.4。
  3) 路径不存在：dify 的 `api/core/model_runtime/` 与 langchain 的
     `libs/langchain/langchain/` 均已改版，本批统一换成核实过的
     `api/core/model_manager.py`、`libs/core/langchain_core/`、`libs/text-splitters/`。
"""
import json
import os
import re

MANIFEST = "content/ai/_manifest.json"
CH_DIR = "content/ai"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，须框定范围）。"""
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- ai-ch01 深度学习基础：张量、前向与反向传播 ----------------
    # 仓库序：tensorflow / firecrawl / AutoGPT / transformers / dify / langchain
    "ai-ch01": [
        "§1.3 VJP（向量-雅可比积）：反向传播的真身 · 读 "
        "`tensorflow/python/eager/backprop.py`：`GradientTape` 记录前向的每个算子，"
        "反向时对每个算子调它注册的 `_vjp` 而不是拼整张雅可比矩阵——"
        "这正是本章「反向传播是逐算子 VJP 的链式叠加」那句的实现形态；"
        "先看 §1.2「计算图：前向建图，反向求导」再看这份源码，"
        "就明白「为什么不需要显式构造导数矩阵」",

        "§4.4 训练循环的标准骨架（含所有工程细节） · 读 "
        "`apps/api/src/index.ts`：抓取任务从「取种子 URL → 队列分发 → 抓取 → 落库」"
        "是一条带重试与限流的标准循环，与本章训练循环的"
        "「取 batch → 前向 → 反向 → step → 记录」是同构的骨架；"
        "对照 §4.5「梯度累积」，就能看出「一个 step 的边界」决定了重试与累积该放在哪层",

        "§4.3 归一化：BatchNorm vs LayerNorm · 看 "
        "`classic/original_autogpt/autogpt/app`：Agent 主循环每一轮都要把"
        "「目标 + 历史 + 最近观察」重新拼成上下文再送模型，"
        "这个「每轮重新归约一次」的动作与 BN/LN 的「每层重新标准化一次输入」是同一个思路——"
        "稳定输入的分布，只是 Agent 里稳定的是文本分布",

        "§1.1 张量不是「多维数组」这么简单 · 读 "
        "`src/transformers/models/llama/modeling_llama.py` 的 `forward`："
        "`(batch, seq, hidden)` 这条约定从 embedding 一路贯穿到 lm_head，"
        "中间所有的 `view`/`transpose` 都在维持它；"
        "配合 §1.2「计算图：前向建图」看，形状对不上时第一眼就该查这里",

        "§3.1 先明确问题：SGD 的三个痛点 · 读 "
        "`api/core/agent/cot_agent_runner.py` 与 `api/core/model_manager.py`："
        "应用层把「策略（怎么想）」与「模型（谁来算）」写成两处，"
        "对应本章 §3.6「学习率调度」也是「更新规则」与「步长规则」两件事——"
        "混在一起写就会出现「换了优化器但调度还按旧步长」的错配",

        "§3.4 Adam = Momentum + RMSProp（加偏差修正） · 读 "
        "`libs/core/langchain_core/runnables/base.py`：`invoke`/`batch`/`stream` 三件套"
        "把一类调用抽象成统一协议，而具体实现各自不同——"
        "这与 §3.2 Momentum 与 §3.3 RMSProp 各自贡献一半、"
        "再由 §3.4 拼成 Adam 的分层方式一致；"
        "配合 §3.5「AdamW 修了什么」，就能看清「组合」与「修正」必须分开做",
    ],
    # ---------------- ai-ch02 视觉与序列建模：CNN、RNN 到注意力机制 ----------------
    "ai-ch02": [
        "§1.1 卷积运算：局部连接与权值共享 · 读 "
        "`tensorflow/python/keras/layers/convolutional.py` 的 `Conv2D.call`："
        "里面就是「滑窗 + 乘加」，而且卷积核只有 `k²·C_in·C_out` 个参数、"
        "与输入尺寸无关——这就是 §1.1 与 §1.2「感受野与尺寸递推」里"
        "「参数量与计算量不是一回事」的源码依据",

        "§2.3 可运行代码：用张量形状核对公式 · 读 "
        "`apps/api/src/index.ts`：抓取结果里图片以 URL 形式保留，"
        "不同站点给的图片尺寸差异很大，"
        "这正是「为什么必须先核对张量形状再进网络」的真实场景——"
        "配合 §2.2「padding='same' / 'valid' 与 stride 尺寸公式」，"
        "就能算出同一张图在两种 padding 下差几格",

        "§3.2 LSTM / GRU 门控机制 · 看 "
        "`classic/original_autogpt/autogpt/app` 的主循环："
        "「保留什么进历史、丢掉什么、这一步要不要输出」三件事各由一个判断控制，"
        "与 LSTM 的遗忘门/输入门/输出门是同一套结构；"
        "区别只在 LSTM 用 `sigmoid` 连续门控，Agent 用规则或模型做离散取舍——"
        "这也解释了 §3.1「BPTT 梯度消失」为什么在 Agent 里变成「上下文越滚越长」",

        "§4.1 缩放点积注意力与缩放动机 · 读 "
        "`src/transformers/models/bert/modeling_bert.py` 的 `BertSelfAttention`："
        "进 softmax 前先乘 `1/√head_dim`，"
        "这正是 §4.1「不缩放会饱和、饱和就没梯度」的防御；"
        "配合 §4.2「多头、位置编码与复杂度对比」，"
        "就能看出多头的成本在多组投影而非 softmax 本身",

        "§1.2 感受野与尺寸递推 · 读 `api/core/model_manager.py`："
        "应用层按模型能力路由请求，一个模型能「看到」多长的上下文是硬性属性，"
        "与本章 §1.2「一层卷积只能看到 k×k、要靠堆层扩感受野」是同一类边界——"
        "区别是 CNN 可以靠加深扩，Decoder 只能靠换模型或改注意力实现",

        "§3.1 RNN 与 BPTT 的梯度消失（数学推导） · 读 "
        "`libs/core/langchain_core/messages/base.py`：把对话压成 token 序列时，"
        "越早的消息在 §3.1 的连乘里被乘的次数越多、衰减越狠；"
        "工程上靠「摘要 + 关键信息单独存」绕过，"
        "对照 §3.2「LSTM 门控」就能说清两种「保长期信息」方案的本质差别",
    ],
    # ---------------- ai-ch03 Transformer 与大语言模型原理 ----------------
    "ai-ch03": [
        "§4.2 注意力效率工程：KV Cache / FlashAttention / MQA-GQA · 读 "
        "`tensorflow/python/ops/nn_ops.py` 的 `softmax`：数值稳定实现先减最大值再 `exp`，"
        "这是理解「注意力为什么不爆数值」的底层；"
        "再回到 §4.2 的 KV Cache——它省的是重算，"
        "而数值稳定省的是溢出，两者是同一块矩阵乘法的两个不同成本项",

        "§2.1 为什么需要位置编码 & 正弦式 · 读 "
        "`apps/api/src/index.ts` 的 markdown 清洗：去掉导航与广告后，"
        "进入上下文的 token 顺序被彻底改变，而顺序正是位置编码要表达的东西；"
        "配合 §2.3「RoPE：把位置旋转进隐空间」，"
        "就能说清「清洗改的是内容与顺序、位置编码改的是顺序的表示」",

        "§4.2 注意力效率工程（续）：KV Cache 的显存代价 · 看 "
        "`classic/original_autogpt/autogpt/app` 的记忆管理：历史太长就摘要、"
        "关键信息单独存，与本章「KV Cache 随序列线性增长」是同一约束的两种应对——"
        "一个从显存侧省、一个从上下文侧省；"
        "对照 §3.2「残差 + LayerNorm 的梯度路径」，"
        "还能看出「层数越深、KV 越多」为什么让长上下文成本翻倍",

        "§1.1 自注意力：从序列到「集合加权」的映射 · 读 "
        "`src/transformers/models/bert/modeling_bert.py` 的 `BertSelfAttention`："
        "`query`/`key`/`value` 三个线性层 + `softmax(QKᵀ/√d)V`，与本章公式逐行对应；"
        "注意它进 softmax 前先乘 `1/√head_dim`，"
        "正是 §1.1 里「不缩放会饱和」的防御",

        "§3.1 Encoder-Decoder vs Decoder-only · 读 "
        "`api/core/rag/retrieval/dataset_retrieval.py`：RAG 把检索片段拼进 prompt，"
        "走的是 Decoder-only 的单向注意力——模型只能在已生成的上下文里做「软对齐」，"
        "这决定了本章 §3.1 里两种架构在「读长文」上的能力差异；"
        "对照 §3.2 的 Pre-LN 残差，就明白为什么 Decoder-only 能堆到很深",

        "§2.3 RoPE：把位置「旋转」进隐空间 · 读 "
        "`libs/text-splitters/langchain_text_splitters/character.py`："
        "切块时保留的 `chunk_overlap` 就是在人为制造「位置重叠」，"
        "而模型侧靠 RoPE 的角度差分辨「谁在谁前面几个位置」——"
        "一边是数据侧造位置关系、一边是模型侧编码位置关系；"
        "配合 §2.2「正弦编码与 RoPE 的对照」代码，"
        "就能看出 RoPE 为什么能外推到训练时没见过的长度",
    ],
    # ---------------- ai-ch04 高效微调与对齐：LoRA、RLHF 与 DPO ----------------
    "ai-ch04": [
        "§1.1 主题一：显存四件套——权重、梯度、优化器状态、激活 · 读 "
        "`tensorflow/python/keras/layers/core.py` 的自定义 `Layer` 写法："
        "每一层在训练时除了权重还要存梯度和优化器槽位，"
        "前向的中间结果还要留着做反向——四件显存就是这样一层层堆出来的；"
        "带着这本账再读 §1.2「SFT 的数据构造与损失掩码」，"
        "就明白掩码省下的不只是损失、还有非 assistant 位置的激活",

        "§2.1 主题一：LoRA 的低秩假设、初始化与 target_modules · 读 "
        "`apps/api/src/index.ts` 的抓取管道：它把「抓取」与「清洗」两个职责"
        "拆成独立步骤、各自可替换，主流程只负责串起来——"
        "LoRA 的思路与此同构：不改主干（抓取器），只在旁边挂一个可训练的低秩增量（新步骤）；"
        "配合 §2.2「QLoRA 的四位量化与分页优化器」，"
        "就能说清「低秩」与「低比特」是省显存的两条独立轴",
        "§3.1 主题一：从人类偏好到奖励模型（Bradley-Terry） · 看 "
        "`classic/original_autogpt/autogpt/app`：Agent 用「这步好不好」的规则"
        "决定要不要重试，就是一个手写的奖励信号；"
        "本章要做的只是把这个手写规则换成训练出来的标量模型，"
        "差别在于 §3.2「PPO 的 KL 约束」——手写规则不会过拟合人类偏好，学出来的会",

        "§2.2 主题二：QLoRA 的四位量化与分页优化器 · 读 "
        "`src/transformers/models/llama/modeling_llama.py` 的 "
        "`LlamaDecoderLayer`：主干层结构固定、参数量占绝对大头，"
        "所以「量化冻结的主干 + 训练低秩增量」才划得来；"
        "配合 §2.1「LoRA 的低秩假设」，"
        "就知道 target_modules 为什么几乎只挑 `q_proj`/`v_proj` 这类方阵",

        "§4.2 主题二：选型原则——注知识用 RAG，改行为用微调 · 读 "
        "`api/core/rag/retrieval/dataset_retrieval.py`：检索层把外部知识"
        "按需拼进上下文、模型权重一点不动，这正是「注知识用 RAG」的工程形态；"
        "与 §4.1「DPO 的闭式推导与工程优势」并读，"
        "就形成「改行为才动权重」的完整判据",

        "§4.1 主题一：DPO 的闭式推导与工程优势 · 读 "
        "`libs/langchain_v1/langchain/chat_models/base.py`：同一套 chat 接口"
        "既能接「奖励模型 + PPO」的两段式，也能接「偏好对直接回归」的一段式，"
        "差别只在训练目标；"
        "对照 §3.2 里 PPO 需要的四个模型（策略/参考/奖励/价值），"
        "就能量化说明 DPO 省掉了哪两块显存",
    ],
    # ---------------- ai-ch05 提示工程与上下文工程 ----------------
    "ai-ch05": [
        "§3.1 一、四层手段：从「约定」到「强制」 · 读 "
        "`tensorflow/python/ops/nn_ops.py` 的 `softmax` 与 argmax 相关实现："
        "「在 logits 层直接屏蔽非法 token」这件事最终就落在这一步的算子链上，"
        "是本章四层手段里最强的一层；"
        "对照 §3.2「校验 - 重试 - 降级」就能看出，"
        "即便有约束解码也仍需要后置校验——语法合法不等于语义合法",

        "§4.5 五、Prompt 注入：结构性难题与纵深防御 · 读 "
        "`apps/api/src/index.ts`：抓来的网页正文与系统提示必须走不同通道，"
        "否则「数据」会被当成「命令」；"
        "这正是 §4.5 里「注入是结构性问题、不能靠提示词解决」的具体场景",

        "§2.3 三、CoT 什么时候反而有害 · 看 "
        "`classic/original_autogpt/autogpt/app` 的主循环：它每一步都强制输出思考再行动，"
        "在简单任务上就是纯浪费 token 与延迟；"
        "这正好印证本章「CoT 在任务本身不需要分步时有害」；"
        "对照 §2.1「CoT 为什么有效」，就能划出该不该强制思考的分界线",

        "§3.2 二、校验 - 重试 - 降级：唯一的健壮架构 · 读 "
        "`src/transformers/generation/logits_process.py`：`LogitsProcessor` 链"
        "按顺序改写 logits，每一步都可能把整段概率压没，"
        "所以即便加了约束解码，也必须在上层做「解析失败 → 重试 → 降级」；"
        "与 §3.3「约束解码的边界」并读，就能说清为什么约束不是银弹",

        "§2.1 一、CoT 为什么有效 · 读 `api/core/agent/cot_agent_runner.py`："
        "它把「思考 → 行动 → 观察」写成显式状态循环，"
        "与 CoT 的「把中间步骤写出来」是同一机制在不同尺度上的实现；"
        "配合 §2.2「CoT 家族的主要变体」，"
        "就能看出 self-consistency 只是在同一个循环里采样多次再表决",

        "§4.3 三、位置策略：lost in the middle · 读 "
        "`libs/core/langchain_core/prompts/chat.py`：`ChatPromptTemplate` 把"
        "system / human / ai 拆成独立消息槽，顺序由模板决定而不是拼接顺序；"
        "这给了「把关键信息固定放在首尾」一个可执行的落点；"
        "配合 §4.4「前缀缓存与 token 预算」，"
        "就能权衡「省钱的顺序」与「模型实际读到的顺序」为什么冲突",

    ],
    # ---------------- ai-ch06 RAG：向量检索与知识增强 ----------------
    "ai-ch06": [
        "§3.1 主题一：混合检索（向量 + BM25）与 RRF 融合 · 读 "
        "`tensorflow/python/ops/nn_ops.py`：向量检索的「相似」最终就是一次内积/余弦计算，"
        "而 BM25 走的是词频统计、完全不经过这一层——"
        "这正是本章「两路检索必须融合、不能互相替代」的底层原因；"
        "配合 §3.2「两阶段召回 + 重排」，"
        "就知道 RRF 只解决「怎么合」、不解决「合完还差」",

        "§1.2 主题二：分块（chunk）策略与粒度 · 读 "
        "`apps/api/src/index.ts` 的 HTML → markdown："
        "解析质量直接决定「切出来的块是否有语义完整性」，这是 RAG 效果的第一道闸；"
        "配合 §1.3 那段可运行代码，"
        "就能用同一份 markdown 试不同 `chunk_size` 看块边界怎么变",

        "§4.1 主题一：向量索引——HNSW / IVF / PQ 的召回-延迟-内存三角 · 看 "
        "`classic/original_autogpt/autogpt/app` 的记忆检索："
        "Top-K 片段拼接、带来源标注，是「拿什么进上下文」的最小实现；"
        "对照本章「检索不到必然答错」的判断，"
        "就能理解为什么召回率比排序精度更值得先优化",

        "§2.3 主题二：余弦 / 内积 / L2 的等价条件 · 读 "
        "`src/transformers/models/bert/modeling_bert.py` 的输出层："
        "同一句话取 `[CLS]` 还是 mean-pool 会得到不同向量，"
        "归一化前后三种度量的排序也会变；"
        "这正是 §2.2 那段可运行代码要证的事——"
        "工程上把 `normalize_embeddings=True` 写进配置，就是在强制走等价分支",

        "§1.1 主题一：RAG 的两条链路——索引与查询 · 读 "
        "`api/core/rag/index_processor/index_processor_base.py` 与 "
        "`api/core/rag/retrieval/dataset_retrieval.py`："
        "前者是离线索引链路、后者是在线查询链路，入口函数分居两个文件，"
        "这就是本章「索引与查询必须分开看」的代码证据；"
        "回读 §5.2「RAG 是一条漏斗，每一层都在漏」就明白为什么要分段评估",

        "§1.2 主题二：分块（chunk）策略与粒度（续） · 读 "
        "`libs/text-splitters/langchain_text_splitters/character.py` 与 "
        "`libs/text-splitters/langchain_text_splitters/markdown.py`："
        "前者按分隔符层级递归下切、后者按标题目录切，"
        "`chunk_overlap` 负责保留跨块上下文；"
        "这解释了本章「块要语义完整」为什么在有标题结构的文档上更容易做到",
    ],
    # ---------------- ai-ch07 Agent 开发：工具调用、记忆与多智能体 ----------------
    "ai-ch07": [
        "§2.3 主题三：工具设计的七条原则 · 读 "
        "`tensorflow/python/eager/backprop.py` 的算子注册表："
        "每个算子只暴露「名字 + 前向 + 反向」三件套、不暴露内部状态，"
        "这正是「好工具」的形状——职责单一、输入输出明确、无隐藏副作用；"
        "对照 §2.2「工具 schema 与参数强类型」，"
        "就能看出 schema 就是给模型看的「函数签名」",

        "§2.3 主题三：工具设计的七条原则（反面样本） · 读 "
        "`apps/api/src/index.ts`：「输入一个 URL、输出 markdown」这一个工具"
        "同时踩中「幂等」「超时」「限流」三条，是七条原则最好的反面教材；"
        "对照 §2.1「Function Calling 机制」就能看出，"
        "模型只负责选工具，超时与重试永远在服务端",

        "§1.2 主题二：ReAct 范式——推理与行动交替 · 看 "
        "`classic/original_autogpt/autogpt/app` 的 `run` 循环："
        "规划 → 调工具 → 观察 → 再规划，直到「无需再调用工具」为止，"
        "就是 ReAct 的字面实现；"
        "配合 §1.3「四种架构模式与『能用工作流就别用 Agent』判据」，"
        "就能判断什么时候该退回静态图",

        "§2.2 主题二：工具 schema 与参数强类型 · 读 "
        "`src/transformers/models/auto/tokenization_auto.py` 的 chat template 挂载点："
        "工具定义最终要被渲染进模型认识的模板里，各家模板不同，"
        "这正是本章「同一个工具定义换个模型就不 work」的原因；"
        "配合 §2.1「Function Calling 机制」，"
        "就知道 schema 该写到多细才既不丢信息又不撑爆上下文",

        "§3.1 主题一：记忆三层——工作记忆 / 短期记忆 / 长期记忆 · 读 "
        "`api/core/memory/token_buffer_memory.py`：`token_limit` 超了就丢最早的轮次，"
        "正是「短期记忆是窗口、不是仓库」的实现；"
        "这解释了本章「长期记忆必须外置」的必要性；"
        "配合 §3.2「写入-检索-遗忘策略」，"
        "就能说清为什么「只加不删」的记忆系统会越跑越慢",

        "§1.1 主题一：Agent 三要素——目标、工具、循环 · 读 "
        "`libs/core/langchain_core/tools/base.py`：`BaseTool` 把"
        "名称 + 描述 + 参数 schema + 执行函数四件套固定下来，"
        "模型只负责「选哪个、传什么」，执行永远在服务端；"
        "再读 `libs/core/langchain_core/runnables/base.py` 的 `invoke`/`stream`，"
        "就能看出「循环」在框架层被抽象成了可组合的链",
    ],
    # ---------------- ai-ch08 LLM 应用工程：推理优化、评测、可观测性与安全 ----------------
    "ai-ch08": [
        "§3.1 主题一：量化方案与精度取舍 · 读 "
        "`tensorflow/python/keras/layers/core.py`：把一层改成低比特权重"
        "等于改 `Dense` 里的 `kernel` 类型，`call` 里的矩阵乘不变但精度变了；"
        "这正是本章「量化不改结构、只改数值」的落点；"
        "配合 §3.2「模型路由、语义缓存与优化顺序」，"
        "就明白量化该排在路由与缓存之后——前两者省钱不改输出、量化会改",

        "§4.1 主题一：可观测性三件套与 AI 特有维度 · 读 "
        "`apps/api/src/index.ts`：「抓了什么、耗时多少、失败原因」三件事"
        "记在同一处，是排查「RAG 突然答不准」的第一手材料；"
        "对照 §4.2「线上评测与 LLM-as-Judge 校准」，"
        "就能看出离线指标好看但线上掉分的常见原因",

        "§5.1 主题一：OWASP LLM Top 10 与提示注入的纵深防御 · 看 "
        "`classic/original_autogpt/autogpt/app` 的工具执行层："
        "每一轮调用都要过权限与参数校验，"
        "不能假设「模型被对齐过就不会越界」；"
        "没有步数上限与超时就会无限循环烧 token——这是成本事故，也是拒绝服务面",

        "§4.2 主题二：线上评测与 LLM-as-Judge 校准 · 读 "
        "`src/transformers/trainer.py` 的 `evaluate`：指标计算与日志记录绑在训练循环上、"
        "每 `eval_steps` 吐一次，这套「在线指标 + 定期全量」的节奏可直接搬到推理侧；"
        "对应 §6.8「评测的最小骨架」，"
        "就知道最小可用版本只需要「样本集 + 打分器 + 趋势图」三件",

        "§3.2 主题二：模型路由、语义缓存与优化顺序 · 读 "
        "`api/core/model_manager.py`：同一份请求按 `provider/model` 路由到不同后端，"
        "这是本章「先做便宜的模型路由、再做语义缓存」里路由那一步的实现；"
        "配合 §6.5「语义缓存」，"
        "就能说清「缓存命中率」与「路由准确率」哪个更该先优化",

        "§5.2 主题二：数据合规：最小化、脱敏与可删除 · 读 "
        "`libs/core/langchain_core/output_parsers/`：解析失败要兜底、输出要过滤，"
        "不能假设模型一定守规矩——这是「输出侧合规」的最小实现；"
        "对照 §6.7「提示注入的基础防护」，"
        "就能拼出「输入过滤 → 模型 → 输出过滤」的完整链路",
    ],
    # ---------------- ai-ch09 生成模型：从自编码器到扩散 ----------------
    "ai-ch09": [
        "§3.1 前向过程：一条「闭式可算」的加噪链 · 读 "
        "`src/diffusers/schedulers/scheduling_ddpm.py`：`__init__` 里用 betas 累乘造出 "
        "`alphas_cumprod`（即 $\\bar\\alpha_t$ 表），`add_noise` 直接按闭式一次跳到第 t 步；"
        "对照 §3.2「反向过程与训练目标」，`step` 里那一步去噪就是 $L_{simple}$ 在推理时的用法",

        "§1.2 VAE：用 ELBO 把「生成」变成可优化目标 · 读 "
        "`ldm/models/diffusion/ddpm.py` 的 `p_losses` 与 `apply_model`："
        "潜空间扩散的主干是 VAE 编码器 + UNet，编码器负责「压到潜空间」、"
        "UNet 负责「在潜空间加噪去噪」，"
        "这正是本章「VAE 给出可优化的下界、扩散负责采样质量」的分工；"
        "再回看 §1.3「隐空间的性质：连续、解耦与『先验不匹配』」就明白压缩比的代价",

        "§3.3 采样：DDPM → DDIM → 引导 · 读 "
        "`models/diffusion.py`：`ddim_sample` 用「预测 $x_0$ 再按跳步子序列反推」"
        "的非马尔可夫过程，把 1000 步压到几十步而不改训练目标——"
        "这就是本章「DDIM 的边缘分布不变」那句",

        "§3.2 反向过程与训练目标：把「去噪」变成回归 · 读 "
        "`guided_diffusion/gaussian_diffusion.py`：`p_mean_variance` 是反向均值/方差的标准写法，"
        "`condition_mean` 的两个分支就是 CFG 的 "
        "$\\varepsilon_{uncond}+s(\\varepsilon_{cond}-\\varepsilon_{uncond})$；"
        "这直接印证 §3.3 里「引导强度 s 是在放大条件与无条件的差」",
    ],
    # ---------------- ai-ch10 训练工程与规模化 ----------------
    "ai-ch10": [
        "§3.3 并行策略：DP、TP、PP、EP 与 ZeRO/FSDP · 读 "
        "`deepspeed/runtime/zero/stage3.py` 与同目录 `stage_1_and_2.py`："
        "stage1 切优化器状态、stage2 再切梯度、stage3 连参数一起切，"
        "三阶段一比较，就知道「切得越细通信越多」这条边界在哪；"
        "配合 §3.2「显存账：训练时到底谁在吃显存」，"
        "就能对上「12 字节/参数」这个经验值",

        "§3.3 并行策略（续）：张量并行 · 读 "
        "`megatron/core/tensor_parallel/layers.py` 的列并行 / 行并行两个 Linear："
        "一个切输出维、一个切输入维，成对出现才能让中间结果不用 all-reduce；"
        "再读 `megatron/core/pipeline_parallel/schedules.py` 的 1F1B，"
        "就能对上 §3.3 里 $(P-1)/(M+P-1)$ 的空泡推导",

        "§2.4 有效 batch：梯度累积、分布式与「等价性」的边界 · 读 "
        "`google-research/tuning_playbook` 的「Batch size」一节："
        "它把「增大 batch 到多少就该同步调 lr」给了经验区间，"
        "并明确写出「换 batch 就要重调 lr、换优化器就要重扫一遍」这条边界；"
        "再读同书「Learning rate schedule」一节，"
        "就能对上 §2.2 里「warmup 长度要随 batch 变」的判据",

        "§1.3 残差与梯度路径：深层网络的「高速公路」 · 读 "
        "`model.py` 的 `Block`：`x + attn(ln1(x))` 与 `x + mlp(ln2(x))` 两条残差支路，"
        "是 Pre-LN 结构的最小完整样本；"
        "把它和 §1.2「归一化：把『每层的输入分布』钉住」并读，"
        "就明白为什么 Pre-LN 比 Post-LN 更不需要 warmup；"
        "同文件的 `train.py` 里 `get_lr` 二十行就是 warmup + cosine，可对照 §2.2",
    ],
    # ---------------- ai-ch11 模型服务化落地：从 train() 跑到线上不崩 ----------------
    "ai-ch11": [
        "§1.1 一个必须成对出现的参数对 · 读 "
        "`vllm/v1/core/sched/scheduler.py` 与 `vllm/v1/core/kv_cache_utils.py`："
        "`max_num_seqs` 与 `max_num_batched_tokens` 必须成对设置"
        "（一个卡并发条数、一个卡单步 token 预算），只调一个会让另一侧先撞墙；"
        "配合 §1.2「为什么等待窗口应该由延迟预算倒推」，就能算出这两个值该取多少",

        "§1.3 一个容易被忽略的细节：批内请求必须同构 · 读 "
        "`ggml/src/ggml-backend.cpp`：批处理要求所有张量的 stride 与类型一致，"
        "这就是「批内请求必须同构」在推理后端层的硬约束；"
        "而 `src/llama-context.cpp` 里按序列切分 batch 的做法，"
        "正是绕开这条约束的工业解法",

        "§2.1 五类必须拦的输入 · 读 "
        "`router/src/validation.rs`：长度、token 上限、参数范围、非法字符、`NaN` "
        "五类各自有独立校验函数，且都在进入推理前拦下——"
        "这就是本章「五类必须拦的输入」的原文；"
        "再读 `router/src/server.rs` 看它如何把错误转成 4xx 而不是 5xx",

        "§3.4 版本：模型状态必须能追溯与回滚 · 读 "
        "`src/main.cc`：模型仓库按版本号建目录、启动时显式加载指定版本，"
        "`--strict-model-config` 会在版本不全时直接拒绝启动；"
        "这正是本章「模型状态必须可追溯」的部署层落点；"
        "配合 §3.5「金丝雀：先让 5% 的流量试」，"
        "就能拼出「版本可切 + 流量可调」的灰度闭环",
    ],
    # ---------------- ai-ch12 SFT 数据工程 ----------------
    "ai-ch12": [
        "§1.2 二、为什么需要 schema 与模板三层 · 读 "
        "`src/transformers/tokenization_utils_base.py` 的 `apply_chat_template`："
        "它按角色拼 token、并用 `{% generation %}` 段标出该算 loss 的部分，"
        "非 assistant 内容置 -100——本章「模板三层」的第三层就在这里；"
        "配合 `src/transformers/models/llama/tokenization_llama.py` 的具体模板，"
        "就能把「格式漂移」追溯到模板版本变更",

        "§2.1 一、前两段：规则过滤与语义去重 · 读 "
        "`src/datasets/arrow_dataset.py` 的 `map`/`filter`："
        "`filter` 支持 `batched=True` 与多进程，"
        "正是本章「先按规则粗筛、再做语义去重」两段流水线要的吞吐能力；"
        "配合 §2.3「三、工程判据」，"
        "就知道去重阈值该怎么定才不至于把长尾样本一起删掉",

        "§3.1 一、难例挖掘与 Kappa 的必要性 · 读 "
        "`vllm/v1/engine/llm_engine.py` 的批量接口："
        "用强模型批量生成候选、再用规则或弱模型打分，"
        "是本章「合成数据规模化」的常见流水线；"
        "但生成质量要靠 §2.2「二、污染检测与留验隔离」守——"
        "强模型见过的题会被它自己答对，混进训练集就是污染",

        "§1.1 一、schema 样例、配比与格式漂移事故 · 读 "
        "`README.md` 里给出的对话格式：`[INST]` / `<<SYS>>` 标记与角色轮次是硬约定，"
        "换一个模板而不同步改数据，就是本章「格式漂移事故」的经典形态；"
        "先读 §1.2 的三层模板，再对照这份 README，"
        "就能把「schema 是什么」落到具体字符上",
    ],
    # ---------------- ai-ch13 推理引擎与量化部署 ----------------
    "ai-ch13": [
        "§1.2 二、PagedAttention 与复用 · 读 "
        "`vllm/v1/core/kv_cache_manager.py` 与 `vllm/v1/core/block_pool.py`："
        "KV Cache 按固定大小块分配、用块表映射逻辑位置，"
        "`block_pool` 负责块申请与回收、`kv_cache_manager` 负责前缀命中判定，"
        "两者合起来才消除「预留最大长度」造成的碎片；"
        "配合 §1.1「一、显存账与碎片问题」，"
        "就能算出碎片到底吃掉了多少可用显存",

        "§3.2 二、AWQ、GGUF 与怎么选 · 读 "
        "`convert_hf_to_gguf.py` 与 `ggml/src/ggml-quants.c`："
        "前者把 HF 权重转成 GGUF 容器、后者实现 Q4_K/Q5_K 等分组量化，"
        "证实本章「GGUF 是格式，不是量化算法」——同一个 GGUF 文件里可装不同量化类型；"
        "对照 §4.8「现场七：GGUF 是格式，不是量化算法」正好互为印证",

        "§3.1 一、位宽账与 GPTQ · 读 `README.md` 与 `mlc-llm` 的编译式部署路线："
        "它走的是「把模型编译成目标硬件 kernel」而不是「通用 runtime 解释执行」，"
        "两条路线对量化的态度截然不同——编译式把位宽当作布局的一部分、"
        "解释式把位宽当作一层可插拔的算子；"
        "这正是本章「先算位宽账、再选算法与部署形态」里那本账的两个分支",

        "§4.11 现场十：首 token 延迟和每 token 延迟是两个指标 · 读 "
        "`src/transformers/generation/utils.py` 的 `generate`："
        "prefill 与 decode 分别走不同的 `forward` 形状，"
        "所以 TTFT 由 prefill 长度决定、TPOT 由 decode 的 batch 与带宽决定，"
        "两者不可能用同一个手段一起压下来；"
        "配合 §4.10「现场九：批大小不是越大越好」，就明白调大 batch 只改善 TPOT",
    ],
    # ---------------- ai-ch14 多模态落地 ----------------
    "ai-ch14": [
        "§1.1 一、对比学习与投影层 · 读 "
        "`src/transformers/models/llama/modeling_llama.py` 的最后一层投影："
        "文本塔把隐状态投到词表空间，CLIP 把图文各投到同一对比空间，"
        "两者都是「先把表示拉到目标空间、再算相似度」；"
        "认识这一点，就能理解 §1.1 里「投影层与归一化决定能不能对齐」；"
        "对照 §1.2「二、检索与模态鸿沟」就明白为什么换塔必须重算索引",

        "§1.2 二、检索与模态鸿沟 · 读 "
        "`clip/model.py` 与 `clip/clip.py`：`build_model` 里视觉塔与文本塔各出一个向量，"
        "再经 `ln_final` 投影后做归一化点积——这就是「对比学习把两种模态拉到同一球面」；"
        "`clip.py` 的 `tokenize` 决定了文本侧输入长度上限，"
        "而视觉侧的分辨率上限在视觉塔里，两侧不对称正是「模态鸿沟」的来源",

        "§1.2 二、检索与模态鸿沟（续） · 读 "
        "`internvl_chat/README.md`：它给出了图像切块（dynamic tiling）后"
        "每块各占多少视觉 token，切得越细越准但成本线性上涨——"
        "这正是本章「鸿沟不只在语义，也在分辨率与 token 预算」的落点；"
        "配合 §3.1「一、形态与图像预处理成本」，就能把预处理成本算进端到端预算",

        "§2.1 一、链路拆解与成本口径 · 读 `README.md` 与 `omnitool/omniparserserver`："
        "版面检测 → 元素识别 → VLM 理解三段，每段的输入输出尺寸直接决定成本口径；"
        "这正是本章「OCR→VLM 流水线的钱花在哪一段」的现成样本；"
        "对照 §3.2「二、延迟预算、成本模型与兜底」，"
        "就能定位误识别该在哪一段拦截、兜底该挂在哪一段之后",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        raw = fb.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8"))

    changed = 0
    for ch in data.get("chapters", []):
        cid = ch.get("id") or ch.get("chapter_id")
        notes = NOTES.get(cid)
        if not notes:
            continue
        res = ch.get("resources") or {}
        cur = res.get("github_notes") or []
        if len(cur) != len(notes):
            print(f"!! {cid}: 原 {len(cur)} 条 / 新 {len(notes)} 条，不匹配，跳过")
            continue
        if cur == notes:
            print(f"== {cid}: 无变化")
            continue
        res["github_notes"] = notes
        ch["resources"] = res
        ok, msg = rewrite_goals_table(cid, notes)
        print(f"{'ok' if ok else '!!'} {cid}: manifest 已改，goals {msg}")
        changed += 1

    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("")
    print(f"\n共改写 {changed} 章")


if __name__ == "__main__":
    main()
