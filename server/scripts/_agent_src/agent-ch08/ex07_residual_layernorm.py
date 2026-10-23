# title: 残差与 LayerNorm 对梯度尺度的影响（24 层数值实验）
# 三种堆叠方式：纯线性、残差、Pre-LN 残差。每层用正交矩阵 ×0.7，观察前向范数与回传梯度。
import numpy as np

rng = np.random.default_rng(5)
B, d, L = 8, 32, 24

def orth(gain=0.7):
    Q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return Q * gain

W = [orth() for _ in range(L)]
h0 = rng.normal(size=(B, d))

def ln_fwd(x, eps=1e-5):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    inv = 1.0 / np.sqrt(var + eps)
    xhat = (x - mu) * inv
    return xhat, (xhat, inv)

def ln_bwd(dy, cache):
    xhat, inv = cache
    N = xhat.shape[-1]
    return inv / N * (N * dy - dy.sum(-1, keepdims=True)
                      - xhat * (dy * xhat).sum(-1, keepdims=True))

def run(mode):
    h, cache = h0, []
    for Wl in W:
        if mode == "plain":
            h = h @ Wl
            cache.append(None)
        elif mode == "residual":
            h = h + h @ Wl
            cache.append(None)
        else:                                   # pre-LN
            z, c = ln_fwd(h)
            h = h + z @ Wl
            cache.append(c)
    loss = 0.5 * np.sum(h ** 2)
    dh = h.copy()                               # d(0.5‖h‖²)/dh
    norm0 = np.linalg.norm(dh)
    for l in range(L - 1, -1, -1):
        if mode == "plain":
            dh = dh @ W[l].T
        elif mode == "residual":
            dh = dh @ (np.eye(d) + W[l]).T
        else:
            dh = dh + ln_bwd(dh @ W[l].T, cache[l])
        if l == 0:
            norm0 = np.linalg.norm(dh)
    return np.linalg.norm(h), norm0, loss

print(f"{L} 层，batch={B}，d={d}，每层权重为随机正交阵 ×0.7")
print(f"{'堆叠方式':<12}{'‖h_L‖':>12}{'‖grad_0‖':>13}{'loss':>14}  现象")
rows = []
for mode, label in (("plain", "纯线性"), ("residual", "残差（无 LN）"), ("preln", "Pre-LN 残差")):
    hn, gn, loss = run(mode)
    rows.append((label, hn, gn, loss))
    tag = "梯度消失" if gn < 1e-3 else ("梯度爆炸" if gn > 1e3 else "尺度稳定")
    print(f"{label:<12}{hn:>12.3e}{gn:>13.3e}{loss:>14.3e}  {tag}")

print(f"\n纯线性：梯度 ≈ 0.7^{L} = {0.7**L:.2e} —— 乘性衰减，深了就回传不到底层。")
print("残差：每层因子 (1+0.7)=1.7，24 层放大 1.7^24 ≈ "
      f"{1.7**24:.1e} 倍 —— 解决了消失，却制造了爆炸。")
print("Pre-LN：分支输入先归一化，残差干道保持恒等路径，前向与梯度都只随深度多项式增长。")

print("\n分层梯度范数（Pre-LN，从输出往输入）：")
h, cache = h0, []
for Wl in W:
    z, c = ln_fwd(h)
    h = h + z @ Wl
    cache.append(c)
dh = h.copy()
norms = [np.linalg.norm(dh)]
for l in range(L - 1, -1, -1):
    dh = dh + ln_bwd(dh @ W[l].T, cache[l])
    norms.append(np.linalg.norm(dh))
print("  " + " ".join(f"L{L-i}:{norms[i]:.2f}" for i in range(0, L + 1, 6)))

print("\n结论：残差解决「深层回传路径太长」，LayerNorm 解决「尺度逐层漂移」，两者缺一不可。")
print("读法：Pre-LN（LN 放在分支里）训练更稳、可不加 warmup，是主流 LLM 的选择；")
print("      Post-LN（LN 放在残差相加之后）表达更强但需要 warmup，深层容易崩。")
