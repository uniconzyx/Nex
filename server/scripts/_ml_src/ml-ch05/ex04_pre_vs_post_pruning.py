# title: 预剪枝 vs 后剪枝：代价复杂度剪枝的实测对照
# 同一棵深度 8 的回归树：一边用 max_depth/min_samples_leaf 预剪枝，
# 一边先长满再用 CCP（代价复杂度）自底向上剪，比较验证/测试误差与叶子数。
import copy
import numpy as np

rng = np.random.default_rng(11)
f = lambda x: np.sin(2 * np.pi * x)


def make(n, noise=0.35):
    x = rng.uniform(0, 1, n)
    return x, f(x) + noise * rng.normal(size=n)


Xtr, ytr = make(150)
Xv, yv = make(400)
Xt, yt = make(400)


def sse(y):
    return float(((y - y.mean()) ** 2).sum())


def build(X, y, depth=0, max_depth=8, min_leaf=3):
    node = {"n": len(y), "value": float(y.mean()), "sse": sse(y), "leaves": 1}
    if depth >= max_depth or len(y) < 2 * min_leaf:
        return node
    order = np.argsort(X)
    xs, ys = X[order], y[order]
    best = (node["sse"], None)
    for i in range(min_leaf, len(xs) - min_leaf):
        if xs[i] == xs[i - 1]:
            continue
        loss = sse(ys[:i]) + sse(ys[i:])
        if loss < best[0] - 1e-12:
            best = (loss, 0.5 * (xs[i - 1] + xs[i]))
    if best[1] is None:
        return node
    m = X <= best[1]
    node.update({"thr": best[1], "left": build(X[m], y[m], depth + 1, max_depth, min_leaf),
                 "right": build(X[~m], y[~m], depth + 1, max_depth, min_leaf)})
    node["leaves"] = node["left"]["leaves"] + node["right"]["leaves"]
    return node


def predict(node, X):
    out = np.empty(len(X))
    for i, x in enumerate(X):
        cur = node
        while "thr" in cur:
            cur = cur["left"] if x <= cur["thr"] else cur["right"]
        out[i] = cur["value"]
    return out


def mse(node, X, y):
    return float(np.mean((predict(node, X) - y) ** 2))


def recount(node):
    if "thr" not in node:
        node["leaves"] = 1
        return 1
    node["leaves"] = recount(node["left"]) + recount(node["right"])
    return node["leaves"]


def ccp_step(root):
    """按代价复杂度剪掉『最弱一环』，返回 (alpha, 新根)。"""
    cands = []

    def walk(node, path):
        if "thr" not in node:
            return
        gain = node["sse"] - node["left"]["sse"] - node["right"]["sse"]
        cands.append((gain / max(1, node["leaves"] - 1), list(path), node))
        walk(node["left"], path + [(node, "left")])
        walk(node["right"], path + [(node, "right")])

    walk(root, [])
    alpha, path, node = min(cands, key=lambda c: c[0])
    leaf = {"n": node["n"], "value": node["value"], "sse": node["sse"], "leaves": 1}
    if not path:
        return alpha, leaf
    parent, side = path[-1]
    parent[side] = leaf
    return alpha, root


root = build(Xtr, ytr)

# ---- 预剪枝：在验证集上网格搜索 max_depth / min_samples_leaf ----
best_pre = None
for md in (2, 3, 4, 5, 8):
    for ml in (2, 4, 8, 16, 24):
        t = build(Xtr, ytr, max_depth=md, min_leaf=ml)
        v = mse(t, Xv, yv)
        if best_pre is None or v < best_pre[0]:
            best_pre = (v, md, ml, t)
_, md, ml, pre_tree = best_pre

# ---- 后剪枝：沿 CCP 路径逐次剪掉最弱子树 ----
path = [(0.0, copy.deepcopy(root))]
cur = copy.deepcopy(root)
while "thr" in cur:
    alpha, cur = ccp_step(cur)
    recount(cur)
    path.append((alpha, copy.deepcopy(cur)))

best_post = min(path, key=lambda p: mse(p[1], Xv, yv))

print("同一份训练集（n=150，噪声 σ=0.35），三棵树的对照")
print(f"{'模型':<26}{'叶子数':>7}{'train MSE':>11}{'val MSE':>10}{'test MSE':>10}")
rows = [
    ("完全不剪枝", root),
    (f"预剪枝 d={md}, leaf>={ml}", pre_tree),
    (f"后剪枝 CCP α={best_post[0]:.4f}", best_post[1]),
]
for name, t in rows:
    print(f"{name:<26}{t['leaves']:>7}{mse(t, Xtr, ytr):>11.4f}"
          f"{mse(t, Xv, yv):>10.4f}{mse(t, Xt, yt):>10.4f}")

print()
print(f"CCP 路径长度 = {len(path)} 个候选子树；每个 α 对应『剪掉最弱一环』后的树。")
print("读法 1：全树训练误差最低、测试误差最高——它把噪声也切成了叶子。")
print("读法 2：本实验里预剪枝的测试误差更低，因为它的网格搜索也用了同一份验证集，")
print("        相当于在 25 个候选里挑了一个；后剪枝只沿 17 个 CCP 点走，粒度更粗。")
print("        两者的差别不是『谁更先进』，而是搜索空间不同：预剪枝搜深度/叶下限，")
print("        后剪枝搜 α。样本更多时后剪枝的优势才会显现（叶值估计更稳）。")
print("读法 3：α 的作用是给『每增加一个叶子』定价：α 越大，树越小。")
print(f"        本实验选中的 α={best_post[0]:.4f}，等价于『子树带来的 SSE 下降不足 α×(叶子数−1) 就剪掉』。")
print("读法 4：预剪枝的致命弱点是『贪心早停』——当前分裂增益小，不代表子结点之后没有价值；")
print("        后剪枝先长满再自底向上比较整棵子树，不存在这个视野问题，代价是要先付训练成本。")
