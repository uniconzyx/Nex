# title: BM25 参数敏感性：k1 与 b 如何翻转「堆砌长文」与「简短准文」的排序
# 本地模拟：构造一对目标文档（长文档堆砌词频 vs 短文档词频低），扫描 k1/b 网格。
# 目的：回答面试追问「k1/b 调大各自意味着什么」——用排序翻转给出可验证的答案。
import math
from collections import Counter

QUERY = ["ai"]
# docA：长文档（40 词），查询词只出现 1 次 —— 「提了一句」的长文
DOC_A = ["ai"] + [f"w{i}" for i in range(39)]
# docB：短文档（8 词），查询词出现 5 次 —— 「堆砌关键词」的短文
DOC_B = ["ai"] * 5 + ["x", "y", "z"]


def idf_of(docs):
    n = len(docs)
    df = Counter(w for d in docs for w in set(d))
    return {w: math.log((n - c + 0.5) / (c + 0.5) + 1) for w, c in df.items()}


def score(doc, query, idf, avgdl, k1, b):
    f, dl = Counter(doc), len(doc)
    return sum(idf.get(q, 0.0) * f[q] * (k1 + 1)
               / (f[q] + k1 * (1 - b + b * dl / avgdl))
               for q in set(query) if q in f)


idf = idf_of([DOC_A, DOC_B])
avgdl = (len(DOC_A) + len(DOC_B)) / 2
print(f"idf(ai) = {idf['ai']:.4f}（2 篇文档都含 ai，N=2）")
print(f"docA: {len(DOC_A)} 词、f(ai)=1    docB: {len(DOC_B)} 词、f(ai)=5\n")

print("== 排序翻转表：每格为 top1（A=长文档 / B=短文档堆砌） ==")
print("k1\\b  " + "".join(f"{b:>8}" for b in (0.0, 0.25, 0.5, 0.75, 1.0)))
flips = []
for k1 in (0.0, 0.5, 1.2, 2.0, 5.0):
    row = []
    for b in (0.0, 0.25, 0.5, 0.75, 1.0):
        sa = score(DOC_A, QUERY, idf, avgdl, k1, b)
        sb = score(DOC_B, QUERY, idf, avgdl, k1, b)
        row.append("A" if sa >= sb else "B")
        flips.append((k1, b, "A" if sa >= sb else "B", sa, sb))
    print(f"{k1:<5}" + "".join(f"{c:>8}" for c in row))

# 边界口径：k1=0 时词频完全不计，退化为布尔匹配（只看含不含）
s_a0 = score(DOC_A, QUERY, idf, avgdl, 0.0, 0.75)
s_b0 = score(DOC_B, QUERY, idf, avgdl, 0.0, 0.75)
print(f"\nk1=0 退化验证：docA={s_a0:.4f} docB={s_b0:.4f}（应相等：布尔匹配不看词频）")
assert abs(s_a0 - s_b0) < 1e-9

# b 的作用：b=1 完全长度归一 vs b=0 完全不归一
s_a_b0 = score(DOC_A, QUERY, idf, avgdl, 1.5, 0.0)
s_a_b1 = score(DOC_A, QUERY, idf, avgdl, 1.5, 1.0)
print(f"b 对长文档的影响（k1=1.5）：docA 得分 b=0 时 {s_a_b0:.4f} → b=1 时 {s_a_b1:.4f}（b 越大越压制长文档，短文档的词频优势被放大）")

# 翻转规律总结
k1_hi = [f for f in flips if f[0] == 5.0]
b_effect = [f for f in k1_hi if f[1] == 0.0][0], [f for f in k1_hi if f[1] == 1.0][0]
print(f"k1=5 时：b=0 top1={b_effect[0][2]}，b=1 top1={b_effect[1][2]}（长度归一把短文档的打分拉回来）")

print("\n结论：k1 控制词频饱和（越大越奖励堆砌），b 控制长度归一（越大越压制长文档/奖励短文档），两者有耦合；")
print("读法：1. 调参方向是面试高频追问——k1 大让「关键词堆砌」更吃得开，b 大让长文档里的一句题外话更吃亏；2. 表格存在翻转格说明「默认 k1=1.5/b=0.75」不是普适最优，真实调参必须用标注查询集扫网格（见 concept/02 第 3 节）；3. k1=0 退化为布尔匹配是必须知道的极限值；4. 本示例只做参数语义验证，真实语料的调参目标用 nDCG@10 或 Recall@50（ch05 的评估口径）。")
