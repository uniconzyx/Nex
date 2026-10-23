# title: 成本看板与预算告警：burn rate、两级阈值与降级链的止损模拟
# 标准库 + numpy：固定种子模拟单日 24 小时成本流（晚高峰尖峰），告警状态机 + 阈值敏感性扫描。


import numpy as np


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


rng = np.random.default_rng(11)

BUDGET = 30.0            # 日预算（元），教学假设
WARN1, WARN2, BREAK = 0.50, 0.80, 0.90   # 两级预警 + 熔断线
DOWNGRADE = [(1.0, "原价模型"), (0.4, "降级:便宜模型"), (0.15, "降级:缓存直答"), (0.0, "熔断:拒绝新请求")]

# 单日 24 小时成本：基准 1.0 元/小时 + 噪声；19-22 晚高峰 x6（公开 demo 的典型形态）
hours = np.arange(24)
base_hourly = np.clip(1.0 + rng.normal(0, 0.15, size=24), 0.2, None)
hourly = base_hourly.copy()
hourly[19:23] *= 6.0

print("== 1) 单日成本流与告警状态机（预算 ¥%.0f） ==" % BUDGET)
print("  " + pad("时", 4) + pad("小时成本", 10) + pad("累计", 8) + pad("水位", 8) + "状态/动作")
cum, level, events = 0.0, 0, []
for h in range(24):
    cum += hourly[h] * DOWNGRADE[level][0]
    pct = cum / BUDGET
    state = "OK"
    if level < 3 and pct >= BREAK:
        level, state = 3, "90%熔断 -> 拒绝新请求(保留核心只读)"
        events.append((h, state))
    elif level < 2 and pct >= WARN2:
        level, state = 2, "80%警告 -> 降级:缓存直答"
        events.append((h, state))
    elif level < 1 and pct >= WARN1:
        level, state = 1, "50%预警 -> 降级:便宜模型"
        events.append((h, state))
    if h in (0, 9, 12, 14, 15, 18, 19, 20, 21, 22, 23):
        print("  " + pad(f"{h:02d}", 4) + pad(f"{hourly[h] * DOWNGRADE[level][0]:.2f}", 10)
              + pad(f"{cum:.2f}", 8) + pad(f"{pct:.0%}", 8)
              + (" <== " + state if state != "OK" else ""))
print("  ...（其余小时略）")
for h, s in events:
    print(f"  事件 @{h:02d} 时: {s}")
no_break_total = float(hourly.sum())
normal_total = float(base_hourly.sum())
print(f"\n  正常日（无尖峰）参照: ¥{normal_total:.2f}")
print(f"  无熔断参照: ¥{no_break_total:.2f}（超支 ¥{max(0, no_break_total - BUDGET):.2f}）")
print(f"  有熔断终值: ¥{cum:.2f}（{'预算内' if cum <= BUDGET else '仍超支'}，降级链生效）")

print("\n== 2) 阈值敏感性：熔断线画在哪，决定「惊呆」还是「狼来了」 ==")
print("  " + pad("熔断线", 8) + pad("动作前已花", 12) + pad("当日终值", 10) + pad("超支(元)", 10) + "评价")


def simulate(break_at):
    c, lv = 0.0, 0
    for h in range(24):
        c += hourly[h] * DOWNGRADE[lv][0]
        if c / BUDGET >= break_at and lv < 3:
            lv = 3
    return c


for t in (0.40, 0.50, 0.70, 0.80, 0.90, 0.95):
    c = simulate(t)
    trig_h = next((h for h in range(24)
                   if sum(hourly[:h + 1]) / BUDGET >= t), None)
    over = max(0.0, c - BUDGET)
    spent_before = t * BUDGET
    if t <= 0.50:
        note = f"过低:正常日(¥{normal_total:.0f})也触发,告警疲劳"
    elif t <= 0.80:
        note = "达标:预算内且留了止损余量"
    else:
        note = f"过高:动作前已花 ¥{spent_before:.1f}，尖峰一波可带走剩余 ¥{BUDGET - spent_before:.1f}"
    print("  " + pad(f"{t:.0%}", 8) + pad(f"¥{spent_before:.1f}({trig_h:02d}时)" if trig_h is not None else "未触发", 12)
          + pad(f"{c:.2f}", 10) + pad(f"{over:.2f}", 10) + note)

print("\n== 3) 降级链每级的止损力（尖峰小时单价系数） ==")
print("  " + pad("级别", 4) + pad("系数", 8) + pad("动作", 22) + "尖峰小时花费(元)")
for i, (k, name) in enumerate(DOWNGRADE):
    print("  " + pad(f"L{i}", 4) + pad(f"x{k}", 8) + pad(name, 22) + f"{hourly[20] * k:.2f}")
print("  降级不是关服务：L1/L2 保留核心功能（便宜模型/缓存答），L3 才拒新请求")
print(f"  burn rate 口径：当前累计 / 已过小时数 = ¥{cum / 24:.2f}/时；")
print(f"  耗尽日预测 = (预算 - 累计) / burn rate（用于「按这个速度还能撑几天」）")

print("\n结论：预算告警的价值在阈值与降级链的预演——50% 预警给 review 时间，80% 该动手降级，90% 只是兜底；")
print("读法：1. 动作线越低越安全（扫描显示 70~80% 预算内且有余量，>=90% 尖峰一波就超支）；但 <=50% 正常日也触发，告警疲劳后没人看；2. 降级链按「贵模型->便宜模型->缓存直答->拒新请求」逐级收，核心功能最后才断；3. burn rate 与耗尽日预测让「月底账单惊吓」变成当天可见；4. 本示例成本流为 numpy 固定种子模拟，真实账本按 token 单价与请求日志累计。")
