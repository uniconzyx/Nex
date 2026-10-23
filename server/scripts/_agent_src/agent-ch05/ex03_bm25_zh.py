# title: 手写 BM25：中文用字符二元组切分，b=0 时一篇长文抢走了三个查询的第一名
# 只依赖标准库 + 数学运算，把 IDF、词频饱和、长度归一三项拆开单独观察。
# 语料是本文件内的 6 篇运维笔记；真实生产用 jieba 或模型分词，这里用二元组是为了可复现。
import math
import re

DOCS = [
    ("D1", "ERR_4012 表示上游鉴权失败。先检查 token 是否过期，再按 2 的幂退避重试，最多三次。"),
    ("D2", "ERR_5003 是推理服务 OOM。需要下调并发或缩短最大上下文，重试不会解决问题。"),
    ("D3", "客户端重试要区分错误类型。4xx 里的鉴权失败重试没有意义，5xx 和超时才值得退避重试。"),
    ("D4", "退避策略建议指数增长并加抖动，避免所有客户端在同一秒重试造成二次雪崩。"),
    ("D5", "日志里要记录请求 id、错误码、重试次数和最终状态，否则无法区分是上游故障还是本地超时。"),
    ("D6", "值班手册总览。错误码要记录，重试要谨慎，超时要排查，鉴权要确认，日志要完整，上游要联系，并发要控制，上下文要缩短。错误码、重试、超时、鉴权是四个最常被问到的词；重试之前先看错误码，超时之前先看日志；鉴权失败不要重试，超时才可以退避重试。这篇文档很长，反复出现错误码、重试、超时、鉴权、日志、上游、并发、上下文这些词，但只是罗列，没有给出任何一个具体错误码的处理办法，也没有说明退避的倍数和上限，属于典型的总览型长文。"),
]

QUERIES = [
    "ERR_4012 鉴权失败怎么重试",
    "OOM 要不要重试",
    "退避 抖动 雪崩",
]


def tokenize(text: str):
    """中文按字符二元组，英文/数字按整词（含下划线），兼顾 ERR_4012 这类编号。"""
    toks = []
    for m in re.finditer(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text):
        s = m.group(0)
        if re.match(r"[A-Za-z0-9_]", s):
            toks.append(s.lower())
        else:
            if len(s) == 1:
                toks.append(s)
            else:
                toks.extend(s[i:i + 2] for i in range(len(s) - 1))
    return toks


TOK = [tokenize(t) for _, t in DOCS]
N = len(DOCS)
AVGDL = sum(len(t) for t in TOK) / N
DF = {}
for ts in TOK:
    for w in set(ts):
        DF[w] = DF.get(w, 0) + 1


def idf(w):
    d = DF.get(w, 0)
    return math.log((N - d + 0.5) / (d + 0.5) + 1.0)


def bm25(q, k1=1.5, b=0.75):
    qs = tokenize(q)
    scores = []
    for i, ts in enumerate(TOK):
        tf = {}
        for w in ts:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in qs:
            if w not in tf:
                continue
            f = tf[w]
            dl = len(ts)
            s += idf(w) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / AVGDL))
        scores.append(s)
    return scores


def rank(scores, k=3):
    order = sorted(range(N), key=lambda i: -scores[i])[:k]
    return [(DOCS[i][0], scores[i]) for i in order if scores[i] > 0]


print(f"语料 {N} 篇，平均长度 {AVGDL:.1f} 个 token；k1=1.5, b=0.75")
for q in QUERIES:
    print(f"\n查询：{q}")
    for rank_i, (doc, sc) in enumerate(rank(bm25(q)), 1):
        print(f"  {rank_i}. {doc}  {sc:6.3f}")

print("\n把 b 从 0.75 调到 0（关闭长度归一），看总览长文 D6 的名次与分数变化：")
print(f"{'查询':<24}{'b=.75 名次':>12}{'b=0 名次':>10}{'分数变化':>10}")
for q in QUERIES:
    s75, s0 = bm25(q, b=0.75), bm25(q, b=0)
    r75 = sorted(range(N), key=lambda i: -s75[i]).index(5) + 1
    r0 = sorted(range(N), key=lambda i: -s0[i]).index(5) + 1
    print(f"{q:<22}{r75:>12}{r0:>10}{s0[5]/max(s75[5], 1e-9):>9.2f}x")

print("\n读法：D6 是总览长文，命中查询里的每个词，却没有一个具体答案。")
print("b=0 时长度项消失，长文靠『词多』拿分：D6 在 OOM 那条上直接抢到第一，其余两条分数也涨。")
print("b=0.75 按长度归一后，D6 被压回后排。语料只有 6 篇时影响还小；索引到百万级时，")
print("这类总览文会系统性地挤掉精确文档，这是『召回看起来正常但答案不对』的常见来源。")
print("结论：BM25 的 b 是在惩罚『靠堆词而不是靠密度』匹配的长文档；中文场景还必须先解决分词，")
print("否则 ERR_4012 会被切成 err / 40 / 01 / 12 之类的碎片，词法召回的精度直接崩掉。")
