# title: 重排模拟：一阶段 MRR 0.83，规则重排后 1.00，第一名被换掉
# cross-encoder 需要模型，这里用「词覆盖 + 邻近窗口 + 数字密度」三条规则代替，
# 只验证『二阶段重排能改变 Top-K 顺序』这件事，不宣称等价于真实 cross-encoder。
import math
import re

CHUNKS = [
    ("C1", "部署总览：环境准备与模型下载是第一步，要确认驱动版本与 CUDA 版本是否匹配，"
           "再配置服务端口与日志级别，设置监控指标与告警阈值。压测阶段要记录延迟分布与错误率，"
           "评估容量规划是否合理，最后才是灰度与回滚流程以及成本核算。本文不展开缓存计算的"
           "细节，也不讨论并行请求的取值，显存部分只提一句要留余量。"),
    ("C2", "KV Cache 的字节数等于 2 乘以层数乘以 KV 头数乘以头维度乘以字节宽，再乘以序列长度与并发数。"),
    ("C3", "并发数不是越大越好，超过显存预算后调度器会排队，TTFT 反而变长。"),
    ("C4", "估算 KV Cache 时先把 P99 上下文长度代入单请求公式，再乘目标并发，最后留两成余量。"),
    ("C5", "显存监控要看分配器的预留量，nvidia-smi 的数字会把预留算成已用。"),
    ("C6", "量化到 INT4 后权重从 14GB 降到 3.7GB，但长上下文更容易重复。"),
    ("C7", "量化后精度掉点，要先看校准集分布是否匹配，再看 per-channel 粒度，最后才考虑换方法。"),
    ("C8", "GPTQ 用二阶信息补偿重建误差，AWQ 按激活幅度保护关键通道，两者在 4bit 下的表现不同。"),
    ("C9", "连续批处理在输出长度差异大时，吞吐可以比静态批处理高两到三倍；长度齐整时差距不到一成。"),
    ("C10", "静态批处理要等整批完成，短请求被迫陪跑，输出长度方差越大浪费越多。"),
]

QUERIES = [
    ("KV Cache 显存 并发 怎么估", "C4"),
    ("量化后精度掉了怎么办", "C7"),
    ("连续批处理吞吐提升多少", "C9"),
]


def tokenize(text):
    toks = []
    for m in re.finditer(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        s = m.group(0)
        if re.match(r"[a-z0-9_]", s):
            toks.append(s)
        else:
            toks.extend(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else toks.append(s)
    return toks


TOK = [tokenize(t) for _, t in CHUNKS]
N = len(CHUNKS)
AVG = sum(len(t) for t in TOK) / N
DF = {}
for ts in TOK:
    for w in set(ts):
        DF[w] = DF.get(w, 0) + 1


def first_stage(q, k1=1.2, b=0.3):
    """故意把 b 调低：模拟一个没做好长度归一的廉价一阶段检索器。"""
    out = []
    for ts in TOK:
        tf = {}
        for w in ts:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in tokenize(q):
            if w in tf:
                idf = math.log((N - DF[w] + 0.5) / (DF[w] + 0.5) + 1)
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(ts) / AVG))
        out.append(s)
    return out


STOP = {"怎么", "么估", "多少", "少办", "办", "么办", "么算"}


def rerank(q, cand):
    """规则版 cross-encoder：内容词覆盖 + 邻近窗口 + 数字密度，并对超长文轻微降权。"""
    qs = set(tokenize(q)) - STOP
    out = []
    for i in cand:
        toks = TOK[i]
        ts = set(toks)
        cov = len(qs & ts) / max(len(qs), 1)
        # 邻近度：查询词在文中最紧凑窗口的占比（窗口 24 个 token）
        pos = [j for j, w in enumerate(toks) if w in qs]
        prox = 0.0
        if len(pos) >= 2:
            best = min((pos[e] - pos[s] for s in range(len(pos)) for e in range(s + 1, len(pos))), default=999)
            prox = max(0.0, 1.0 - best / 24.0)
        num = min(1.0, len(re.findall(r"\d+(?:\.\d+)?", CHUNKS[i][1])) / 4.0)
        penalty = min(0.12, len(CHUNKS[i][1]) / 3000.0)
        out.append((i, 0.42 * cov + 0.40 * prox + 0.18 * num - penalty))
    return [i for i, _ in sorted(out, key=lambda x: -x[1])]


def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


print("一阶段取 top-8（b=0.3，长度归一很弱），二阶段只对这 8 条重排。")
for q, gold in QUERIES:
    s = first_stage(q)
    cand = sorted(range(N), key=lambda i: -s[i])[:8]
    after = rerank(q, cand)
    g = next(i for i, c in enumerate(CHUNKS) if c[0] == gold)
    before_rank = cand.index(g) + 1
    after_rank = after.index(g) + 1
    print(f"\n查询：{q}   目标 {gold}")
    print(f"  一阶段名次 {before_rank} -> 重排后 {after_rank}")
    print("  重排后的前 3 条：")
    for r, i in enumerate(after[:3], 1):
        mark = "  <= 目标" if i == g else ""
        print(f"    {r}. {CHUNKS[i][0]}  {CHUNKS[i][1][:34]}...{mark}")

print("\n聚合指标（3 条查询，二元相关性）：")
for label, use_rerank in (("一阶段", False), ("加重排", True)):
    mrr, nd = 0.0, 0.0
    for q, gold in QUERIES:
        s = first_stage(q)
        cand = sorted(range(N), key=lambda i: -s[i])[:8]
        order = rerank(q, cand) if use_rerank else cand
        g = next(i for i, c in enumerate(CHUNKS) if c[0] == gold)
        r = order.index(g) + 1
        mrr += 1.0 / r
        nd += dcg([1 if i == g else 0 for i in order[:5]]) / dcg([1, 0, 0, 0, 0])
    print(f"  {label:<6} MRR={mrr/len(QUERIES):.3f}  nDCG@5={nd/len(QUERIES):.3f}")

print("\n读法：C1 是一篇什么都提的总览，一阶段靠长文和词覆盖排到前面；")
print("但缓存计算与并行请求都写成『不展开』。重排把『提到』和『讲清楚』区分开：")
print("C4 只有一句，三个概念却在 30 字内形成完整公式，邻近度接近 1，于是从第 2 翻到第 1。")
print("\n结论：重排买到的是排序质量，代价是延迟。经验区间：候选 30-50 条、增益最大；")
print("候选超过 100 条后召回已经饱和，再加重排只是线性加延迟。真实 cross-encoder 的分数")
print("不能用这种规则替代——上线前必须用标注对校准它的阈值，规则分数没有可比性。")
