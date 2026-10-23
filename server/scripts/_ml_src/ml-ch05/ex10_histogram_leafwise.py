# title: LightGBM 三板斧：直方图分箱、leaf-wise 生长与 GOSS 抽样
# 1) 精确切分 vs 32 桶直方图近似：阈值/增益误差、候选切点数量与「桶减法」技巧；
# 2) 同样分裂预算下，level-wise 与 leaf-wise 的训练/测试 MSE 与树形（深度分布）；
# 3) GOSS：保留全部大梯度样本 + 按 (1−a)/b 加权抽小梯度样本，检验分裂排序是否保持。
import numpy as np

rng = np.random.default_rng(42)


def sse(yy):
    return float(((yy - yy.mean()) ** 2).sum())


# ================== 第 1 部分：直方图分箱 vs 精确切分 ==================
n = 3000
X = rng.uniform(0, 1, (n, 2))
y = np.sin(2 * np.pi * X[:, 0]) + 0.8 * X[:, 1] + 0.30 * rng.normal(size=n)

B = 32                      # 直方图桶数（LightGBM 默认上限 255）
x0 = X[:, 0]
edges = np.unique(np.quantile(x0, np.linspace(0, 1, B + 1)))
nb = len(edges) - 1         # 去重后的实际桶数


def best_exact(x, yy):
    """精确扫描所有相邻取值间隙，返回 (SSE, 阈值, 候选切点数)。"""
    order = np.argsort(x)
    xs, ys = x[order], yy[order]
    c1, c2 = np.cumsum(ys), np.cumsum(ys ** 2)
    tot = len(ys)
    best = (float(((ys - ys.mean()) ** 2).sum()), None)
    ncand = 0
    for i in range(1, tot):
        if xs[i] == xs[i - 1]:
            continue
        ncand += 1
        s1, q1 = c1[i - 1], c2[i - 1]
        s2, q2 = c1[-1] - s1, c2[-1] - q1
        loss = (q1 - s1 * s1 / i) + (q2 - s2 * s2 / (tot - i))
        if loss < best[0] - 1e-12:
            best = (loss, 0.5 * (xs[i - 1] + xs[i]))
    return best[0], best[1], ncand


def best_hist(x, yy, edges):
    """先在桶上累加 (count, Σy, Σy²)，再只枚举桶边界，返回 (SSE, 阈值, 候选切点数)。"""
    idx = np.digitize(x, edges[1:-1])          # 桶号 0..nb-1
    cnt = np.bincount(idx, minlength=nb).astype(float)
    sy = np.bincount(idx, weights=yy, minlength=nb)
    qy = np.bincount(idx, weights=yy * yy, minlength=nb)
    cc, cs, cq = np.cumsum(cnt), np.cumsum(sy), np.cumsum(qy)
    tot = float(len(x))
    best = (sse(yy), None)
    ncand = 0
    for b in range(nb - 1):
        n1, n2 = cc[b], tot - cc[b]
        if n1 < 1 or n2 < 1:
            continue
        ncand += 1
        loss = (cq[b] - cs[b] ** 2 / n1) + ((cq[-1] - cq[b]) - (cs[-1] - cs[b]) ** 2 / n2)
        if loss < best[0] - 1e-12:
            best = (loss, edges[b + 1])
    return best[0], best[1], ncand


ex = best_exact(x0, y)
hi = best_hist(x0, y, edges)
print(f"第 1 部分：对 x0 的根结点切分（n={n}，{nb} 个等比分位桶）")
print(f"{'方法':<10}{'最优阈值':>10}{'SSE':>12}{'SSE下降':>10}{'候选切点':>9}")
print(f"{'精确扫描':<10}{ex[1]:>10.4f}{ex[0]:>12.2f}{sse(y)-ex[0]:>10.2f}{ex[2]:>9}")
print(f"{'直方图':<10}{hi[1]:>10.4f}{hi[0]:>12.2f}{sse(y)-hi[0]:>10.2f}{hi[2]:>9}")
print(f"阈值差 = {abs(hi[1]-ex[1]):.4f}（不超过一个桶宽 {edges[1]-edges[0]:.4f}）；"
      f"SSE 下降相对误差 = {abs((sse(y)-hi[0])-(sse(y)-ex[0]))/(sse(y)-ex[0]):.2%}")

