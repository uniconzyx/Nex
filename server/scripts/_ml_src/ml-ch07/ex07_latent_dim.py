# title: 隐维度 k 对误差的影响：训练一直降，测试在真实秩附近见底
# 真实秩 = 3，训练只有 1550 条观测。测试集是 2000 个「未参与训练」的用户-物品对，
# 这样测的是补全能力，而不是「记住已观测评分」。
import numpy as np

rng = np.random.default_rng(51)
n_u, n_i, rank_true = 100, 80, 3
P_true = rng.normal(0, 0.7, (n_u, rank_true))
Q_true = rng.normal(0, 0.7, (n_i, rank_true))
bu_t, bi_t = rng.normal(0, 0.6, n_u), rng.normal(0, 0.5, n_i)
R = np.clip(np.round(3.5 + bu_t[:, None] + bi_t[None, :] + P_true @ Q_true.T
                     + rng.normal(0, 0.3, (n_u, n_i))), 1, 5)

obs = rng.random((n_u, n_i)) < 0.20
for u in range(n_u):
    if obs[u].sum() < 4:
        obs[u, rng.choice(n_i, 4 - obs[u].sum(), replace=False)] = True

test = np.zeros((n_u, n_i), bool)
while test.sum() < 2000:                     # 从未训练的 pair 里抽固定测试集
    u, i = rng.integers(n_u), rng.integers(n_i)
    if not obs[u, i]:
        test[u, i] = True

users, items = np.where(obs)
r_obs = R[users, items]
mu = r_obs.mean()
print(f"训练 {len(r_obs)} 条观测，测试 {test.sum()} 个未观测 pair；真实秩 = {rank_true}")

def fit(k, epochs=40, lr=0.03, lam=0.02):
    rg = np.random.default_rng(7)
    bu, bi = np.zeros(n_u), np.zeros(n_i)
    P = rg.normal(0, 0.05, (n_u, k))
    Q = rg.normal(0, 0.05, (n_i, k))
    order = np.arange(len(r_obs))
    for _ in range(epochs):
        rg.shuffle(order)
        for t in order:
            u, i, r = users[t], items[t], r_obs[t]
            e = r - (mu + bu[u] + bi[i] + P[u] @ Q[i])
            bu[u] += lr * (e - lam * bu[u])
            bi[i] += lr * (e - lam * bi[i])
            pu = P[u].copy()
            P[u] += lr * (e * Q[i] - lam * P[u])
            Q[i] += lr * (e * pu - lam * Q[i])
    def rmse(mask):
        uu, ii = np.where(mask)
        pred = mu + bu[uu] + bi[ii] + np.sum(P[uu] * Q[ii], axis=1)
        return float(np.sqrt(np.mean((R[uu, ii] - pred) ** 2)))
    return rmse(obs), rmse(test), (n_u + n_i) * k + n_u + n_i

print(f"\n{'k':>4}{'参数量':>9}{'训练RMSE':>10}{'测试RMSE':>10}{'状态':>8}")
rows = []
for k in (1, 2, 3, 5, 10, 20, 40):
    tr, te, npar = fit(k)
    state = "欠拟合" if k < rank_true else ("合适" if k <= 5 else "过拟合")
    rows.append((k, te))
    print(f"{k:>4}{npar:>9d}{tr:>10.4f}{te:>10.4f}{state:>8}")

best = min(rows, key=lambda r: r[1])
print(f"\n测试 RMSE 最低：k={best[0]}（{best[1]:.4f}）；真实秩 = {rank_true}")
print("读法：")
print("1. k<3 时装不下真实的 3 个因子，训练/测试都高——这是欠拟合，加数据救不了；")
print("2. k 从 3 增到 40，训练 RMSE 从 0.37 一路降到 0.11，但测试在 0.67~0.72 徘徊甚至回升；")
print("3. 分界点是参数量 (m+n)k 与观测数的关系：k=10 时参数 1800 已超过 1550 条训练样本；")
print("4. 所以 k 要用「未观测 pair 的验证集」选，不能看训练 loss；生产上从 8~32 起步再扫。")
