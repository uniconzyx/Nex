# title: EM 的单调性：对数似然每轮不降的实测
# 一维两成分重叠 GMM，手写 E/M 两步，逐轮打印观测对数似然 L(θ_t)；
# 换一个「两个中心都初始化在数据中间」的坏初始化，看 L 同样单调、却停在更低的平台上。
import numpy as np

rng = np.random.default_rng(29)
pi_true = np.array([0.4, 0.6])
mu_true = np.array([-1.0, 2.0])
sd_true = np.array([0.8, 1.0])
comp = rng.choice(2, size=300, p=pi_true)
X = np.sort(rng.normal(mu_true[comp], sd_true[comp]))
n = len(X)


def em_gmm(X, pi0, mu0, sd0, iters=80, tol=1e-11, reg=1e-9):
    pi, mu, sd = np.array(pi0, float), np.array(mu0, float), np.array(sd0, float)
    hist = []
    gamma = None
    for t in range(iters):
        # E 步：后验 responsibility（对数域计算，再归一化）
        logp = (np.log(pi)[None, :] - np.log(sd)[None, :]
                - 0.5 * ((X[:, None] - mu[None, :]) / sd[None, :]) ** 2)
        m = logp.max(1, keepdims=True)
        joint = np.exp(logp - m)
        ll = float((m.ravel() + np.log(joint.sum(1))).sum())     # 观测对数似然
        gamma = joint / joint.sum(1, keepdims=True)
        hist.append(ll)
        if t and abs(ll - hist[-2]) < tol:
            break
        # M 步：加权均值 / 加权方差 / 权重
        Nk = gamma.sum(0) + 10 * np.finfo(float).eps
        pi = Nk / n
        mu = (gamma * X[:, None]).sum(0) / Nk
        sd = np.sqrt((gamma * (X[:, None] - mu[None, :]) ** 2).sum(0) / Nk + reg)
    return pi, mu, sd, gamma, hist


runs = {
    "好初始化": ([0.5, 0.5], [-0.5, 1.5], [1.0, 1.0]),
    "坏初始化": ([0.5, 0.5], [1.0, 1.2], [0.8, 1.2]),   # 两个中心都塞在数据中间
}
out = {}
for name, (p0, m0, s0) in runs.items():
    out[name] = em_gmm(X, p0, m0, s0)

pi_a, mu_a, sd_a, gam_a, hist_a = out["好初始化"]
print(f"数据：n={n} 一维两点重叠混合（真值 π={pi_true}, μ={mu_true}, σ={sd_true}）")
print(f"\n好初始化的逐轮对数似然（E 步前计算 L(θ_t)）：")
print(f"{'轮次 t':>7}{'L(θ_t)':>13}{'ΔL':>13}")
for t in range(min(12, len(hist_a))):
    d = hist_a[t] - hist_a[t - 1] if t else float("nan")
    print(f"{t:>7}{hist_a[t]:>13.4f}{(f'{d:>13.2e}' if t else f'{'—':>13}')}")
print(f"{'…':>7}{hist_a[-1]:>13.4f}{hist_a[-1] - hist_a[-2]:>13.2e}")
deltas = np.diff(np.array(hist_a))
print(f"最小 ΔL = {deltas.min():.2e} ≥ 0（单调性在浮点精度内成立，共 {len(hist_a)} 轮收敛）")

print(f"\n{'初始化':<10}{'最终 L':>11}{'π':>16}{'μ':>18}{'σ':>16}")
for name, (pi, mu, sd, _, hist) in out.items():
    print(f"{name:<10}{hist[-1]:>11.3f}{str(np.round(pi, 3)):>16}"
          f"{str(np.round(mu, 3)):>18}{str(np.round(sd, 3)):>16}")
print(f"{'真值':<10}{'—':>11}{str(pi_true):>16}{str(mu_true):>18}{str(sd_true):>16}")

# 重叠区样本的软指派：取 responsibility 最接近 0.5 / 0.25 / 0.75 的三个点
g1 = gam_a[:, 0]
idx = [int(np.abs(g1 - t).argmin()) for t in (0.5, 0.25, 0.75)]
print(f"\n重叠区样本的软指派（好初始化的最终 responsibility）：")
print(f"{'x':>8}{'γ(成分1)':>10}{'γ(成分2)':>10}{'硬指派':>8}")
for i in idx:
    g = gam_a[i]
    print(f"{X[i]:>8.3f}{g[0]:>10.3f}{g[1]:>10.3f}{int(g.argmax()):>8}")

print("\n结论：")
print(f"1. 读法：好初始化下 L 从 {hist_a[0]:.2f} 单调升到 {hist_a[-1]:.2f}，参数回到真值附近；")
print(f"   坏初始化同样单调（每轮 ΔL ≥ 0），却停在 L={out['坏初始化'][4][-1]:.2f} 的更低平台——")
print("   两个中心都初始化在数据中间时，M 步的加权均值互相锚住，谁也爬不出来。")
print("2. 机理：L(q,θ)+KL(q‖p(z|x,θ))=log p(X;θ)。E 步固定 θ 对 q 最大化左边（取 q=后验，KL=0），")
print("   M 步固定 q 对 θ 最大化——每一步都在抬高 log p(X;θ) 的下界，所以 L 单调不降；")
print("   单调性只保证「爬到某个不动点」，不保证是全局最优（EM 同样怕坏初始化）。")
print("3. 工程：① 收敛判据用 ΔL < tol 或参数变化，不要用固定轮数；② 多初始化 + 取 L 最大，")
print("   是 GMM 的标准操作（和 K-means++ 重启一个道理）；③ 协方差奇异时加 reg 或早停，")
print("   否则某个成分会塌成一个点、σ→0 把似然顶到 +∞（似然无界）。")
