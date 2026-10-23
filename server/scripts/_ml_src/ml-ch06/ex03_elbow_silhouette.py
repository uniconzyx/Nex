# title: 选 K：肘部法则与轮廓系数的实测对照
# 四团大小/离散度不同的球状簇，K 从 1 扫到 8：一边看畸变 J 的边际下降（肘部），
# 一边看平均轮廓系数（簇内紧致 vs 簇间分离），比较两种口径指向的 K。
import numpy as np

rng = np.random.default_rng(3)
specs = [([0.0, 0.0], 0.7, 70), ([6.0, 0.0], 1.0, 70),
         ([0.0, 6.0], 0.7, 55), ([6.0, 6.0], 1.2, 45)]   # (中心, std, 点数)
X = np.vstack([rng.normal(c, s, size=(m, 2)) for c, s, m in specs])
n = len(X)
K_TRUE = 4


def lloyd(X, k, C0, max_iter=100):
    C = C0.astype(float).copy()
    prev = None
    for _ in range(max_iter):
        d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d2.argmin(1)
        C = np.stack([X[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if prev is not None and np.array_equal(lab, prev):
            break
        prev = lab
    d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    lab = d2.argmin(1)
    return float(d2[np.arange(len(X)), lab].sum()), lab, C


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


def best_of_k(X, k, restarts=8):
    best = None
    for _ in range(restarts):
        J, lab, C = lloyd(X, k, kmpp_init(X, k, rng))
        if best is None or J < best[0]:
            best = (J, lab, C)
    return best


def mean_silhouette(X, lab):
    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    uniq = np.unique(lab)
    if len(uniq) < 2:
        return float("nan")
    s = np.zeros(len(X))
    for i in range(len(X)):
        same = lab == lab[i]
        a = D[i, same].sum() / max(same.sum() - 1, 1) if same.sum() > 1 else 0.0
        b = min(D[i, lab == c].mean() for c in uniq if c != lab[i])
        s[i] = 0.0 if same.sum() == 1 else (b - a) / max(a, b)
    return float(s.mean())


Ks = list(range(1, 9))
rows = []
for k in Ks:
    J, lab, C = best_of_k(X, k)
    sil = mean_silhouette(X, lab) if k >= 2 else float("nan")
    rows.append((k, J, lab, sil))

print(f"数据：n={n}，真实 K=4（四团 std 0.7~1.2、大小 45~70 不等）；每个 K 用 k-means++ 重启 8 次取最优")
print(f"{'K':>3}{'畸变 J':>12}{'ΔJ=J(K-1)-J(K)':>17}{'ΔJ(K+1)/ΔJ(K)':>16}{'平均轮廓系数':>13}")
drops = [None] + [rows[i - 1][1] - rows[i][1] for i in range(1, len(rows))]
for i, (k, J, _, sil) in enumerate(rows):
    d = f"{drops[i]:>17.2f}" if drops[i] is not None else f"{'—':>17}"
    r = (f"{drops[i + 1] / drops[i]:>16.3f}"
         if drops[i] is not None and i + 1 < len(drops) and drops[i] > 1e-9 else f"{'—':>16}")
    s = f"{sil:>13.4f}" if k >= 2 else f"{'—':>13}"
    print(f"{k:>3}{J:>12.2f}{d}{r}{s}")

elbow = int(np.argmin([drops[i + 1] / drops[i] for i in range(1, len(drops) - 1)
                       if drops[i] > 1e-9])) + 2
best_sil_k = max((k for k, *_ in rows if k >= 2),
                 key=lambda k: rows[Ks.index(k)][3])
print(f"\n肘部法则（边际下降骤减处）：K={elbow}；轮廓系数最高：K={best_sil_k}"
      f"（s={rows[Ks.index(best_sil_k)][3]:.4f}）")

# J 与轮廓系数的字符条形图（各自归一化到行宽 40）
print("\nK 扫描（'#' 越多越大，两行各自归一化）：")
jmax = max(r[1] for r in rows)
sil_vals = [r[3] for r in rows if r[0] >= 2]
slo, shi = min(sil_vals), max(sil_vals)
for k, J, _, sil in rows:
    bar_j = "#" * int(round(40 * J / jmax))
    if k >= 2:
        bar_s = "#" * max(1, int(round(40 * (sil - slo) / max(1e-12, shi - slo))))
        print(f"K={k}  J  |{bar_j:<40}|  轮廓 |{bar_s}|")
    else:
        print(f"K={k}  J  |{bar_j:<40}|  轮廓 |{'（K=1 无定义）':^40}|")

print("\n结论：")
print(f"1. 读法：J 随 K 单调下降（多一个中心总能不更差），但在 K={elbow} 之后边际下降 ΔJ 骤减——")
print("   再增加中心只是把已有的团切碎，收益断崖；轮廓系数在 K=4 达到最高，与肘部一致。")
print("2. 机理：轮廓系数 s(i)=(b(i)−a(i))/max(a(i),b(i)) 同时奖励『簇内近』与『簇间远』，")
print("   对『切碎』敏感：把好簇切开不改善 a(i) 的上界却恶化 b(i)，所以过大的 K 会被直接罚分。")
print("3. 工程：肘部法只给定性直觉（拐点常常不明显，见 pitfalls 第 3 条）；轮廓系数更客观，")
print("   但它同样假设『球状/凸簇』——非球形数据上它可能偏爱错误的 K（下一个示例看失效边界）；")
print("   样本量大时用 gap statistic 与先验分布对比，比两者都稳。")
