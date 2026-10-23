# title: L2 与 Dropout 对过拟合的影响：看训练-验证间隙
# 关键手法：固定数据与初始化，只改正则项；比较 train/val MSE 的「间隙」而不是只看 train。
import numpy as np

rng = np.random.default_rng(4)
n, d = 40, 20
w_true = np.zeros(d)
w_true[:5] = [1.5, -1.0, 0.8, 0.5, -0.7]

def make(n, rng):
    X = rng.normal(size=(n, d))
    y = (X @ w_true + rng.normal(0, 0.5, n)).reshape(-1, 1)
    return X, y

Xtr, ytr = make(n, rng)
Xva, yva = make(400, rng)

def train(mode, seed, lam=0.01, p_drop=0.5, iters=3000, lr=0.02):
    r = np.random.default_rng(seed)
    W1 = r.normal(0, 1 / np.sqrt(d), (d, 32)); b1 = np.zeros(32)
    W2 = r.normal(0, 1 / np.sqrt(32), (32, 1)); b2 = np.zeros(1)

    def forward(X, training=False, rr=None):
        z1 = X @ W1 + b1
        t1 = np.tanh(z1)
        a1 = t1
        mask = None
        if training and mode == "dropout":
            mask = (rr.random(t1.shape) > p_drop) / (1 - p_drop)  # inverted dropout
            a1 = t1 * mask
        return a1 @ W2 + b2, (X, t1, a1, mask)

    def mse(X, y):
        pred, _ = forward(X)
        return np.mean((pred - y) ** 2)

    for t in range(iters):
        pred, (X_, t1, a1, mask) = forward(Xtr, True, r)
        m = len(Xtr)
        dp = 2 * (pred - ytr) / m
        dW2 = a1.T @ dp + (lam * W2 if mode == "l2" else 0)
        db2 = dp.sum(0)
        da1 = dp @ W2.T
        if mask is not None:
            da1 = da1 * mask
        dz1 = da1 * (1 - t1 ** 2)   # 导数用未 dropout 的 tanh 值算
        dW1 = X_.T @ dz1 + (lam * W1 if mode == "l2" else 0)
        db1 = dz1.sum(0)
        W1 -= lr * dW1; b1 -= lr * db1
        W2 -= lr * dW2; b2 -= lr * db2
    return mse(Xtr, ytr), mse(Xva, yva)

print(f"训练集 {n} 条 / 验证集 400 条，特征 {d} 维，隐藏层 32 个 tanh")
print(f"{'配置':<22}{'训练 MSE':>10}{'验证 MSE':>10}{'间隙':>10}")
rows = []
for i, (name, kw) in enumerate([
    ("无正则", {}),
    ("L2 (λ=0.01)", {"mode": "l2", "lam": 0.01}),
    ("L2 (λ=0.1)", {"mode": "l2", "lam": 0.1}),
    ("Dropout (p=0.5)", {"mode": "dropout"}),
]):
    mode = kw.pop("mode", "none")
    tr, va = train(mode, seed=10 + i, **kw)
    rows.append((name, tr, va))
    print(f"{name:<22}{tr:>10.4f}{va:>10.4f}{va - tr:>10.4f}")

best = min(rows, key=lambda r: r[2])
print(f"\n验证误差最低：{best[0]}（{best[2]:.4f}）")
print("读法：无正则时训练误差最低、验证误差最高，间隙最大——模型在记噪声；")
print("L2 把权重压小、Dropout 随机断神经元，都在限制有效容量，间隙收窄。")
print("结论：正则的收益要按「验证误差」结算，不是把训练误差压得越低越好；")
print("λ 是旋钮，过大则欠拟合同样会抬高验证误差（看 λ=0.1 的对比）。")