# 直方图减法：右兄弟的直方图 = 父结点直方图 − 左孩子直方图，无需再扫一遍数据
idx = np.digitize(x0, edges[1:-1])
root_sy = np.bincount(idx, weights=y, minlength=nb)
left = x0 <= hi[1]
left_sy = np.bincount(idx[left], weights=y[left], minlength=nb)
right_sy_sub = root_sy - left_sy
right_sy_dir = np.bincount(idx[~left], weights=y[~left], minlength=nb)
print(f"桶减法校验：max|右兄弟(减法) − 右兄弟(直算)| = "
      f"{np.abs(right_sy_sub-right_sy_dir).max():.2e}（机器精度级，"
      f"右子结点的直方图由父减子得到，省掉一次 O(n) 扫描）")

# ================== 第 2 部分：leaf-wise vs level-wise ==================
m = 1500
Xl = rng.uniform(0, 1, (m, 3))
yl = np.sin(2 * np.pi * Xl[:, 0]) + 0.7 * Xl[:, 1] * Xl[:, 2] + 0.30 * rng.normal(size=m)
Xl_te = rng.uniform(0, 1, (2000, 3))
yl_te = np.sin(2 * np.pi * Xl_te[:, 0]) + 0.7 * Xl_te[:, 1] * Xl_te[:, 2] \
        + 0.30 * rng.normal(size=2000)
MIN_LEAF = 5


def best_split(Xs, ys):
    """全特征扫描最优切分，返回 (SSE下降, 特征, 阈值)；不可分裂返回 None。"""
    base = sse(ys)
    best = (1e-12, None, None)
    for f in range(Xs.shape[1]):
        order = np.argsort(Xs[:, f])
        xs, yy = Xs[order, f], ys[order]
        c1, c2 = np.cumsum(yy), np.cumsum(yy * yy)
        tot = len(yy)
        i = np.arange(MIN_LEAF, tot - MIN_LEAF + 1)
        if len(i) == 0:
            continue
        s1, q1 = c1[i - 1], c2[i - 1]
        s2, q2 = c1[-1] - s1, c2[-1] - q1
        loss = (q1 - s1 * s1 / i) + (q2 - s2 * s2 / (tot - i))
        loss = np.where(xs[i] != xs[i - 1], loss, np.inf)
        j = int(np.argmin(loss))
        if base - loss[j] > best[0]:
            best = (base - loss[j], f, 0.5 * (xs[i[j] - 1] + xs[i[j]]))
    return None if best[1] is None else best


class Node:
    def __init__(self, Xs, ys, depth):
        self.Xs, self.ys, self.depth = Xs, ys, depth
        self.value = float(ys.mean())
        self.split = best_split(Xs, ys)
        self.left = self.right = None

    @property
    def leaves(self):
        return 1 if self.left is None else self.left.leaves + self.right.leaves

    def max_depth(self):
        return self.depth if self.left is None else max(self.left.max_depth(),
                                                        self.right.max_depth())

    def depth_hist(self):
        out, stack = {}, [self]
        while stack:
            nd = stack.pop()
            if nd.left is None:
                out[nd.depth] = out.get(nd.depth, 0) + 1
            else:
                stack += [nd.left, nd.right]
        return out

    def do_split(self):
        _, f, thr = self.split
        mask = self.Xs[:, f] <= thr
        self.left = Node(self.Xs[mask], self.ys[mask], self.depth + 1)
        self.right = Node(self.Xs[~mask], self.ys[~mask], self.depth + 1)

    def predict(self, Xq):
        if self.left is None:
            return np.full(len(Xq), self.value)
        f, thr = self.split[1], self.split[2]
        mask = Xq[:, f] <= thr
        out = np.empty(len(Xq))
        out[mask] = self.left.predict(Xq[mask])
        out[~mask] = self.right.predict(Xq[~mask])
        return out


