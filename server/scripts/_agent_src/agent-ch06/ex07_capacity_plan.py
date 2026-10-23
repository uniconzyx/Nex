# title: 容量规划：30 rps 的峰值要 37 个副本，其中 10 个是为 P99 SLO 与 N+1 付的
# 从「稳定」到「达标」再到「可运维」三步推副本数，每一步都给出拒绝它的理由。
# 模型沿用 M/M/c；真实服务时间方差更大，所以最后再乘 1.3 的安全系数。
import math

SLO_TTFT_P99 = 0.8      # 秒
SLO_TPOT_P99 = 0.05     # 秒/token
S = 0.9                 # 单副本处理一个请求的平均时间
PREFILL = 0.15
PEAK = 30.0             # 峰值到达率 req/s
HEADROOM = 1.3          # 突发与流量增长的安全系数
GPU_HOURLY = 12.0       # 元/卡时（A100 级别，经验价）


def erlang_c(lam, c, mu):
    a = lam / mu
    if lam >= c * mu:
        return 1.0
    term = sum(a ** k / math.factorial(k) for k in range(c))
    last = a ** c / (math.factorial(c) * (1 - lam / (c * mu)))
    return last / (term + last)


def p99_ttft(lam, c, mu, prefill):
    if lam >= c * mu:
        return float("inf")
    pw = erlang_c(lam, c, mu)
    if pw <= 0.01:
        return prefill
    return prefill + math.log(pw / 0.01) / (c * mu - lam)


mu = 1.0 / S
stable = math.ceil(PEAK / mu)
print(f"峰值 {PEAK} rps，单副本 {mu:.2f} req/s → 稳定下限 {stable} 个副本（ρ<1）")

rows = []
for c in range(stable, stable + 20):
    rho = PEAK / (c * mu)
    t99 = p99_ttft(PEAK, c, mu, PREFILL)
    rows.append((c, rho, t99, t99 <= SLO_TTFT_P99))

meet = next((r for r in rows if r[3]), None)
print(f"\n{'副本':>4}{'ρ':>7}{'TTFT P99':>10}{'达标':>6}{'目标负载(含1.3x)':>16}")
for c, rho, t99, ok in rows[:14]:
    scaled = PEAK * HEADROOM / (c * mu)
    txt = "∞" if t99 == float("inf") else f"{t99*1000:.0f}ms"
    print(f"{c:>4}{rho:>7.2f}{txt:>10}{'OK' if ok else '-':>6}{scaled:>15.2f}")

print(f"\n第 1 步（稳定性）：{stable} 个副本，ρ=1.00，队列不稳定，不能上线。")
print(f"第 2 步（SLO）：{meet[0]} 个副本，P99 {meet[2]*1000:.0f}ms 刚好压线；")
print("  但这是在『平均 30 rps』下算的，没有余量，一次流量尖峰就破线。")
need = math.ceil(PEAK * HEADROOM / mu)
final = max(meet[0], need) + 1
print(f"第 3 步（可运维）：{PEAK}×{HEADROOM} = {PEAK*HEADROOM:.0f} rps 需要 {need} 个副本，"
      f"再加 1 个冗余（N+1）= {final} 个。")

print(f"\n其中 {final - stable} 个副本是为了 SLO 与冗余付的，占总数的 {(final-stable)/final:.0%}。")
print(f"成本：{final} 卡 × ¥{GPU_HOURLY}/h = ¥{final*GPU_HOURLY:.0f}/h ≈ ¥{final*GPU_HOURLY*24*30/10000:.1f} 万/月。")

print("\n同一套算法换流量档位（目标 P99 800ms，含 1.3x 与 N+1）：")
print(f"{'峰值 rps':>9}{'稳定下限':>9}{'SLO 下限':>9}{'最终副本':>9}{'月成本(万元)':>13}")
for peak in (5, 10, 30, 60, 120):
    st = math.ceil(peak / mu)
    slo = next((c for c in range(st, st + 80) if p99_ttft(peak, c, mu, PREFILL) <= SLO_TTFT_P99), None)
    fin = max(slo, math.ceil(peak * HEADROOM / mu)) + 1
    print(f"{peak:>9}{st:>9}{slo:>9}{fin:>9}{fin*GPU_HOURLY*24*30/10000:>13.1f}")

print("\n读法：副本数不是线性外推——SLO 下限比稳定下限高得多，因为要压的是 P99 不是均值。")
print("这也是为什么『压测 QPS 达标』不等于『线上能扛』：压测通常只看均值吞吐，不看尾延迟。")
print("\n结论：容量规划的交付物必须包含四个数：峰值 rps、单副本服务能力、P99 目标、冗余策略。")
print("少任何一个，算出来的副本数都只是猜测。另外别忘了 KV Cache 对并发的约束——")
print("副本数够但单卡塞不下对应并发时，瓶颈会从队列转移到显存。")
