# title: 小批量梯度：方差按 1/B 下降，但收益会饱和
# 这是「为什么 batch size 不是越大越好」的最直接证据。
import numpy as np

rng = np.random.default_rng(3)
n, d = 2000, 20
X = rng.normal(size=(n, d))
w_true = rng.normal(size=d)
y = X @ w_true + rng.normal(0, 0.5, n)

def grad(idx):
    Xi, yi = X[idx], y[idx]
    return Xi.T @ (Xi @ w_true - yi) / idx.size

full = grad(np.arange(n))
print(f"{'batch':>6} {'|g_B − g_full| 均值':>20} {'方差':>12} {'方差×B':>10}")
for B in (1, 4, 16, 64, 256):
    diffs = []
    for _ in range(300):
        idx = rng.choice(n, B, replace=False)
        diffs.append(grad(idx) - full)
    diffs = np.array(diffs)
    v = diffs.var(axis=0).mean()
    print(f"{B:>6} {np.abs(diffs).mean():>20.4f} {v:>12.4f} {v*B:>10.4f}")

print("\n读法：方差 × B 近似为常数 → 方差 ∝ σ²/B（理想线性加速）。")
print("但真实训练里梯度计算可并行、通信与显存不可并行，所以超过临界 batch 后")
print("「每步更准」换不来「更少步数」，性价比急剧下降；这也是线性缩放学习率有上限的原因。")
