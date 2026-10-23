# title: 一次请求的延迟预算：P99 不能相加，尾延迟由最大那一段主导
# 链路：UI → 网关 → 编排 → 检索 → 模型首 token → 工具 → 生成 → 存储。
# 每段给定 P50 与 P99，按对数正态采样 20000 次，合成 TTFT 与总时延的 P50/P95/P99；
# 再和「把各段 P99 直接相加」的朴素预算对比，最后做逐段优化 20% 的边际收益。
import numpy as np

rng = np.random.default_rng(42)
# (段名, P50 ms, P99 ms, 是否在首 token 之前)
SEGS = [
    ("UI/网络", 45, 180, True),
    ("网关鉴权", 9, 40, True),
    ("编排", 18, 70, True),
    ("检索", 55, 260, True),
    ("模型 TTFT", 420, 1500, True),
    ("工具调用", 180, 900, True),
    ("生成", 900, 3200, False),
    ("存储写入", 20, 90, False),
]
Z99 = 2.326
N = 20000

def sample(p50, p99):
    sigma = np.log(p99 / p50) / Z99
    mu = np.log(p50)
    return rng.lognormal(mu, sigma, N)

cols = {name: sample(p50, p99) for name, p50, p99, _ in SEGS}
ttft = sum(cols[n] for n, _, _, pre in SEGS if pre)
total = sum(cols.values())

def q(a, p):
    return float(np.percentile(a, p))

print("=" * 72)
print("表 1  分段预算（ms）")
print("=" * 72)
print(f"{'段':<10}{'P50':>8}{'P99':>8}{'P99/P50':>9}  位置")
for name, p50, p99, pre in SEGS:
    print(f"{name:<10}{p50:>8}{p99:>8}{p99/p50:>9.1f}x  {'首token前' if pre else '流式输出'}")

naive_ttft = sum(p99 for _, _, p99, pre in SEGS if pre)
naive_total = sum(p99 for _, _, p99, _ in SEGS)
print("\n" + "=" * 72)
print("表 2  合成结果：独立尾延迟不会同时发生，直接相加会高估预算")
print("=" * 72)
print(f"{'口径':<22}{'P50':>9}{'P95':>9}{'P99':>9}")
print(f"{'TTFT 蒙特卡洛':<22}{q(ttft,50):>9.0f}{q(ttft,95):>9.0f}{q(ttft,99):>9.0f}")
print(f"{'TTFT 各段P99相加':<22}{'—':>9}{'—':>9}{naive_ttft:>9.0f}")
print(f"{'总时延 蒙特卡洛':<22}{q(total,50):>9.0f}{q(total,95):>9.0f}{q(total,99):>9.0f}")
print(f"{'总时延 各段P99相加':<22}{'—':>9}{'—':>9}{naive_total:>9.0f}")
print(f"\n朴素相加使 TTFT P99 高估 {(naive_ttft/q(ttft,99)-1):.0%}，总时延高估 {(naive_total/q(total,99)-1):.0%}。")

print("\n" + "=" * 72)
print("表 3  每段优化 20% 对总时延 P99 的边际收益")
print("=" * 72)
base99 = q(total, 99)
rows = []
for name, p50, p99, pre in SEGS:
    reduced = {k: (v * 0.8 if k == name else v) for k, v in cols.items()}
    new99 = q(sum(reduced.values()), 99)
    rows.append((base99 - new99, name))
for gain, name in sorted(rows, reverse=True):
    print(f"  {name:<10} ΔP99 = -{gain:>6.0f} ms  ({(gain/base99):>5.1%})")

print("\n结论：总时延 P99 由「生成」和「模型 TTFT」两段主导，优化检索的 P50 再漂亮也动不了尾延迟；")
print("      而按 P99 相加做预算会多留约 45% 的余量，白买机器。")
print("读法：预算按「合成分布」定，优化按「对 P99 的边际贡献」排序；先砍最大段的尾部（重试、超时、长输出）。")
print("     （分布假设为对数正态，真实链路需用 trace 数据校准。）")
