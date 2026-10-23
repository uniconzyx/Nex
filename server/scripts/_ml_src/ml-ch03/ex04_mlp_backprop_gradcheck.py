# title: 两层 MLP 手写反向传播 + 数值梯度校验
# 关键手法：先把每层的前向结果缓存下来，反向时直接用；再用中心差分逐个核对梯度。
import numpy as np

rng = np.random.default_rng(2)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def forward(params, X):
    W1, b1, W2, b2 = params
    z1 = X @ W1 + b1
    a1 = np.tanh(z1)
    z2 = a1 @ W2 + b2
    p = sigmoid(z2)
    return p, (X, a1, W2)

def loss_fn(params, X, y):
    p, _ = forward(params, X)
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

def backward(params, X, y):
    W1, b1, W2, b2 = params
    p, (X_, a1, W2_) = forward(params, X)
    m = len(X)
    dz2 = (p - y) / m                 # sigmoid + BCE 的梯度，干净得只剩 p-y
    dW2 = a1.T @ dz2
    db2 = dz2.sum(0)
    da1 = dz2 @ W2_.T
    dz1 = da1 * (1 - a1 ** 2)         # tanh 的导数
    dW1 = X_.T @ dz1
    db1 = dz1.sum(0)
    return [dW1, db1, dW2, db2]

X = np.array([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
y = np.array([[0.], [1.], [1.], [0.]])
params = [rng.normal(0, 1, (2, 4)), np.zeros(4),
          rng.normal(0, 1, (4, 1)), np.zeros(1)]

# ---- 1) 数值梯度校验（训练前，参数还是随机的）----
grads = backward(params, X, y)
names = ["W1", "b1", "W2", "b2"]
eps = 1e-5
print("数值梯度校验（中心差分 vs 解析梯度）：")
worst = 0.0
for k, (P, G) in enumerate(zip(params, grads)):
    flat = P.ravel()
    for idx in range(min(2, flat.size)):
        old = flat[idx]
        flat[idx] = old + eps
        lp = loss_fn(params, X, y)
        flat[idx] = old - eps
        lm = loss_fn(params, X, y)
        flat[idx] = old
        num = (lp - lm) / (2 * eps)
        ana = G.ravel()[idx]
        rel = abs(num - ana) / max(1e-12, abs(num) + abs(ana))
        worst = max(worst, rel)
        print(f"  {names[k]}[{idx}] 解析 {ana:+.6f} 数值 {num:+.6f} 相对误差 {rel:.2e}")
print(f"  最大相对误差 = {worst:.2e}  ->  {'通过（<1e-6）' if worst < 1e-6 else '不通过'}")

# ---- 2) 用这套梯度训练 XOR ----
lr, iters = 0.5, 5000
for t in range(iters + 1):
    if t in (0, 500, 2000, 5000):
        print(f"  iter {t:>4}: loss = {loss_fn(params, X, y):.6f}")
    g = backward(params, X, y)
    params = [P - lr * G for P, G in zip(params, g)]

p, _ = forward(params, X)
print("\n训练后输出：")
for xi, yi, pi in zip(X, y.ravel(), p.ravel()):
    print(f"  x={xi.astype(int)}  y={int(yi)}  p={pi:.4f}  {'OK' if (pi >= .5) == yi else 'ERR'}")
print(f"  准确率 = {np.mean((p.ravel() >= .5) == y.ravel()):.2f}")

print("\n读法：dz2=(p-y)/m 是「输出误差」，乘 W2ᵀ 传回隐藏层，再乘 tanh' 得到 dz1。")
print("结论：反向传播没有新数学，只是链式法则 + 复用前向缓存；")
print("数值校验是手写网络唯一可靠的「防抄错」手段，成本 O(参数量)。")
