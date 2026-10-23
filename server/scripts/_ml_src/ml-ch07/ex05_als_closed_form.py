# title: ALS 一步闭式解：解正规方程并验证目标单调下降
# 固定 Q 时，p_u = (Q_uᵀQ_u + λI)⁻¹ Q_uᵀ r_u 是该用户所有观测上的全局最优。
# 本示例同时验证：解出的 p_u 使梯度为 0，且整体目标逐轮单调不增。
import numpy as np

rng = np.random.default_rng(31)
n_u, n_i, k = 40, 30, 3
P_true = rng.normal(0, 0.7, (n_u, k))
Q_true = rng.normal(0, 0.7, (n_i, k))
R = np.clip(np.round(3.5 + P_true @ Q_true.T + rng.normal(0, 0.35, (n_u, n_i))), 1, 5)

obs = rng.random((n_u, n_i)) < 0.45
test = obs & (rng.random((n_u, n_i)) < 0.15)
train = obs & ~test
lam = 0.15
mu = float(R[train].mean())          # 先去掉全局均值，因子只拟合残差
Y = R - mu

def solve_users(P, Q):
    """每个用户解 (Q_uᵀQ_u+λI)p_u = Q_uᵀr_u，只用该用户观测过的物品。"""
    out = np.zeros_like(P)
    for u in range(n_u):
        idx = np.where(train[u])[0]
        if idx.size == 0:
            continue
        Qs, rs = Q[idx], Y[u, idx]
        out[u] = np.linalg.solve(Qs.T @ Qs + lam * np.eye(k), Qs.T @ rs)
    return out

def solve_items(Q, P):
    """每个物品解 (P_iᵀP_i+λI)q_i = P_iᵀr_i，只用评过它的用户。"""
    out = np.zeros_like(Q)
    for i in range(n_i):
        idx = np.where(train[:, i])[0]
        if idx.size == 0:
            continue
        Ps, rs = P[idx], Y[idx, i]
        out[i] = np.linalg.solve(Ps.T @ Ps + lam * np.eye(k), Ps.T @ rs)
    return out

def objective():
    pred = P @ Q.T
    err = (Y - pred)[train]
    return float(np.sum(err ** 2) + lam * (np.sum(P ** 2) + np.sum(Q ** 2)))

def rmse(mask):
    uu, ii = np.where(mask)
    pred = mu + np.sum(P[uu] * Q[ii], axis=1)
    return float(np.sqrt(np.mean((R[uu, ii] - pred) ** 2)))

P = rng.normal(0, 0.1, (n_u, k))
Q = rng.normal(0, 0.1, (n_i, k))
print(f"观测 {obs.sum()} / {n_u*n_i}，k={k}，λ={lam}")
print(f"{'轮':>3}{'目标函数':>12}{'训练RMSE':>10}{'测试RMSE':>10}")
history = []
for it in range(1, 9):
    P = solve_users(P, Q)                # 用户侧闭式解
    Q = solve_items(Q, P)                # 物品侧闭式解
    history.append(objective())
    print(f"{it:>3}{history[-1]:>12.3f}{rmse(train):>10.4f}{rmse(test):>10.4f}")

mono = all(history[i + 1] <= history[i] + 1e-9 for i in range(len(history) - 1))
print(f"\n目标单调不增: {mono}（{history[0]:.2f} → {history[-1]:.2f}）")

u = 0
idx = np.where(train[u])[0]
Qu = Q[idx]
p = np.linalg.solve(Qu.T @ Qu + lam * np.eye(k), Qu.T @ Y[u, idx])
grad = 2 * (Qu.T @ (Qu @ p - Y[u, idx]) + lam * p)
print(f"验证 u0 的正规方程残差 ‖∇L(p)‖ = {np.linalg.norm(grad):.2e}")
print(f"u0 的解 p_u = {np.round(p, 3)}")

print("\n读法：")
print("1. 每轮对 P 或 Q 都是「固定另一侧后的全局最优」，所以目标函数必然不增；")
print("2. 正规方程残差 ~1e-15，说明闭式解精确，不是梯度近似；")
print("3. 用户之间完全独立，可把 40 个 k×k 系统批量求解/多机并行——这是 ALS 相对 SGD 的最大优势；")
print("4. 代价是每轮要构造 Q_uᵀQ_u（O(k²·nnz)）并解 k×k 系统，k 大时比 SGD 贵。")
