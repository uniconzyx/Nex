# title: 按请求计费模型：输入、输出、缓存命中三档怎么算
# 单价为演示假设（不是任何厂商报价）：输入 2.0 元/百万 token，缓存命中 0.2，输出 8.0。
# 这个脚本回答一个具体问题：前缀缓存到底能省多少，以及在什么命中率下值得改造。

PRICE_IN = 2.0        # 元 / 1M tokens
PRICE_CACHE = 0.2     # 元 / 1M tokens（命中缓存的输入）
PRICE_OUT = 8.0       # 元 / 1M tokens
PROMPT = 2000         # 每次请求输入 token
CACHED_PREFIX = 1500  # 其中可缓存的前缀（系统提示 + 工具定义）
OUTPUT = 400
DAILY = 20000


def cost(n_requests, hit_rate, prompt=PROMPT, cached=CACHED_PREFIX, output=OUTPUT):
    hit = cached * hit_rate
    miss = prompt - hit
    inp = (miss * PRICE_IN + hit * PRICE_CACHE) / 1e6
    out = output * PRICE_OUT / 1e6
    return n_requests * (inp + out)


print(f"单请求画像：输入 {PROMPT} token（其中可缓存前缀 {CACHED_PREFIX}），输出 {OUTPUT} token")
print(f"假设单价：输入 {PRICE_IN} / 缓存 {PRICE_CACHE} / 输出 {PRICE_OUT} 元每百万 token\n")
print(f"{'缓存命中率':>8}{'单请求(元)':>12}{'千次(元)':>11}{'日成本(元)':>12}{'月成本(元)':>13}")
base = None
for h in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0):
    c = cost(1, h)
    base = base or c
    print(f"{h:>8.0%}{c:>12.4f}{c*1000:>11.2f}{c*DAILY:>12.1f}{c*DAILY*30:>13.0f}")

c0, c1 = cost(1, 0.0), cost(1, 1.0)
print(f"\n全命中相对不缓存：单请求 {c0:.4f} → {c1:.4f} 元，降幅 {(1-c1/c0):.1%}")
print(f"日活 {DAILY} 次时，一个月的差额约 {(c0-c1)*DAILY*30:,.0f} 元。")

print("\n成本归因拆解（命中率 75%）：")
hit = CACHED_PREFIX * 0.75
parts = [
    ("输入-未命中", (PROMPT - hit) * PRICE_IN / 1e6),
    ("输入-命中", hit * PRICE_CACHE / 1e6),
    ("输出", OUTPUT * PRICE_OUT / 1e6),
]
total = sum(v for _, v in parts)
for name, v in parts:
    print(f"  {name:<12}{v:>9.5f} 元  {v/total:>6.1%}")
print(f"  {'合计':<12}{total:>9.5f} 元")

print("\n读法：输出单价是输入的 4 倍，但这里输出只占 "
      f"{parts[2][1]/total:.0%} 的成本；输入侧的体积才是账单大头。")
print("结论：先压输入（去冗余 few-shot、稳定前缀、缓存友好排序），再压输出（max_tokens + 结构化约束）；")
print("      缓存只对「前缀逐字节稳定」生效——在系统提示里塞时间戳，会让命中率直接归零。")
