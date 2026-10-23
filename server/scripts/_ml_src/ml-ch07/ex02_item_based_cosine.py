# title: item-based 相似度三口径：原始余弦 / 调整余弦 / Jaccard
# 同一个「物品-物品」相似度，换口径会得到完全不同的近邻。
# 结论先给：显式评分用调整余弦，隐式 0-1 用 Jaccard，原始余弦会被流行度和尺度污染。
import numpy as np

R = np.array([
    [5, 4, 0, 0, 5, 1],
    [4, 5, 0, 0, 4, 0],
    [0, 0, 5, 4, 1, 5],
    [0, 0, 4, 5, 2, 4],
    [5, 4, 1, 2, 4, 3],
    [1, 0, 5, 4, 5, 5],
], dtype=float)
mask = R > 0
user_mu = np.array([R[u][mask[u]].mean() for u in range(6)])

def raw_cos(a, b):
    m = mask[:, a] & mask[:, b]
    if m.sum() == 0:
        return 0.0
    va, vb = R[m, a], R[m, b]
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))

def adj_cos(a, b):
    """调整余弦：减的是用户均值 μ_u（不是物品均值）。"""
    m = mask[:, a] & mask[:, b]
    if m.sum() == 0:
        return 0.0
    va, vb = R[m, a] - user_mu[m], R[m, b] - user_mu[m]
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))

def jaccard(a, b):
    sa, sb = set(np.where(mask[:, a])[0]), set(np.where(mask[:, b])[0])
    return len(sa & sb) / max(len(sa | sb), 1)

target = 0
print(f"目标物品 i{target}；用户均值 μ_u = {np.round(user_mu, 2)}（调整余弦减的是它）")
print(f"\n{'物品':>4}{'共评人数':>8}{'原始余弦':>10}{'调整余弦':>10}{'Jaccard':>9}")
rows = []
for j in range(1, 6):
    m = mask[:, target] & mask[:, j]
    rows.append((j, int(m.sum()), raw_cos(target, j), adj_cos(target, j), jaccard(target, j)))
    print(f"{'i'+str(j):>4}{m.sum():>8d}{raw_cos(target, j):>10.3f}{adj_cos(target, j):>10.3f}{jaccard(target, j):>9.3f}")

for name, idx in (("原始余弦", 2), ("调整余弦", 3), ("Jaccard", 4)):
    top = sorted(rows, key=lambda r: -r[idx])[:2]
    print(f"\n{name} Top-2 近邻: " + ", ".join(f"i{r[0]}({r[idx]:+.2f})" for r in top))

# 用 i0 的调整余弦近邻给 u0 推荐未评物品
u = 0
cand = [j for j in range(6) if not mask[u, j]]
def score_item(i):
    num = den = 0.0
    for j in np.where(mask[u])[0]:
        s = adj_cos(i, j)
        if s <= 0:                  # 只用正相关邻居，负相关不参与加权
            continue
        num += s * R[u, j]
        den += s
    if den == 0:
        return float(R[:, i][mask[:, i]].mean())   # 无正邻居 → 退化为物品均值
    return num / den

print(f"\nu0 已评物品 {[int(x) for x in np.where(mask[u])[0]]}，候选 {cand}")
for i in cand:
    print(f"  预测 u0 对 i{i} 的分数（调整余弦加权）= {score_item(i):.3f}")
print("\n读法：")
print("1. 原始余弦把所有分量当正数，i0 与 i4（都很热）天然接近，流行度被当成相似；")
print("2. 调整余弦减用户均值后，i0 与 i2/i5 的相似度转负——它们服务的是相反口味的人群；")
print("3. Jaccard 只看「谁评过」，对分数不敏感，适合隐式行为，但会把「都很多人评」当相似；")
print("4. item-based 的相似度可离线预计算、按 TopN 截断，这是它在工业界比 user-based 常用的原因。")
