# title: 复现差异归因表：单因素 Δ、交互残差与止损判定
# 工具类：输入「原文指标 + 各因素的单因素实验 Δ + 复现预算」，输出归因表、
# 残差告警、修复优先级与止损判定。所有数值为教学构造的账本条目。

REPORTED = 94.5          # 论文报告指标
MINE = 91.2              # 自己完整配置的复现结果
NOISE_BAND = 1.0         # 自己复现的噪声带（多跑种子估的 2σ，个点）
BUDGET_H = 6.0           # 复现总工时预算（小时）
ATTRIBUTION_CAP = 0.5    # 归因阶段工时上限 = 预算的 50%


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


# (层, 因素, 单因素实验的 Δ(个点), 修复成本(小时))
FACTORS = [
    ("评测口径", "micro/macro 平均口径不同", -0.3, 0.5),
    ("数据",     "测试集划分种子不同",       -0.7, 1.0),
    ("数据",     "训练集缩样到 1/10",        -1.5, 2.0),
    ("实现",     "初始化尺度不同",           -0.4, 1.5),
    ("实现",     "未使用 warmup",            -0.2, 0.5),
]


def attribute(reported, mine, factors):
    """返回 (总差, 单因素合计, 残差=交互效应)。"""
    total = mine - reported
    summed = sum(d for _, _, d, _ in factors)
    return total, summed, total - summed


def judge(total, factors, residual):
    biggest = max(abs(d) for _, _, d, _ in factors)
    if abs(residual) > 0.3 * abs(total) and abs(residual) > biggest:
        return "存在交互效应：禁止单因素解读，需 2x2 网格隔离"
    return "无显著交互：可按单因素排序修复"


total, summed, residual = attribute(REPORTED, MINE, FACTORS)
verdict = judge(total, FACTORS, residual)

print("== 1) 差异归因表（单因素实验：从原文配置出发每次只改一个）==")
print(f"{pad('层', 6)}{pad('因素', 24)}{'Δ(个点)':>8}{'修复成本(h)':>10}{'性价比':>8}")
for layer, name, d, cost in sorted(FACTORS, key=lambda f: -abs(f[2])):
    ratio = abs(d) / cost
    print(f"{pad(layer, 6)}{pad(name, 24)}{d:>+8.1f}{cost:>10.1f}{ratio:>8.2f}")

print(f"\n== 2) 分解与残差 ==")
print(f"总差 = {total:+.1f} 个点；单因素合计 = {summed:+.1f}；残差（交互）= {residual:+.1f}")
print(f"判定：{verdict}")
print(f"噪声带 = ±{NOISE_BAND:.1f} 个点 -> 差距 {'在' if abs(total) <= NOISE_BAND else '超出'}"
      f"噪声带，{'无需追查' if abs(total) <= NOISE_BAND else '值得追查'}")

print("\n== 3) 修复优先级（幅度降序，同幅度按成本升序）==")
for i, (layer, name, d, cost) in enumerate(
        sorted(FACTORS, key=lambda f: (-abs(f[2]), f[3])), 1):
    print(f"  {i}. [{layer}] {name}（Δ={d:+.1f}，成本 {cost}h，性价比 {abs(d)/cost:.2f} 点/h）")

print("\n== 4) 止损判定 ==")
cap_h = BUDGET_H * ATTRIBUTION_CAP
cheap_fix = sum(c for _, _, _, c in FACTORS if c <= 1.0)
print(f"归因工时上限 = {BUDGET_H}h x {ATTRIBUTION_CAP:.0%} = {cap_h:.1f}h")
print(f"若已耗归因工时 > {cap_h:.1f}h 且差距仍 > 2 个点 -> 止损，降级为「部分复现」")
print(f"低成本修复（<=1h）合计 {cheap_fix:.1f}h，可覆盖 Δ 合计 "
      f"{sum(d for _, _, d, c in FACTORS if c <= 1.0):+.1f} 个点")
print(f"剩余差距 = {total - summed - residual:+.1f} 个点（= 总差 - 单因素合计 - 残差，校验应为 0.0）")

print("\n结论：归因表把「差几个点」拆成可行动的修复项，残差负责抓住单因素解释不了的交互效应，")
print("读法：1. 单因素 Δ 必须从原文配置各自独立测得，不能用「累计替换」的每步差——那会望远镜相消、残差恒为 0；2. 修复优先级按「幅度降序 + 同幅度成本升序」，性价比 = |Δ|/成本，先修又大又便宜的；3. 残差超总差 30% 且超最大单因素时，任何单因素解释都是过度归因，正确动作是 2x2 网格；4. 止损线是归因工时超预算 50% 且差距仍 > 2 个点——已验证部分 + 存疑清单本身就是交付物。")
