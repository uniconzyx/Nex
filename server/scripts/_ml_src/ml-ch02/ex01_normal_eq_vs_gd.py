# title: 正规方程 vs 梯度下降：同解、速度与条件数
# 同一组数据，闭式解与一阶迭代给出同一组系数；但迭代步数由 κ(XᵀX) 决定。
import numpy as np

rng = np.random.default_rng(0)
n, d = 200, 5
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)          # 标准化后再比较，避免量纲污染 κ
w_true = np.array([1.5, -1.0, 0.8, -0.5, 0.3])
y = X @ w_true + rng.normal(0, 0.3, n)

G, b = X.T @ X, X.T @ y
w_ne = np.linalg.solve(G, b)             # 正规方程
L = np.linalg.eigvalsh(G).max()
eta = 1.0 / L

w_gd = np.zeros(d)
for k in range(1, 20001):
    g = G @ w_gd - b
    if np.linalg.norm(g) < 1e-8:
        break
    w_gd = w_gd - eta * g

print(f"n={n}, d={d}, κ(XᵀX)={np.linalg.cond(G):.2f}, L={L:.2f}, η=1/L={eta:.4f}")
print(f"{'方法':<8}{'w[0]':>9}{'w[1]':>9}{'w[2]':>9}{'‖w-w_NE‖∞':>13}")
print(f"{'正规方程':<8}{w_ne[0]:>9.4f}{w_ne[1]:>9.4f}{w_ne[2]:>9.4f}{0.0:>13.2e}")
print(f"{'梯度下降':<8}{w_gd[0]:>9.4f}{w_gd[1]:>9.4f}{w_gd[2]:>9.4f}"
      f"{np.max(np.abs(w_gd - w_ne)):>13.2e}")
print(f"GD 达到 ‖∇f‖<1e-8 用了 {k} 步")

print("\n条件数对迭代步数的影响（二维二次目标，η=1/L，停止 ‖∇f‖<1e-10）")
print(f"{'κ':>6}{'GD 步数':>9}{'收缩因子 1-1/κ':>17}")
for kappa in (1, 10, 100, 1000):
    A = np.diag([float(kappa), 1.0])
    bb = np.array([1.0, 1.0])
    x = np.zeros(2)
    for it in range(1, 200001):
        x = x - (1.0 / kappa) * (A @ x - bb)
        if np.linalg.norm(A @ x - bb) < 1e-10:
            break
    print(f"{kappa:>6}{it:>9}{1.0 - 1.0 / kappa:>17.4f}")

print("\n结论：")
print("1. 正规方程与梯度下降给出同一组最优系数（差≈机器精度），它们是同一问题的两种解法；")
print("2. 步长上限是 1/L（L 为 Hessian 最大特征值），超过 2/L 必然发散；")
print("3. 迭代步数≈κ·log(1/ε)：κ=1000 时要两万步以上，所以「先标准化」是最便宜的加速手段；")
print("4. 工程上小 d 用 lstsq/SVD（稳定），大 d 用 GD/L-BFGS（避免 O(d³) 求逆）。")
