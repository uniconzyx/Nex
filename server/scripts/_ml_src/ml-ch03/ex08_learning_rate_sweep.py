# title: 学习率过大与过小：同一条损失曲线上的两种失败
# 关键手法：固定初始化与数据，只扫学习率，记录多个检查点的损失和是否发散。
import numpy as np

np.seterr(over="ignore", invalid="ignore")
rng = np.random.default_rng(3)
n, d = 160, 2
X = rng.uniform(-2, 2, (n, d))
y = (np.sin(2 * X[:, 0]) + np.cos(2 * X[:, 1]) + rng.normal(0, 0.05, n)).reshape(-1, 1)
Xva = rng.uniform(-2, 2, (300, d))
yva = (np.sin(2 * Xva[:, 0]) + np.cos(2 * Xva[:, 1])).reshape(-1, 1)

def init():
    r = np.random.default_rng(7)
    return [r.normal(0, 0.5, (d, 24)), np.zeros(24),
            r.normal(0, 0.5, (24, 1)), np.zeros(1)]

def mse(params, X, y):
    W1, b1, W2, b2 = params
    p = np.tanh(X @ W1 + b1) @ W2 + b2
    return np.mean((p - y) ** 2)

def train(lr, iters=400):
    params = init()
    hist = {}
    for t in range(iters):
        W1, b1, W2, b2 = params
        a1 = np.tanh(X @ W1 + b1)
        p = a1 @ W2 + b2
        m = len(X)
        dp = 2 * (p - y) / m
        dW2 = a1.T @ dp; db2 = dp.sum(0)
        dz1 = (dp @ W2.T) * (1 - a1 ** 2)
        dW1 = X.T @ dz1; db1 = dz1.sum(0)
        params = [W1 - lr * dW1, b1 - lr * db1, W2 - lr * dW2, b2 - lr * db2]
        if t + 1 in (20, 100, 200, 400):
            hist[t + 1] = mse(params, X, y)
        if not np.all(np.isfinite(params[2])):
            for k in (20, 100, 200, 400):
                hist.setdefault(k, float("inf"))
            break
    return hist, mse(params, Xva, yva) if np.all(np.isfinite(params[2])) else float("inf")

print("目标：y = sin(2x1) + cos(2x2)，网络 2-24-1 tanh，全批量梯度下降")
print(f"{'lr':>8}{'@20':>12}{'@100':>12}{'@200':>12}{'@400':>12}{'验证 MSE':>12}  状态")
for lr in (0.001, 0.01, 0.05, 0.2, 0.5):
    h, v = train(lr)
    last = h[400]
    if not np.isfinite(last) or last > 1e6:
        status = "发散"
    elif last > 0.2:
        status = "几乎没学"
    else:
        status = "正常收敛"
    def fmt(x):
        return "inf" if (not np.isfinite(x) or x > 1e6) else f"{x:.4f}"
    print(f"{lr:>8}{fmt(h[20]):>12}{fmt(h[100]):>12}{fmt(h[200]):>12}{fmt(last):>12}{fmt(v):>12}  {status}")

print("\n读法：lr 太小时 400 步仍在高位；lr 适中时损失快速下降后走平；")
print("lr 过大时参数越过谷底反复弹跳，损失震荡甚至指数发散（inf/nan）。")
print("结论：先用对数网格粗扫（1e-4 ~ 1），再在最优附近细调；")
print("配合 warmup/余弦退火能让大 lr 也稳定，但那是 ai 学科的训练技巧，本章不展开。")
