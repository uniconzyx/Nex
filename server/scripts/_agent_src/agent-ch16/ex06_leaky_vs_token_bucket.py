# title: 漏桶 vs 令牌桶：同一突发序列下的行为对比与选型判据
# 本地模拟：构造「空静默 60s 后 50 个同刻请求」的突发序列，分别过两种限流算法。
# 目的：回答面试高频对比题——输出平滑性与突发容忍为什么不可兼得。


class TokenBucket:
    """令牌桶：允许受控突发（桶里攒多少就放多少）。"""

    def __init__(self, capacity, rate):
        self.cap, self.rate = capacity, rate
        self.tokens, self.last = float(capacity), 0.0

    def admit(self, now):
        self.tokens = min(self.cap, self.tokens + self.rate * max(0.0, now - self.last))
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class LeakyBucket:
    """漏桶：请求先进队列，以恒定速率漏出；队列满则拒绝（输出强制匀速）。"""

    def __init__(self, rate, queue_cap):
        self.rate, self.queue_cap = rate, queue_cap
        self.queue = []
        self.last_out = 0.0

    def admit(self, now):
        if len(self.queue) >= self.queue_cap:
            return False                       # 队列满：拒绝（不会「晚一点放过你」）
        self.queue.append(now)
        return True

    def drain(self, until):
        """按恒定速率输出，返回 [(输出时刻, 原始到达时刻)]，即输出时间线。"""
        out = []
        t = self.last_out
        while self.queue and t <= until:
            t = max(t + 1.0 / self.rate, self.queue[0])   # 下一个输出时刻不早于到达
            if t > until:
                break
            out.append((round(t, 3), self.queue.pop(0)))
        self.last_out = t
        return out


SERIES = [60.0] * 50        # 空静默 60s 后，50 个请求同一时刻到达

# ---------- 1) 令牌桶：前 20 个立即准入，其余直接拒绝 ----------
tb = TokenBucket(capacity=20, rate=5)
tb.tokens, tb.last = 0.0, 0.0
tb_results = [tb.admit(t) for t in SERIES]
tb_admitted = sum(tb_results)
print("== 1) 令牌桶（C=20, r=5）面对 50 个同刻突发 ==")
print(f"  准入 {tb_admitted}/50：前 20 个凭积累的令牌立即放行，后 30 个当场拒绝（429 + Retry-After）")
assert tb_admitted == 20

# ---------- 2) 漏桶：全部入队，按 5/s 匀速漏出 ----------
lb = LeakyBucket(rate=5, queue_cap=100)
lb_results = [lb.admit(t) for t in SERIES]
out = lb.drain(until=80.0)
lb_admitted = sum(lb_results)
print("\n== 2) 漏桶（r=5, 队列 100）面对同一突发 ==")
print(f"  入队 {lb_admitted}/50（无拒绝），但输出被拉长到 {out[-1][0] - 60:.0f}s：")
print("  输出时间线（前 6 个 + 最后 1 个）：")
for t_out, t_in in out[:6]:
    print(f"    到达 t=60.0 -> 输出 t={t_out}")
print(f"    ... 第 50 个 -> 输出 t={out[-1][0]}")
assert lb_admitted == 50 and len(out) == 50

# ---------- 3) 行为对比表 ----------
first_out_latency = out[0][0] - 60.0
print("\n== 3) 行为对比 ==")
print(f"{'维度':<14}{'令牌桶':>22}{'漏桶':>22}")
rows = [
    ("突发容忍", "放行 min(C, r·Δt) 个", "不允许，先进队列"),
    ("输出平滑", "不平滑（可瞬时 20 个）", "严格匀速 5/s"),
    ("首请求延迟", "0s（立即）", f"{first_out_latency:.2f}s（排队）"),
    ("超额行为", "直接拒绝（客户端可见）", "排队延迟（客户端干等）"),
    ("队列风险", "无队列", "队列满才拒绝，尾延迟长"),
]
for r in rows:
    print(f"{r[0]:<14}{r[1]:>22}{r[2]:>22}")

print("\n== 4) 选型判据 ==")
print("  API 网关/下游怕瞬压  -> 令牌桶：早高峰所有人同时提问是正常突发，削平它反而伤体验")
print("  / 下游要求严格匀速   -> 漏桶：如第三方计费接口有硬速率上限，超了要赔钱")
print("  / 客户端可重试       -> 令牌桶 + 429 + Retry-After：拒绝比让用户干等 10s 更诚实")
print("  / 客户端不可重试     -> 漏桶小队列：牺牲尾延迟换成功率，但队列深度要设上限")

print("\n结论：令牌桶用「受控突发」换「即时响应」，漏桶用「输出平滑」换「尾延迟」，两者不可兼得；")
print("读法：1. 令牌桶的突发上限是 min(C, r·Δt)，C 按「下游能吸收的最大瞬时并发」定，r 按「下游可持续吞吐×安全系数」定；2. 漏桶的队列长度就是尾延迟上限（50 个 / 5 每秒 = 10s），队列必须设上限否则内存与耐心一起爆；3. 企业知识库 Agent 的入口限流选令牌桶（ch14 部署篇的网关口径），对第三方接口的出口限流选漏桶；4. 本示例为本地模拟，真实网关（Nginx/Envoy）的限流参数见 ch14。")
