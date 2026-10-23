# title: 变量重要性偏差：纯噪声数据上不纯度重要性仍然「有话可说」
# 场景 A：y 与所有特征独立，看不纯度重要性如何虚构出 10% 量级的份额；
# 场景 B：有效特征与它的副本共存，看置换重要性如何被相关特征摊薄。
import numpy as np

rng = np.random.default_rng(31)
B, depth, min_leaf = 40, 4, 5
depth_limit = depth


N_TOTAL = 1


def _grow(X, y, imp, node, d):
    if d >= depth_limit or len(y) < 2 * min_leaf:
        return node
    best = (node["sse"], None, None)
    for f in range(X.shape[1]):
        order = np.argsort(X[:, f])
        xs, ys = X[order, f], y[order]
        c1, c2 = np.cumsum(ys), np.cumsum(ys ** 2)
        tot = len(ys)
        for i in range(min_leaf, tot - min_leaf + 1):
            if xs[i] == xs[i - 1]:
                continue
            s1, q1 = c1[i - 1], c2[i - 1]
            s2, q2 = c1[-1] - s1, c2[-1] - q1
            loss = (q1 - s1 * s1 / i) + (q2 - s2 * s2 / (tot - i))
            if loss < best[0] - 1e-12:
                best = (loss, f, 0.5 * (xs[i - 1] + xs[i]))
    if best[1] is None:
        return node
    f, thr = best[1], best[2]
    m = X[:, f] <= thr
    left = _grow(X[m], y[m], imp, {"value": float(y[m].mean()),
                                   "sse": float(((y[m] - y[m].mean()) ** 2).sum())}, d + 1)
    right = _grow(X[~m], y[~m], imp, {"value": float(y[~m].mean()),
                                      "sse": float(((y[~m] - y[~m].mean()) ** 2).sum())}, d + 1)
    imp[f] += (node["sse"] - left["sse"] - right["sse"]) / max(1, N_TOTAL)
    node.update({"feat": f, "thr": thr, "left": left, "right": right})
    return node


def predict_tree(node, X):
    out = np.empty(len(X))
    for i, x in enumerate(X):
        cur = node
        while "thr" in cur:
            cur = cur["left"] if x[cur["feat"]] <= cur["thr"] else cur["right"]
        out[i] = cur["value"]
    return out


def train_forest(X, y, B=B):
    global N_TOTAL
    N_TOTAL = len(X)
    imp = np.zeros(X.shape[1])
    trees = []
    for _ in range(B):
        idx = rng.integers(0, len(X), len(X))
        trees.append(_grow(X[idx], y[idx], imp, {"value": float(y[idx].mean()),
                                                "sse": float(((y[idx] - y[idx].mean()) ** 2).sum())}, 0))
    return imp, trees


def forest_predict(trees, X):
    return np.mean([predict_tree(t, X) for t in trees], axis=0)


def perm_importance(trees, X, y, repeats=2):
    base = float(np.mean((forest_predict(trees, X) - y) ** 2))
    out = np.zeros(X.shape[1])
    for f in range(X.shape[1]):
        ds = []
        for _ in range(repeats):
            Xp = X.copy()
            Xp[:, f] = rng.permutation(Xp[:, f])
            ds.append(float(np.mean((forest_predict(trees, Xp) - y) ** 2)) - base)
        out[f] = float(np.mean(ds))
    return out, base


# ---------------- 场景 A：纯噪声 ----------------
n = 400
Xa = np.column_stack([rng.integers(0, 2, n).astype(float), rng.normal(size=(n, 9))])
ya = rng.normal(size=n)
Xa_te = np.column_stack([rng.integers(0, 2, n).astype(float), rng.normal(size=(n, 9))])
ya_te = rng.normal(size=n)
imp_a, trees_a = train_forest(Xa, ya)
perm_a, mse_a = perm_importance(trees_a, Xa_te, ya_te)
imp_a = imp_a / imp_a.sum()

print("场景 A：y 与全部 10 个特征独立（纯噪声），B=40, depth=4")
print(f"{'特征':<12}{'不纯度占比':>10}{'置换ΔMSE':>10}")
names_a = ["x_bin"] + [f"noise{j}" for j in range(1, 10)]
for i in np.argsort(-imp_a):
    print(f"{names_a[i]:<12}{imp_a[i]:>10.3f}{perm_a[i]:>10.4f}")
print(f"不纯度重要性最大值 = {imp_a.max():.3f}；置换重要性最大值 = {perm_a.max():.4f}")
print("读法 1：没有任何有效特征，不纯度重要性仍然人人有份（最大 0.24）。")
print("        这是训练集上的过拟合份额，不是预测能力。")
print("读法 2：二叉特征只有 1 个候选切点，连续噪声有 n−1 个，候选越多越容易碰巧下降；")
print("        所以高基数/连续变量的不纯度重要性被系统性高估（Strobl et al., 2007）。")
print("读法 3：置换重要性在独立测试集上全部≈0：打乱噪声特征不会让模型变差，")
print("        它衡量的是预测能力，不会为候选切点数量买单。")

# ---------------- 场景 B：相关副本摊薄 ----------------
n2 = 400
z1, z2 = rng.normal(size=n2), rng.normal(size=n2)
Xb = np.column_stack([z1, z1 + 0.01 * rng.normal(size=n2),
                      z2, z2 + 0.01 * rng.normal(size=n2),
                      rng.normal(size=(n2, 2))])
yb = 2.0 * z1 + 2.0 * z2 + 0.4 * rng.normal(size=n2)
z1t, z2t = rng.normal(size=n2), rng.normal(size=n2)
Xb_te = np.column_stack([z1t, z1t + 0.01 * rng.normal(size=n2),
                         z2t, z2t + 0.01 * rng.normal(size=n2),
                         rng.normal(size=(n2, 2))])
yb_te = 2.0 * z1t + 2.0 * z2t + 0.4 * rng.normal(size=n2)
imp_b, trees_b = train_forest(Xb, yb)
perm_b, mse_b = perm_importance(trees_b, Xb_te, yb_te)

print()
print("场景 B：两个强因子各带一个近副本（副本相关系数≈0.999）")
print(f"{'特征':<12}{'置换ΔMSE':>10}")
names_b = ["z1", "z1_copy", "z2", "z2_copy", "noise1", "noise2"]
for i in range(len(names_b)):
    print(f"{names_b[i]:<12}{perm_b[i]:>10.4f}")
print(f"z1 组（本体+副本）合计 = {perm_b[0] + perm_b[1]:.3f}")
print(f"z2 组（本体+副本）合计 = {perm_b[2] + perm_b[3]:.3f}")
print("读法 4：打乱一个副本，另一个仍在树上，模型几乎不受影响，所以单个都被低估；")
print("        按单特征排名会把一个强因子拆成两个『中等重要』特征。")
print("        重要性是『相对于当前特征集合』的边际贡献，报告时要声明特征集，")
print("        并把相关特征分组求和，否则会得出『这两个都不重要』的错误结论。")
