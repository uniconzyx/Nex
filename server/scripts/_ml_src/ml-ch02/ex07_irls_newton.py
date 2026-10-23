# title: IRLS / 牛顿法：每步都是加权最小二乘
# 逻辑回归的牛顿步 w ← w − H⁻¹g，H=XᵀWX（W=diag(p(1-p))），等价于解一个加权最小二乘。
import numpy as np

rng = np.random.default_rng(8)
n, d, latent = 300, 10, 2
A = rng.normal(size=(latent, d))
X = rng.normal(size=(n, latent)) @ A + rng.normal(0, 0.05, (n, d))
X = (X - X.mean(0)) / X.std(0)
Xb = np.column_stack([np.ones(n), X])
w_true = np.zeros(d + 1)
w_true[:4] = [0.1, 1.0, -0.7, 0.5]
p_true = 1.0 / (1.0 + np.exp(-Xb @ w_true))
y = (rng.random(n) < p_true).astype(float)

lam = 0.01                                       # 目标：mean BCE + λ/2‖w‖²


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def objective(w):
    p = sigmoid(Xb @ w)
    bce = -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
    return bce + 0.5 * lam * (w @ w)


def grad_hess(w):
    p = sigmoid(Xb @ w)
    g = Xb.T @ (p - y) / n + lam * w
    W = p * (1 - p)
    H = Xb.T @ (Xb * W[:, None]) / n + lam * np.eye(d + 1)
    return g, H


L = 0.25 * np.linalg.eigvalsh(Xb.T @ Xb).max() / n + lam
w_gd = np.zeros(d + 1)
for k_gd in range(1, 200001):
    g, _ = grad_hess(w_gd)
    if np.linalg.norm(g) < 1e-6:
        break
    w_gd = w_gd - (1.0 / L) * g

w_nt = np.zeros(d + 1)
for k_nt in range(1, 51):
    g, H = grad_hess(w_nt)
    if np.linalg.norm(g) < 1e-6:
        break
    w_nt = w_nt - np.linalg.solve(H, g)

g_nt, H_nt = grad_hess(w_nt)
print(f"n={n}, d={d} 个特征 + 截距，λ={lam}，停止条件 ‖∇ℓ‖<1e-6")
print(f"{'求解器':<16}{'步数':>8}{'目标值':>12}{'‖∇ℓ‖':>11}")
print(f"{'梯度下降 η=1/L':<16}{k_gd:>8}{objective(w_gd):>12.6f}{np.linalg.norm(grad_hess(w_gd)[0]):>11.2e}")
print(f"{'IRLS/牛顿':<16}{k_nt:>8}{objective(w_nt):>12.6f}{np.linalg.norm(g_nt):>11.2e}")
print(f"\n两者目标值之差：{abs(objective(w_gd) - objective(w_nt)):.2e}")
print(f"收敛点 Hessian 最小特征值：{np.linalg.eigvalsh(H_nt).min():.4f}（>0 ⇒ 严格凸、解唯一）")

print("\n结论：")
print("1. IRLS 用 5~8 步达到梯度下降上千步的精度——二阶信息把 κ 的影响消掉了，进入二次收敛区；")
print("2. 每步解 (XᵀWX+λI)δ=Xᵀ(p−y)+λw，正是以 W=diag(p(1−p)) 为权、z=Xw+W⁻¹(y−p) 为响应的加权最小二乘；")
print("3. Hessian=XᵀWX 半正定（p(1−p)≥0）⇒ 目标凸；λ>0 使其正定 ⇒ 强凸、解唯一；")
print("4. 代价是每步 O(d³)：小 d 用牛顿/L-BFGS，大 d 或稀疏用 SGD/saga。")
