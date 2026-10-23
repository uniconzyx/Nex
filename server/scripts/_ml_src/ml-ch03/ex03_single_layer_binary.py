# title: 单层网络做二分类：线性边界的能与不能
# 关键手法：同一个神经元（logistic）先解线性可分问题，再解 XOR，用准确率暴露假设空间。
import numpy as np

rng = np.random.default_rng(1)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

def train(X, y, iters=800, lr=0.5):
    Xb = np.c_[np.ones(len(X)), X]          # 加一列偏置，等价于 b
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = sigmoid(Xb @ w)
        w -= lr * Xb.T @ (p - y) / len(y)    # 交叉熵梯度 = Xᵀ(p-y)/m
    return w, sigmoid(Xb @ w)

# 场景 A：两个高斯团，线性可分
n = 300
X0 = rng.normal([-1.2, -1.2], 0.55, (n // 2, 2))
X1 = rng.normal([1.2, 1.2], 0.55, (n // 2, 2))
X = np.vstack([X0, X1])
y = np.r_[np.zeros(n // 2), np.ones(n // 2)]
w, p = train(X, y)
acc = np.mean((p >= 0.5) == y)
print("[A] 两个高斯团（线性可分）")
print(f"  学到的决策边界: {w[1]:+.3f}*x1 {w[2]:+.3f}*x2 {w[0]:+.3f} = 0")
print(f"  训练准确率: {acc:.3f}  (单层足够，边界是一条直线)")

# 场景 B：XOR，线性不可分
Xx = np.array([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
yx = np.array([0., 1., 1., 0.])
wx, px = train(Xx, yx, iters=4000, lr=0.5)
accx = np.mean((px >= 0.5) == yx)
print("\n[B] XOR（线性不可分）")
print("  四个样本的预测概率:", np.round(px, 3))
print(f"  训练准确率: {accx:.3f}")
print("  最优线性边界也只能到 0.5：任何直线都无法把对角的两类分开。")

print("\n读法：单层网络 = 一个线性分类器，加 sigmoid 只改变输出标定，不改变边界形状。")
print("结论：需要「同或/异或、组合特征、交互项」时，必须在中间加一层非线性")
print("（隐藏层 + ReLU/tanh），这就是 MLP 存在的最直接理由。")
