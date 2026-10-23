# title: 样本权重与 class_weight：加权等价于按权重重复样本
# 加权最小二乘 (XᵀSX)⁻¹XᵀSy 与复制样本同解；逻辑回归的 class_weight 也是同一机制。
import numpy as np

rng = np.random.default_rng(19)

# ---------- 1. 加权最小二乘 = 复制样本 ----------
n, d = 60, 4
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)
w_true = np.array([1.0, -0.5, 0.8, 0.3])
y = X @ w_true + rng.normal(0, 0.2, n)
s = np.ones(n)
s[:10] = 3.0

w_wls = np.linalg.solve(X.T @ (s[:, None] * X), X.T @ (s * y))
Xr = np.vstack([X] + [X[:10]] * 2)
yr = np.concatenate([y] + [y[:10]] * 2)
w_dup, *_ = np.linalg.lstsq(Xr, yr, rcond=None)
w_ols, *_ = np.linalg.lstsq(X, y, rcond=None)

print("加权最小二乘（前 10 个样本权重 3）vs 物理复制这些样本：")
print(f"  加权解   {np.round(w_wls, 6)}")
print(f"  复制解   {np.round(w_dup, 6)}")
print(f"  最大差   {np.max(np.abs(w_wls - w_dup)):.2e}（应≈0）")
print(f"  无权解   {np.round(w_ols, 6)}（权重改变拟合重心）")

# ---------- 2. 逻辑回归：class_weight = 正类重复 ----------
n2, d2 = 1500, 3
X2 = rng.normal(size=(n2, d2))
X2 = (X2 - X2.mean(0)) / X2.std(0)
Xb = np.column_stack([np.ones(n2), X2])
beta = np.array([-2.5, 1.0, -0.8, 0.6])
p_true = 1.0 / (1.0 + np.exp(-Xb @ beta))
y2 = (rng.random(n2) < p_true).astype(float)
pos_weight = 30.0
s2 = np.where(y2 == 1, pos_weight, 1.0)


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def fit_irls(Xb, y, s):
    w = np.zeros(Xb.shape[1])
    for _ in range(100):
        p = sigmoid(Xb @ w)
        W = s * p * (1 - p)
        g = Xb.T @ (s * (p - y))
        H = Xb.T @ (Xb * W[:, None]) + 1e-8 * np.eye(Xb.shape[1])
        step = np.linalg.solve(H, g)
        w = w - step
        if np.linalg.norm(step) < 1e-11:
            break
    return w


w_weighted = fit_irls(Xb, y2, s2)
idx = np.where(y2 == 1)[0]
Xrep = np.vstack([Xb] + [Xb[idx]] * (int(pos_weight) - 1))
yrep = np.concatenate([y2] + [y2[idx]] * (int(pos_weight) - 1))
w_rep = fit_irls(Xrep, yrep, np.ones(len(yrep)))

print(f"\n逻辑回归：正类权重 {pos_weight:.0f} vs 把正类样本物理复制 {int(pos_weight)} 份")
print(f"  加权解   {np.round(w_weighted, 6)}")
print(f"  复制解   {np.round(w_rep, 6)}")
print(f"  最大差   {np.max(np.abs(w_weighted - w_rep)):.2e}（应≈0，两目标只差常数因子）")
p_w = sigmoid(Xb @ w_weighted)
print(f"  加权后正类平均预测概率 = {p_w[y2 == 1].mean():.3f}，"
      f"负类 = {p_w[y2 == 0].mean():.3f}（分布被整体抬升）")

print("\n结论：")
print("1. 加权最小二乘与『把样本重复 sᵢ 次』给出完全相同的解——权重就是重复次数，不是玄学；")
print("2. class_weight={0:1,1:30} 等价于在损失里给正类乘 30，等价于正类过采样 30 倍（只改权重，不复制内存）；")
print("3. 它改变的是决策边界与概率分布（正类得分被抬高），不改变模型的表达能力；")
print("4. 权重不修复共线性/泄漏/特征质量；且会破坏概率校准，上线前要重新选阈值或做校准。")
