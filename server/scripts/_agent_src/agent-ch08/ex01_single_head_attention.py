# title: 手写单头缩放点积注意力：形状、权重归一与缩放的作用
# 只用 numpy 复现 Attention(Q,K,V) = softmax(QKᵀ/√d_k)V，并验证每一行权重和为 1。
import numpy as np

rng = np.random.default_rng(0)
T, D, DK = 4, 6, 4

X = rng.normal(size=(T, D))
Wq = rng.normal(scale=0.5, size=(D, DK))
Wk = rng.normal(scale=0.5, size=(D, DK))
Wv = rng.normal(scale=0.5, size=(D, DK))

Q, K, V = X @ Wq, X @ Wk, X @ Wv
scores = Q @ K.T
attn = np.exp(scores - scores.max(axis=1, keepdims=True))
attn = attn / attn.sum(axis=1, keepdims=True)
out = attn @ V

print(f"X {X.shape} → Q {Q.shape}, K {K.shape}, V {V.shape}")
print("\n原始打分 QKᵀ（未缩放）：")
for row in scores:
    print("  " + " ".join(f"{v:>7.2f}" for v in row))
print("\n注意力权重（每行应和为 1）：")
for row, s in zip(attn, attn.sum(axis=1)):
    print("  " + " ".join(f"{v:>7.3f}" for v in row) + f"   sum={s:.6f}")
print(f"\n输出 {out.shape}；第 0 行 = Σ_j A[0,j]·V[j]")
manual = sum(attn[0, j] * V[j] for j in range(T))
print(f"  逐项手算与矩阵乘最大差：{np.abs(manual - out[0]).max():.2e}")

# 缩放的作用：d_k 越大，点积方差越大（≈d_k），softmax 越容易饱和
print("\n缩放前后 softmax 的尖锐程度（20 个 key，重复 500 次取均值）：")
print(f"{'d_k':>5}{'点积标准差':>12}{'最大权重(未缩放)':>18}{'最大权重(缩放)':>15}"
      f"{'熵(未缩放)':>12}{'熵(缩放)':>10}")

def stats(scores):
    z = scores - scores.max(axis=1, keepdims=True)
    p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
    return p.max(axis=1).mean(), -(p * np.log(p + 1e-12)).sum(axis=1).mean()

for dk in (4, 16, 64, 256, 1024):
    raw = rng.normal(0, np.sqrt(dk), size=(500, 20))     # 点积的 std ≈ √d_k
    scaled = raw / np.sqrt(dk)
    mw_raw, h_raw = stats(raw)
    mw_sc, h_sc = stats(scaled)
    print(f"{dk:>5}{raw.std():>12.1f}{mw_raw:>18.3f}{mw_sc:>15.3f}{h_raw:>12.3f}{h_sc:>10.3f}")

print("\n结论：除以 √d_k 把点积方差拉回 O(1)；不缩放时 d_k=1024 的最大权重接近 1，")
print("      softmax 饱和成 one-hot，梯度几乎消失，训练推不动。")
print(f"读法：形状三件套 —— Q/K/V 同 d_k、权重每行和为 1、输出形状 {out.shape} 与 V 一致。")
