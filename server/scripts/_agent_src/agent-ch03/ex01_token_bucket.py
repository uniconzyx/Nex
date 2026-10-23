# title: 令牌桶限流器：突发流量不是「拒绝」，而是「用容量换平滑」
# 本地模拟，不联网。桶容量 10、补充速率 5 token/s，对比「无突发容量」的纯速率限制。
# 关键工程判断：容量决定能吸收多长的突发，速率决定长期平均吞吐，两者不能互相替代。

class TokenBucket:
    def __init__(self, capacity: float, rate_per_sec: float):
        self.capacity = float(capacity)
        self.rate = float(rate_per_sec)
        self.tokens = float(capacity)
        self.last_ms = 0.0
        self.accepted = 0
        self.rejected = 0

    def allow(self, now_ms: float) -> bool:
        elapsed = max(0.0, (now_ms - self.last_ms) / 1000.0)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_ms = now_ms
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.accepted += 1
            return True
        self.rejected += 1
        return False


def arrivals():
    """t=0 一次来 12 个请求（突发），随后 4 秒内每秒 3 个（稳态）。"""
    events = [(0.0, "burst") for _ in range(12)]
    for sec in range(1, 5):
        events += [(sec * 1000.0, "steady") for _ in range(3)]
    return events


def run(capacity: float, rate: float = 5.0):
    bucket = TokenBucket(capacity, rate)
    per_sec = {}
    peak_reject_sec = None
    for ts, kind in arrivals():
        ok = bucket.allow(ts)
        sec = int(ts // 1000)
        row = per_sec.setdefault(sec, [0, 0, 0, 0.0])
        row[0] += 1
        row[1 if ok else 2] += 1
        row[3] = bucket.tokens
        if not ok and kind == "burst" and peak_reject_sec is None:
            peak_reject_sec = sec
    return bucket, per_sec, peak_reject_sec


print("模拟设定：容量 C=10，补充速率 r=5 token/s；t=0 突发 12 个请求，之后 4 秒每秒 3 个")
print("（这是模拟：真实接入时 allow() 要放在调用模型之前，见本章 concept/01 第 3 节）\n")

for cap, label in ((10.0, "C=10（有突发容量）"), (1.0, "C=1（退化为纯速率限制）")):
    bucket, per_sec, _ = run(cap)
    print(f"[{label}]")
    print(f"{'秒':>3} {'到达':>4} {'放行':>4} {'拒绝':>4} {'秒末令牌':>8}")
    for sec in sorted(per_sec):
        a, ok, no, bal = per_sec[sec]
        print(f"{sec:>3} {a:>4} {ok:>4} {no:>4} {bal:>8.1f}")
    generated = cap + 5.0 * 4.0
    util = bucket.accepted / generated
    print(f"合计：放行 {bucket.accepted}，拒绝 {bucket.rejected}，"
          f"长期利用率≈{util:.1%}（放行数 / (初始容量+补充量)）\n")

print("读法：C=10 时突发只丢掉 2 个请求，稳态全部放行；C=1 时突发丢掉 11 个，")
print("      而且稳态每秒还丢 2 个——因为桶容量小于单秒到达数，补进来的令牌顶到上限就浪费了。")
print("结论：C 至少要覆盖一个到达批次的大小，否则速率配得再高也会持续丢包；")
print("      C/r 就是系统能承受的突发时长（这里是 2 秒），按 P99 突发定 C、按下游配额定 r。")
