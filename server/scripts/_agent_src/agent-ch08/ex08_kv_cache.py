# title: KV Cache 显存账本：为什么长上下文又慢又贵
# bytes = 2(K,V) × 层数 × KV头数 × head_dim × 序列长 × batch × 每元素字节。
import numpy as np

GB = 1024 ** 3

def kv_bytes(L, n_kv, dh, seq, batch, bytes_per=2):
    return 2 * L * n_kv * dh * seq * batch * bytes_per

L, DH = 32, 128
print(f"以 32 层、head_dim={DH} 的 7B 模型为例，单条序列（batch=1, fp16）")
print(f"{'序列长度':>9}{'MHA(32头)':>12}{'GQA(8头)':>11}{'MQA(1头)':>10}{'相对 2k':>9}")
base = kv_bytes(L, 32, DH, 2048, 1)
for seq in (2048, 8192, 32768, 131072):
    mha = kv_bytes(L, 32, DH, seq, 1)
    gqa = kv_bytes(L, 8, DH, seq, 1)
    mqa = kv_bytes(L, 1, DH, seq, 1)
    print(f"{seq:>9}{mha/GB:>11.2f}G{gqa/GB:>10.2f}G{mqa/GB:>9.2f}G{mha/base:>8.1f}×")

print("\nbatch 的影响（32k 序列，GQA 8 头）：")
print(f"{'batch':>6}{'KV Cache':>11}{'权重':>8}{'合计':>8}{'80G 卡余量':>11}")
w = 13.5
for b in (1, 4, 8, 16, 32):
    kv = kv_bytes(L, 8, DH, 32768, b)
    total = kv / GB + w
    print(f"{b:>6}{kv/GB:>10.1f}G{w:>7.1f}G{total:>7.1f}G{80-total:>10.1f}G")

print("\n精度的影响（32k, batch=8, GQA 8 头）：")
for name, bp in (("FP16", 2), ("INT8", 1), ("FP8", 1)):
    kv = kv_bytes(L, 8, DH, 32768, 8, bp)
    print(f"  {name:<6}{kv/GB:>8.2f}G")

print("\n算一笔账：同样 32k 上下文，MHA 的 KV 是 GQA(8) 的 4 倍、MQA 的 32 倍；")
print(f"  32k/batch=8/GQA 需要 {kv_bytes(L,8,DH,32768,8)/GB:.1f}G，已超过 24G 卡；"
      f"batch=1 也要 {kv_bytes(L,8,DH,32768,1)/GB:.1f}G。")
print("\n结论：长上下文的成本主要不是注意力矩阵，而是**每生成一个 token 都要读完整 KV**。")
print("读法：")
print("1. 显存随 seq×batch 线性涨，解码带宽也随 seq 线性涨，所以 128k 的首 token 延迟远高于 4k；")
print("2. GQA/MQA 用「多个 query 头共享一组 KV」换显存，是当前开源模型的默认配置；")
print("3. PagedAttention 解决的是碎片与共享，不改变这条线性公式；")
print("4. 量化 KV 到 INT8 直接减半，但要注意离群值对精度的伤害。")
