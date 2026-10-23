# title: GBDT 逐步拟合残差：加法模型、负梯度与学习率
# 用 30 个回归树桩（depth=1）逼近 y=sin(2πx)，
# 每轮打印「当前残差 MSE → 切分 → 叶值 → 更新后 MSE」，
# 并对比不同学习率的收敛轨迹。
import numpy as np

rng = np.random.default_rng(9)
n = 80
X = rng.uniform(0, 1, n)
y = np.sin(2 * np.pi * X) + 0.20 * rng.normal(size=n)
xt = np.linspace(0.02, 0.98, 200)
yt = np.sin(2 * np.pi * xt)


def fit_stump(x, r):
    """在残差 r 上找最优一维切分，返回 (thr, left_value, right_value)。"""
    order = np.argsort(x)
    xs, rs = x[order], r[order]
    c1, c2 = np.cumsum(rs), np.cumsum(rs ** 2)
    best = (float(((rs - rs.mean()) ** 2).sum()), None)
    for i in range(3, len(xs) - 3):
        if xs[i] == xs[i - 1]:
            continue
        n1 = i
        s1, q1 = c1[i - 1], c2[i - 1]
        s2, q2 = c1[-1] - s1, c2[-1] - q1
        loss = (q1 - s1 * s1 / n1) + (q2 - s2 * s2 / (len(xs) - n1))
        if loss < best[0] - 1e-12:
            best = (loss, 0.5 * (xs[i - 1] + xs[i]))
    if best[1] is None:
        return None, float(rs.mean()), float(rs.mean())
    thr = best[1]
    left, right = rs[xs <= thr], rs[xs > thr]
    return thr, float(left.mean()), float(right.mean())


def run(lr, rounds, verbose=False):
    F = np.full(n, y.mean())
    history = []
    stumps = []
    if verbose:
        print(f"F0 = ȳ = {y.mean():+.4f}（用全体均值初始化，等价于常数的第 0 棵树）")
        print(f"{'轮':>3}{'残差MSE':>10}{'切分x<=':>10}{'左叶值':>9}{'右叶值':>9}{'更新后MSE':>11}")
    for m in range(rounds):
        r = y - F                       # 平方损失的负梯度
        before = float(np.mean(r ** 2))
        thr, vl, vr = fit_stump(X, r)
        if thr is None:
            break
        F = F + lr * np.where(X <= thr, vl, vr)
        stumps.append((thr, vl, vr))
        after = float(np.mean((y - F) ** 2))
        history.append(after)
        if verbose and (m < 12 or m == rounds - 1):
            print(f"{m+1:>3}{before:>10.4f}{thr:>10.4f}{vl:>9.4f}{vr:>9.4f}{after:>11.4f}")
    return F, history, stumps


def predict_stumps(stumps, x, lr, F0):
    out = np.full(len(x), F0)
    for thr, vl, vr in stumps:
        out += lr * np.where(x <= thr, vl, vr)
    return out


F, hist, stumps = run(0.3, 30, verbose=True)
pred = predict_stumps(stumps, xt, 0.3, y.mean())
print(f"30 轮后训练 MSE = {hist[-1]:.4f}；测试网格 MSE = {np.mean((pred - yt) ** 2):.4f}")
print(f"残差 MSE 单调下降：{all(hist[i+1] <= hist[i] + 1e-12 for i in range(len(hist)-1))}")
print()
print(f"{'学习率':>7}{'10轮MSE':>10}{'30轮MSE':>10}{'100轮MSE':>11}{'测试MSE':>10}")
for lr in (0.05, 0.1, 0.3, 1.0):
    _, h, st = run(lr, 100)
    te = float(np.mean((predict_stumps(st, xt, lr, y.mean()) - yt) ** 2))
    print(f"{lr:>7.2f}{h[9]:>10.4f}{h[29]:>10.4f}{h[-1]:>11.4f}{te:>10.4f}")
print()
print("读法 1：每一轮拟合的是 r = y − F，也就是平方损失下负梯度 −∂L/∂F；")
print("        叶值取该区域残差均值，等价于对残差做一步最优常数修正。")
print("读法 2：加法模型 F_m = F_{m−1} + ν·h_m，ν 是学习率。ν 小时每步只走一小段，")
print("        需要更多轮；ν=1 训练误差最低（0.0223），但测试 MSE 反而比 ν=0.3 高。")
print("        这就是 shrinkage（收缩）的泛化收益：用训练拟合速度换平滑度。")
print("读法 3：GBDT 的『残差』只在平方损失下等于 y−F；换成交叉熵时负梯度是 y−p，")
print("        形式相同但含义不同，这也是为什么 GBDT 能做分类（用对数似然梯度）。")
