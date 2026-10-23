# title: 梯度下降 vs 牛顿法：条件数如何决定迭代数
# 同一个二次目标，只改 κ（Hessian 谱的比值），收敛速度差两个数量级。
import numpy as np

def gd(A, b, kappa, tol=1e-10, max_iter=200000):
    L = A[0, 0]
    x = np.zeros(2)
    for k in range(1, max_iter + 1):
        x = x - (1.0 / L) * (A @ x - b)
        if np.linalg.norm(A @ x - b) < tol:
            return k, x
    return max_iter, x

def newton(A, b, tol=1e-10, max_iter=50):
    x = np.zeros(2)
    for k in range(1, max_iter + 1):
        g = A @ x - b
        if np.linalg.norm(g) < tol:
            return k - 1, x
        x = x - np.linalg.solve(A, g)
    return max_iter, x

b = np.array([1.0, 1.0])
print(f"{'条件数κ':>8} {'GD迭代':>8} {'牛顿迭代':>9} {'GD最终误差':>12}")
for kappa in (1, 10, 100, 1000, 10000):
    A = np.array([[kappa, 0.0], [0.0, 1.0]])
    k_gd, x_gd = gd(A, b, kappa)
    k_nt, _ = newton(A, b)
    print(f"{kappa:>8} {k_gd:>8} {k_nt:>9} {np.linalg.norm(A @ x_gd - b):>12.2e}")

print("\n结论：")
print("1. 牛顿法对二次目标 1 步精确收敛（迭代数与 κ 无关），代价是每步 O(d³) 求逆；")
print("2. 梯度下降迭代数≈κ·log(1/ε)，κ=10⁴ 时要上万步；")
print("3. 所以「特征标准化」不是习惯，是在把 κ 压下来 —— 这是最便宜的加速手段。")
