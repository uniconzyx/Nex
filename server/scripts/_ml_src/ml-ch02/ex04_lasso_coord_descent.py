# title: Lasso 坐标下降手写：软阈值与精确零系数
# 目标 ½‖y-Xw‖² + λ‖w‖₁；逐坐标解 wⱼ=S(Xⱼᵀr, λ)/‖Xⱼ‖²，其中 S(z,λ)=sign(z)max(|z|-λ,0)。
import numpy as np

rng = np.random.default_rng(11)
n, d = 100, 6
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)
w_true = np.array([3.0, -2.0, 0.0, 0.0, 0.0, 0.0])
y = X @ w_true + rng.normal(0, 0.15, n)
y = y - y.mean()


def soft(z, t):
    return np.sign(z) * np.maximum(np.abs(z) - t, 0.0)


def lasso_cd(X, y, lam, iters=2000, tol=1e-10):
    n, d = X.shape
    w = np.zeros(d)
    r = y.copy()
    for it in range(1, iters + 1):
        w_old = w.copy()
        for j in range(d):
            r += X[:, j] * w[j]                 # 先把第 j 维的旧贡献加回残差
            c = X[:, j] @ X[:, j]
            w[j] = soft(X[:, j] @ r, lam) / c   # 软阈值，阈值 = λ/‖Xⱼ‖²
            r -= X[:, j] * w[j]
        if np.max(np.abs(w - w_old)) < tol:
            break
    return w, it


print(f"n={n}, d={d}，真实非零系数 = [3.0, -2.0, 0, 0, 0, 0]；特征已标准化、y 已中心化")
print(f"{'λ':>6}{'非零个数':>10}{'迭代':>6}   系数向量")
for lam in (0.0, 1.0, 3.0, 6.0, 10.0):
    if lam == 0.0:
        w, *_ = np.linalg.lstsq(X, y, rcond=None)
        it = 0
    else:
        w, it = lasso_cd(X, y, lam)
    nnz = int((np.abs(w) > 1e-8).sum())
    vec = " ".join(f"{v:6.2f}" for v in w)
    print(f"{lam:>6.1f}{nnz:>10}{it:>6}   [{vec}]")

print("\n结论：")
print("1. λ=0 时退化为最小二乘，6 个系数全非零（噪声维也会分到小权重）；")
print("2. λ 增大后 S(z,λ) 把小于 λ 的分量直接截成 0，非零个数单调下降——这是精确稀疏，不是『很小』；")
print("3. 阈值必须除以 ‖Xⱼ‖²：目标里的二次项系数由该列尺度决定，不标准化就会偏向大方差特征；")
print("4. 坐标下降每步只解一维分段二次问题，代价 O(nd)，在 d≫n 的稀疏问题上比牛顿法更实用。")
