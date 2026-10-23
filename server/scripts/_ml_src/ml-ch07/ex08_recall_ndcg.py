# title: Recall@K / AP / NDCG@K 手算：分母、折扣与 IDCG 归一化
# 两个用户、多级相关性。把每个位置的 gain、discount 打出来，避免口径错误。
import numpy as np

# 用户 A：物品 A~F 的真实相关性等级（0~3）
rel_A = {"A": 3, "B": 0, "C": 2, "D": 0, "E": 1, "F": 0}
rank_A = ["A", "B", "C", "D", "E"]          # 模型排序
# 用户 B：只有 2 个相关物品，用来验证「IDCG 必须按人算」
rel_B = {"A": 2, "B": 0, "C": 0, "D": 3, "E": 0, "F": 0}
rank_B = ["B", "A", "C", "D", "F"]

def dcg(gains):
    return sum((2 ** g - 1) / np.log2(i + 2) for i, g in enumerate(gains))

def ndcg(ranking, rel):
    gains = [rel[x] for x in ranking]
    ideal = sorted(rel.values(), reverse=True)[:len(ranking)]
    return dcg(gains), dcg(ideal), dcg(gains) / dcg(ideal)

def ap(ranking, rel, k=None):
    hits, precisions = 0, []
    total = sum(1 for v in rel.values() if v > 0)
    for pos, x in enumerate(ranking[:k], start=1):
        if rel[x] > 0:
            hits += 1
            precisions.append(hits / pos)
    return sum(precisions) / total

for name, ranking, rel in (("用户A", rank_A, rel_A), ("用户B", rank_B, rel_B)):
    print(f"\n{name} 排序: {ranking}")
    print(f"{'位置':>4}{'物品':>6}{'rel':>5}{'gain':>6}{'discount':>10}{'累计DCG':>9}")
    gain_list, acc = [], 0.0
    for pos, x in enumerate(ranking, start=1):
        g = 2 ** rel[x] - 1
        disc = 1 / np.log2(pos + 1)
        acc += g * disc
        gain_list.append(g)
        print(f"{pos:>4}{x:>6}{rel[x]:>5}{g:>6}{disc:>10.3f}{acc:>9.3f}")
    d, idcg, score = ndcg(ranking, rel)
    rel_cnt = sum(1 for v in rel.values() if v > 0)
    print(f"  P@3={sum(rel[x] > 0 for x in ranking[:3])/3:.3f}  "
          f"R@5={sum(rel[x] > 0 for x in ranking[:5])/rel_cnt:.3f}  "
          f"AP={ap(ranking, rel):.3f}")
    print(f"  DCG={d:.3f}  IDCG={idcg:.3f}  NDCG={score:.3f}")

print("\n对照：把用户A的排序反转")
rev = list(reversed(rank_A))
d, idcg, score = ndcg(rev, rel_A)
print(f"  反转排序 {rev}：DCG={d:.3f}，NDCG={score:.3f}")
print(f"  理想排序（按 rel 降序）：{sorted(rel_A, key=lambda x: -rel_A[x])[:5]}，NDCG=1.000")
print(f"  反转后 R@5 仍为 1.000——Recall 只看「有没有」，不看位置")

print("\n读法：")
print("1. DCG 的 gain 用 2^rel−1（指数放大高相关），discount 用 1/log₂(pos+1)；")
print("2. IDCG 必须用「该用户自己的」相关物品降序算，不同用户的相关数不同，不能共用一个分母；")
print("3. NDCG 对位置敏感、对多级相关敏感；Recall@K 只看命中，二者回答不同问题；")
print("4. AP 的分母是「相关物品总数」，不是 K；这是它与 Precision@K 最关键的区别。")
