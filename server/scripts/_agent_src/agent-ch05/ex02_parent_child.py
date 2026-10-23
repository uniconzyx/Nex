# title: 父子块：父块直检被长文稀释，子检索父喂把 5/6 拉回 6/6
# 三种取上下文的方式对同一批查询做对比：父块直检、子块直喂、子检索父喂。
# 语料自造（6 篇部署笔记，每篇 7 句，其中 3 篇是同主题干扰项）；全部本地计算。
import re
import numpy as np

PARENTS = {
    "P1": [
        "单卡部署第一步是算显存账本，权重、KV Cache、激活三块要分开估。",
        "7B 模型以 FP16 加载时，权重约占 14 GB。",
        "在 4090 的 24 GB 显存上，减去权重后只剩约 9 GB 可以留给 KV Cache 和激活。",
        "如果上下文开到 8192、并发 16，KV Cache 需要约 8 GB。",
        "此时峰值显存会贴近上限，任何长度抖动都会触发 OOM。",
        "把并发降到 8，KV Cache 减半，余量才够应付偶发的长请求。",
        "所以容量规划要把 P99 长度而不是平均长度代入公式。",
    ],
    "P2": [
        "量化不是免费的压缩，它用数值精度换显存和带宽。",
        "INT4 量化把权重压到约 3.7 GB。",
        "但它同时降低了数值精度，长上下文下更容易出现重复与胡言。",
        "AWQ 按激活幅度保护关键通道，4bit 下通常比朴素 round-to-nearest 稳。",
        "GPTQ 用二阶信息逐层补偿重建误差，小模型上更容易掉点。",
        "量化粒度也重要，per-channel 通常优于 per-tensor。",
        "是否量化要按任务分布评测，不能只看困惑度。",
    ],
    "P3": [
        "批处理策略决定了同一张卡上能同时服务多少请求。",
        "静态批处理要等一批请求凑齐或超时才发车。",
        "批内最长的那条决定了整批的完成时间，短请求被迫陪跑。",
        "连续批处理在新请求到达时立即插队，不必等整批结束。",
        "它的收益在输出长度差异大时最明显。",
        "输出长度齐整时，连续批处理与静态批处理的差距会缩小到一成以内。",
        "压测要用真实长度分布，否则会高估吞吐。",
    ],
    "P4": [
        "线上显存监控要同时采集分配量、预留量和实际占用。",
        "只看 nvidia-smi 的显存数字，会把缓存分配器的预留当成真实使用。",
        "4090 这类消费卡没有 ECC，显存吃紧时表现为驱动重置而不是干净报错。",
        "告警阈值建议设在可用显存的八成，给突发并发留缓冲。",
        "监控粒度要细到请求级别，否则无法定位是哪个租户打满了卡。",
        "长上下文请求要单独打标签，它们的 KV Cache 占用是短请求的十几倍。",
        "把并发配额和显存水位联动，比事后扩容更省钱。",
    ],
    "P5": [
        "量化模型的运维和浮点模型不完全一样。",
        "INT4 权重在推理前要反量化，算子融合没做好会拖慢首 token。",
        "AWQ 的校准集如果只覆盖英文，中文长文的精度损失会被低估。",
        "GPTQ 在 batch 变大时可能出现数值不稳定，需要限制最大批。",
        "量化版本要和浮点版本共用一套评测集，指标差异超过阈值就不发。",
        "回滚路径必须保留一份未量化权重，否则出问题只能等重训。",
        "版本号里要带量化方法，避免灰度时把两种权重混在一个池子里。",
    ],
    "P6": [
        "压测脚本首先要定义清楚指标口径。",
        "TTFT 是从请求发出到第一个 token 的时间，包含排队和预填充。",
        "TPOT 是后续每个 token 的平均间隔，主要由解码阶段决定。",
        "P99 延迟对样本量敏感，几百个请求估出来的 P99 不可信。",
        "输出长度分布要按线上真实流量采样，不能用固定长度。",
        "错误率要分状态码统计，超时和限流不能混在一起看。",
        "压测结论要写清硬件、模型版本、并发数和长度分布四要素。",
    ],
}

# (query, 父块, 事实句下标, 条件句下标)
QUERIES = [
    ("4090 上 7B 还能留多少显存给 KV Cache", "P1", 2, 1),
    ("峰值显存什么时候会贴近上限", "P1", 4, 3),
    ("INT4 量化后权重占多少", "P2", 1, 0),
    ("AWQ 为什么比朴素量化稳", "P2", 3, 2),
    ("连续批处理什么时候收益最明显", "P3", 4, 3),
    ("输出长度齐整时差距多大", "P3", 5, 4),
]


