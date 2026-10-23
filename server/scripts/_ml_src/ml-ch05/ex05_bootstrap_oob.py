# title: Bootstrap 与 OOB：为什么是 0.632，以及免费验证集怎么来的
# 1) 实测每个 bootstrap 样本集的唯一比例，对照 1-(1-1/n)^n；
# 2) 用 OOB 预测估计泛化误差，与独立测试集对比；
# 3) 同一份数据上比较单棵树与 300 棵 Bagging 的测试误差。
import numpy as np

rng = np.random.default_rng(2024)
n, B, p = 200, 300, 2
X = rng.uniform(-1, 1, (n, p))
y = 2 * X[:, 0] + np.sin(2 * np.pi * X[:, 1]) + 0.30 * rng.normal(size=n)

Xt = rng.uniform(-1, 1, (5000, p))
yt = 2 * Xt[:, 0] + np.sin(2 * np.pi * Xt[:, 1]) + 0.30 * rng.normal(size=5000)


def sse(yy):
    return float(((yy - yy.mean()) ** 2).sum())


def build(X, y, depth=0, max_depth=4, min_leaf=5):
    node = {"value": float(y.mean()), "sse": sse(y)}
    if depth >= max_depth or len(y) < 2 * min_leaf:
        return node
    best = (node["sse"], None, None)
    for f in range(X.shape[1]):
        order = np.argsort(X[:, f])
        xs, ys = X[order, f], y[order]
        c1, c2 = np.cumsum(ys), np.cumsum(ys ** 2)
        tot = len(ys)
        for i in range(min_leaf, tot - min_leaf):
            if xs[i] == xs[i - 1]:
                continue
            n1 = i
            s1, q1 = c1[i - 1], c2[i - 1]
            s2, q2 = c1[-1] - s1, c2[-1] - q1
            loss = (q1 - s1 * s1 / n1) + (q2 - s2 * s2 / (tot - n1))
            if loss < best[0] - 1e-12:
                best = (loss, f, 0.5 * (xs[i - 1] + xs[i]))
    if best[1] is None:
        return node
    f, thr = best[1], best[2]
    m = X[:, f] <= thr
    node.update({"feat": f, "thr": thr,
                 "left": build(X[m], y[m], depth + 1, max_depth, min_leaf),
                 "right": build(X[~m], y[~m], depth + 1, max_depth, min_leaf)})
    return node


def predict_one(node, x):
    while "thr" in node:
        node = node["left"] if x[node["feat"]] <= node["thr"] else node["right"]
    return node["value"]


def predict(node, X):
    return np.array([predict_one(node, x) for x in X])


oob_sum = np.zeros(n)
oob_cnt = np.zeros(n, int)
unique_frac = []
preds_test = np.empty((B, len(Xt)))

for b in range(B):
    idx = rng.integers(0, n, n)
    unique_frac.append(np.unique(idx).size / n)
    tree = build(X[idx], y[idx])
    in_bag = np.zeros(n, bool)
    in_bag[idx] = True
    mask = ~in_bag
    oob_sum[mask] += predict(tree, X[mask])
    oob_cnt[mask] += 1
    preds_test[b] = predict(tree, Xt)

oob_pred = oob_sum[oob_cnt > 0] / oob_cnt[oob_cnt > 0]
oob_mse = float(np.mean((y[oob_cnt > 0] - oob_pred) ** 2))
test_mse = float(np.mean((preds_test.mean(axis=0) - yt) ** 2))
single_mse = float(np.mean((preds_test[0] - yt) ** 2))
theory = 1 - (1 - 1 / n) ** n

print(f"n={n}, B={B}, 特征数={p}")
print(f"平均唯一入样比例 = {np.mean(unique_frac):.4f}   理论 1-(1-1/n)^n = {theory:.4f}")
print(f"每样本被 OOB 的树数：min={oob_cnt.min()}  mean={oob_cnt.mean():.1f}  max={oob_cnt.max()}")
print(f"OOB MSE      = {oob_mse:.4f}")
print(f"独立测试 MSE  = {test_mse:.4f}")
print(f"相对偏差      = {abs(oob_mse - test_mse) / test_mse:.2%}")
print(f"单棵树测试 MSE = {single_mse:.4f}   集成后 = {test_mse:.4f}   "
      f"下降 {1 - test_mse / single_mse:.1%}")
print()
print("读法 1：某个样本一次都没被抽中的概率是 (1−1/n)^n → e^{−1} ≈ 0.368，")
print("        所以唯一入样比例趋近 1−e^{−1} ≈ 0.632；n=200 时已经非常接近。")
print("读法 2：OOB 是『每棵树只在没见过该样本时预测它』，等价于交叉验证，")
print("        但不需要额外切分数据——这是 Bagging 顺带送的验证集。")
print("读法 3：OOB 估计与独立测试集的差距在 1 个百分点量级，说明它可用；")
print("        但 OOB 对强相关的树会低估集成方差，不能替代最终的独立测试。")
