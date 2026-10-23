# title: 用 Hessian 特征值验凸性：二次型 / 鞍点 / 逻辑回归
# 判据：∇²f ⪰ 0 ⇔ 最小特征值 ≥ 0。数值上要留容差，且 h 不能过大或过小。
import numpy as np

def hessian(f, x, h=1e-5):
    n = x.size
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            ei = np.eye(n)[i] * h
            ej = np.eye(n)[j] * h
            H[i, j] = (f(x + ei + ej) - f(x + ei - ej)
                       - f(x - ei + ej) + f(x - ei - ej)) / (4 * h * h)
    return H

A = np.array([[2.0, 0.5], [0.5, 1.0]])
b = np.array([1.0, -1.0])
quad = lambda w: 0.5 * w @ A @ w - b @ w
saddle = lambda w: w[0] ** 2 - w[1] ** 2

# 逻辑回归负对数似然（带 L2，避免退化）
rng = np.random.default_rng(5)
X = rng.normal(size=(40, 2))
y = (X[:, 0] - X[:, 1] + rng.normal(0, 0.3, 40) > 0).astype(float)
lam = 1e-2
def nll(w):
    z = X @ w
    # log(1+exp(z)) − y z，用 logaddexp 保证数值稳定
    return np.sum(np.logaddexp(0, z) - y * z) + 0.5 * lam * w @ w

cases = [("二次型(A 正定)", quad, np.array([0.3, -0.2])),
         ("鞍点 f=w1²−w2²", saddle, np.array([0.3, -0.2])),
         ("逻辑回归 NLL", nll, np.array([0.1, -0.1]))]

print(f"{'目标函数':<16} {'Hessian 特征值':<30} {'判定'}")
for name, f, w0 in cases:
    ev = np.linalg.eigvalsh(hessian(f, w0))
    convex = ev.min() >= -1e-6
    print(f"{name:<16} {np.array2string(ev, precision=4):<30} "
          f"{'凸' if convex else '非凸（负曲率方向存在）'}")

print("\n说明：")
print("1. 二次型的 Hessian 恒为 A，与点无关；鞍点有一个负特征值，说明沿 w2 方向是极大值；")
print("2. 逻辑回归 Hessian = Xᵀ diag(p(1−p)) X + λI，p∈(0,1) 保证半正定，λ>0 使其正定 → 强凸；")
print("3. 没有 λ 时，若数据可分，p→0/1 使 Hessian 退化，此时不收敛（本章陷阱 3）。")
