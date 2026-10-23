# title: 训练/测试划分的方差：小测试集为什么不可信
# 关键手法：同一批模型、同一个测试池，只改测试集大小，重复抽样看误差估计的波动。
import numpy as np

rng = np.random.default_rng(11)
N, d = 3000, 3
X = rng.normal(size=(N, d))
w_true = np.array([1.2, -0.8, 0.5])
z = X @ w_true + rng.normal(0, 0.5, N)
y = (rng.random(N) < 1 / (1 + np.exp(-z))).astype(float)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def train_logistic(Xtr, ytr, iters=500, lr=0.2):
    Xb = np.c_[np.ones(len(Xtr)), Xtr]
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = sigmoid(Xb @ w)
        w -= lr * Xb.T @ (p - ytr) / len(ytr)
    return w

def predict(w, X):
    return sigmoid(np.c_[np.ones(len(X)), X] @ w) >= 0.5

REPS = 60
sizes = (10, 30, 100, 300)
errs = {k: [] for k in sizes}
pool_idx = np.arange(N)

for _ in range(REPS):
    perm = rng.permutation(pool_idx)
    tr, rest = perm[:300], perm[300:]
    w = train_logistic(X[tr], y[tr])
    order = rng.permutation(rest)
    for k in sizes:
        te = order[:k]
        errs[k].append(np.mean(predict(w, X[te]) != y[te]))

print(f"{'测试集大小':>10}{'平均误差':>10}{'标准差':>10}{'二项标准误':>12}{'95%CI 半宽':>12}")
for k in sizes:
    e = np.array(errs[k])
    p = e.mean()
    se = np.sqrt(p * (1 - p) / k)
    print(f"{k:>10}{p:>10.3f}{e.std(ddof=1):>10.3f}{se:>12.3f}{1.96 * e.std(ddof=1):>12.3f}")

print("\n读法：测试集 10 条时，同一模型换一批样本误差可差十几个百分点；")
print("测试集 300 条时波动明显收窄，标准差大致按 1/√k 下降。")
print("结论：单次小测试集的结果不能直接比较模型（差异可能全来自抽样）；")
print("要么扩大测试集，要么重复划分报告均值±置信区间，要么用交叉验证。")
