# title: 泄漏量化：先标准化再切分 vs 目标泄漏
# 关键手法：同一份随机标签数据，对比「预处理泄漏」和「标签泄漏」对 CV 分数的不同破坏力。
import numpy as np

rng = np.random.default_rng(17)
n, d, K = 200, 50, 5
X = rng.normal(size=(n, d))
y = rng.integers(0, 2, n).astype(float)      # 纯随机标签：真实上限就是 50%

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def fit(Xtr, ytr, iters=400, lr=0.1, lam=0.01):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Z = (Xtr - mu) / sd
    Zb = np.c_[np.ones(len(Z)), Z]
    w = np.zeros(Zb.shape[1])
    for _ in range(iters):
        p = sigmoid(Zb @ w)
        g = Zb.T @ (p - ytr) / len(ytr)
        g[1:] += lam * w[1:]
        w -= lr * g
    return w, mu, sd

def predict(model, Xte):
    w, mu, sd = model
    Zb = np.c_[np.ones(len(Xte)), (Xte - mu) / sd]
    return (sigmoid(Zb @ w) >= 0.5).astype(float)

def cv(X, y, leak_scale=False):
    order = rng.permutation(n)
    accs = []
    for i in range(K):
        te = order[i::K]
        tr = np.setdiff1d(np.arange(n), te)
        if leak_scale:
            mu, sd = X.mean(0), X.std(0) + 1e-9     # 用了全量数据（含测试折）的统计量
            Xtr = (X[tr] - mu) / sd
            Xte = (X[te] - mu) / sd
            Zb = np.c_[np.ones(len(Xtr)), Xtr]
            w = np.zeros(Zb.shape[1])
            for _ in range(400):
                p = sigmoid(Zb @ w)
                g = Zb.T @ (p - y[tr]) / len(tr); g[1:] += 0.01 * w[1:]
                w -= 0.1 * g
            pred = (sigmoid(np.c_[np.ones(len(Xte)), Xte] @ w) >= 0.5).astype(float)
        else:
            pred = predict(fit(X[tr], y[tr]), X[te])
        accs.append(np.mean(pred == y[te]))
    return np.array(accs)

a_ok = cv(X, y, leak_scale=False)
a_leak = cv(X, y, leak_scale=True)
print("随机标签（真实可达约 0.5）")
print("  正确流程（折内标准化）每折:", np.round(a_ok, 3).tolist(), f" 平均 {a_ok.mean():.3f}")
print("  先标准化再切分        每折:", np.round(a_leak, 3).tolist(), f" 平均 {a_leak.mean():.3f}")
print(f"  预处理泄漏带来的虚高 = {a_leak.mean() - a_ok.mean():+.3f}")

# 目标泄漏：特征里直接混入标签
X_leak = np.c_[X, y * 2.0 + rng.normal(0, 0.3, n)]
a_target = cv(X_leak, y, leak_scale=False)
print("\n加入一个由标签生成的「特征」（目标泄漏）")
print("  正确流程每折:", np.round(a_target, 3).tolist(), f" 平均 {a_target.mean():.3f}")
print(f"  目标泄漏带来的虚高 = {a_target.mean() - a_ok.mean():+.3f}")

print("\n读法：标准化泄漏只用了测试折的均值/方差，没用到标签，虚高通常很小；")
print("目标泄漏把 y 的信息直接塞进特征，CV 会给出接近 100% 的假象。")
print("结论：两类泄漏根因相同——用了预测时拿不到的信息；但破坏力取决于是否携带标签。")
print("工程上不靠自觉：所有 fit（标准化、特征选择、目标编码、过采样）都放进 Pipeline，")
print("让交叉验证在每个训练折内重新 fit，测试折只 transform。")
