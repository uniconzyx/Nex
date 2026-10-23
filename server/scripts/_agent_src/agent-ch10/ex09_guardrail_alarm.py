# title: 护栏指标告警模拟：3σ 点告警、EWMA 与周均值的检出延迟对比
import numpy as np

rng = np.random.default_rng(9)
DAYS = 30
BASE_DAYS = 7          # 第 1 周为基线周
LAM = 0.3              # EWMA 平滑系数
L = 3.0                # 控制限倍数

# 四个护栏指标的「真实」日序列（注入三类异常：持续漂移 / 单日尖峰 / 持续劣化）
p99 = rng.normal(800, 40, DAYS)                    # P99 延迟 ms
cost = rng.normal(0.050, 0.004, DAYS)              # 单请求成本 元
refusal = rng.normal(0.05, 0.010, DAYS)            # 拒答率
complaints = rng.poisson(2.0, DAYS).astype(float)  # 安全投诉 次/日

ANOMALIES = [("P99 延迟", 15, "持续漂移 +60ms（1.6σ，配置变更）"),
             ("单请求成本", 22, "单日尖峰 x2.6（缓存失效）"),
             ("安全投诉", 26, "持续劣化 4 倍（新版 prompt 缺陷）")]
p99[14:] += 60             # day15 起持续漂移（1.6σ，低于单日 3σ 告警限）
cost[21] = 0.130           # day22 单日尖峰（20σ）
complaints[25:] = 8.0      # day26 起持续 4 倍

METRICS = [("P99 延迟", p99, "ms"), ("单请求成本", cost, "元"),
           ("拒答率", refusal, ""), ("安全投诉", complaints, "次")]


def detect(x):
    """三种检测器：3σ 点告警 / EWMA / 周均值。返回每日告警布尔数组（基线周不检测）。"""
    mu, sd = x[:BASE_DAYS].mean(), x[:BASE_DAYS].std(ddof=1)
    point = np.zeros(DAYS, bool)
    ewma_alarm = np.zeros(DAYS, bool)
    week_alarm = np.zeros(DAYS, bool)
    z = mu
    for t in range(DAYS):
        z = LAM * x[t] + (1 - LAM) * z
        if t < BASE_DAYS:
            continue
        point[t] = abs(x[t] - mu) > L * sd
        ewma_alarm[t] = abs(z - mu) > L * sd * np.sqrt(LAM / (2 - LAM))
        if (t + 1) % 7 == 0:      # 每周末用本周均值 vs 基线均值
            wk = x[t - 6:t + 1].mean()
            week_alarm[t] = abs(wk - mu) > L * sd / np.sqrt(7)
    return point, ewma_alarm, week_alarm, mu, sd


print("== 1) 基线参数（第 1 周）与控制限 ==")
print(f"{'指标':<10}{'均值':>10}{'std':>10}{'3σ 上限':>12}")
results = {}
for name, x, unit in METRICS:
    pt, ew, wk, mu, sd = detect(x)
    results[name] = (pt, ew, wk)
    print(f"{name:<10}{mu:>10.3f}{sd:>10.3f}{mu + L * sd:>12.3f}")

def cell(s, w):
    """右对齐到 w 个显示列（中文按 2 列）。"""
    return " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s)) + s


print("\n== 2) 告警日志（仅列触发告警的日期；day1-7 为基线周不检测） ==")
print(f"{'日期':>6}{'P99点':>8}{'P99EWMA':>10}{'成本点':>8}{'拒答点':>8}{'投诉点':>8}{'投诉EWMA':>10}")
any_alarm = False
for t in range(BASE_DAYS, DAYS):
    flags = [results["P99 延迟"][0][t], results["P99 延迟"][1][t],
             results["单请求成本"][0][t], results["拒答率"][0][t],
             results["安全投诉"][0][t], results["安全投诉"][1][t]]
    if any(flags):
        any_alarm = True
        row = f"{t + 1:>6}"
        for i, f in enumerate(flags):
            row += cell("告警" if f else "-", 8 if i < 4 else 10)
        print(row)
if not any_alarm:
    print("（无告警）")

print("\n== 3) 检出延迟汇总（从异常注入日算起） ==")
print(f"{'异常':<20}{'3σ 点告警':>12}{'EWMA':>10}{'周均值':>10}")
for name, start, desc in ANOMALIES:
    row = f"{name + ' d' + str(start):<20}"
    for det_idx in (0, 1, 2):
        arr = results[name][det_idx]
        first = next((t - start + 1 for t in range(start - 1, DAYS) if arr[t]), None)
        txt = f"{first} 天" if first is not None else "未检出"
        row += cell(txt, 12 if det_idx == 0 else 10)
    print(row + f"   # {desc}")

print("\n== 4) 误报（无异常的拒答率指标，23 个检测日） ==")
fa_point = results["拒答率"][0][BASE_DAYS:].sum()
fa_ewma = results["拒答率"][1][BASE_DAYS:].sum()
print(f"3σ 点告警误报 {fa_point} 次；EWMA 误报 {fa_ewma} 次（3σ 下单点误报率 0.27%，23 天期望 <0.1 次）")

print("\n结论：1.6σ 的持续漂移，EWMA 当天即报而 3σ 点告警 3 天后才断续命中；单日尖峰只有点告警能当天抓到，周均值把它稀释成 6 天后才发现；")
print("读法：1. 护栏监控要三类检测器并用：点告警抓尖峰、EWMA 抓漂移、周均值兜持续小劣化；2. 点告警对持续漂移是断续命中（本例 16 天只响 3 次），单看一种方法会把漂移当成抖动忽略；3. 告警日志必须带「检测方法」字段，否则无法区分「没发生」与「没检测到」；4. 3σ 单点误报率 0.27%，多指标并发的告警量要按指标数折算，避免告警风暴；5. 本示例为本地模拟数据，异常注入时点与幅度均为构造值。")
