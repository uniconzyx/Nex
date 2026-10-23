# title: 排队模型：10 个副本 TTFT P99 要 3.9 秒，13 个副本才进 800ms
# M/M/c 的 Erlang C：λ=10 req/s，单请求服务时间 0.9s，看副本数怎么影响尾延迟。
# 模型假设泊松到达、指数服务、无优先级；真实推理的服务时间方差更大，尾会更长。
import math

LAM = 10.0          # 到达率 req/s
S = 0.9             # 单请求平均服务时间（prefill + decode 折算）
PREFILL = 0.15      # 首 token 之前的固定计算时间
MU = 1.0 / S
A = LAM / MU        # 提供的负载（erlang）


def erlang_c(c):
    if LAM >= c * MU:
        return 1.0
    term = sum(A ** k / math.factorial(k) for k in range(c))
    last = A ** c / (math.factorial(c) * (1 - LAM / (c * MU)))
    return last / (term + last)


print(f"λ={LAM}/s，服务时间 {S}s，负载 A=λ/μ={A:.1f} erlang")
print(f"理论上至少需要 {math.ceil(A)} 个副本才能稳定（ρ<1）\n")
print(f"{'副本':>4}{'ρ':>7}{'P(排队)':>9}{'平均排队':>10}{'TTFT P50':>10}{'TTFT P99':>10}{'SLO 800ms':>11}")
for c in range(8, 16):
    rho = LAM / (c * MU)
    if rho >= 1:
        print(f"{c:>4}{rho:>7.2f}{1.0:>9.2f}{'∞':>10}{'∞':>10}{'∞':>10}{'FAIL':>11}")
        continue
    pw = erlang_c(c)
    wq = pw / (c * MU - LAM)
    t99 = math.log(pw / 0.01) / (c * MU - LAM) if pw > 0.01 else 0.0
    ttft50 = PREFILL + wq
    ttft99 = PREFILL + t99
    print(f"{c:>4}{rho:>7.2f}{pw:>9.3f}{wq*1000:>9.0f}ms{ttft50*1000:>9.0f}ms"
          f"{ttft99*1000:>9.0f}ms{'OK' if ttft99 <= 0.8 else 'FAIL':>11}")

print("\n为什么 9 个副本不行：ρ=0.99 时利用率看似『充分利用』，")
print("排队时间近似与 1/(1-ρ) 成正比，尾延迟放大的速度远快于利用率下降的速度。")
print("Erlang C 给出 P(排队)=0.67，平均排队 602ms；而 9 个副本时 ρ=1.00，队列根本不稳定。")

print("\nTPOT 是另一条曲线：它由解码阶段决定，基本不随排队变化，但随 batch 上升。")
for batch in (1, 8, 32, 64):
    tpot = 28 * (1 + 0.012 * (batch - 1))     # 经验模型：batch 越大，单步越慢
    print(f"  batch={batch:>3}  TPOT≈{tpot:>5.1f} ms/token  →  100 token 的回答约 {tpot*100/1000:.1f}s")

print("\n读法：TTFT 由『排队 + prefill』决定，是容量问题；TPOT 由『解码 + batch』决定，是调度问题。")
print("扩容只能压 TTFT，压不了 TPOT；想降 TPOT 要减 batch（牺牲吞吐）或用量化/更快的卡。")
print("\n结论：容量规划要分别对 TTFT 和 TPOT 立 SLO。把两者合成一个『端到端 P99』，")
print("会导致你既不知道是排队还是解码慢，也无法判断该加副本还是该减 batch。")
