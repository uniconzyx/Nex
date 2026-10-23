# title: 修复轮的成本与成功率：第 3 轮之后，每多救一单都在亏时间
# 初始合法率 70%；每轮修复能救回剩余失败的 55%，但一次修复要 1.4 倍 token、2.5 秒。
# 目标函数不是「成功率最高」，而是「含人工兜底的期望总成本最低 + P99 延迟可接受」。
P0, FIX_RATE = 0.70, 0.55
REPAIR_COST, BASE_COST = 1.4, 1.0
HUMAN_COST = 8.0          # 转人工的期望成本（含等待与上下文重建）
REPAIR_SEC = 2.5
BASE_SEC, SLO_SEC = 1.8, 10.0

print("=" * 86)
print("表 1  修复轮数 r 的成功率、成本与延迟（成本以首次调用为 1 个单位）")
print("=" * 86)
print(f"{'r':>3}{'成功率':>9}{'期望token成本':>15}{'人工率':>8}{'期望总成本':>12}{'每成功成本':>12}{'P99延迟':>10}")
rows = []
for r in range(6):
    success = 1 - (1 - P0) * (1 - FIX_RATE) ** r
    # 第 i 次修复只在「此前仍失败」时发生
    repair = sum(REPAIR_COST * (1 - P0) * (1 - FIX_RATE) ** i for i in range(r))
    token_cost = BASE_COST + repair
    total = token_cost + (1 - success) * HUMAN_COST
    per_success = total / success
    p99 = BASE_SEC + r * REPAIR_SEC * 1.6      # 粗略把单次修复的尾延迟放大 1.6 倍
    rows.append((r, success, token_cost, total, per_success, p99))
    print(f"{r:>3}{success:>9.1%}{token_cost:>15.2f}{1-success:>8.1%}{total:>12.2f}{per_success:>12.2f}{p99:>9.1f}s")

print("\n" + "=" * 86)
print("表 2  边际账：多修一轮买到了什么")
print("=" * 86)
for i in range(1, len(rows)):
    r0, s0, c0, t0, _, p0 = rows[i - 1]
    r1, s1, c1, t1, _, p1 = rows[i]
    extra_cost = c1 - c0
    extra_success = s1 - s0
    print(f"  r {r0}→{r1}: 成功率 {extra_success*100:+.1f}pp，多花 {extra_cost:.2f} 单位 → "
          f"每 pp 成本 {extra_cost/(extra_success*100):.2f}；总成本 {t1-t0:+.2f}；P99 {p1:.1f}s")

valid = [x for x in rows if x[5] <= SLO_SEC]
best = min(valid, key=lambda x: x[3])
print(f"\n在 P99 ≤ {SLO_SEC:.0f}s 约束下，期望总成本最低的是 r={best[0]}（总成本 {best[3]:.2f}，成功率 {best[1]:.1%}）。")
knee = min(rows[1:], key=lambda x: (x[4] - rows[rows.index(x)-1][4]) / max(x[1]-rows[rows.index(x)-1][1], 1e-9))
print(f"每 pp 成功率的 token 成本在各轮之间基本恒定，说明「修复」在本模型里是线性商品；")
print(f"真正变化的是延迟：r=2 时 P99 已到 {rows[2][5]:.1f}s，r=3 越过 {SLO_SEC:.0f}s 的 SLO。")

print("\n结论：修复轮把成功率从 70% 推到 94% 只多花 0.61 个单位，但 P99 从 1.8s 涨到 9.8s；")
print("      再修一轮成功率只 +3.3pp，延迟却直接越过 SLO——卡住修复轮的是延迟，不是 token 钱。")
print("读法：先设 SLO 与人工成本，再定最大修复轮（多数场景 2 轮）；")
print("      并且只对「结构错误」重试，语义错误重试同一 prompt 不会变好。")
