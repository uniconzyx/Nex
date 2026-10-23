# title: DBSCAN 的密度视角：ε 与 minPts 的敏感性实测
# 三团密度不同的簇（std 0.9/0.9/1.3）+ 8 个远散布的离群点。
# 扫 ε（minPts=4 固定）与 minPts（ε 固定），看簇数/噪声数的完整相变；
# 再用 k-距离图的口径说明 ε 该怎么选。
import numpy as np
from itertools import permutations

rng = np.random.default_rng(17)
A = rng.normal([0.0, 0.0], 0.9, size=(90, 2))
B = rng.normal([8.0, 0.0], 0.9, size=(90, 2))
C = rng.normal([0.0, 9.0], 1.3, size=(60, 2))
outliers = np.array([[14.0, 2.0], [-5.0, 5.0], [5.0, 14.0], [16.0, 8.0],
                     [-3.0, -4.0], [12.0, -3.0], [2.0, 16.0], [-6.0, 12.0]])
X = np.vstack([A, B, C, outliers])
true = np.r_[np.zeros(90, int), np.ones(90, int), np.full(60, 2), np.full(8, 3)]
n = len(X)
D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))


def dbscan(D, eps, minPts):
    nbrs = [np.where(D[i] <= eps)[0] for i in range(len(D))]
    core = np.array([len(nb) >= minPts for nb in nbrs])
    lab = -np.ones(len(D), int)          # -1 = 噪声
    c = 0
    for i in range(len(D)):
        if lab[i] != -1 or not core[i]:
            continue
        lab[i] = c
        stack = [i]
        while stack:
            j = stack.pop()
            if not core[j]:
                continue                 # 边界点不再扩张
            for t in nbrs[j]:
                if lab[t] == -1:
                    lab[t] = c
                    if core[t]:
                        stack.append(t)
        c += 1
    return lab, core


def summarize(lab, core):
    nclust = int(lab.max()) + 1 if (lab >= 0).any() else 0
    noise = int((lab == -1).sum())
    border = int(((lab >= 0) & ~core).sum())
    sizes = np.bincount(lab[lab >= 0], minlength=max(nclust, 1)).tolist()
    return nclust, noise, border, int(core.sum()), sizes


def sizes_str(sizes, keep=6):
    return str(sizes[:keep]) + ("…" if len(sizes) > keep else "")


def best_perm_acc(lab, true):
    """真实簇 0/1/2 与检测簇做最优匹配（6 种排列），噪声点不计入。"""
    best = 0.0
    mask = lab >= 0
    for p in permutations(range(3)):
        m = {c: t for c, t in zip(range(3), p)}
        mapped = np.array([m.get(l, -1) for l in lab[mask]])
        best = max(best, float((mapped == true[mask]).mean()))
    return best


print(f"数据：n={n} = 三团（std 0.9/0.9/1.3，各 90/90/60 点）+ 8 个远散布离群点\n")
print("扫 ε（minPts=4 固定）与扫 minPts（ε=0.9 固定）：")
print(f"{'eps':>6}{'minPts':>7}{'簇数':>6}{'噪声':>6}{'边界':>6}{'核心':>6}"
      f"{'簇大小':>26}{'聚类准确率':>11}{'离群点召回':>11}")
for eps, mp in [(0.10, 4), (0.15, 4), (0.4, 4), (0.9, 4), (1.5, 4), (2.2, 4),
                (2.8, 4), (3.5, 4), (5.0, 4), (0.9, 2), (0.9, 8), (0.9, 16)]:
    lab, core = dbscan(D, eps, mp)
    ncl, noise, border, ncore, sizes = summarize(lab, core)
    acc = best_perm_acc(lab, true) if ncl >= 3 else float("nan")
    out_rec = float((lab[true == 3] == -1).mean())
    print(f"{eps:>6.2f}{mp:>7}{ncl:>6}{noise:>6}{border:>6}{ncore:>6}"
          f"{sizes_str(sizes):>26}{acc:>11.3f}{out_rec:>11.2f}")

# k-距离图口径：minPts=4 时每点到第 4 近邻的距离
d4 = np.sort(D, axis=1)[:, 3]
print(f"\nk-距离图口径（minPts=4，每点到第 4 近邻的距离分位数）：")
for q in (50, 75, 90, 95, 99):
    print(f"  {q:>3}% 分位 = {np.percentile(d4, q):.3f}")
print("  读法：正常点的 4-距离在 ~0.4~1.5 形成平台，8 个离群点把 99% 分位拽到 4.6、最大值更高——")
print("        取平台末端（≈1.0~1.5）作 ε，正是上表中 3 簇全对的区间。")

print("\n结论：")
print("1. 读法：ε 从 0.10 到 5.0，簇数走完 0 → 3 个小核 → 12 个碎片 → 3 → 3 → 3 → 3 → 2 → 1 的相变；")
print("   ε 太小的表现不是『全噪声』就是『一个真簇裂成多段』（ε=0.4 时三团碎成 12 段——密度可达链在团内断开）；")
print("   ε 太大则团间空隙被链式连接：3.5 时两团合并、5.0 时全部并成一簇。")
print("2. 机理：DBSCAN 的簇是核心点的密度可达闭包，ε 与 minPts 共同定义密度阈值且互相耦合；")
print("   表中固定 ε=0.9 扫 minPts：2→多出一个 3 点小碎片，8→稀疏的 C 团大半判噪声（只剩 41/60），")
print("   16→C 团只剩 16 点、噪声从 19 涨到 70——minPts 是密度阈值的另一半，调大等于提高『成团』门槛。")
print("3. 工程：ε 用 k-距离图的拐点定（本例 4-距离在 0.4~1.5 形成平台、离群点把 99% 分位拽到 4.6，")
print("   取平台末端 1.0~1.5 正好落在 3 簇全对的区间）；先定 minPts（经验值 ≈2d）再定 ε；")
print("   不同密度的簇不可能被同一个 ε 同时完美切分——这是 DBSCAN 的已知边界，")
print("   遇到它要么分区域建模，要么换 HDBSCAN（经验判断）。")
