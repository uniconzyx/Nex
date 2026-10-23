# title: RRF 融合：BM25 与向量各错一条，融合后 Recall@1 从 5/6 回到 6/6
# BM25 用真实文本算；向量一路是本地模拟的「概念标签余弦」（不联网、不加载模型）。
# 这样能稳定复现两路互补：词法赢在错误码，向量赢在同义改写。
import math
import re

DOCS = [
    ("D1", "显存不足时先下调并发，再把最大上下文缩短，避免 OOM 触发驱动重置。", {"vram", "oom", "concurrency"}),
    ("D2", "ERR_4012 表示鉴权失败，token 过期要重新签发，重试没有意义。", {"auth", "token"}),
    ("D3", "cross-encoder 精排把查询和段落拼在一起过模型，延迟是双塔的十倍，只适合对前五十个候选做。", {"rerank", "latency"}),
    ("D4", "切块重叠取一成到一成半，切口落在句子中间会丢主语。", {"chunk", "overlap"}),
    ("D5", "错误处理总览：鉴权类错误不要重试，限流类错误应该退避，超时类错误要看幂等性；错误码要分类统计。", {"auth", "error", "retry"}),
    ("D5b", "RRF 用排名的倒数求和，能融合词法与向量两路结果，不需要分数归一。", {"fusion", "rrf"}),
    ("D6", "语义切块按句子边界打包，块长不固定，适合问答检索。", {"chunk", "semantic"}),
    ("D7", "向量检索对同义改写敏感，用户说 GPU 内存，文档写显存也能匹配。", {"dense", "vram"}),
    ("D8", "BM25 的 b 参数控制长度归一，长文档堆词会被压分。", {"bm25", "length"}),
]

QUERIES = [
    ("GPU 内存不够怎么办", "D1", {"vram", "oom"}),
    ("ERR_4012 报错", "D2", {"error", "auth"}),
    ("重排模型太慢能不能砍掉", "D3", {"rerank", "latency"}),
    ("分块重叠设多少", "D4", {"chunk", "overlap"}),
    ("两路召回怎么融合", "D5b", {"fusion"}),
    ("向量能不能匹配同义词", "D7", {"dense", "vram"}),
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


TOK = [tokenize(t) for _, t, _ in DOCS]
N = len(DOCS)
AVG = sum(len(t) for t in TOK) / N
DF = {}
for ts in TOK:
    for w in set(ts):
        DF[w] = DF.get(w, 0) + 1


def bm25(q, k1=1.5, b=0.75):
    out = []
    for ts in TOK:
        tf = {}
        for w in ts:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in tokenize(q):
            if w not in tf:
                continue
            idf = math.log((N - DF[w] + 0.5) / (DF[w] + 0.5) + 1)
            s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(ts) / AVG))
        out.append(s)
    return out


def dense(q_tags):
    out = []
    for _, _, tags in DOCS:
        inter = len(q_tags & tags)
        union = len(q_tags | tags)
        out.append(inter / union if union else 0.0)
    return out


def order(scores):
    return sorted(range(N), key=lambda i: (-scores[i], i))


def rrf(list_a, list_b, k=60):
    s = [0.0] * N
    for lst in (list_a, list_b):
        for rank, i in enumerate(lst, 1):
            s[i] += 1.0 / (k + rank)
    return s


def recall_at(scores, k):
    hit = 0
    for q, gold, tags in QUERIES:
        g = next(i for i, d in enumerate(DOCS) if d[0] == gold)
        hit += g in order(scores(q))[:k]
    return hit


bm25_r1 = recall_at(lambda q: bm25(q), 1)
dense_r1 = recall_at(lambda q: dense(next(t for qq, _, t in QUERIES if qq == q)), 1)
bm25_r3 = recall_at(lambda q: bm25(q), 3)
dense_r3 = recall_at(lambda q: dense(next(t for qq, _, t in QUERIES if qq == q)), 3)

fused = lambda q: rrf(order(bm25(q)), order(dense(next(t for qq, _, t in QUERIES if qq == q))))
rrf_r1 = recall_at(fused, 1)
rrf_r3 = recall_at(fused, 3)

print(f"{'方法':<12}{'Recall@1':>10}{'Recall@3':>10}{'失败查询':>22}")
fails_bm25 = [q for q, g, t in QUERIES
              if next(i for i, d in enumerate(DOCS) if d[0] == g) not in order(bm25(q))[:1]]
fails_dense = [q for q, g, t in QUERIES
               if next(i for i, d in enumerate(DOCS) if d[0] == g) not in order(dense(t))[:1]]
fails_rrf = [q for q, g, t in QUERIES
             if next(i for i, d in enumerate(DOCS) if d[0] == g) not in order(fused(q))[:1]]
print(f"{'BM25':<12}{bm25_r1:>8}/6{bm25_r3:>8}/6{', '.join(x[:6] for x in fails_bm25):>22}")
print(f"{'向量(模拟)':<10}{dense_r1:>8}/6{dense_r3:>8}/6{', '.join(x[:6] for x in fails_dense):>22}")
print(f"{'RRF':<12}{rrf_r1:>8}/6{rrf_r3:>8}/6{', '.join(x[:6] for x in fails_rrf):>22}")

print("\n逐条看名次的互补性：")
for q, gold, tags in QUERIES:
    g = next(i for i, d in enumerate(DOCS) if d[0] == gold)
    rb = order(bm25(q)).index(g) + 1
    rd = order(dense(tags)).index(g) + 1
    rf = order(fused(q)).index(g) + 1
    print(f"  {q:<18} BM25 {rb}  向量 {rd}  RRF {rf}   目标 {gold}")

print("\n读法：RRF 只用名次，不用原始分数——BM25 的分数是 0~10 的开区间，余弦是 0~1，")
print("直接加权求和会被量纲吃掉。1/(k+rank) 把两路压到同一尺度，k=60 是原论文的经验值。")
print("注意：融合只在两路『各自有独立正确的时候』有效；如果向量模型整体退化，")
print("RRF 会把噪声也稳定地融进来，此时应该先修召回而不是调 k。")
print("\n结论：混合检索的收益来自错误相关性低，而不是单路更强。上线前分别测两路的失败集，")
print("确认它们的失败查询不重叠，再决定要不要付双路索引的成本。")
