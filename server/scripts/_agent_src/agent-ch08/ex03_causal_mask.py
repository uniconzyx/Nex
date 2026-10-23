# title: 因果 mask 验证：未来 token 不能影响当前输出
# 做法不是「看代码像对的」，而是真的改掉最后一个 token，检查前缀输出是否一字不变。
import numpy as np

rng = np.random.default_rng(2)
T, D = 6, 4
X = rng.normal(size=(T, D))
Wq, Wk, Wv = (rng.normal(scale=0.5, size=(D, D)) for _ in range(3))

def attend(X, causal=True, post_softmax=False):
    Q, K, V = X @ Wq, X @ Wk, X @ Wv
    S = Q @ K.T / np.sqrt(D)
    if causal and not post_softmax:
        S = np.where(np.tril(np.ones((T, T))) > 0, S, -1e9)
    A = np.exp(S - S.max(axis=1, keepdims=True))
    A = A / A.sum(axis=1, keepdims=True)
    if causal and post_softmax:
        A = A * np.tril(np.ones((T, T)))       # 错误示范：softmax 后再遮
    return A @ V, A

out, A = attend(X)
print("因果 mask（1=可见）：")
for i in range(T):
    print("  " + " ".join("1" if j <= i else "·" for j in range(T)) +
          f"   row_sum={A[i].sum():.6f}  future_weight={A[i, i+1:].sum():.1e}")

X2 = X.copy()
X2[-1] += rng.normal(scale=1.0, size=D)       # 只改最后一个 token
out_m, _ = attend(X2)
diff = np.abs(out_m - out).max(axis=1)
print("\n改动最后一个 token 后，各位置输出的最大变化：")
print("  " + " ".join(f"t{i}:{d:.2e}" for i, d in enumerate(diff)))
print(f"前缀（t0~t{T-2}）最大变化 = {diff[:-1].max():.2e}；最后一位 = {diff[-1]:.2e}")

out_nc, _ = attend(X, causal=False)
out_nc2, _ = attend(X2, causal=False)
print(f"\n不加 mask 时，前缀最大变化 = {np.abs(out_nc2 - out_nc)[:-1].max():.2e}（信息泄漏）")

out_ps, A_ps = attend(X, causal=True, post_softmax=True)
print("\n错误示范：softmax 后再乘 mask（没有重新归一化）：")
for i in range(T):
    print(f"  t{i}: row_sum={A_ps[i].sum():.3f}  output_norm={np.linalg.norm(out_ps[i]):.3f}")
print(f"  正确做法的 row_sum 全为 1；错误做法每行权重和都不为 1"
      f"（第 0 行 {A_ps[0].sum():.3f}、第 1 行 {A_ps[1].sum():.3f}），输出幅度随位置乱掉")

print("\n结论：因果性是一个可测试的性质 —— 扰动未来位置，前缀输出必须逐位相等。")
print("读法：mask 要在 softmax **之前**加（-1e9/-inf），否则要么泄漏，要么每行权重和不为 1；")
print("      自回归训练时标签右移一位，mask 保证第 t 个位置只看 ≤t 的输入。")
