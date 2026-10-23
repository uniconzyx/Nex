# title: 逻辑回归手写梯度下降：交叉熵、步长与准确率
# 伯努利标签 + 交叉熵梯度 Xᵀ(p-y)/n；对比不同步长下的收敛步数、损失与准确率。
import numpy as np

rng = np.random.default_rng(5)
n, d = 500, 3
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)
Xb = np.column_stack([np.ones(n), X])            # 截距列
w_true = np.array([0.2, 1.2, -0.8, 0.6])
p_true = 1.0 / (1.0 + np.exp(-Xb @ w_true))
y = (rng.random(n) < p_true).astype(float)       # 伯努利标签，存在贝叶斯误差


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def loss(w):
    p = sigmoid(Xb @ w)
    return -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))


L = 0.25 * np.linalg.eigvalsh(Xb.T @ Xb).max() / n
print(f"n={n}, d={d} 个特征 + 截距，正例比例={y.mean():.3f}")
print(f"光滑常数 L≈0.25·λmax(XᵀX)/n={L:.3f}，步长上限 1/L={1/L:.3f}")
print(f"{'η':>7}{'步数':>8}{'最终损失':>10}{'准确率':>8}{'‖∇ℓ‖':>10}")

for eta in (0.05 / L, 0.5 / L, 1.0 / L):
    w = np.zeros(d + 1)
    for it in range(1, 20001):
        p = sigmoid(Xb @ w)
        g = Xb.T @ (p - y) / n
        if np.linalg.norm(g) < 1e-7:
            break
        w = w - eta * g
    p = sigmoid(Xb @ w)
    acc = ((p >= 0.5).astype(float) == y).mean()
    print(f"{eta:>7.3f}{it:>8}{loss(w):>10.4f}{acc:>8.3f}{np.linalg.norm(g):>10.2e}")

print("\n结论：")
print("1. 交叉熵梯度是 Xᵀ(p−y)/n，不含 p(1−p) 因子，所以在 p→0/1 的饱和区仍有过得去的信号；")
print("2. 步长越小越慢，接近 1/L 最快；理论上二次目标超过 2/L 会发散，逻辑回归的实际曲率更小，")
print("   但步长过大仍会震荡或越过最优点，不要拿 2/L 当安全边界；")
print("3. 这里的准确率上不去 100% 是正常的：标签由概率生成，存在不可约的贝叶斯误差；")
print("4. 真实工程还要加 L2：完全可分时交叉熵没有有限最优解，‖w‖ 会一直涨（见 ex07）。")
