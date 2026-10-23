# title: 单位经济模型：ARPU、单次成本与盈亏平衡用量
# 按 29 元/月订阅、4% 月流失、120 元获客成本，算毛利、LTV/CAC 与保本用量。
# 这不是财务预测，是一张「这个价格能不能覆盖这个用量」的账。

ARPU = 29.0
CHANNEL_FEE = 0.02      # 支付通道 2%
CHURN = 0.04
CAC = 120.0
FIXED_PER_USER = 2.0    # 基础设施/客服摊销（元/月）
COST_PER_REQ = 0.006    # 模型+检索的单次变动成本
FREE_QUOTA = 100


def economics(reqs):
    revenue = ARPU * (1 - CHANNEL_FEE)
    variable = max(0, reqs - FREE_QUOTA) * COST_PER_REQ + FREE_QUOTA * COST_PER_REQ * 0.3
    contribution = revenue - FIXED_PER_USER - variable
    margin = contribution / ARPU
    ltv = contribution / CHURN
    return revenue, variable, contribution, margin, ltv, ltv / CAC


print(f"ARPU {ARPU} 元/月，通道费 {CHANNEL_FEE:.0%}，固定摊销 {FIXED_PER_USER} 元/月，")
print(f"单次变动成本 {COST_PER_REQ} 元，免费额度 {FREE_QUOTA} 次（按 30% 成本计）\n")
print(f"{'月用量':>6}{'变动成本':>9}{'贡献毛利':>9}{'毛利率':>8}{'LTV':>8}{'LTV/CAC':>9}  判定")
for reqs in (100, 300, 600, 1000, 2000, 4000, 5000):
    revenue, variable, contribution, margin, ltv, ratio = economics(reqs)
    verdict = "健康" if ratio >= 3 else ("临界" if ratio >= 1 else "亏损")
    print(f"{reqs:>6}{variable:>9.2f}{contribution:>9.2f}{margin:>8.1%}{ltv:>8.1f}{ratio:>9.1f}  {verdict}")

# 保本用量：贡献毛利 = 0
revenue = ARPU * (1 - CHANNEL_FEE)
budget = revenue - FIXED_PER_USER
free_cost = FREE_QUOTA * COST_PER_REQ * 0.3
break_even = FREE_QUOTA + (budget - free_cost) / COST_PER_REQ
print(f"\n保本用量：约 {break_even:,.0f} 次/月（贡献毛利为 0 的边界）")
print(f"当前假设用量 300 次/月时，毛利率 {economics(300)[3]:.0%}，LTV/CAC = {economics(300)[5]:.1f}")

print("\n读法：用量从 300 涨到 2000，毛利率从 86% 掉到 51%——单次成本不高，乘以用量就很可观；")
print("      真正危险的是免费额度：100 次免费已经吃掉约 0.18 元，占收入 0.6%，可控。")
print("结论：单位经济成立的前提是「客单价 × 付费率 > 单次成本 × 用量 + 固定摊销」；")
print("      如果产品是低客单价（如 9.9 元），同样的用量结构会直接击穿毛利，必须改成按量计费。")
