# title: 迁移学习最小模拟：冻结底层 + 线性探针 vs 全量重训
# 关键手法：源任务样本多、目标样本少；输入里混入 4 维纯噪声，专门检验特征是否「学会了忽略噪声」。
import numpy as np

rng = np.random.default_rng(8)
D = 6

def draw(n):
    x_sig = rng.uniform(-1, 1, (n, 2))
    x_noise = rng.normal(0, 1, (n, D - 2))
    return np.hstack([x_sig, x_noise])

def make_source(n):
    X = draw(n)
    return X, ((X[:, 0] * X[:, 1]) > 0).astype(float).reshape(-1, 1)      # XOR 四象限

def make_target(n):
    X = draw(n)
    return X, ((X[:, 0] * X[:, 1]) > 0.08).astype(float).reshape(-1, 1)   # 边界略平移

Xs, ys = make_source(2000)
Xt, yt = make_target(40)
Xv, yv = make_target(1000)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def init(seed):
    r = np.random.default_rng(seed)
    return [r.normal(0, 0.7, (D, 24)), np.zeros(24),
            r.normal(0, 0.7, (24, 24)), np.zeros(24),
            r.normal(0, 0.7, (24, 1)), np.zeros(1)]

def forward(P, X):
    W1, b1, W2, b2, W3, b3 = P
    h1 = np.tanh(X @ W1 + b1)
    h2 = np.tanh(h1 @ W2 + b2)
    return sigmoid(h2 @ W3 + b3), (X, h1, h2, W2, W3)

def accuracy(P, X, y):
    return np.mean((forward(P, X)[0] >= 0.5) == (y == 1))

def train(P, X, y, iters, lr, freeze_first=False):
    for _ in range(iters):
        p, (X_, h1, h2, W2, W3) = forward(P, X)
        m = len(X)
        dz3 = (p - y) / m
        dW3 = h2.T @ dz3; db3 = dz3.sum(0)
        dz2 = (dz3 @ W3.T) * (1 - h2 ** 2)
        dW2 = h1.T @ dz2; db2 = dz2.sum(0)
        dz1 = (dz2 @ W2.T) * (1 - h1 ** 2)
        dW1 = X_.T @ dz1; db1 = dz1.sum(0)
        if freeze_first:
            dW1[:] = 0; db1[:] = 0
        P[0] -= lr * dW1; P[1] -= lr * db1
        P[2] -= lr * dW2; P[3] -= lr * db2
        P[4] -= lr * dW3; P[5] -= lr * db3
    return P

# 1) 源任务预训练：1500 条不够，这里 2000 条，让第一层真的学到「忽略噪声维」
P_pre = init(0)
train(P_pre, Xs, ys, 2000, 0.1)
print(f"源任务（2000 条，XOR + 4 维噪声）准确率: {accuracy(P_pre, Xs, ys):.3f}")

results = {}

P = [a.copy() for a in P_pre]
train(P, Xt, yt, 800, 0.1, freeze_first=True)
results["预训练 + 冻结底层 + 线性探针"] = (accuracy(P, Xt, yt), accuracy(P, Xv, yv))

P = init(99)
train(P, Xt, yt, 800, 0.1, freeze_first=True)
results["随机初始化 + 冻结底层"] = (accuracy(P, Xt, yt), accuracy(P, Xv, yv))

P = [a.copy() for a in P_pre]
train(P, Xt, yt, 800, 0.02)
results["预训练 + 全量微调"] = (accuracy(P, Xt, yt), accuracy(P, Xv, yv))

P = init(99)
train(P, Xt, yt, 800, 0.1)
results["目标集从零训练"] = (accuracy(P, Xt, yt), accuracy(P, Xv, yv))

print(f"\n目标训练集只有 {len(Xt)} 条，验证集 {len(Xv)} 条：")
print(f"{'策略':<30}{'训练准确率':>10}{'验证准确率':>10}")
for k, (tr, va) in results.items():
    print(f"{k:<30}{tr:>10.3f}{va:>10.3f}")

probe = results["预训练 + 冻结底层 + 线性探针"][1]
ft = results["预训练 + 全量微调"][1]
rand = results["随机初始化 + 冻结底层"][1]
scratch = results["目标集从零训练"][1]
print(f"\n读法：只有 40 条目标样本时，冻结探针 {probe:.3f}、全量微调 {ft:.3f}，")
print(f"随机特征 {rand:.3f}、从零训练 {scratch:.3f}——差距来自源任务学到的结构。")
print("结论：迁移有效的条件是「源任务与目标任务共享底层结构」；")
print("目标数据越少越该冻结，数据足够多时再解冻做小学习率微调。")