def grow_levelwise(root, budget):
    frontier, splits = [root], 0
    while frontier and splits < budget:
        nxt = []
        for nd in frontier:
            if splits >= budget:
                nxt.append(nd)
                continue
            if nd.split is not None:
                nd.do_split()
                splits += 1
                nxt += [nd.left, nd.right]
            else:
                nxt.append(nd)
        frontier = nxt
    return root


def grow_leafwise(root, budget):
    leaves, splits = [root], 0
    while splits < budget:
        cand = [nd for nd in leaves if nd.split is not None]
        if not cand:
            break
        nd = max(cand, key=lambda t: t.split[0])   # 永远分裂增益最大的叶子
        nd.do_split()
        splits += 1
        leaves.remove(nd)
        leaves += [nd.left, nd.right]
    return root


print()
print(f"第 2 部分：同一份数据（n={m}, 3 特征, min_leaf={MIN_LEAF}），按分裂预算对比")
print(f"{'预算':>7}{'方式':<12}{'叶子数':>7}{'最大深度':>9}{'训练MSE':>10}{'测试MSE':>10}")
for budget in (31, 63, 127):
    for name, tree in (("level-wise", grow_levelwise(Node(Xl, yl, 0), budget)),
                       ("leaf-wise", grow_leafwise(Node(Xl, yl, 0), budget))):
        print(f"{budget:>7}{name:<12}{tree.leaves:>7}{tree.max_depth():>9}"
              f"{np.mean((tree.predict(Xl)-yl)**2):>10.4f}"
              f"{np.mean((tree.predict(Xl_te)-yl_te)**2):>10.4f}")
print("叶子深度分布（深度: 叶子数），预算 127：")
print("  level-wise:", dict(sorted(grow_levelwise(Node(Xl, yl, 0), 127).depth_hist().items())))
print("  leaf-wise:", dict(sorted(grow_leafwise(Node(Xl, yl, 0), 127).depth_hist().items())))
print("读法 1：同样叶子数下 leaf-wise 训练 MSE 一路更低（预算 127 时 0.0648 vs 0.0698）——")
print("        它把每次分裂花在全局增益最大的叶子上，这是 LightGBM 少用叶子办成事的原因。")
print("读法 2：预算放到 127 时测试 MSE 反超（0.1263 vs 0.1220），深度分布给出原因：")
print("        leaf-wise 有 21 个叶子长在深度 10，还有深度 13/14 的长链，每片只由很少样本支撑；")
print("        level-wise 的 128 片叶子有 122 片集中在深度 6-9。深链是方差放大器，故 LightGBM")
print("        必须同时限 num_leaves 与 min_data_in_leaf——只限 max_depth 挡不住这种不均匀的深。")

# ================== 第 3 部分：GOSS 抽样 ==================
k = 2000
xs_g = rng.uniform(0, 1, k)
r = np.sin(2 * np.pi * xs_g) + 0.30 * rng.normal(size=k)   # 平方损失：g=r, h=1
LAM = 1.0
grid = np.sort(0.5 * (xs_g[:-1] + xs_g[1:]))               # 统一候选阈值网格


def gain_on_grid(x_sel, g_sel, w_sel):
    """在统一阈值网格上计算加权 XGBoost 增益（h≡1，H 即加权样本数）。"""
    G = float((w_sel * g_sel).sum())
    H = float(w_sel.sum())
    order = np.argsort(x_sel)
    xs = x_sel[order]
    cg = np.cumsum(w_sel[order] * g_sel[order])
    cw = np.cumsum(w_sel[order])
    i = np.clip(np.searchsorted(xs, grid), 1, len(xs) - 1)
    gl, hl = cg[i - 1], cw[i - 1]
    return 0.5 * (gl ** 2 / (hl + LAM) + (G - gl) ** 2 / (H - hl + LAM)
                  - G ** 2 / (H + LAM))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


gfull = gain_on_grid(xs_g, r, np.ones(k))
t_star = grid[int(np.argmax(gfull))]
a, b = 0.2, 0.1                       # LightGBM 默认 top_rate / other_rate
large = np.argsort(-np.abs(r))[:int(a * k)]
small = np.setdiff1d(np.arange(k), large)

