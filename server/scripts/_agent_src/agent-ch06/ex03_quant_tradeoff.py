# title: 量化收益：INT4 把 7B 权重从 14GB 压到 3.7GB，但解码只快 2.3 倍而不是 3.8 倍
# 解码是带宽瓶颈：tok/s ≈ 有效带宽 / 每 token 要读的字节数。
# 量化省的是字节，不是 FLOPs；batch 一大就转成算力瓶颈，收益立刻打折。
GB = 1e9
BW = 2039e9          # A100 80GB HBM2e 峰值带宽 B/s
BW_EFF = 0.75        # 实测可达比例
FLOPS = 312e12       # FP16 稠密算力

DTYPES = {
    "FP16": {"bytes": 2.0, "kernel": 0.80, "note": "基线"},
    "INT8": {"bytes": 1.0, "kernel": 0.65, "note": "W8A8"},
    "INT4": {"bytes": 0.53125, "kernel": 0.45, "note": "AWQ/GPTQ，group=128"},
}

MODELS = {"7B": 7.0e9, "14B": 14.0e9, "70B": 70.0e9}

print(f"带宽 {BW/1e9:.0f} GB/s × 有效率 {BW_EFF:.0%} = {BW*BW_EFF/1e9:.0f} GB/s；FP16 算力 {FLOPS/1e12:.0f} TFLOPS\n")
print(f"{'模型':<6}{'精度':>6}{'权重GB':>9}{'读权重耗时':>12}{'理论上限tok/s':>15}{'折算后tok/s':>13}{'相对FP16':>10}")
base = {}
for m, p in MODELS.items():
    for d, cfg in DTYPES.items():
        wb = p * cfg["bytes"]
        t = wb / (BW * BW_EFF)
        theo = 1.0 / t
        real = theo * cfg["kernel"]
        base.setdefault(m, real)
        gain = real / base[m]
        print(f"{m:<6}{d:>6}{wb/GB:>9.1f}{t*1e3:>11.1f}ms{theo:>15.0f}{real:>13.0f}{gain:>9.2f}x")

print("\n表里的『折算后』已乘 kernel 效率（FP16 0.80 / INT8 0.65 / INT4 0.45）：")
print("INT4 的 4 倍字节压缩，到端到端只剩 2.3 倍左右——差在反量化与算子融合。")

print("\n什么时候量化不再提速（batch 增大后转为算力瓶颈）：")
for m, p in MODELS.items():
    for d, cfg in DTYPES.items():
        wb = p * cfg["bytes"]
        t_mem = wb / (BW * BW_EFF)
        t_comp_per_seq = 2 * p / FLOPS
        cross = t_mem / t_comp_per_seq
        print(f"  {m}/{d:<5} 权重读一次 {t_mem*1e3:5.1f}ms，单序列算力 {t_comp_per_seq*1e3:4.2f}ms，"
              f"batch>{int(cross):>4} 后转算力瓶颈")

print("\n读法：上表说明三件事——")
print("1) 小模型量化收益更小：7B/INT4 的权重只有 3.7GB，读一次 2.4ms，kernel 调度与采样开始占大头；")
print("2) 大模型量化收益更大：70B/FP16 要 140GB，单卡根本放不下，INT4 才能塞进 80GB；")
print("3) batch 一旦超过交叉点，加 batch 不再免费，TTFT 会明显上升。")

print("\n精度代价（经验判断，非本脚本实测）：4bit 权重量化在通用问答上困惑度通常涨 2%-8%，")
print("代码与数学任务更敏感；AWQ 在 7B 上一般比 round-to-nearest 稳 1-3 个点。")
print("上线口径不是看困惑度，而是看你的黄金集：忠实度、格式合规率、拒答率三项都不能掉超过 2 个点。")

print("\n结论：量化是把『显存墙』换成『kernel 效率』的交易。先确认瓶颈在带宽（decode、低并发），")
print("再量化；如果是 prefill 为主或高并发，收益会被算力与调度吃掉，不如加卡或换更小的模型。")
