# title: 参数量计算器：embedding、注意力、FFN 各占多少
# 用公式拆开三个真实配置，验证「7B 里 FFN 占约 2/3、词表在小模型里很贵」。
import numpy as np

def count(V, d, L, ffn, mlp_mats=3, tied=True, norm_per_layer=None, kv_ratio=1.0):
    if norm_per_layer is None:
        norm_per_layer = 4 * d
    emb = V * d
    head = 0 if tied else V * d
    # kv_ratio = n_kv_heads / n_heads；1.0 为 MHA，1/8 为 GQA-8
    attn = 2 * d * d + 2 * d * int(d * kv_ratio)
    mlp = mlp_mats * d * ffn
    per_layer = attn + mlp + norm_per_layer
    total = emb + head + L * per_layer + 2 * d
    return {"embed": emb, "attn": L * attn, "mlp": L * mlp,
            "norm": L * norm_per_layer + 2 * d, "total": total}

CONFIGS = [
    ("GPT-2 small", dict(V=50257, d=768, L=12, ffn=3072, mlp_mats=2, tied=True)),
    ("Llama-7B 式", dict(V=32000, d=4096, L=32, ffn=11008, mlp_mats=3, tied=False)),
    ("80L · MHA", dict(V=32000, d=8192, L=80, ffn=28672, mlp_mats=3, tied=False)),
    ("80L · GQA-8", dict(V=32000, d=8192, L=80, ffn=28672, mlp_mats=3,
                         tied=False, kv_ratio=0.125)),
]

print(f"{'配置':<14}{'embed':>10}{'attention':>11}{'FFN':>10}{'norm':>8}"
      f"{'总计':>10}{'FFN 占比':>9}")
for name, cfg in CONFIGS:
    c = count(**cfg)
    print(f"{name:<14}{c['embed']/1e6:>9.1f}M{c['attn']/1e6:>10.1f}M"
          f"{c['mlp']/1e6:>9.1f}M{c['norm']/1e6:>7.2f}M"
          f"{c['total']/1e9:>9.2f}B{c['mlp']/c['total']:>8.0%}")

print("\n单层拆解（Llama-7B 式）：")
d, ffn = 4096, 11008
parts = [("Wq/Wk/Wv/Wo", 4 * d * d), ("gate/up", 2 * d * ffn), ("down", ffn * d)]
for name, p in parts:
    print(f"  {name:<14}{p/1e6:>8.1f}M  ({p/(4*d*d+3*d*ffn):>5.1%} of layer)")

print("\n缩放规律（固定 d/ffn，只改层数）：")
print(f"{'L':>4}{'总参数':>10}{'embed 占比':>11}")
for L in (12, 24, 32, 48, 80):
    c = count(V=32000, d=4096, L=L, ffn=11008, mlp_mats=3, tied=False)
    print(f"{L:>4}{c['total']/1e9:>9.2f}B{c['embed']/c['total']:>10.1%}")

print("\n结论：FFN 约占 2/3 参数（SwiGLU 三矩阵），注意力只占约 1/3；")
print("      层数增加时 embedding 占比线性下降，所以小模型必须先看词表是否过大。")
print("读法：面试报参数量要说明口径 —— 是否共享输出头、MLP 是 2 矩阵还是 3 矩阵、")
print("      是否含 bias 与 LayerNorm，否则同一「7B」能差出 0.5B。")
