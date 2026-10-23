# title: FFN 作为键值记忆：存储与检索的直觉实验
# 把 W1 的行当 key、W2 的列当 value，用 Hebbian 方式写入 K 条模式，看检索如何随容量退化。
import numpy as np

rng = np.random.default_rng(4)
d = 32

def make_patterns(K, orthogonal=False):
    if orthogonal:
        Q, _ = np.linalg.qr(rng.normal(size=(max(K, d), d)))
        P = Q[:K]
    else:
        P = rng.normal(size=(K, d))
    return P / np.linalg.norm(P, axis=1, keepdims=True)

def retrieve(P, idx, noise=0.4):
    K = P.shape[0]
    W1 = P                      # K × d：每行是一个 key
    W2 = P.T                    # d × K：每列是同一个 key 作为 value
    q = P[idx] + rng.normal(0, noise / np.sqrt(d), d)
    h = np.maximum(W1 @ q, 0)   # 相似度（ReLU 稀疏化）
    out = W2 @ h
    return out @ P[idx] / (np.linalg.norm(out) * np.linalg.norm(P[idx]) + 1e-12)

print("每条模式是 d=32 的单位向量；查询 = 目标模式 + 噪声；指标 = 输出与目标模式的 cos。")
print(f"{'存储条数K':>10}{'随机 key':>12}{'正交 key':>12}{'K/d':>8}")
for K in (1, 2, 4, 8, 16, 32, 64, 128):
    r = np.mean([retrieve(make_patterns(K), 0) for _ in range(20)])
    o = np.mean([retrieve(make_patterns(K, True), 0) for _ in range(20)])
    print(f"{K:>10}{r:>12.3f}{o:>12.3f}{K/d:>8.2f}")

# 串扰：查询模式 0，但模式 1 与它高度相似
P = make_patterns(8)
P[1] = 0.9 * P[0] + 0.1 * P[1]
P[1] /= np.linalg.norm(P[1])
W1, W2 = P, P.T
q = P[0]
h = np.maximum(W1 @ q, 0)
out = W2 @ h
print("\n两条 key 高度相似时的激活（查询模式 0）：")
for i in range(4):
    print(f"  pattern {i}: key·q={W1[i] @ q:>6.3f}  relu={h[i]:>6.3f}  "
          f"对输出的贡献占比={h[i]/h.sum():>6.1%}")

print("\n结论：FFN 的两层矩阵可以看成「K 个 key → K 个 value」的联想记忆，")
print("      W1 做模式匹配、ReLU 做稀疏选择、W2 做加权取回。")
print("读法：容量不是无限的 —— key 越相似、存得越多，串扰越大；正交 key 在 K≤d 时几乎无损。")
print("      这也是为什么「模型能记住事实」与「模型会混淆相似实体」是同一机制的两面。")
