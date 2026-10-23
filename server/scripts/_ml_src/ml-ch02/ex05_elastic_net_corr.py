# title: 弹性网 vs Lasso：重复特征上的「留谁」与「组效应」
# 构造完全重复的两列，比较 Lasso 的列顺序依赖与弹性网的分摊解。
import numpy as np

rng = np.random.default_rng(42)
n = 150
base = rng.normal(size=(n, 4))
X = np.column_stack([base, base[:, 0]])          # 第 5 列 = 第 1 列的精确复制
X = (X - X.mean(0)) / X.std(0)
w_true = np.array([1.5, -1.0, 0.8, 0.0, 1.5])    # 两列都含信号，组合权重 3.0
y = X @ w_true + rng.normal(0, 0.1, n)
y = y - y.mean()


def soft(z, t):
    return np.sign(z) * np.maximum(np.abs(z) - t, 0.0)


def fit(X, y, lam, l1_ratio, iters=4000, tol=1e-12):
    n, d = X.shape
    w = np.zeros(d)
    r = y.copy()
    l1, l2 = lam * l1_ratio, lam * (1.0 - l1_ratio)
    for _ in range(iters):
        w_old = w.copy()
        for j in range(d):
            r += X[:, j] * w[j]
            c = X[:, j] @ X[:, j]
            w[j] = soft(X[:, j] @ r, l1) / (c + l2)
            r -= X[:, j] * w[j]
        if np.max(np.abs(w - w_old)) < tol:
            break
    return w


lam = 2.0
print("第 1 列与第 5 列完全相同（都带信号 1.5，组合权重真值 3.0）；λ=2.0")
for name, ratio in (("Lasso(ρ=1)", 1.0), ("弹性网(ρ=0.5)", 0.5)):
    w = fit(X, y, lam, ratio)
    print(f"  {name:<14} w[1]={w[0]:6.3f}  w[5]={w[4]:6.3f}  "
          f"组合={w[0]+w[4]:6.3f}  |w1-w5|={abs(w[0]-w[4]):.3f}")

# 只交换两列的处理顺序，数据完全等价
perm = [4, 1, 2, 3, 0]
Xp = X[:, perm]
wl = fit(Xp, y, lam, 1.0)
we = fit(Xp, y, lam, 0.5)
print("\n交换这两列顺序后（仅改变坐标下降的处理次序）：")
print(f"  Lasso   原第1列={wl[4]:6.3f}  原第5列={wl[0]:6.3f}  |差|={abs(wl[4]-wl[0]):.3f}")
print(f"  弹性网  原第1列={we[4]:6.3f}  原第5列={we[0]:6.3f}  |差|={abs(we[4]-we[0]):.3f}")

print("\n结论：")
print("1. Lasso 在完全重复的列上解不唯一，坐标下降把权重全给先处理的那一列，交换列序结果就翻转；")
print("2. 弹性网的 L2 项给出严格凸性，解唯一，并把重复列『平分』——这就是组效应（Zou & Hastie, 2005）；")
print("3. 机理：L2 惩罚让两列权重之差有界 |wⱼ-wₖ| ≤ λ(1-ρ)/(1+ρ)，相关越强越倾向一起动；")
print("4. 工程口径：相关特征组、one-hot 派生列、共线指标优先用弹性网；要可复现的『留谁』别交给 Lasso。")
