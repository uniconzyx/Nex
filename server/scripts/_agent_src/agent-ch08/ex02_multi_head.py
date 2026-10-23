# title: 手写多头注意力：拆分、并行、拼接与输出投影
# d_model=12 拆成 3 个头（每头 4 维），验证「多头 = 多个子空间 + 一次输出投影」。
import numpy as np

rng = np.random.default_rng(1)
T, D, H = 5, 12, 3
DH = D // H

X = rng.normal(size=(T, D))
Wq = rng.normal(scale=0.4, size=(D, D))
Wk = rng.normal(scale=0.4, size=(D, D))
Wv = rng.normal(scale=0.4, size=(D, D))
Wo = rng.normal(scale=0.4, size=(D, D))

def split_heads(M):
    return M.reshape(T, H, DH).transpose(1, 0, 2)      # H × T × DH

def softmax(s):
    s = s - s.max(axis=-1, keepdims=True)
    e = np.exp(s)
    return e / e.sum(axis=-1, keepdims=True)

Q, K, V = split_heads(X @ Wq), split_heads(X @ Wk), split_heads(X @ Wv)
scores = Q @ K.transpose(0, 2, 1) / np.sqrt(DH)       # H × T × T
A = softmax(scores)
head_out = A @ V                                       # H × T × DH
concat = head_out.transpose(1, 0, 2).reshape(T, D)     # T × D
out = concat @ Wo

print(f"X {X.shape} → 拆头 Q {Q.shape}（H={H}, T={T}, d_head={DH}）")
print(f"每个头的打分矩阵 {scores.shape}，输出 {head_out.shape} → 拼回 {concat.shape}")
print("\n各头对第 0 个 token 的注意力分布（每行和为 1）：")
for h in range(H):
    print(f"  head {h}: " + " ".join(f"{v:.3f}" for v in A[h, 0]) +
          f"   sum={A[h,0].sum():.6f}  entropy={-(A[h,0]*np.log(A[h,0]+1e-12)).sum():.3f}")
print(f"\n最终输出 {out.shape}；与手算 concat·Wo 的最大差 "
      f"{np.abs(concat @ Wo - out).max():.2e}")

# 单头（d_head=12）与多头（3×4）参数量相同，差别只在「子空间划分」
p_multi = 4 * D * D          # Wq, Wk, Wv, Wo
p_single = 4 * D * D
print(f"\n参数量：单头 {p_single:,}，多头 {p_multi:,} —— 完全相同")
print(f"计算量（每 token）：单头 4·T·D²，多头同样 4·T·D²；多头并没有更贵")

# 等价性：H=1 时多头退化为单头
Q1 = (X @ Wq).reshape(T, 1, D).transpose(1, 0, 2)
K1 = (X @ Wk).reshape(T, 1, D).transpose(1, 0, 2)
V1 = (X @ Wv).reshape(T, 1, D).transpose(1, 0, 2)
o1 = (softmax(Q1 @ K1.transpose(0, 2, 1) / np.sqrt(D)) @ V1)[0] @ Wo
single = (softmax((X @ Wq) @ (X @ Wk).T / np.sqrt(D)) @ (X @ Wv)) @ Wo
print(f"H=1 退化检查：多头实现 vs 单头实现最大差 {np.abs(o1 - single).max():.2e}")

print("\n各头平均注意力熵（越低越聚焦）：")
for h in range(H):
    ent = -(A[h] * np.log(A[h] + 1e-12)).sum(axis=1).mean()
    print(f"  head {h}: {ent:.3f}  （上限 ln T = {np.log(T):.3f}）")

print("\n结论：多头把 d_model 切成 H 份并行做注意力，再拼接投影；参数与 FLOPs 都不变。")
print("读法：头的分工不是设计出来的，是训练出来的；分析时可看熵与最大注意力位置，")
print("      但不要假定「第 0 个头一定学句法」——那只是事后叙事。")