def bigrams(s):
    s = re.sub(r"\s+", "", s)
    return [s[i:i + 2] for i in range(len(s) - 1)]


def tfidf(texts):
    toks = [bigrams(t) for t in texts]
    vocab = {}
    for ts in toks:
        for t in set(ts):
            vocab.setdefault(t, len(vocab))
    X = np.zeros((len(texts), len(vocab)))
    df = np.zeros(len(vocab))
    for i, ts in enumerate(toks):
        for t in ts:
            X[i, vocab[t]] += 1
        for t in set(ts):
            df[vocab[t]] += 1
    idf = np.log((1 + len(texts)) / (1 + df)) + 1
    X *= idf
    n = np.linalg.norm(X, axis=1, keepdims=True)
    n[n == 0] = 1
    return X / n, vocab, idf


def qvec(q, vocab, idf):
    v = np.zeros(len(vocab))
    for t in bigrams(q):
        if t in vocab:
            v[vocab[t]] += 1
    v *= idf
    n = np.linalg.norm(v)
    return v / n if n else v


children = []
for pid, sents in PARENTS.items():
    for i, s in enumerate(sents):
        children.append({"pid": pid, "idx": i, "text": s})
parents = [{"pid": pid, "text": "".join(sents)} for pid, sents in PARENTS.items()]

Xc, vc, ic = tfidf([c["text"] for c in children])
Xp, vp, ip = tfidf([p["text"] for p in parents])


def run_parent_only(k=1):
    fact = cond = 0
    chars = 0.0
    for q, pid, fi, ci in QUERIES:
        top = np.argsort(-(Xp @ qvec(q, vp, ip)))[:k]
        picked = [parents[i]["pid"] for i in top]
        chars += sum(len(parents[i]["text"]) for i in top)
        fact += pid in picked
        cond += pid in picked
    return fact, cond, chars / len(QUERIES)


def run_child_only(k):
    fact = cond = 0
    chars = 0.0
    for q, pid, fi, ci in QUERIES:
        top = np.argsort(-(Xc @ qvec(q, vc, ic)))[:k]
        ctx = [children[i] for i in top]
        chars += sum(len(c["text"]) for c in ctx)
        fact += any(c["pid"] == pid and c["idx"] == fi for c in ctx)
        cond += any(c["pid"] == pid and c["idx"] == ci for c in ctx)
    return fact, cond, chars / len(QUERIES)


def run_child_to_parent(k_child=3, k_parent=1):
    fact = cond = 0
    chars = 0.0
    for q, pid, fi, ci in QUERIES:
        top = np.argsort(-(Xc @ qvec(q, vc, ic)))[:k_child]
        picked = []
        for i in top:
            p = children[i]["pid"]
            if p not in picked:
                picked.append(p)
        picked = picked[:k_parent]
        chars += sum(len(next(p["text"] for p in parents if p["pid"] == x)) for x in picked)
        fact += pid in picked
        cond += pid in picked
    return fact, cond, chars / len(QUERIES)


rows = [
    ("父块 top-1", *run_parent_only(1)),
    ("子块 top-1", *run_child_only(1)),
    ("子块 top-4", *run_child_only(4)),
    ("子检索→父块", *run_child_to_parent()),
]

print("6 条查询，每条都需要「事实句 + 它的前提句」同时在场才算能回答：")
print(f"{'取法':<12}{'事实命中':>9}{'条件完整':>9}{'平均上下文字符':>15}")
for name, f, c, ch in rows:
    print(f"{name:<10}{f:>9}/6{c:>9}/6{ch:>15.0f}")

c1 = run_child_only(1)
c4 = run_child_only(4)
pc = run_child_to_parent()
p1 = run_parent_only(1)
print(f"\n父块直检有 {6-p1[0]} 条查不到：整篇 200 多字的相似度被同主题干扰篇盖过，")
print("查询说的是「KV Cache 留多少」，父块里还混着 OOM 和 P99，向量被摊薄。")
print(f"子块 top-1 只用 {c1[2]:.0f} 字，条件完整率 {c1[1]}/6：命中的句子带「此时」「它」，前提在邻句。")
print(f"子块 top-4 补到 {c4[1]}/6，字数 {c4[2]:.0f} 已接近父块，说明加 k 是在用钱买完整。")
print(f"子检索父喂：{pc[0]}/6、{pc[1]}/6、{pc[2]:.0f} 字——匹配精度取子块，阅读完整性取父块。")
print("\n结论：父块不是「更大的块」，而是二级寻址结构。索引建在子块上，上下文预算花在父块上。")
print("注意：父块过大会稀释注意力，经验做法是父块 800-1500 字、子块 120-250 字，比例约 5:1。")
