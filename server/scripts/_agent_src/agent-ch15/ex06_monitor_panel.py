# title: 监控面板四指标：请求量、P95 延迟、错误率与单次成本的按天汇总
# 标准库 + numpy：固定种子模拟 7 天请求流（含一次错误率突发），四指标按天报表与告警标记。


import numpy as np


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


rng = np.random.default_rng(7)  # 固定种子：7 天流量可复现

DAYS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
CAPACITY = 1000          # 单副本日吞吐能力（请求/天），教学假设
P95_BASELINE_FACTOR = 2  # P95 超过基线 2 倍告警（阈值需按实测标定）
ERR_RATE_ALERT = 0.02    # 错误率超过 2% 持续告警
VOL_ALERT = 0.70         # 请求量超过容量 70% 告警

# 每日请求量：基准 700 + 噪声，D6/D7 周末回落；D5 埋一个错误率突发（p=0.08，重试致延迟 x4）
base_vol = np.array([720, 760, 700, 810, 950, 540, 580], dtype=int)
err_p = np.array([0.008, 0.008, 0.008, 0.008, 0.08, 0.008, 0.008])
# 每日单请求成本：基准 0.0042 + 噪声（D5 上下文变长略涨），单位：元
cost_base = np.array([0.0042, 0.0043, 0.0041, 0.0044, 0.0052, 0.0042, 0.0041])

daily = []
for d in range(7):
    n = base_vol[d]
    # 延迟：对数正态长尾（中位 0.8s，sigma 0.55），单位秒
    lat = rng.lognormal(mean=np.log(0.8), sigma=0.55, size=n)
    # 错误：伯努利注入；出错请求走重试，D5 突发日延迟 x6、平日 x2
    err = rng.random(n) < err_p[d]
    lat = np.where(err, lat * (6.0 if d == 4 else 2.0), lat)
    p95 = float(np.percentile(lat, 95))
    cost = cost_base[d] * (1 + rng.normal(0, 0.08, size=n))
    daily.append({"day": DAYS[d], "n": n, "p95": p95,
                  "err_rate": float(err.mean()), "avg_cost": float(cost.mean()),
                  "daily_cost": float(cost.sum())})

p95_base = daily[0]["p95"]

print("== 1) 四指标按天报表（容量 %d，P95 基线 D1=%.2fs） ==" % (CAPACITY, p95_base))
print("  " + pad("天", 5) + pad("请求量", 8) + pad("P95(s)", 9) + pad("错误率", 9)
      + pad("单次成本(元)", 14) + pad("日成本(元)", 12) + "告警")
for r in daily:
    alerts = []
    if r["p95"] > p95_base * P95_BASELINE_FACTOR:
        alerts.append("P95")
    if r["err_rate"] > ERR_RATE_ALERT:
        alerts.append("ERR")
    if r["n"] > CAPACITY * VOL_ALERT:
        alerts.append("VOL")
    print("  " + pad(r["day"], 5) + pad(str(r["n"]), 8) + pad(f"{r['p95']:.2f}", 9)
          + pad(f"{r['err_rate']:.1%}", 9) + pad(f"{r['avg_cost']:.4f}", 14)
          + pad(f"{r['daily_cost']:.2f}", 12) + (",".join(alerts) if alerts else "-"))

print("\n== 2) 请求量 ASCII 条形（# = 50 请求） ==")
for r in daily:
    print(f"  {r['day']} |{'#' * (r['n'] // 50):<20}| {r['n']}")

first_alert = next((r["day"] for r in daily if r["err_rate"] > ERR_RATE_ALERT), None)
p95_alert_day = next((r["day"] for r in daily if r["p95"] > p95_base * P95_BASELINE_FACTOR), None)
burst = daily[4]
print("\n== 3) 故障时序：哪个指标先动 ==")
print(f"  错误率首警: {first_alert}（突发日错误率 {burst['err_rate']:.1%}，质量信号最先亮）")
print(f"  P95 首警:   {p95_alert_day}（同一天：出错请求重试致延迟 x6，P95 被带高）")
print("  解读：同源故障先体现在错误率，P95 是跟随指标——先看错误类型分布，再查延迟")

week_cost = sum(r["daily_cost"] for r in daily)
week_req = sum(r["n"] for r in daily)
print(f"\n== 4) 周汇总 ==")
print(f"  周请求量 {week_req}，周成本 ¥{week_cost:.2f}，周均单次成本 ¥{week_cost / week_req:.4f}")
print(f"  容量水位：峰值 {max(r['n'] for r in daily)}/{CAPACITY} = "
      f"{max(r['n'] for r in daily) / CAPACITY:.0%}（>70% 触发放量/限流评估）")

print("\n结论：四指标（请求量/P95/错误率/单次成本）按天上图，阈值来自容量、基线与错误成本三本账；")
print("读法：1. P95 用最近邻分位数不用平均值——投诉来自长尾；2. 错误率是先行指标、P95 是跟随指标，故障时先看错误类型分布；3. 单次成本按天盯着，它随上下文长度与模型选择漂移，是月底账单的先行指标；4. 本示例流量为 numpy 固定种子模拟，真实接入见 ch03 客户端封装的请求日志。")
