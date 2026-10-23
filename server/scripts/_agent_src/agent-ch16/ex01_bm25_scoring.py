# title: 手写题一：BM25 打分与 top-k 排序（含未登录词行为）
# 本地模拟：内置小型预分词文档集，不调用任何检索服务/API。
# 目的：把 BM25 公式落成 20 行内可白板的核心逻辑，并验证失效输入的行为。
import math
from collections import Counter

DOCS = [
    ["检索", "排序", "bm25", "算法", "文档"],        # doc0
    ["向量", "检索", "embedding", "语义", "模型"],   # doc1
    ["限流", "令牌桶", "算法", "服务", "网关"],       # doc2
    ["检索", "向量", "混合", "融合", "排序"],        # doc3
]


def bm25(query, docs, k1=1.5, b=0.75, topk=2):
    """BM25 打分 + top-k。返回 [(分数, 文档索引)]，按 (-分数, 索引) 排序保证同分确定性。"""
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs
    df = Counter(w for d in docs for w in set(d))          # 文档频率，不是词频
    idf = {w: math.log((n_docs - n + 0.5) / (n + 0.5) + 1) for w, n in df.items()}
    scored = []
    for i, d in enumerate(docs):
        f, dl = Counter(d), len(d)
        s = sum(idf.get(q, 0.0) * f[q] * (k1 + 1)
                / (f[q] + k1 * (1 - b + b * dl / avgdl))
                for q in set(query) if q in f)
        scored.append((s, i))
    return sorted(scored, key=lambda t: (-t[0], t[1]))[:topk]


# ---------- 1) 正常查询：top-2 与逐项手算验证 ----------
q1 = ["检索", "排序"]
top = bm25(q1, DOCS)
print("== 1) 查询 ['检索','排序'] 的 top-2 ==")
for s, i in top:
    print(f"  doc{i}: score={s:.4f}  terms={DOCS[i]}")

# 手算复核（k1=1.5, b=0.75, 所有文档等长 5 = avgdl，长度因子恰为 1）：
# idf(检索)=ln((4-3+0.5)/3.5+1)=0.3567, idf(排序)=ln((4-2+0.5)/2.5+1)=0.6931
# doc0/doc3 两词各中 1 次：0.3567+0.6931=1.0498；doc1 只中「检索」：0.3567；doc2：0
assert abs(top[0][0] - 1.0498) < 1e-3 and top[0][1] == 0
assert abs(top[1][0] - 1.0498) < 1e-3 and top[1][1] == 3
print(f"手算复核：doc0 = 0.3567+0.6931 = {top[0][0]:.4f}，与公式一致")

# ---------- 2) 失效输入：查询词全库缺失 ----------
q2 = ["不存在的词", "外星科技"]
top2 = bm25(q2, DOCS, topk=4)
print("\n== 2) 失效输入：查询词全库缺失 ==")
for s, i in top2:
    print(f"  doc{i}: score={s:.4f}")
assert all(s == 0.0 for s, _ in top2), "未登录词应贡献 0 分而不是抛错"
print("行为：每篇 0 分、不抛 KeyError、排序按索引确定 —— 生产上还应向上游抛「部分查询词未命中」信号")

# ---------- 3) 未登录词与登录词混合 ----------
q3 = ["检索", "不存在的词"]
top3 = bm25(q3, DOCS, topk=2)
print("\n== 3) 混合查询：['检索', '不存在的词'] 的 top-2 ==")
for s, i in top3:
    print(f"  doc{i}: score={s:.4f}")
assert top3[0][1] == 0 and abs(top3[0][0] - 0.3567) < 1e-3
print("行为：未登录词被 idf.get(q, 0.0) 吞掉，只按登录词打分，结果与单查 ['检索'] 一致")

print("\n结论：BM25 的核心 20 行 = 文档频率 IDF + 词频饱和与长度归一的打分公式 + 确定性 top-k；")
print("读法：1. IDF 用「多少篇文档含该词」不是「出现多少次」，用错整个 IDF 都会错；2. 失效输入（查询词全缺失）的正确行为是 0 分 + 信号上抛，不是异常；3. 同分按索引排序，保证白板实现可复现；4. 这是本地小语料模拟，真实接入是把 DOCS 换成倒排索引与线上文档库（ch05/ch14 的检索服务）。")
