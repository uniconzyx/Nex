# title: 项目 ROI 与盈亏平衡：真正的杠杆是采纳率，不是模型单价
# 内部知识助手：建设成本 + 月度运营成本 vs 节省工时收益。
# 输出三种采纳率下的盈亏平衡月与 24 个月累计净收益，并做单变量敏感性分析。
USERS = 80               # 目标用户数
HOURS_SAVED = 2.0        # 每人每周节省工时（经验假设）
LOADED_COST = 90         # 含社保/工位的每小时人力成本（元）
WEEKS = 4.33

BUILD = 90000 + 25000    # 3 人月 + 系统集成
MONTHLY_FIXED = 4800     # 模型调用 + 向量库 + 监控
MAINTENANCE = 6000       # 0.2 FTE 维护

def monthly_benefit(adoption):
    return USERS * adoption * HOURS_SAVED * WEEKS * LOADED_COST

print("=" * 70)
print("表 1  单月账本（采纳率 30%）")
print("=" * 70)
b = monthly_benefit(0.30)
print(f"  受益人数      {USERS * 0.30:.0f} / {USERS}")
print(f"  月节省工时    {USERS * 0.30 * HOURS_SAVED * WEEKS:.0f} h")
print(f"  月收益        ¥{b:,.0f}")
print(f"  月运营成本    ¥{MONTHLY_FIXED + MAINTENANCE:,.0f}（模型/存储 {MONTHLY_FIXED} + 维护 {MAINTENANCE}）")
print(f"  月净收益      ¥{b - MONTHLY_FIXED - MAINTENANCE:,.0f}")
print(f"  一次性投入    ¥{BUILD:,.0f}")

print("\n" + "=" * 70)
print("表 2  采纳率敏感性：盈亏平衡点对采纳率的弹性远大于对单价的弹性")
print("=" * 70)
print(f"{'采纳率':>7}{'月净收益':>12}{'回本月数':>10}{'24个月累计':>14}  判定")
for a in (0.10, 0.20, 0.30, 0.45, 0.60):
    net = monthly_benefit(a) - MONTHLY_FIXED - MAINTENANCE
    if net <= 0:
        print(f"{a:>7.0%}{net:>12,.0f}{'永不':>10}{net*24 - BUILD:>14,.0f}  亏损")
        continue
    be = BUILD / net
    cum = net * 24 - BUILD
    print(f"{a:>7.0%}{net:>12,.0f}{be:>10.1f}{cum:>14,.0f}  {'健康' if be <= 12 else '偏慢'}")

print("\n" + "=" * 70)
print("表 3  单变量敏感性（基准：采纳 30%）")
print("=" * 70)
base_net = monthly_benefit(0.30) - MONTHLY_FIXED - MAINTENANCE
cases = [
    ("模型单价 -50%", monthly_benefit(0.30) - MONTHLY_FIXED * 0.5 - MAINTENANCE),
    ("模型单价 +100%", monthly_benefit(0.30) - MONTHLY_FIXED * 2 - MAINTENANCE),
    ("人均节省 +20%", monthly_benefit(0.30) * 1.2 - MONTHLY_FIXED - MAINTENANCE),
    ("采纳率 -10pp", monthly_benefit(0.20) - MONTHLY_FIXED - MAINTENANCE),
    ("维护人力 +50%", monthly_benefit(0.30) - MONTHLY_FIXED - MAINTENANCE * 1.5),
]
for name, net in cases:
    delta = (net - base_net) / base_net
    print(f"  {name:<14} 月净 {net:>9,.0f}  ({delta:+.0%})")

print(f"\n结论：模型/存储成本只占月支出的 {MONTHLY_FIXED/(MONTHLY_FIXED+MAINTENANCE):.0%}，"
      f"而采纳率从 30% 掉到 20% 就让回本期从 {BUILD/base_net:.1f} 个月拉长到 "
      f"{BUILD/(monthly_benefit(0.20)-MONTHLY_FIXED-MAINTENANCE):.1f} 个月。")
print("读法：ROI 估算先把「有多少人真的会用」写成可验证指标（周活/人均调用次数），")
print("      再谈单价；否则算出来的正收益只是电子表格里的正收益。")
