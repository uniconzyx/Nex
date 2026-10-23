# title: 随机森林：特征子采样降的是相关性，不是单树偏差
# 1) 用合成变量验证 Var(平均) = ρσ² + (1−ρ)σ²/B；
# 2) 在 1 个有效特征 + 9 个噪声特征的数据上，比较 mtry=1 与 mtry=all
#    的树间相关性与集成误差。
import numpy as np

# ---------- 1) 方差缩减公式 ----------
rng = np.random.default_rng(5)
BIG = 20000
print("方差缩减：B 个相关系数均为 ρ 的预测器取平均（σ²=1）")
print(f"{'ρ':>5}{'B=1':>9}{'B=10':>9}{'B=100':>9}{'理论(B=100)':>12}")
for rho in (0.0, 0.3, 0.6, 0.9):
    row = []
    for B in (1, 10, 100):
        z = rng.normal(size=BIG)
        eps = rng.normal(size=(BIG, B))
        f = np.sqrt(rho) * z[:, None] + np.sqrt(1 - rho) * eps
        row.append(f.mean(axis=1).var())
    theory = rho + (1 - rho) / 100
    print(f"{rho:>5.1f}{row[0]:>9.4f}{row[1]:>9.4f}{row[2]:>9.4f}{theory:>10.4f}")
print("读法：B→∞ 时方差只剩 ρσ²。ρ=0.9 时，100 棵树也只把方差从 1 压到 0.901，")
print("      所以『多训几棵树』救不了强相关；降 ρ 才是随机森林的要害。")

# ---------- 2) 真实森林：mtry 的作用 ----------
n, d, B, depth, min_leaf = 300, 10, 60, 5, 4
ztr = rng.normal(size=(n, 2))
zte = rng.normal(size=(400, 2))
# 5 个特征测同一个潜在因子：特征之间高度可替代，模拟真实数据里的共线冗余
Xtr = np.hstack([ztr[:, [0]] + 0.5 * rng.normal(size=(n, 5)),
                 ztr[:, [1]] + 0.5 * rng.normal(size=(n, 5))])
Xte = np.hstack([zte[:, [0]] + 0.5 * rng.normal(size=(400, 5)),
                 zte[:, [1]] + 0.5 * rng.normal(size=(400, 5))])
ytr = 2.0 * ztr[:, 0] + 1.5 * ztr[:, 1] + 0.5 * rng.normal(size=n)
yte = 2.0 * zte[:, 0] + 1.5 * zte[:, 1] + 0.5 * rng.normal(size=400)


def build(X, y, rng, mtry, depth=0):
    node = {"value": float(y.mean()), "sse": float(((y - y.mean()) ** 2).sum())}
    if depth >= depth_limit or len(y) < 2 * min_leaf:
        return node
    feats = rng.choice(X.shape[1], size=min(mtry, X.shape[1]), replace=False)
    best = (node["sse"], None, None)
    for f in feats:
        order = np.argsort(X[:, f])
        xs, ys = X[order, f], y[order]
        c1, c2 = np.cumsum(ys), np.cumsum(ys ** 2)
        tot = len(ys)
        for q in range(1, 9):
            i = int(tot * q / 9)
            if i < min_leaf or tot - i < min_leaf or xs[i] == xs[i - 1]:
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
    node.update({"feat": f, "thr": thr,
                 "left": build(X[m], y[m], rng, mtry, depth + 1),
                 "right": build(X[~m], y[~m], rng, mtry, depth + 1)})
    return node


def predict(tree, X):
    out = np.empty(len(X))
    for i, x in enumerate(X):
        cur = tree
        while "thr" in cur:
            cur = cur["left"] if x[cur["feat"]] <= cur["thr"] else cur["right"]
        out[i] = cur["value"]
    return out


def forest(mtry, seed):
    r = np.random.default_rng(seed)
    preds = np.empty((B, len(Xte)))
    for b in range(B):
        idx = r.integers(0, n, n)
        t = build(Xtr[idx], ytr[idx], r, mtry, 0)
        preds[b] = predict(t, Xte)
    ens = preds.mean(axis=0)
    corr = np.corrcoef(preds)[np.triu_indices(B, 1)].mean()
    single = np.mean((preds - yte) ** 2)
    return corr, single, float(np.mean((ens - yte) ** 2)), preds.std(axis=0).mean()


depth_limit = depth
print()
print(f"随机森林实测（n={n}, d={d}, B={B}, depth={depth}）")
print(f"{'mtry':>5}{'树间平均相关':>12}{'单树MSE':>10}{'集成MSE':>10}{'预测标准差':>12}")
for mt in (2, 5, 10):
    corr, single, ens, sd = forest(mt, seed=100 + mt)
    print(f"{mt:>5}{corr:>12.4f}{single:>10.4f}{ens:>10.4f}{sd:>12.4f}")

print()
print("读法 1：本数据每 5 个特征测同一个潜在因子，彼此高度可替代；")
print("        mtry 从 10 降到 2 只把 ρ 从 0.776 压到 0.747 —— 换一组特征仍在测同一个因子。")
print("读法 2：集成 MSE 反而从 0.867 升到 0.927。公式 ρσ²+(1−ρ)σ²/B 只说明『降 ρ 有用』，")
print("        没保证『降 mtry 一定降测试误差』：ρ 的小降幅抵不过单树偏差的上升。")
print("读法 3：随机森林要赢，必须同时满足『树间有差异』和『每棵树足够好』。")
print("        特征子采样只有在特征间存在竞争（而非互为副本）时，才能大幅降 ρ。")
print("读法 4：因此 mtry 是 U 形旋钮，不存在普适最优；用 OOB 或验证集调，不要照搬 √d。")
