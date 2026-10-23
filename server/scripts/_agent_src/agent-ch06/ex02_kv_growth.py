# title: KV Cache 增长曲线：128k 上下文单条就要 51GB，GQA 把它压到 14.6GB
# 同一个 7B 模型，只改注意力头配置（MHA 28 个 KV 头 vs GQA 8 个）与 KV 精度。
# 结论先行：长上下文不是「显存不够就加卡」，而是先看 KV 头数与并发数。
GB = 1e9
LAYERS, HEADS, KV_HEADS, HEAD_DIM = 28, 28, 8, 128
SEQ = [2048, 8192, 32768, 131072]
BATCH = [1, 8, 32]


def kv_gb(seq, batch, kv_heads, bytes_per=2.0):
    return 2 * LAYERS * kv_heads * HEAD_DIM * bytes_per * seq * batch / GB


for name, kvh, bpe in (("MHA / FP16", HEADS, 2.0),
                       ("GQA(8) / FP16", KV_HEADS, 2.0),
                       ("GQA(8) / INT8", KV_HEADS, 1.0)):
    print(f"\n{name}  KV Cache 显存（GB）")
    print(f"{'seq\\batch':>10}" + "".join(f"{b:>10}" for b in BATCH))
    for s in SEQ:
        print(f"{s:>10}" + "".join(f"{kv_gb(s, b, kvh, bpe):>10.1f}" for b in BATCH))

print("\n单条序列的 KV 占用（GQA/FP16）：")
for s in SEQ:
    print(f"  {s:>7} tokens  {kv_gb(s, 1, KV_HEADS):>6.2f} GB  "
          f"（每条 1k token 约 {kv_gb(1024, 1, KV_HEADS):.3f} GB）")

print(f"\nMHA 在 128k/并发 1 时需要 {kv_gb(131072, 1, HEADS):.1f} GB，"
      f"已超过 80GB 卡的可用显存；换 GQA 后是 {kv_gb(131072, 1, KV_HEADS):.1f} GB。")
print(f"同一张 80GB 卡（可用 72GB，扣掉 14GB 权重）能放："
      f"MHA {int(58 / kv_gb(32768, 1, HEADS))} 条 32k 序列，"
      f"GQA {int(58 / kv_gb(32768, 1, KV_HEADS))} 条。")

print("\n读法：KV Cache 对序列长度和并发都是线性的，所以它是『乘积』增长，不是加法。")
print("把并发从 8 提到 32，等于把上下文从 32k 提到 128k——两者对显存的压力完全等价。")
print("GQA 的收益来自 KV 头数从 28 降到 8，也就是 3.5 倍；这也是为什么 7B/14B 模型普遍用 GQA。")
print("\n结论：容量规划要写清三个数——P99 输入长度、P99 输出长度、目标并发；")
print("三者相乘才是 KV 预算。只报『支持 128k 上下文』而不报并发，等于没说。")
