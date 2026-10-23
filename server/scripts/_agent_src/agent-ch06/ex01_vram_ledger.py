# title: 显存账本：7B/INT4 在 4090 上开 16 并发 8k，余量只剩 0.5GB
# 权重 + KV Cache + 激活 + 框架开销 四项分开算，任何一项漏掉都会在压测时变成 OOM。
# 参数量与层数取公开配置的近似值（7B: 28 层 8 个 KV 头），单位按 1e9 字节计，非 GiB。
import numpy as np

GB = 1e9

MODELS = {
    "7B":  {"params": 7.0e9,  "layers": 28, "kv_heads": 8, "head_dim": 128},
    "14B": {"params": 14.0e9, "layers": 40, "kv_heads": 8, "head_dim": 128},
    "70B": {"params": 70.0e9, "layers": 80, "kv_heads": 8, "head_dim": 128},
}
DTYPE = {"FP16": 2.0, "INT8": 1.0, "INT4": 0.55}   # INT4 含 group scale 开销


def ledger(model, dtype, ctx, conc):
    m = MODELS[model]
    b = DTYPE[dtype]
    weights = m["params"] * b
    kv_per_tok = 2 * m["layers"] * m["kv_heads"] * m["head_dim"] * 2.0  # KV 通常仍是 FP16
    kv = kv_per_tok * ctx * conc
    act = 0.6e9 + conc * 0.05e9               # 经验值：固定 0.6GB + 每并发约 50MB 临时缓冲
    overhead = 0.8e9                          # CUDA context + 通信缓冲
    return weights, kv, act, overhead


def show(model, dtype, ctx, cap_gb):
    w, kv, act, ov = ledger(model, dtype, ctx, 1)
    print(f"\n{model} / {dtype} / ctx={ctx}")
    print(f"{'并发':>4}{'权重':>8}{'KV Cache':>10}{'激活':>8}{'开销':>7}{'合计':>9}{'余量':>9}{'判定':>8}")
    for conc in (1, 8, 16, 32):
        w, _, _, _ = ledger(model, dtype, ctx, 1)
        kv1 = 2 * MODELS[model]["layers"] * MODELS[model]["kv_heads"] * MODELS[model]["head_dim"] * 2.0 * ctx
        kv = kv1 * conc
        act = 0.6e9 + conc * 0.05e9
        ov = 0.8e9
        total = w + kv + act + ov
        free = cap_gb * GB * 0.9 - total
        ok = "OK" if free > 0 else "OOM"
        print(f"{conc:>4}{w/GB:>8.1f}{kv/GB:>10.1f}{act/GB:>8.1f}{ov/GB:>7.1f}"
              f"{total/GB:>9.1f}{free/GB:>9.1f}{ok:>8}")


print("可用显存按标称的 90% 计（驱动与碎片预留 10%）：")
print("4090 24GB -> 21.6GB 可用；A100 80GB -> 72GB 可用")
show("7B", "FP16", 8192, 24)
show("7B", "INT4", 8192, 24)
show("14B", "INT4", 8192, 24)
show("70B", "INT4", 8192, 80)

w, kv1, act, ov = ledger("7B", "INT4", 8192, 16)
print("\n单项占比（7B/INT4/8k/并发 16）：")
bel = {"权重": w, "KV Cache": kv1, "激活": act, "开销": ov}
tot = sum(bel.values())
for k, v in bel.items():
    print(f"  {k:<9}{v/GB:>7.1f} GB  {v/tot:>6.1%}")

print("\n读法：7B/INT4 在 4090 上跑到 16 并发 8k 时合计 21.1GB，余量只剩 0.5GB；")
print("而 KV Cache 是按『最大上下文』预留的，只要来两个 16k 请求就会击穿这条线。")
print("FP16 连 8 并发都放不下（23.3GB > 21.6GB），INT4 省下的 10GB 才让 16 并发成立。")
print("\n结论：显存规划的第一优先级不是权重，是 KV Cache：它随上下文线性、随并发线性，")
print("而权重是常数。先按 P99 长度 × 目标并发 算出 KV，再看剩下的空间够不够放权重。")
print("注意：这里按 1e9 计，nvidia-smi 显示的是 GiB，两者差 7.4%，边界情况下这 7% 就是 OOM 与不 OOM 的差别。")
