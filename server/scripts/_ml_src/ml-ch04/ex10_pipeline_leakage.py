# title: Pipeline 防泄漏：特征选择必须在折内做
# 关键手法：纯随机标签 + 高维噪声特征；一旦在切分前选特征，CV 就能「选中」偶然相关的列。
import numpy as np

rng = np.random.default_rng(20)
n, d, K, TOP = 100, 800, 5, 30
X = rng.normal(size=(n, d))
y = rng.integers(0, 2, n).astype(float)     # 无任何真实信号，真实准确率上限 50%

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def logistic(Xtr, ytr, iters=300, lr=0.2, lam=1e-3):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Z = np.c_[np.ones(len(Xtr)), (Xtr - mu) / sd]
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = sigmoid(Z @ w)
        g = Z.T @ (p - ytr) / len(ytr); g[1:] += lam * w[1:]
        w -= lr * g
    return w, mu, sd

def predict(model, Xte):
    w, mu, sd = model
    return (sigmoid(np.c_[np.ones(len(Xte)), (Xte - mu) / sd] @ w) >= 0.5).astype(float)

def top_features(Xtr, ytr, k=TOP):
    Xc = Xtr - Xtr.mean(0)
    yc = ytr - ytr.mean()
    corr = np.abs(Xc.T @ yc) / (np.linalg.norm(Xc, axis=0) * np.linalg.norm(yc) + 1e-12)
    return np.argsort(-corr)[:k]

# 泄漏做法：在全量数据上先选一次特征
leak_cols = top_features(X, y)
print(f"全量数据上选出的前 {TOP} 个特征（纯随机标签，本不该有稳定信号）")

order = rng.permutation(n)
acc_leak, acc_ok = [], []
for i in range(K):
    te = order[i::K]
    tr = np.setdiff1d(np.arange(n), te)
    # 泄漏：直接用在全量数据（含测试折）上选出的列
    acc_leak.append(np.mean(predict(logistic(X[tr][:, leak_cols], y[tr]), X[te][:, leak_cols]) == y[te]))
    # 正确：只用训练折选特征
    cols = top_features(X[tr], y[tr])
    acc_ok.append(np.mean(predict(logistic(X[tr][:, cols], y[tr]), X[te][:, cols]) == y[te]))

print("\n" + f"{'折':>4}{'泄漏版准确率':>12}{'Pipeline':>12}")
for i, (a, b) in enumerate(zip(acc_leak, acc_ok), 1):
    print(f"{i:>4}{a:>12.3f}{b:>12.3f}")
print(f"{'平均':>4}{np.mean(acc_leak):>12.3f}{np.mean(acc_ok):>12.3f}")
print(f"\n虚高 = {np.mean(acc_leak) - np.mean(acc_ok):+.3f}（真实上限 0.500）")

print("读法：泄漏版用测试折的标签参与「哪些特征与 y 相关」的筛选，")
print("在 800 维噪声里总能挑到一批偶然与测试标签同向的列，CV 于是显著高于 50%。")
print("Pipeline 把选择器放进每个训练折内 fit，测试折完全不参与，分数回到随机水平。")
print("结论：标准化、特征选择、目标编码、过采样、超参搜索都属于「会看数据」的步骤，")
print("必须整体放进 Pipeline，再让交叉验证在外层调用；这不是代码风格，是评估有效性的前提。")
