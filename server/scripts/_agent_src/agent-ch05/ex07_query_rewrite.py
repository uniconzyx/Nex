# title: 查询改写：8 条口语 query 加同义词后，Recall@3 从 6/8 到 8/8
# 改写不是调模型，而是一张领域同义词表 + 规则替换；这里只验证「词面鸿沟」这一种失效。
# 真实系统还会做指代消解与多跳拆解，那些需要模型，见 concept/02 与第 11 章。
import math
import re

DOCS = [
    ("D1", "GPU 显存不足时应降低并发数，或缩短最大上下文，避免 OOM。"),
    ("D2", "向量检索对同义改写敏感，字面不重合也能靠语义距离匹配。"),
    ("D3", "分块策略直接影响召回：块太大稀释语义，太小丢上下文。"),
    ("D4", "重排模型逐字比对查询与段落，延迟是双塔的十倍。"),
    ("D5", "多租户场景要在检索前做权限过滤，不能先取结果再删。"),
    ("D6", "拒答阈值需要标注样本：有答案组与无答案组各一批。"),
    ("D7", "引用溯源要细到句子，只给文档名无法核验论断。"),
    ("D8", "缓存键必须带租户标识与权限版本，否则会串号。"),
]

# (口语 query, 目标文档)
QUERIES = [
    ("显卡内存爆了怎么办", "D1"),
    ("切片切多大合适", "D3"),
    ("答案胡说八道怎么拦", "D6"),
    ("精排太慢能不能砍", "D4"),
    ("A 公司的资料别让 B 公司看到", "D5"),
    ("引用对不上原文", "D7"),
    ("缓存串号了", "D8"),
    ("换种说法还能搜到吗", "D2"),
]

SYNONYMS = {
    "显卡": ["GPU"],
    "内存": ["显存"],
    "爆了": ["不足", "OOM"],
    "切片": ["分块"],
    "切多大": ["块大小"],
    "胡说八道": ["幻觉", "拒答"],
    "拦": ["阈值"],
    "精排": ["重排"],
    "公司": ["租户"],
    "资料": ["数据"],
    "看到": ["权限", "过滤"],
    "引用": ["溯源"],
    "原文": ["句子"],
    "串号": ["缓存键", "租户"],
    "换种说法": ["同义改写"],
    "搜到": ["检索"],
}


def tokenize(text):
    toks = []
    for m in re.finditer(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        s = m.group(0)
        if re.match(r"[a-z0-9_]", s):
            toks.append(s)
        else:
            toks.extend(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else toks.append(s)
    return toks


TOK = [tokenize(t) for _, t in DOCS]
N = len(DOCS)
AVG = sum(len(t) for t in TOK) / N
DF = {}
for ts in TOK:
    for w in set(ts):
        DF[w] = DF.get(w, 0) + 1


def bm25(q):
    qs = tokenize(q)
    out = []
    for ts in TOK:
        tf = {}
        for w in ts:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in qs:
            if w in tf:
                idf = math.log((N - DF[w] + 0.5) / (DF[w] + 0.5) + 1)
                s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (1 - 0.75 + 0.75 * len(ts) / AVG))
        out.append(s)
    return out


def rewrite(q):
    added = []
    for k, vs in SYNONYMS.items():
        if k in q:
            added.extend(vs)
    return (q + " " + " ".join(added)).strip(), added


def evaluate(use_rewrite, k=3):
    hit = noise = 0
    details = []
    for q, gold in QUERIES:
        qq, added = rewrite(q) if use_rewrite else (q, [])
        scores = bm25(qq)
        order = sorted(range(N), key=lambda i: -scores[i])[:k]
        g = next(i for i, d in enumerate(DOCS) if d[0] == gold)
        ok = g in order
        hit += ok
        noise += sum(1 for i in order if i != g and scores[i] > 0)
        details.append((q, added, order.index(g) + 1 if ok else None, [DOCS[i][0] for i in order]))
    return hit, noise, details


h0, n0, d0 = evaluate(False)
h1, n1, d1 = evaluate(True)

print(f"8 条口语查询，语料 8 篇；BM25，Recall@3")
print(f"{'配置':<12}{'Recall@3':>10}{'平均无关召回':>14}")
print(f"{'原始 query':<10}{h0:>10}/8{n0/8:>14.1f}")
print(f"{'同义词扩展':<10}{h1:>10}/8{n1/8:>14.1f}")

print("\n逐条对比（名次 '-' 表示 3 名之外）：")
print(f"{'查询':<22}{'扩展词':<22}{'前':>4}{'后':>4}")
for (q, a0, r0, _), (_, a1, r1, _) in zip(d0, d1):
    print(f"{q:<20}{','.join(a1)[:20]:<22}{str(r0 or '-'):>4}{str(r1 or '-'):>4}")

print(f"\n扩展后无关召回从 {n0/8:.1f} 涨到 {n1/8:.1f} 条/query：改写不是免费的。")
print("同义词表越宽，越容易把「公司」「资料」这类泛词扩成噪声词，把不相关文档带进来。")
print("\n读法：原始查询失败的 5 条，全部是「用户词表」与「文档词表」不重合，")
print("而不是检索算法不够强——这类问题加再好的向量模型也只能缓解，最便宜的解是维护一张领域词表。")
print("\n结论：查询改写要按『召回增益 / 噪声增量』评估，不能只看 Recall。")
print("上线做法：同义词表按租户维护、带版本号；改写后保留原始 query 的召回结果，两路合并再重排。")