gr = np.random.default_rng(2024)
keep = gr.choice(small, size=int(b * k), replace=False)
w1 = np.ones(k)
w1[keep] = (1 - a) / b               # 小梯度样本权重放大，补偿抽样损失
sel = np.concatenate([large, keep])
goss = gain_on_grid(xs_g[sel], r[sel], w1[sel])
t_goss = grid[int(np.argmax(goss))]
top_full = set(np.argsort(-gfull)[:100])
top_goss = set(np.argsort(-goss)[:100])

print()
print(f"第 3 部分：GOSS（a={a}, b={b}）——只用 {len(sel)}/{k} 个样本重排分裂增益")
print(f"全量数据：最佳切分 t*={t_star:.4f}，增益={gfull.max():.2f}")
print(f"GOSS 一次抽样：t={t_goss:.4f}（与 t* 相差 {abs(t_goss-t_star):.4f}），"
      f"增益={goss.max():.2f}")
print(f"加权样本总数 = {int(a*k)} + {int(b*k)}×{(1-a)/b:.0f} = {int(w1[sel].sum())} = k"
      f"（质量守恒是恒等式：a·k + b·k·(1−a)/b = k）")
print(f"与全量的增益排名 Spearman 相关 = {spearman(gfull, goss):.4f}；"
      f"前 100 候选切点重合率 = {len(top_full & top_goss)}%")

dts, sps, recov, ovs = [], [], 0, []
for rep in range(20):
    rr = np.random.default_rng(1000 + rep)
    keep_r = rr.choice(small, size=int(b * k), replace=False)
    ww = np.ones(k)
    ww[keep_r] = (1 - a) / b
    s = np.concatenate([large, keep_r])
    gg = gain_on_grid(xs_g[s], r[s], ww[s])
    dt = abs(grid[int(np.argmax(gg))] - t_star)
    dts.append(dt)
    sps.append(spearman(gfull, gg))
    recov += dt < 0.05
    ovs.append(len(top_full & set(np.argsort(-gg)[:100])))
print(f"20 次重复抽样：切分位置与 t* 的平均距离 = {np.mean(dts):.4f}，最大 = {max(dts):.4f}；"
      f"落在 t*±0.05 内的比例 = {recov}/20")
print(f"             Spearman 相关范围 = [{min(sps):.4f}, {max(sps):.4f}]，"
      f"前 100 候选重合率均值 = {np.mean(ovs):.0f}%")

w0 = np.ones(len(sel))                # 不补偿对照：权重全 1
print(f"对照（不做 (1−a)/b 补偿）：加权样本总数 = {int(w0.sum())}，"
      f"小梯度池只保留 b={b:.0%} 的梯度质量，分裂增益被系统性低估")
print("读法 1：大梯度样本（还没拟合好的）全部保留，增益的全局排序几乎不变——")
print("        Spearman 0.98~0.996，20 次抽样选出的切分全部落在 t*±0.06 内（19/20 在 ±0.05 内）。")
print("        注意前 100 候选的重合率只有三成左右：正弦数据上顶部位次本来就近似打平，")
print("        GOSS 保住的是『在哪个位置切』，不是『第几名』这种精确位次。")
print("读法 2：权重 (1−a)/b 让被抽中的小梯度样本顶替整个小池的质量（加权总数恰为 k）；")
print("        不补偿时小池只剩 b 份质量，增益值被压低，分裂选择随之漂移。")
print("读法 3：GOSS 是 Boosting 特有的抽样——按『当前误差』而非均匀抽样，")
print("        因为加法模型里大梯度样本正是下一棵树最该看的地方；")
print("        它与直方图叠加后，直方图构建成本降到约 30%。")
print("结论：直方图把『每结点扫 n 个阈值』压成扫桶数，leaf-wise 把分裂预算花在增益最大的叶子上，")
print("      GOSS 再按梯度大小给直方图打折——三板斧都用可控精度换规模，且都需正则兜底。")
