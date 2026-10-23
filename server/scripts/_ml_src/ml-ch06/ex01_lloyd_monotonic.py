# title: Lloyd 迭代的单调性：畸变 J 每步不增的实测
# 手写 K-means 的两步循环，逐轮打印畸变 J，分步验证「分配步不增、更新步必减」；
# 再扫 30 个随机初始化，看同一份数据落到不同的局部极小。
import numpy as np

rng = np.random.default_rng(7)
k = 3
centers_true = np.array([[0.0, 0.0], [4.0, 3.0], [0.0, 5.0]])
X = np.vstack([rng.normal(c, 0.9, size=(60, 2)) for c in centers_true])
n = len(X)


def pair_d2(X, C):
    return ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)


def lloyd(X, k, C0, max_iter=100):
    """返回 (最终中心, 最终指派, 历史[(轮次, 分配后J, 更新后J)])。"""
    C = C0.astype(float).copy()
    hist = []
    prev_lab = None
    for it in range(1, max_iter + 1):
        d2 = pair_d2(X, C)
        lab = d2.argmin(1)
        J_assign = float(d2[np.arange(len(X)), lab].sum())      # 分配步后的 J
        C_new = np.stack([X[lab == j].mean(0) if np.any(lab == j) else C[j]
                          for j in range(k)])                   # 更新步：簇内均值
        J_update = float(pair_d2(X, C_new)[np.arange(len(X)), lab].sum())  # 用旧指派重算
        hist.append((it, J_assign, J_update))
        C = C_new
        if prev_lab is not None and np.array_equal(lab, prev_lab):
            break                                              # 指派不再变化 = 不动点
        prev_lab = lab
    return C, lab, hist


# ---- 主实验：一个「不太好」的初始中心（两个落在同一个真簇里） ----
C0 = X[[3, 8, 140]].astype(float)
C, lab, hist = lloyd(X, k, C0)

print(f"数据：n={n}，k={k}（三团球状簇，std=0.9）；初始中心取自样本点 [3, 8, 140]")
print(f"{'轮次':>4}{'分配后 J':>14}{'更新后 J':>14}{'分配步降幅':>14}{'更新步降幅':>14}")
prev_update = None
for it, Ja, Ju in hist:
    ga = f"{prev_update - Ja:>14.4f}" if prev_update is not None else f"{'—':>14}"
    print(f"{it:>4}{Ja:>14.4f}{Ju:>14.4f}{ga}{Ja - Ju:>14.4f}")
    prev_update = Ju

J_final = hist[-1][2]
print(f"\n收敛：{len(hist)} 轮后指派不再变化，J*={J_final:.4f}")
print(f"最终中心与真中心的对应误差：{np.abs(np.sort(C[:, 0]) - np.sort(centers_true[:, 0])).max():.3f}")

# J 轨迹字符画（按轮次映射到 8 级高度）
chars = " .:-=+*#@"
Js = [h[2] for h in hist]
lo, hi = min(Js), max(Js)
line = "".join(chars[int(round(7 * (Ju - lo) / max(1e-12, hi - lo)))] for _, _, Ju in hist)
print(f"J 轨迹（低→高）：{line}")

# ---- 30 个随机初始化：局部极小不唯一 ----
finals = []
for _ in range(30):
    idx = rng.choice(n, k, replace=False)
    _, _, h = lloyd(X, k, X[idx])
    finals.append(h[-1][2])
finals = np.array(finals)
best, worst = finals.min(), finals.max()
print(f"\n30 个随机初始化的最终 J：最好={best:.2f}  中位={np.median(finals):.2f}  最差={worst:.2f}")
print(f"距最优 ≤0.1% 的重启：{int((finals <= best * 1.001).sum())}/30；"
      f"J > 1.05×最优的重启：{int((finals > best * 1.05).sum())}/30")

print("\n结论：")
print("1. 读法：分配步把每个点独立派给最近中心，是硬指派子问题的最优解，J 不增；")
print("   更新步对固定指派取簇内均值（对 μ_k 求导即得），J 严格下降；")
print("   每轮 J 单调不增且有下界 0，迭代必停在不动点——这就是 Lloyd 收敛性的全部机制。")
print(f"2. 机理：J 关于 (μ, r) 联合非凸，交替最小化只能降到起点附近的坑；")
print(f"   30 个初始化落到 {len(np.unique(np.round(finals, 1)))} 个不同的 J 平台（最好 {best:.1f}、最差 {worst:.1f}），")
print("   「收敛」只保证不动点，不保证全局最优——初始化决定落到哪个坑。")
print("3. 工程：所以生产用 k-means++ 初始化 + 多次重启（下一个示例实测两者差距），")
print("   并把「重启后 J 的离散度」当作聚类稳定性的体检指标。")
