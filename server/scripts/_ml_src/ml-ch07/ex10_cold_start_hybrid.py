# title: 冷启动混合策略模拟：CF、内容与置信度加权
# 40 个冷用户（只有 2 条评分）+ 160 个热用户（25 条评分）。
# 对比 global mean / 内容画像 / user-CF / 混合，分冷热两段报告 RMSE。
import numpy as np

rng = np.random.default_rng(71)
n_u, n_i, n_g = 200, 120, 5
cold = np.zeros(n_u, bool)
cold[:40] = True

genre = rng.integers(0, n_g, n_i)            # 真实类型（生成评分用）
genre_feat = genre.copy()                    # 内容特征有 30% 标错/噪声
flip = rng.random(n_i) < 0.15
genre_feat[flip] = rng.integers(0, n_g, flip.sum())
G = np.eye(n_g)[genre_feat]                  # 模型看到的内容特征
theta = rng.dirichlet(np.ones(n_g), n_u)     # 用户口味分布
b_u = rng.normal(0, 0.5, n_u)
aff = 1.5 * (n_g * theta[:, genre] - 1.0)    # 内容可解释的口味匹配
Uv = rng.normal(0, 1.1, (n_u, 3))            # 内容解释不了的个体-物品交互
Vv = rng.normal(0, 1.1, (n_i, 3))
R = np.clip(np.round(3.4 + b_u[:, None] + aff + Uv @ Vv.T
                     + rng.normal(0, 0.35, (n_u, n_i))), 1, 5)

obs = np.zeros((n_u, n_i), bool)
for u in range(n_u):
    if cold[u]:
        fav = int(np.argmax(theta[u]))                 # 冷用户从「最爱类型」开始逛
        pool = np.where(genre == fav)[0]
        picked = list(rng.choice(pool, min(3, pool.size), replace=False))
        rest = [i for i in range(n_i) if i not in picked]
        picked += list(rng.choice(rest, 2, replace=False))
        obs[u, picked] = True
    else:
        obs[u, rng.choice(n_i, 60, replace=False)] = True
test = np.zeros_like(obs)
for u in range(n_u):
    idx = np.where(obs[u])[0]
    n_test = 2 if cold[u] else 4
    test[u, idx[:n_test]] = True
train = obs & ~test

mu_u = np.array([R[u, train[u]].mean() if train[u].sum() else R[train].mean() for u in range(n_u)])
gmean = float(R[train].mean())

def content_score(u, i, lam=2.0):
    """岭回归估计用户对 5 类内容的偏好：θ = (GᵀG+λI)⁻¹Gᵀ(r−μ_u)。"""
    idx = np.where(train[u])[0]
    if idx.size == 0:
        return gmean
    X = G[idx]
    y = R[u, idx] - mu_u[u]
    theta = np.linalg.solve(X.T @ X + lam * np.eye(n_g), X.T @ y)
    return mu_u[u] + float(G[i] @ theta)

# item-based CF：物品-物品调整余弦（减用户均值）
Z = np.where(train, R - mu_u[:, None], 0.0)
S_item = np.zeros((n_i, n_i))
for a in range(n_i):
    for b in range(a + 1, n_i):
        m = train[:, a] & train[:, b]
        if m.sum() < 3:
            continue
        va, vb = Z[m, a], Z[m, b]
        raw = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
        S_item[a, b] = S_item[b, a] = raw * m.sum() / (m.sum() + 3)

def cf_score(u, i, topk=20):
    rated = np.where(train[u])[0]
    sims = S_item[i, rated]
    keep = sims > 1e-9
    if keep.sum() == 0:
        return mu_u[u]
    order = np.argsort(-sims[keep])[:topk]
    j = rated[keep][order]
    w = sims[keep][order]
    return mu_u[u] + float(np.sum(w * (R[u, j] - mu_u[u])) / np.sum(w))

def hybrid_score(u, i, alpha=5.0):
    n = train[u].sum()
    w = n / (n + alpha)
    return w * cf_score(u, i) + (1 - w) * content_score(u, i)

methods = {"全局均值": lambda u, i: gmean,
           "内容画像": content_score,
           "item-CF": cf_score,
           "混合(α=5)": hybrid_score}
print(f"物品类型 {n_g} 类；冷用户 {cold.sum()}（各 5 条，2 条留测），热用户 {(~cold).sum()}（各 60 条，4 条留测）")
print(f"{'方法':>10}{'冷用户RMSE':>12}{'热用户RMSE':>12}{'总体RMSE':>11}")
for name, fn in methods.items():
    err_c, err_w = [], []
    for u in range(n_u):
        for i in np.where(test[u])[0]:
            e = fn(u, i) - R[u, i]
            (err_c if cold[u] else err_w).append(e)
    print(f"{name:>10}{np.sqrt(np.mean(np.square(err_c))):>12.4f}"
          f"{np.sqrt(np.mean(np.square(err_w))):>12.4f}"
          f"{np.sqrt(np.mean(np.square(err_c + err_w))):>11.4f}")

print("\n读法：")
print("1. 冷用户只有 4 条训练评分，CF 的邻居共同项太少，相似度几乎是噪声；")
print("2. 内容画像只需要「评过什么类型」，几条就能估出粗粒度口味，冷段更好；")
print("3. 热用户相反：CF 能用群体行为，内容画像反而丢了个体细粒度信息；")
print("4. 混合权重 w=n/(n+α) 随交互数平滑上升，避免「新老用户硬切换」在阈值处跳变；")
print("5. α 是先验强度：α 越大越晚信任 CF，应按业务容忍度用验证集选。")
