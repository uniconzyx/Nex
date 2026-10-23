# title: 步长上限 1/L：超过它，下降引理失效并开始发散
# L 是 Hessian 的最大特征值。这个实验把「学习率不能乱设」变成可验证的事实。
import numpy as np

A = np.diag([10.0, 1.0])          # L = 10
b = np.array([1.0, 1.0])
L = np.linalg.eigvalsh(A).max()
w_star = np.linalg.solve(A, b)
f = lambda w: 0.5 * w @ A @ w - b @ w
f_star = f(w_star)

print(f"L = {L:.1f}  →  理论步长上限 1/L = {1/L:.4f}，2/L = {2/L:.4f}")
print(f"{'η':>8} {'η·L':>6} {'f_50 − f*':>12} {'单调下降':>8}")
for ratio in (0.25, 0.5, 1.0, 1.5, 1.9, 2.1):
    eta = ratio / L
    w, hist = np.zeros(2), []
    for _ in range(50):
        w = w - eta * (A @ w - b)
        hist.append(f(w) - f_star)
    mono = all(hist[i + 1] <= hist[i] + 1e-15 for i in range(len(hist) - 1))
    print(f"{eta:>8.4f} {eta*L:>6.2f} {hist[-1]:>12.3e} {str(mono):>8}")

print("\n机理：沿特征向量方向误差按 |1 − ηλ_i| 收缩。")
print("η < 1/L 时所有方向都收缩；1/L < η < 2/L 时最大特征值方向开始震荡但仍有界；")
print("η > 2/L 时 |1 − ηλ_max| > 1，误差被指数放大 → 发散。")
