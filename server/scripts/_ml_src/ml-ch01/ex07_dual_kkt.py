# title: 对偶与 KKT：三个点的硬间隔 SVM，谁才是支持向量
# 枚举「哪两个点是支持向量」，解对偶方程组，再用 KKT 的互补松弛验证第三个点。
import numpy as np

X = np.array([-1.0, 3.0, -2.0])     # 一维特征
y = np.array([-1.0, 1.0, -1.0])
n = len(y)

def solve_pair(i, j):
    """未知量 [α_i, α_j, b]。

    对偶约束 α_i y_i + α_j y_j = 0；
    两个支持向量的间隔条件 y_k(w·x_k + b) = 1，其中 w = Σ α_k y_k x_k。
    """
    kii, kij = X[i] * X[i], X[i] * X[j]
    kjj = X[j] * X[j]
    M = np.array([
        [y[i], y[j], 0.0],
        [kii, y[i] * y[j] * kij, y[i]],
        [y[i] * y[j] * kij, kjj, y[j]],
    ])
    rhs = np.array([0.0, 1.0, 1.0])
    return np.linalg.solve(M, rhs)

print(f"{'支持向量对':<12} {'α':<26} {'w':>8} {'b':>8} {'最小间隔':>9}  可行")
valid = []
for i in range(n):
    for j in range(i + 1, n):
        a_i, a_j, b = solve_pair(i, j)
        a = np.zeros(n)
        a[i], a[j] = a_i, a_j
        w = float(np.sum(a * y * X))
        margins = y * (w * X + b)
        ok = bool((a >= -1e-9).all() and margins.min() >= 1 - 1e-9)
        print(f"({i},{j})".ljust(12) + f"{np.array2string(a, precision=4):<26}"
              f"{w:>8.4f} {b:>8.4f} {margins.min():>9.4f}  {'✓' if ok else '✗'}")
        if ok:
            valid.append((a, w, b, margins))

a, w, b, margins = valid[0]
print(f"\n最优解：α = {np.round(a, 4)}，w = {w:.4f}，b = {b:.4f}")
print(f"间隔 = 1/|w| = {1 / abs(w):.4f}")
print("\nKKT 互补松弛 α_i·(1 − y_i(w·x_i+b)) = 0 的核对：")
for k in range(n):
    slack = 1 - margins[k]
    role = "支持向量" if a[k] > 1e-9 else "非支持向量(α=0)"
    print(f"  点{k}: α={a[k]:.4f}, 间隔余量={margins[k]:.4f}, "
          f"α·(1−margin)={a[k]*slack:+.2e}  {role}")
print("\n结论：非支持向量的 α 精确为 0 —— 稀疏性不是巧合，是互补松弛的必然结果。")
