# title: Token 经济账：上下文不是越长越好，成本要按「解决一单」算
# 三档单价（元 / 百万 token），输入含缓存命中折扣；上下文 2k→128k，输出固定 500 token。
# 关键：准确率随上下文提升但边际递减，所以真正的指标是「每解决一单的成本」。
PRICES = {
    "经济档": {"in": 2.0, "out": 8.0, "cache": 0.1},
    "均衡档": {"in": 4.0, "out": 16.0, "cache": 0.1},
    "旗舰档": {"in": 8.0, "out": 32.0, "cache": 0.25},
}
SYSTEM = 600
OUT = 500
# 上下文长度 → 任务成功率（经验曲线：8k 之后收益很小）
CTX = [2000, 8000, 32000, 128000]
SUCCESS = [0.62, 0.80, 0.86, 0.87]

def cost(ctx, price, cache_hit=0.0):
    cached = SYSTEM * cache_hit
    fresh = ctx - cached
    return (fresh * price["in"] + cached * price["in"] * price["cache"] + OUT * price["out"]) / 1e6

print("=" * 78)
print("表 1  单次请求成本（元），括号内为「每解决一单」成本 = 单次成本 / 成功率")
print("=" * 78)
header = f"{'上下文':>8}" + "".join(f"{k:>22}" for k in PRICES)
print(header)
for ctx, sr in zip(CTX, SUCCESS):
    row = f"{ctx:>8}"
    for name, p in PRICES.items():
        c = cost(ctx, p, cache_hit=0.6)
        row += f"{c:>10.4f} ({c/sr:>7.4f})"
    print(row)

print("\n" + "=" * 78)
print("表 2  上下文翻倍的边际账（均衡档，缓存命中 60%）")
print("=" * 78)
p = PRICES["均衡档"]
print(f"{'区间':<18}{'成本增幅':>10}{'成功率增幅':>11}{'每单成本增幅':>13}")
for i in range(1, len(CTX)):
    c0, c1 = cost(CTX[i-1], p, 0.6), cost(CTX[i], p, 0.6)
    s0, s1 = SUCCESS[i-1], SUCCESS[i]
    ratio = (c1/s1) / (c0/s0) - 1
    print(f"{CTX[i-1]//1000}k → {CTX[i]//1000}k{'':<4}{(c1/c0-1):>9.0%}{(s1-s0)*100:>10.0f}pp{ratio:>12.0%}")

print("\n" + "=" * 78)
print("表 3  缓存命中率的影响（32k 上下文，均衡档）")
print("=" * 78)
print(f"{'缓存命中':>9}{'单次成本':>11}{'相对无缓存':>12}")
base = cost(32000, p, 0.0)
for hit in (0.0, 0.3, 0.6, 0.9):
    c = cost(32000, p, hit)
    print(f"{hit:>9.0%}{c:>11.4f}{c/base:>12.0%}")

r_cost = cost(128000, p, 0.6) / cost(32000, p, 0.6)
r_task = (cost(128000, p, 0.6) / SUCCESS[3]) / (cost(32000, p, 0.6) / SUCCESS[2])
print(f"\n结论：32k→128k 单次成本涨 {r_cost:.1f} 倍，成功率只从 {SUCCESS[2]:.0%} 到 {SUCCESS[3]:.0%}，")
print(f"      每单成本反而涨 {r_task:.1f} 倍——上下文的最优点在「刚好覆盖证据」的位置，不在模型支持的上限。")
print("读法：报价按「每解决一单」倒推，并把缓存命中率当成一等指标（它直接把输入成本打到 1 折）。")
print("     （单价与成功率是教学假设，真实值需用自己的黄金集实测。）")
