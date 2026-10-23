# title: softmax 多分类：log-sum-exp 稳定化与梯度校验
# 朴素 exp 在大 logit 下溢出；减最大值后概率不变。并验证交叉熵梯度 = Xᵀ(P−Y)/n。
import numpy as np

rng = np.random.default_rng(13)


def logsumexp(Z):
    a = Z.max(axis=1, keepdims=True)
    return (a + np.log(np.exp(Z - a).sum(axis=1, keepdims=True))).ravel()


def softmax(Z):
    Z = Z - Z.max(axis=1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(axis=1, keepdims=True)


# --- 1. 数值稳定：极端 logit ---
z = np.array([1000.0, 1001.0, 1002.0])
with np.errstate(over="ignore", invalid="ignore"):
    e = np.exp(z)
    p_naive = e / e.sum()
print(f"极端 logit z = {z.astype(int).tolist()}")
print(f"朴素 exp：{e} → 概率 {p_naive}（inf/inf = nan）")
p_stable = softmax(z[None, :])[0]
print(f"减最大值：概率 {np.round(p_stable, 4)}，和={p_stable.sum():.6f}（与理论 softmax 一致）")
print(f"log-sum-exp = {logsumexp(z[None, :])[0]:.4f}（有限，可直接用于交叉熵）")

# --- 2. 梯度校验 ---
n, d, K = 200, 4, 3
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)
W_true = rng.normal(size=(d, K))
P_true = softmax(X @ W_true)
y = np.array([rng.choice(K, p=P_true[i]) for i in range(n)])


def ce(W):
    Z = X @ W
    return np.mean(logsumexp(Z) - Z[np.arange(n), y])


def grad(W):
    P = softmax(X @ W)
    Y = np.eye(K)[y]
    return X.T @ (P - Y) / n


W = rng.normal(scale=0.1, size=(d, K))
G = grad(W)
eps = 1e-6
G_num = np.zeros_like(W)
for i in range(d):
    for k in range(K):
        E = np.zeros_like(W)
        E[i, k] = eps
        G_num[i, k] = (ce(W + E) - ce(W - E)) / (2 * eps)
rel = np.abs(G - G_num).max() / max(np.abs(G_num).max(), 1e-12)
print(f"\n梯度校验：解析梯度与中心差分最大相对误差 = {rel:.2e}（应 <1e-6）")
print(f"初始交叉熵 = {ce(W):.4f}")

# --- 3. 训练几步看损失下降 ---
eta = 1.0
for _ in range(200):
    W = W - eta * grad(W)
P = softmax(X @ W)
acc = (P.argmax(1) == y).mean()
print(f"训练 200 步（η={eta}）：交叉熵 {ce(W):.4f}，训练准确率 {acc:.3f}")

print("\n结论：")
print("1. softmax 对整体平移不变：减去 max(z) 不改变概率，却把 exp 的自变量压到 ≤0，永不溢出；")
print("2. 交叉熵应直接用 log-sum-exp 实现，避免『先 softmax 再 log』在 p 很小时丢精度；")
print("3. 多分类交叉熵对 logits 的梯度是 p−onehot，对权重是 Xᵀ(P−Y)/n——与二分类同构；")
print("4. 多类时参数不唯一（各类 logits 同加常数概率不变），通常靠 L2 正则或固定一类为基准消除。")
