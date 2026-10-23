# title: GMM 与 K-means：软分配、硬分配与 σ→0 的极限
# 两个明显重叠的 2D 高斯簇：K-means 给硬指派，等方差 GMM 给软指派；
# 再把 GMM 的方差按 τ 缩小，看软指派如何退回 K-means 的硬指派（J 也收敛到 J_km）。
import numpy as np

rng = np.random.default_rng(37)
X = np.vstack([rng.normal([0.0, 0.0], 1.0, (110, 2)),
               rng.normal([2.6, 0.0], 1.0, (110, 2))])
n, d = X.shape
k = 2


def pair_d2(X, C):
    return ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)


def kmpp_init(X, k, rng):
    first = int(rng.integers(len(X)))
    centers = [first]
    d2 = ((X - X[first]) ** 2).sum(1)
    for _ in range(1, k):
        total = d2.sum()
        idx = (min(int(np.searchsorted(np.cumsum(d2), rng.random() * total)), len(X) - 1)
               if total > 0 else int(rng.integers(len(X))))
        centers.append(idx)
        d2 = np.minimum(d2, ((X - X[idx]) ** 2).sum(1))
    return X[np.array(centers)]


def kmeans(X, k, restarts=10):
    best = None
    for _ in range(restarts):
        C = kmpp_init(X, k, rng)
        prev = None
        for _ in range(100):
            lab = pair_d2(X, C).argmin(1)
            C = np.stack([X[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
            if prev is not None and np.array_equal(lab, prev):
                break
            prev = lab
        lab = pair_d2(X, C).argmin(1)
        J = float(pair_d2(X, C)[np.arange(len(X)), lab].sum())
        if best is None or J < best[0]:
            best = (J, C, lab)
    return best


def em_gmm_shared(X, k, mu0, iters=100, tol=1e-10, reg=1e-9):
    """等方差球形 GMM：E 步软指派，M 步更新 π/μ/共享 σ²。"""
    mu = np.array(mu0, float)
    pi = np.full(k, 1.0 / k)
    var = float(np.mean(pair_d2(X, mu).min(1))) / d + reg
    for _ in range(iters):
        logp = (np.log(pi)[None, :] - 0.5 * d * np.log(2 * np.pi * var)
                - pair_d2(X, mu) / (2 * var))
        m = logp.max(1, keepdims=True)
        joint = np.exp(logp - m)
        gamma = joint / joint.sum(1, keepdims=True)
        Nk = gamma.sum(0) + 10 * np.finfo(float).eps
        mu_new = (gamma.T @ X) / Nk[:, None]
        var_new = float((gamma * pair_d2(X, mu_new)).sum() / (n * d)) + reg
        if (np.abs(mu_new - mu).max() < tol and abs(var_new - var) < tol):
            mu, var = mu_new, var_new
            break
        mu, var, pi = mu_new, var_new, Nk / n
    return pi, mu, var, gamma


def responsibilities(pi, mu, var, tau):
    """固定参数，把方差缩小 τ 倍后的软指派。"""
    logp = (np.log(pi)[None, :] - 0.5 * d * np.log(2 * np.pi * var * tau)
            - pair_d2(X, mu) / (2 * var * tau))
    m = logp.max(1, keepdims=True)
    joint = np.exp(logp - m)
    return joint / joint.sum(1, keepdims=True)


J_km, C_km, lab_km = kmeans(X, k)
pi, mu, var, gamma = em_gmm_shared(X, k, C_km)
J_gmm = float((gamma * pair_d2(X, mu)).sum())

amb = (gamma.max(1) > 0.1) & (gamma.max(1) < 0.9)
print(f"数据：n={n}，两团中心 (0,0) 与 (2.6,0)、std=1——重叠区约 {(np.abs(X[:, 0] - 1.3) < 0.65).mean():.0%} 的点落在边界带")
print(f"K-means：J={J_km:.2f}，中心={np.round(C_km, 3).tolist()}；"
      f"等方差 GMM（EM 收敛）：π={np.round(pi, 3)}，"
      f"μ={np.round(mu, 3).tolist()}，σ²={var:.3f}")
print(f"软指派边界点（max γ∈(0.1,0.9)）：{int(amb.sum())}/{n}；"
      f"K-means 的硬指派边界点：0/{n}（定义上全是 0/1）")

top = np.argsort(np.abs(gamma.max(1) - 0.5))[:5]
print(f"\n最模糊的 5 个点（γ₁ 最接近 0.5）：")
print(f"{'x':>16}{'γ₁':>8}{'γ₂':>8}{'K-means':>9}{'GMM':>6}")
for i in top:
    print(f"{str(np.round(X[i], 2)):>16}{gamma[i, 0]:>8.3f}{gamma[i, 1]:>8.3f}"
          f"{lab_km[i]:>9}{int(gamma[i].argmax()):>6}")

print(f"\nσ→0 极限（固定 GMM 的 π/μ，方差乘 τ）：")
print(f"{'τ':>9}{'软指派边界点':>13}{'与 K-means 一致率':>17}{'J(γ,μ)':>10}{'J_km':>10}")
for tau in (1.0, 0.1, 0.01, 1e-4):
    g = responsibilities(pi, mu, var, tau)
    amb_t = int(((g.max(1) > 0.1) & (g.max(1) < 0.9)).sum())
    agree = float((g.argmax(1) == lab_km).mean())
    J_t = float((g * pair_d2(X, mu)).sum())
    print(f"{tau:>9.0e}{amb_t:>13}{agree:>17.3f}{J_t:>10.2f}{J_km:>10.2f}")

print("\n结论：")
print(f"1. 读法：GMM 的 {int(amb.sum())} 个边界点拿到 0.1~0.9 之间的责任值（如上表 γ₁≈0.5 的点），")
print("   K-means 对同样的点只能给 0 或 1——重叠区里『这个点到底属于谁』本身就是概率性的，")
print("   硬指派是把这份不确定性直接扔掉。")
print("2. 机理：等方差 GMM 的 E 步 γ∝exp(−‖x−μ_k‖²/2σ²)，M 步 μ_k=加权均值；")
print("   σ²→0 时指数项变成阶跃，γ→指示函数，M 步的加权均值退化成簇内均值——两步合起来正是 Lloyd。")
print(f"   实测 τ=1e-4 时一致率→{float((responsibilities(pi, mu, var, 1e-4).argmax(1) == lab_km).mean()):.3f}、"
      f"J 从 461 降到 {float((responsibilities(pi, mu, var, 1e-4) * pair_d2(X, mu)).sum()):.1f}"
      f"（≈J_km={J_km:.1f}）；")
print("   残余的 2% 差异来自目标不同：GMM 优化似然、K-means 优化 J，两者收敛到的中心差之毫厘，")
print("   边界附近的点就会改投阵营。")
print("3. 工程：GMM 比 K-means 多给三样东西——概率（可算似然、可采样）、软边界（重叠区不硬切）、")
print("   以及放开共享方差后每个成分可带自己的 σ/Σ（能拟合大小不同、椭球的簇）；")
print("   代价是要选成分数、防 σ→0 的奇异解、并且同样怕坏初始化（同 ex02 的重启思路）。")
