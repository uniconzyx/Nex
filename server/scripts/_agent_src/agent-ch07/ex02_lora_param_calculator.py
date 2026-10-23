# title: LoRA 参数量计算器：rank 与作用层怎么选
# 同一基座，改变 rank 与挂载模块，算出可训练参数、占比与每 token 的额外计算量。
import numpy as np

D, L, FFN, VOCAB = 4096, 32, 11008, 32000

# 基座参数量（Llama 式：attn 4 个 d×d，MLP 为 gate/up/down，词表 embedding 共享输出头）
per_layer = 4 * D * D + 3 * D * FFN
base = L * per_layer + VOCAB * D
print(f"基座：{L} 层，d={D}，ffn={FFN}，词表={VOCAB}")
print(f"基座参数量 ≈ {base/1e9:.2f}B（每层 {per_layer/1e6:.1f}M）\n")

# 每个被挂载的线性层，LoRA 参数 = r*(in+out)
def lora_params(r, modules):
    total = 0
    for in_dim, out_dim in modules:
        total += r * (in_dim + out_dim)
    return L * total

qkv = [(D, D), (D, D), (D, D), (D, D)]                       # q, k, v, o
all_lin = qkv + [(D, FFN), (D, FFN), (FFN, D)]               # + gate, up, down
qv_only = [(D, D), (D, D)]                                   # 只挂 q, v

print(f"{'rank':>5} {'q,v':>12} {'q,k,v,o':>12} {'全部线性层':>14} {'占比(全线性)':>12}")
for r in (4, 8, 16, 32, 64):
    p_qv = lora_params(r, qv_only)
    p_qkvo = lora_params(r, qkv)
    p_all = lora_params(r, all_lin)
    print(f"{r:>5} {p_qv:>12,} {p_qkvo:>12,} {p_all:>14,} {p_all/base:>11.2%}")

print(f"\nα 的缩放：LoRA 输出乘以 α/r，α=16 时")
for r in (8, 16, 32):
    print(f"  r={r:>2} → 缩放 {16/r:.2f}；r 翻倍而 α 不变，等于把增量幅度减半")

# 每 token 每层额外 FLOPs（乘加各算 1 次）：q/k/v/o 各 2*d*r，MLP 各 2*d*r
r = 16
extra_per_token = L * (4 * 2 * D * r) / 1e9
print(f"\nr={r} 挂 q,k,v,o：每 token 额外 ≈ {extra_per_token:.2f} GFLOPs")
print("对比基座前向每 token ≈ 2×6.6B = 13.2 GFLOPs，增量约 "
      f"{extra_per_token/13.2:.1%}，推理几乎无感。")
print("\n结论：rank 从 8 加到 32，参数涨 4 倍，但表达力提升通常远小于 4 倍；")
print("读法：先固定 r=16 挂 q,k,v,o 跑基线，只有训练 loss 下不去才加 rank 或加 MLP 层。")
print("      α 与 r 要一起调（常用 α=2r），否则改 rank 会顺带改掉有效学习率。")
