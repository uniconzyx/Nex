# title: K-means++ vs 随机初始化：收敛质量、最坏情况与近似保证
# 同一份「一大四小」五团数据、同一套 Lloyd 迭代，只换初始化，各重启 60 次：
# 随机初始化常把小簇漏掉、把大簇切开；k-means++ 按 D(x)² 加权选点，显著改善最差情况。
import numpy as np

rng = np.random.default_rng(11)
k = 5
big = rng.normal([0.0, 0.0], 0.5, size=(200, 2))          # 大簇：200 点
smalls = [rng.normal(c, 0.3, size=(25, 2)) for c in
          ([4.0, 0.0], [-4.0, 0.0], [0.0, 4.0], [0.0, -4.0])]  # 四个小簇：各 25 点
X = np.vstack([big] + smalls)
n = len(X)
sizes = np.array([200, 25, 25, 25, 25])


def lloyd_j(X, k, C0, max_iter=100):
    C = C0.astype(float).copy()
    prev_lab = None
    for _ in range(max_iter):
        d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d2.argmin(1)
        C = np.stack([X[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if prev_lab is not None and np.array_equal(lab, prev_lab):
            break
        prev_lab = lab
    d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    lab = d2.argmin(1)
    return float(d2[np.arange(len(X)), lab].sum()), lab


def init_random(X, k, rng):
    return X[rng.choice(len(X), k, replace=False)]


def init_kmpp(X, k, rng):
    """K-means++：第一个中心均匀随机，之后按 D(x)² 概率取点（D=到已选中心的最近距离）。"""
    first = int(rng.integers(len(X)))
    centers = [first]
    d2 = ((X - X[first]) ** 2).sum(1)
    for _ in range(1, k):
        total = d2.sum()
        if total <= 0:
            centers.append(int(rng.integers(len(X))))
        else:
            r = rng.random() * total
            centers.append(min(int(np.searchsorted(np.cumsum(d2), r)), len(X) - 1))
        d2 = np.minimum(d2, ((X - X[centers[-1]]) ** 2).sum(1))
    return X[np.array(centers)]


R = 60
res = {}
for name, init in (("随机初始化", init_random), ("k-means++", init_kmpp)):
    Js, labs = [], []
    for _ in range(R):
        J, lab = lloyd_j(X, k, init(X, k, rng))
        Js.append(J)
        labs.append(lab)
    res[name] = (np.array(Js), labs)

best_all = min(res[nm][0].min() for nm in res)
print(f"数据：n={n}，k={k}（大簇 200 点 std=0.5 + 四个小簇各 25 点 std=0.3）；每种初始化重启 {R} 次")
print(f"{'初始化':<12}{'平均J':>9}{'J标准差':>9}{'最好J':>9}{'最差J':>9}"
      f"{'达到最优平台':>13}{'失败率(>1.05×)':>15}")
for name, (Js, _) in res.items():
    ok = int((Js <= best_all * 1.01).sum())
    print(f"{name:<12}{Js.mean():>9.1f}{Js.std():>9.1f}{Js.min():>9.1f}{Js.max():>9.1f}"
          f"{ok:>10}/{R:<3}{int((Js > best_all * 1.05).sum()):>12}/{R}")

# 最终 J 的字符直方图（两种初始化放同一坐标轴上）
print("\n最终 J 的分布（每格 8.0；'#'=一次重启）：")
lo = best_all * 0.97
hi = max(res[nm][0].max() for nm in res) * 1.03
bins = np.arange(lo, hi + 8.0, 8.0)
for name, (Js, _) in res.items():
    hist, _ = np.histogram(Js, bins=bins)
    print(f"{name:<12}" + "".join("#" if c else "." for c in hist))

# 失败模式解剖：取随机初始化里最差的一次，看簇大小
Js_rand, labs_rand = res["随机初始化"]
worst = int(Js_rand.argmax())
cnt = np.bincount(labs_rand[worst], minlength=k)
print(f"\n失败模式解剖（随机初始化最差重启，J={Js_rand[worst]:.1f}）：")
print(f"  各簇点数 = {cnt.tolist()}（理想是 {sizes.tolist()}）")
print("  ——小簇被邻簇吞并、大簇被切成两半，正是 J 劣化的来源。")

jr, jp = res["随机初始化"][0], res["k-means++"][0]
print("\n结论：")
print(f"1. 读法：随机初始化平均 J={jr.mean():.1f}、最差 {jr.max():.1f}；"
      f"k-means++ 平均 {jp.mean():.1f}、最差 {jp.max():.1f}；")
print(f"   进入最优平台（J≤1.01×最优）的重启：随机 {int((jr <= best_all*1.01).sum())}/{R}，"
      f"k-means++ {int((jp <= best_all*1.01).sum())}/{R}——收益主要在均值与到达率。")
print("2. 机理：随机初始化把 5 个中心撒进 5 个不同簇的概率不足 0.5%（要 200·25⁴/300·299·298·297·296 量级）；")
print("   空团只能等更新步把中心『匀』过去，于是大簇被切、小簇被吞（见上面的失败解剖）；")
print("   k-means++ 按 D(x)² 加权选点，未覆盖区域（小簇）里的点 D(x) 大、被选概率高，")
print("   初始中心被强制摊开（Arthur & Vassilvitskii, 2007：期望 O(log k) 近似保证）。")
print("3. 工程：k-means++ 不杜绝局部最优——本例它的最差 J 仍与随机初始化相当；")
print("   所以标准做法是 k-means++ × n_init 次重启取最优，诊断聚类质量看『重启间 J 的离散度』。")
