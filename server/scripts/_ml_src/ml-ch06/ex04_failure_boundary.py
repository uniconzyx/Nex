# title: K-means 失效边界：非球形簇与异常点的双重打击
# 场景 A：同心环数据，K-means(K=2) 的指派边界只能切出凸区域，错分率≈50%；
# 场景 B：两团好数据里掺 3 个远端异常点，看平方损失如何把质心和簇结构拖坏。
import numpy as np

rng = np.random.default_rng(5)


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


def lloyd(X, k, C0, max_iter=100):
    C = C0.astype(float).copy()
    prev = None
    for _ in range(max_iter):
        lab = pair_d2(X, C).argmin(1)
        C = np.stack([X[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if prev is not None and np.array_equal(lab, prev):
            break
        prev = lab
    lab = pair_d2(X, C).argmin(1)
    return C, lab


def best_run(X, k, restarts=10):
    best = None
    for _ in range(restarts):
        C, lab = lloyd(X, k, kmpp_init(X, k, rng))
        J = float(pair_d2(X, C)[np.arange(len(X)), lab].sum())
        if best is None or J < best[0]:
            best = (J, C, lab)
    return best


def accuracy_vs_true(lab, true):
    """二分类：在两种标签映射里取较好的那个。"""
    return max(float((lab == true).mean()), float((lab == 1 - true).mean()))


# ---------- 场景 A：同心环 ----------
def ring(r, m, noise, rng):
    a = rng.uniform(0, 2 * np.pi, m)
    rr = r + noise * rng.normal(size=m)
    return np.c_[rr * np.cos(a), rr * np.sin(a)]


Xr = np.vstack([ring(1.0, 120, 0.12, rng), ring(4.0, 120, 0.12, rng)])
true_r = np.r_[np.zeros(120, int), np.ones(120, int)]
Jr, Cr, labr = best_run(Xr, 2)

print("场景 A：同心环（内环 120 点 r=1，外环 120 点 r=4，噪声 0.12），K-means K=2")
print(f"  错分率 = {1 - accuracy_vs_true(labr, true_r):.3f}（随机猜测是 0.5），J={Jr:.2f}")
ct = np.array([[int(((labr == c) & (true_r == t)).sum()) for c in (0, 1)] for t in (0, 1)])
print(f"  混淆矩阵（行=真实环，列=预测簇）：\n    {ct[0].tolist()}\n    {ct[1].tolist()}")
print(f"  两个最终中心 = {np.round(Cr, 2).tolist()}（都挤在原点附近，只能按角度切每一环）")

# ---------- 场景 B：异常点拖偏 ----------
Xb = rng.normal([0.0, 0.0], 1.0, size=(100, 2))
Xb2 = rng.normal([8.0, 8.0], 1.0, size=(100, 2))
outliers = np.array([[20.0, 0.0], [-18.0, 4.0], [2.0, -19.0]])
clean = np.vstack([Xb, Xb2])
dirty = np.vstack([clean, outliers])

Jc, Cc, labc = best_run(clean, 2)
Jd, Cd, labd = best_run(dirty, 2)
order_c = np.argsort(Cc[:, 0])
order_d = np.argsort(Cd[:, 0])

print("\n场景 B：两团各 100 点（中心 (0,0) 与 (8,8)，std=1）+ 3 个远端异常点，K-means K=2")
print(f"{'数据':<10}{'J':>10}{'簇1中心':>18}{'簇2中心':>18}{'簇大小':>14}")
print(f"{'干净':<10}{Jc:>10.2f}{str(np.round(Cc[order_c[0]], 2)):>18}"
      f"{str(np.round(Cc[order_c[1]], 2)):>18}{str(np.bincount(labc, minlength=2)[order_c].tolist()):>14}")
print(f"{'含异常点':<10}{Jd:>10.2f}{str(np.round(Cd[order_d[0]], 2)):>18}"
      f"{str(np.round(Cd[order_d[1]], 2)):>18}{str(np.bincount(labd, minlength=2)[order_d].tolist()):>14}")

mu_clean = clean.mean(0)
mu_dirty = dirty.mean(0)
J_1c = float(((clean - mu_clean) ** 2).sum())
J_1d = float(((dirty - mu_dirty) ** 2).sum())
print(f"\n  K=1 视角：质心从 {np.round(mu_clean, 3)} 被拖到 {np.round(mu_dirty, 3)}"
      f"（偏移 {np.linalg.norm(mu_dirty - mu_clean):.3f}）；")
print(f"  总平方和从 {J_1c:.1f} 涨到 {J_1d:.1f}（+{100 * (J_1d / J_1c - 1):.0f}%），"
      f"其中 3 个异常点贡献了 {float((outliers ** 2).sum()):.0f}。")

print("\n结论：")
print(f"1. 读法 A：同心环上错分率 {1 - accuracy_vs_true(labr, true_r):.2f}——每个环被一条过原点的直线切成两半；")
print("   K-means 的指派边界是『到中心更近』，Voronoi 单元全是凸集，月牙/环/细条这类非凸簇永远切不对。")
print(f"2. 读法 B：只多 3 个点（占 1.5%），J 从 {Jc:.0f} 涨到 {Jd:.0f}（×{Jd / Jc:.1f}），")
print(f"   质心被拖偏 {np.linalg.norm(mu_dirty - mu_clean):.2f}，且 K=2 时异常点没有『噪声』概念、")
print(f"   被直接吸收进两个真簇（簇大小 {np.bincount(labd, minlength=2).tolist()}）——平方损失按距离²计价，")
print("   异常点的杠杆被平方放大，它用 1.5% 的点撬动了 14% 的总平方和。")
print("3. 工程：非凸簇换 DBSCAN/谱聚类（下一个示例看 DBSCAN），异常点先 Robust 化再聚类；")
print("   『先除噪再聚类』不是洁癖——J、质心、簇边界都会被少数极端点绑架，且你从输出里看不出来。")
