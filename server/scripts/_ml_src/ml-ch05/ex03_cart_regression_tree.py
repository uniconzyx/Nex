# title: CART 回归树：叶值为什么是均值，分裂为什么用 SSE
# 手写一棵一维 CART，打印每个结点的候选切分与 SSE 下降，
# 并验证「叶值 = 该叶样本均值」是平方损失下的最优常数。
import numpy as np

rng = np.random.default_rng(7)
n = 60
X = np.sort(rng.uniform(0, 1, n))
y = np.sin(2 * np.pi * X) + 0.25 * rng.normal(size=n)


def sse(yy):
    return float(((yy - yy.mean()) ** 2).sum())


def build(X, y, depth=0, max_depth=3, min_leaf=4):
    node = {"n": len(y), "value": float(y.mean()), "sse": sse(y)}
    node["leaves"] = 1
    if depth >= max_depth or len(y) < 2 * min_leaf:
        return node
    best = (node["sse"], None, None)
    order = np.argsort(X)
    xs, ys = X[order], y[order]
    for i in range(min_leaf, len(xs) - min_leaf):
        if xs[i] == xs[i - 1]:
            continue
        thr = 0.5 * (xs[i - 1] + xs[i])
        left = ys[:i]
        right = ys[i:]
        loss = sse(left) + sse(right)
        if loss < best[0] - 1e-12:
            best = (loss, thr, i)
    if best[1] is None:
        return node
    _, thr, i = best
    mask = X <= thr
    node.update({"thr": thr, "feat": 0,
                 "left": build(X[mask], y[mask], depth + 1, max_depth, min_leaf),
                 "right": build(X[~mask], y[~mask], depth + 1, max_depth, min_leaf)})
    node["leaves"] = node["left"]["leaves"] + node["right"]["leaves"]
    return node


def show(node, indent=0):
    pad = "  " * indent
    if "thr" not in node:
        print(f"{pad}└─ 叶: n={node['n']:>2}  value={node['value']:+.4f}  sse={node['sse']:.4f}")
        return
    print(f"{pad}if x <= {node['thr']:.4f}:  (n={node['n']}, mean={node['value']:+.4f}, "
          f"sse={node['sse']:.4f})")
    show(node["left"], indent + 1)
    print(f"{pad}else:")
    show(node["right"], indent + 1)


def predict(node, x):
    while "thr" in node:
        node = node["left"] if x <= node["thr"] else node["right"]
    return node["value"]


root = build(X, y)
print("CART 回归树（max_depth=3, min_samples_leaf=4）")
show(root)

pred = np.array([predict(root, v) for v in X])
print()
print(f"训练 MSE = {np.mean((y - pred) ** 2):.4f}   叶子数 = {root['leaves']}")
print(f"常数基线 MSE = {np.mean((y - y.mean()) ** 2):.4f}")

# 验证叶值 = 均值：按预测值分组，比较每个叶子的预测与该组 y 的均值
groups = {}
for xi, pi, yi in zip(X, pred, y):
    groups.setdefault(round(pi, 10), []).append(yi)
max_dev = max(abs(np.mean(v) - k) for k, v in groups.items())
print(f"每个叶子的预测值与该叶样本均值的最大偏差 = {max_dev:.2e}")
print()
print("读法：平方损失下，叶结点最优常数是 min_c Σ(y_i−c)²，令导数为 0 得 c = mean(y)；")
print("      分裂准则则是 min_{j,s}[SSE_left + SSE_right]，等价于最大化方差下降。")
print("      注意：MSE 对异常值敏感，叶值会被拉到异常值一侧；要稳健就换 MAE（此时叶值是中位数）。")
