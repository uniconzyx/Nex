# title: 低秩近似的参数量与误差：LoRA 的数学前提
# 对 d×d 权重做 SVD，只保留前 r 个奇异值，观察「参数省了多少」与「误差丢了多少」。
# 关键结论：省参数几乎线性，误差取决于奇异值谱的衰减速度——不是任何矩阵都能低秩近似。
import numpy as np

rng = np.random.default_rng(7)
d_in, d_out = 256, 256

# 构造一个「谱衰减」的权重：模拟微调增量 ΔW 常见的长尾结构
u, _ = np.linalg.qr(rng.normal(size=(d_out, d_out)))
v, _ = np.linalg.qr(rng.normal(size=(d_in, d_in)))
s = 1.0 / (np.arange(1, d_in + 1) ** 1.1)      # 幂律衰减的奇异值
W = (u * s) @ v.T

sv = np.linalg.svd(W, compute_uv=False)
energy = np.cumsum(sv ** 2) / np.sum(sv ** 2)
full_params = d_in * d_out

print(f"权重形状 {d_out}×{d_in}，满秩参数量 {full_params:,}")
print(f"{'rank':>5} {'参数量':>9} {'占比':>7} {'Frobenius 误差':>15} {'能量占比':>9}")
for r in (1, 2, 4, 8, 16, 32, 64):
    # 截断 SVD：W_r = U_r S_r V_r^T
    Wr = (u[:, :r] * sv[:r]) @ v[:, :r].T
    err = np.linalg.norm(W - Wr) / np.linalg.norm(W)
    params = r * (d_in + d_out)
    print(f"{r:>5} {params:>9,} {params/full_params:>6.1%} "
          f"{err:>15.4f} {energy[r-1]:>8.1%}")

# 对照：同样是 rank=8，但奇异值平坦（近似随机矩阵）时误差会差多少
W_flat = rng.normal(size=(d_out, d_in)) / np.sqrt(d_in)
u2, s2, vt2 = np.linalg.svd(W_flat, full_matrices=False)
Wr2 = (u2[:, :8] * s2[:8]) @ vt2[:8]
err_flat = np.linalg.norm(W_flat - Wr2) / np.linalg.norm(W_flat)
Wr1 = (u[:, :8] * sv[:8]) @ v[:, :8].T
err_decay = np.linalg.norm(W - Wr1) / np.linalg.norm(W)
print(f"\n同样 rank=8：谱衰减矩阵误差 {err_decay:.1%}，平坦谱随机矩阵误差 {err_flat:.1%}")
print(f"rank=8 只占参数 {8*(d_in+d_out)/full_params:.1%}，但谱衰减时已保住 {energy[7]:.1%} 的能量。")
print("\n结论：LoRA 省的是「增量 ΔW 的自由度」，不是「基座 W 的秩」。")
print("读法：真实微调增量常呈长尾谱，所以 r=8~16 够用；若任务要求全新能力（谱平坦），")
print("      小 rank 会欠拟合，此时应先怀疑数据与任务定义，而不是盲目加 rank。")
