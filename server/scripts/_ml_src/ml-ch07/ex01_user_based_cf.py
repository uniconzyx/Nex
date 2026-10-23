# title: user-based 协同过滤手算：中心化余弦、邻居与加权预测
# 5 个用户 × 6 个物品，缺失用 0 标记（真实含义是「未观测」）。
# 重点看：中心化前后相似度的排序如何变化，以及预测为什么要减 μ_v 加 μ_u。
import numpy as np

R = np.array([
    [5, 4, 0, 1, 5, 2],
    [4, 5, 0, 2, 4, 1],
    [1, 2, 5, 4, 1, 5],
    [2, 1, 4, 5, 2, 4],
    [4, 4, 2, 2, 5, 3],
], dtype=float)
mask = R > 0
names = ["u0", "u1", "u2", "u3", "u4"]
mu = np.array([R[u][mask[u]].mean() for u in range(5)])

print("评分矩阵（0 = 未观测）：")
print("      i0  i1  i2  i3  i4  i5     μ_u")
for u in range(5):
    row = "  ".join(" ?" if not mask[u, i] else f"{int(R[u, i]):2d}" for i in range(6))
    print(f"{names[u]}  {row}   {mu[u]:.2f}")

def cos_raw(a, b):
    m = mask[a] & mask[b]
    va, vb = R[a, m], R[b, m]
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))

def cos_centered(a, b):
    m = mask[a] & mask[b]
    va, vb = R[a, m] - mu[a], R[b, m] - mu[b]
    return float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))

print("\n与 u0 的相似度（共同评分数）：")
print(f"{'用户':>4}{'原始余弦':>10}{'中心化余弦':>12}{'共同评分':>8}")
sims = {}
for v in range(1, 5):
    m = mask[0] & mask[v]
    sims[v] = cos_centered(0, v)
    print(f"{names[v]:>4}{cos_raw(0, v):>10.3f}{cos_centered(0, v):>12.3f}{m.sum():>8d}")

target_item = 2
neigh = sorted(sims, key=lambda v: -sims[v])[:2]
rated = [v for v in neigh if mask[v, target_item]]
num = sum(sims[v] * (R[v, target_item] - mu[v]) for v in rated)
den = sum(abs(sims[v]) for v in rated)
pred = mu[0] + num / den
raw_avg = float(np.mean([R[v, target_item] for v in rated]))

print(f"\n预测 u0 对 i{target_item} 的评分：")
print(f"  邻居（中心化余弦 Top-2）: {[names[v] for v in neigh]}")
print(f"  其中评过 i{target_item} 的: {[names[v] for v in rated]}"
      f"（u1 对 i2 未观测，不能当 0 参与）")
print(f"  加权原始分均值（不做均值修正）= {raw_avg:.2f}")
print(f"  公式预测 = μ_u0({mu[0]:.2f}) + Σ sim·(r−μ_v)/Σ|sim| = {pred:.3f}")

print("\n读法：")
print("1. u1 与 u0 的原始余弦最高，但两者都爱打高分，原始相似度被评分尺度放大；")
print("2. 中心化后 u1 仍是最近邻（口味确实同向），u2/u3 的相似度转负（口味相反）；")
print("3. 预测必须先减邻居均值再乘相似度，否则「宽容邻居」会把分数整体抬高；")
print("4. 只有 3~4 个共同评分时相似度方差很大，生产上要加收缩 |I|/(|I|+λ)。")
