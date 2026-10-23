# title: 免费配额与转化漏斗：LTV/CAC 与回收期测算
# 数值实验（示例测算）：自下而上产品的免费→付费漏斗与单位经济。

import numpy as np

DAU = 10000            # 日活（示例测算）
TOK_COST = 0.030       # 单任务成本 ¥（token+卡时+向量库，示例测算）
P_SUB = 49.0           # 订阅价 ¥/月（示例测算）
CAC = 35.0             # 单用户获客成本 ¥（示例测算）
CHURN = 0.08           # 月流失率（示例测算）
PAID_DAILY_TASKS = 8   # 付费用户日均任务数（经验判断）
FREE_ACTIVE_DAYS = 30  # 免费用户月活跃天数（经验判断）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def conv_of(quota):
    """转化率随配额上升但边际饱和（经验判断的教学曲线，真实项目用自己的漏斗拟合）"""
    return 0.08 * (1 - np.exp(-quota / 5))


def ltv(price, churn, cogs=0.0):
    """订阅 LTV = 月毛利 / 月流失率（离散口径）"""
    return (price - cogs) / churn


COGS_PAID = PAID_DAILY_TASKS * 30 * TOK_COST      # 付费用户月任务成本
LTV_PAID = ltv(P_SUB, CHURN, cogs=COGS_PAID)

print("== 漏斗账本（单日，转化率 3%，示例测算） ==")
CONV = 0.03
free_users, paid_users = DAU * (1 - CONV), DAU * CONV
free_tasks = free_users * 5
print(f"日活 {DAU:,}：免费 {free_users:,.0f} 人 / 付费 {paid_users:,.0f} 人")
print(f"免费配额成本 = {free_tasks:,.0f} 任务 × ¥{TOK_COST} = ¥{free_tasks*TOK_COST:,.0f}/日")
print(f"付费订阅收入 = {paid_users:,.0f} × ¥{P_SUB} = ¥{paid_users*P_SUB:,.0f}/日")

print("\n== 单位经济（月度口径，示例测算） ==")
print(f"付费用户 LTV = ¥{LTV_PAID:,.0f}（月流失 {CHURN:.0%}，含月任务成本 ¥{COGS_PAID:.1f}）")
print(f"CAC = ¥{CAC:.0f} → LTV/CAC = {LTV_PAID/CAC:.1f}，"
      f"回收期 = {CAC/(P_SUB - COGS_PAID):.1f} 个月")

print("\n== 免费配额的成本-转化权衡（月新增 1000 人，示例测算） ==")
print(f"{pad('日配额', 8)}{'免费成本¥/月':>13}{'转化率':>9}{'LTV/CAC':>10}")
rows = {}
for quota in (3, 5, 8, 12, 20):
    conv = conv_of(quota)
    free_cost = (1 - conv) * 1000 * quota * FREE_ACTIVE_DAYS * TOK_COST
    ratio = (conv * LTV_PAID) / (CAC + free_cost / 1000)
    rows[quota] = ratio
    print(f"{pad(str(quota), 8)}{free_cost:>13,.0f}{conv:>9.1%}{ratio:>10.2f}")

best_quota = max(rows, key=rows.get)
print(f"\nLTV/CAC 最优日配额 ≈ {best_quota} 次 —— 配额不是越大越好，免费成本吃掉的转化收益会反超")

print("\n结论：免费配额是获客投资不是慈善，最优配额由「边际转化收益 = 边际免费成本」决定，LTV/CAC 与回收期是唯二裁判，")
print("读法：1. LTV=月毛利/月流失率，月流失 8% 时订阅 LTV 约为 12.5 个月毛利，CAC 回收期=CAC/月毛利；2. 免费用户的 token 成本按「配额×活跃天数」实打实发生，转化率却随配额边际饱和——表中 20 次配额的 LTV/CAC 已低于 12 次；3. LTV/CAC<1 的增长是失血，>3 才值得加投（经验判断）；4. 转化曲线为教学假设（示例测算），真实项目必须用自己漏斗的分段数据拟合。")
