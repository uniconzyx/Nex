# title: 岭回归路径：λ 同时压系数范数、条件数与方差
# 闭式解 (XᵀX + λI)⁻¹Xᵀy。观察 λ 增大时 ‖w‖、κ 与测试误差怎么走。
import numpy as np

rng = np.random.default_rng(7)
n, d = 60, 12
X = rng.normal(size=(n, d))
# 构造共线性：后 6 列是前 6 列的近似线性组合（κ 很大）
X[:, 6:] = X[:, :6] @ rng.normal(size=(6, 6)) + rng.normal(0, 0.01, (n, 6))
w_true = np.array([1.5, -1.0, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0.0])
y = X @ w_true + rng.normal(0, 0.3, n)

Xte = rng.normal(size=(400, d))
yte = Xte @ w_true + rng.normal(0, 0.3, 400)
XtX = X.T @ X
Xty = X.T @ y

print(f"{'λ':>8} {'‖w‖':>8} {'κ(XᵀX+λI)':>12} {'训练MSE':>9} {'测试MSE':>9}")
for lam in (0.0, 1e-4, 1e-2, 1e-1, 1, 10, 100):
    A = XtX + lam * np.eye(d)
    w = np.linalg.solve(A, Xty)
    kappa = np.linalg.cond(A)
    tr = np.mean((X @ w - y) ** 2)
    te = np.mean((Xte @ w - yte) ** 2)
    print(f"{lam:>8.0e} {np.linalg.norm(w):>8.3f} {kappa:>12.1f} {tr:>9.4f} {te:>9.4f}")

print("\n读法：")
print("1. λ=0 时共线性使 κ 爆炸、系数被放大到不合理，测试误差偏高；")
print("2. λ 增大 → ‖w‖ 收缩、κ 下降 → 方差下降，测试误差先降；")
print("3. λ 过大 → 偏差主导，训练与测试误差同时上升（U 形右支）。")
print("所以「正则化改善泛化」与「正则化改善可优化性」是同一件事的两面。")
