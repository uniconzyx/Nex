# title: 岭回归收缩路径：λ 如何同时压低 ‖w‖、κ 与方差
# 闭式解 w(λ)=(XᵀX+λI)⁻¹Xᵀy；扫 λ 看系数范数、条件数、有效自由度与测试误差的 U 形。
import numpy as np

rng = np.random.default_rng(7)
n, d, latent = 25, 10, 3
Z = rng.normal(size=(n, latent))
A = rng.normal(size=(latent, d))
X = Z @ A + rng.normal(0, 0.05, (n, d))       # 3 个潜在因子 → 强共线
X = (X - X.mean(0)) / X.std(0)
w_true = np.zeros(d)
w_true[:4] = [1.5, -1.0, 0.8, 0.5]
y = X @ w_true + rng.normal(0, 0.5, n)

Zte = rng.normal(size=(800, latent))
Xte = Zte @ A + rng.normal(0, 0.05, (800, d))
Xte = (Xte - Xte.mean(0)) / Xte.std(0)
yte = Xte @ w_true + rng.normal(0, 0.5, 800)

G, b = X.T @ X, X.T @ y
s2 = np.linalg.eigvalsh(G)

print(f"n={n}, d={d}, κ(XᵀX)={s2.max()/s2.min():.0f}，真实非零系数 4 个")
print(f"{'λ':>8}{'‖w‖':>9}{'κ(XᵀX+λI)':>14}{'有效自由度':>12}{'训练MSE':>10}{'测试MSE':>10}")
rows = []
for lam, tag in ((0.0, "0"), (1e-3, "1e-3"), (1e-2, "1e-2"), (1e-1, "1e-1"),
                 (1.0, "1"), (10.0, "10"), (100.0, "100")):
    if lam == 0.0:
        w, *_ = np.linalg.lstsq(X, y, rcond=None)
    else:
        w = np.linalg.solve(G + lam * np.eye(d), b)
    Areg = G + lam * np.eye(d)
    kappa = np.linalg.cond(Areg)
    dof = float(np.sum(s2 / (s2 + lam)))
    tr = float(np.mean((X @ w - y) ** 2))
    te = float(np.mean((Xte @ w - yte) ** 2))
    rows.append((tag, np.linalg.norm(w), kappa, dof, tr, te))
    print(f"{tag:>8}{np.linalg.norm(w):>9.3f}{kappa:>14.1f}{dof:>12.2f}{tr:>10.4f}{te:>10.4f}")

best = min(rows, key=lambda r: r[5])
print(f"\n测试误差最低：λ={best[0]}（MSE={best[5]:.4f}），有效自由度 {best[3]:.2f}/{d}")
print(f"从 λ=0 到 λ=100：‖w‖ {rows[0][1]:.2f}→{rows[-1][1]:.2f}，"
      f"测试 MSE {rows[0][5]:.4f}→（最低 {best[5]:.4f}）→{rows[-1][5]:.4f}。")

print("\n结论：")
print("1. λ↑ → ‖w‖↓、κ↓、有效自由度↓：岭回归在谱上按 σᵢ²/(σᵢ²+λ) 滤波，小奇异值方向先被压掉；")
print("2. 测试误差先降后升（U 形）：左支是方差主导，右支是偏差主导，λ 必须按验证集选；")
print("3. λ=0 时 κ 达 10⁴，系数对扰动极敏感；λ>0 使 XᵀX+λI 正定，问题变强凸且解唯一；")
print("4. 注意岭回归不产生稀疏：它只把系数整体压小，要做特征选择得用 L1（见 ex04）。")
