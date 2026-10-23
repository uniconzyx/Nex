# title: softmax 与数值稳定：为什么要先减最大值
# 关键手法：直接 exp(1000) 会溢出成 inf；减去 max(logits) 不改变结果，只把指数搬进安全区。
import numpy as np

np.seterr(over="ignore", invalid="ignore")

def softmax_naive(z):
    e = np.exp(z)
    return e / e.sum()

def softmax_stable(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()

z = np.array([1000.0, 1001.0, 1002.0])
print("logits =", z)
print("naive  exp =", np.exp(z), " -> softmax =", softmax_naive(z))
print("stable 减 max 后 =", z - z.max(), " -> softmax =", np.round(softmax_stable(z), 6))

print("\n平移不变性（softmax(z) == softmax(z - c)）：")
for c in (0.0, 1000.0, 1e6):
    print(f"  c={c:>8.0f}: {np.round(softmax_stable(z - c), 6)}")

# 交叉熵：对独热标签，CE = logsumexp(z) - z_true
def ce_stable(z, k):
    m = z.max()
    return (m + np.log(np.exp(z - m).sum())) - z[k]

k = 2
p = softmax_stable(z)
print(f"\n真实类别 k={k}：p_k = {p[k]:.6f}")
print(f"交叉熵 -log p_k = {ce_stable(z, k):.6f}")
print("与手算 logsumexp - z_true 一致：", f"{np.log(np.exp(z - z.max()).sum()) + z.max() - z[k]:.6f}")

# 反向梯度：softmax + CE 对 logits 的梯度就是 p - onehot
onehot = np.zeros(3)
onehot[k] = 1.0
print("\n梯度 p - onehot =", np.round(p - onehot, 6))
print("梯度之和 =", f"{(p - onehot).sum():.2e}", "（恒为 0，因为概率和为 1）")

print("\n小 logits 时两者也一致：")
z2 = np.array([0.5, -1.0, 2.0])
print("  naive :", np.round(softmax_naive(z2), 6))
print("  stable:", np.round(softmax_stable(z2), 6))
print("  差    :", f"{np.abs(softmax_naive(z2) - softmax_stable(z2)).max():.2e}")

print("\n读法：数值稳定不是「精度更高」，而是避免 inf/inf = nan 直接毁掉整批梯度。")
print("结论：任何 softmax / logsumexp / sigmoid 实现，先减最大值（或 clip）是硬性要求；")
print("多分类的交叉熵梯度与二分类同形：p - y。")
