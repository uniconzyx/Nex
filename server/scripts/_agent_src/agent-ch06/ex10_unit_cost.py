# title: 单 token 成本账本：一张卡月租 3000 元、吞吐 800 tok/s，自托管边际成本 1.44 元/百万 token
# 固定成本（卡租）被「有效吞吐 × 利用率」摊薄，利用率是成本的第一杠杆。
# 数字为工程估算口径，月租与云端单价取经验近似值，便于演示账本结构。
GPU_MONTH = 3000.0        # 单卡月租（元，A100 级别的协商价，经验判断）
THROUGHPUT = 800.0        # 单卡平均有效吞吐（tok/s，含批处理与碎片折扣）
CLOUD_PER_M = 14.0        # 云端 API 单价（元 / 百万 token，取公开报价的近似值）
SEC_MONTH = 30 * 24 * 3600

# 1) 边际成本：满负载下每百万 token 的成本
tok_month = THROUGHPUT * SEC_MONTH
cost_per_m = GPU_MONTH * 1e6 / tok_month
print(f"单卡月租 ¥{GPU_MONTH:.0f}，有效吞吐 {THROUGHPUT:.0f} tok/s")
print(f"满负载月产出 {tok_month/1e9:.2f} B token，边际成本 {cost_per_m:.2f} 元/百万 token")

# 2) 利用率扫描：利用率越低，单位成本越高（固定成本摊到更少 token）
print(f"\n{'利用率':>8}{'有效吞吐(tok/s)':>16}{'月产出(B)':>12}{'成本(元/百万)':>14}")
for u in (0.1, 0.25, 0.5, 0.75, 1.0):
    tp = THROUGHPUT * u
    tm = tp * SEC_MONTH
    cpm = GPU_MONTH * 1e6 / tm
    print(f"{u*100:>7.0f}%{tp:>15.0f}{tm/1e9:>11.2f}{cpm:>14.2f}")

# 3) 与云端 API 打平：自托管需要的最低月 token 量
breakeven_tok = GPU_MONTH / (CLOUD_PER_M / 1e6)
print(f"\n云端单价 {CLOUD_PER_M:.0f} 元/百万 token；自托管打平点 = {GPU_MONTH:.0f} / "
      f"{CLOUD_PER_M/1e6:.1e} ≈ {breakeven_tok/1e6:.0f} M token/月（约 {breakeven_tok/1e9:.2f} B）")

# 4) 单请求成本：不同输入/输出长度
def req_cost(nin, nout, cpm):
    return (nin + nout) * cpm / 1e6

print("\n满负载下单个请求成本：")
print(f"{'输入':>8}{'输出':>8}{'成本(元)':>12}")
for nin, nout in ((1000, 2000), (500, 500), (200, 800)):
    c = req_cost(nin, nout, cost_per_m)
    print(f"{nin:>8}{nout:>8}{c:>12.4f}")

print("\n读法：固定成本（卡租）被『有效吞吐 × 利用率』摊薄，所以利用率是成本的第一杠杆；")
print("云端按 token 计费没有闲置惩罚，低流量时反而更便宜——打平点以下别自建。")

print("\n结论：自托管决策看两个数——当前月 token 量是否过打平点、以及平均利用率能否 >50%；")
print("两者都满足才谈得上省钱，否则先走云端 API，等流量稳定再迁移。")
