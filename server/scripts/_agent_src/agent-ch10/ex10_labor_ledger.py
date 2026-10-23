# title: 指标账本：一次回归要花多少人工工时，三种评测策略的季度对比
# 口径：黄金集 50 条/次；校准集 100 条（一次性）；每周 2 次回归，一季度 13 周共 26 次；
# 人工标注 4 分钟/条（教学假设值，真实值按团队实测替换）；单条 judge 调用 0.5 秒 / ¥0.002。

MIN_PER_LABEL = 4.0        # 人工标注单条分钟数
LABELS_CALIB = 100         # 校准集规模
LABELS_GOLD = 50           # 黄金集规模
RUNS = 26                  # 季度回归次数
REPORT_MIN = 30            # 每次回归读报告 + 抽检复核的分钟数
JUDGE_SEC = 0.5            # 单条 judge 机器耗时
JUDGE_YUAN = 0.002         # 单条 judge 机器成本
SAMPLE_RATIO = 0.20        # 策略 B 的人工抽检比例
REGRESS_WITH_TRUE_BUG = 3  # 季度内含真实退化的回归次数（教学假设）
MISS_COST_HOURS = 40       # 一次漏检事故的善后人时（复盘 + 回滚 + 客诉处理）
DAY_HOURS = 8              # 1 人日折算


def ledger(name, calib_min, per_run_min, report=True, judge_machine=False):
    """季度账本：返回 (名称, 校准人分, 回归人分, 报告人分, 总人分, judge 机器分, judge 机器成本元)"""
    run_min = per_run_min * RUNS
    report_min = REPORT_MIN * RUNS if report else 0.0
    judge_min = JUDGE_SEC * LABELS_GOLD * RUNS / 60 if judge_machine else 0.0
    judge_cost = JUDGE_YUAN * LABELS_GOLD * RUNS if judge_machine else 0.0
    total = calib_min + run_min + report_min
    return name, calib_min, run_min, report_min, total, judge_min, judge_cost


rows = [
    # A：纯人工，每条都人评
    ledger("A 纯人工评测", LABELS_CALIB * MIN_PER_LABEL,
           LABELS_GOLD * MIN_PER_LABEL),
    # B：judge 预筛 + 20% 人工抽检（推荐）
    ledger("B judge 预筛 + 20% 抽检", LABELS_CALIB * MIN_PER_LABEL,
           LABELS_GOLD * SAMPLE_RATIO * MIN_PER_LABEL, judge_machine=True),
    # C：全自动 judge，跳过校准、抽检与人工读报告
    ledger("C 全自动 judge（未校准）", 0.0, 0.0, report=False, judge_machine=True),
]

print("== 1) 季度账本（26 次回归，人分 -> 人日按 8h 折算） ==")
print(f"{'策略':<24}{'校准人分':>9}{'回归人分':>9}{'报告人分':>9}{'总人时':>8}{'人日':>7}{'judge机器':>10}")
for name, c, r, rep, total, jm, jc in rows:
    print(f"{name:<24}{c:>9.0f}{r:>9.0f}{rep:>9.0f}{total / 60:>8.1f}{total / 60 / DAY_HOURS:>7.1f}"
          f"{jm:>8.1f}分")

print("\n== 2) 单次回归账本分解（策略 B） ==")
per_run = LABELS_GOLD * SAMPLE_RATIO * MIN_PER_LABEL
print(f"  judge 跑 50 条 = {LABELS_GOLD * JUDGE_SEC:.0f} 秒（机器，成本 ¥{LABELS_GOLD * JUDGE_YUAN:.3f}）")
print(f"  人工抽检 20% = 10 条 x {MIN_PER_LABEL:.0f} 分钟 = {per_run:.0f} 分钟")
print(f"  读报告 + 复核分歧样本 = {REPORT_MIN} 分钟")
print(f"  单次合计 {per_run + REPORT_MIN:.0f} 分钟 ≈ {(per_run + REPORT_MIN) / 60:.1f} 人时")

print("\n== 3) C 策略的隐藏成本：零人工账本不等于零成本 ==")
miss_rate = 0.70   # 未校准 judge 对真实退化的漏检率（教学假设：kappa 0.32 量级的 judge，检出率约 3 成）
expected_miss = REGRESS_WITH_TRUE_BUG * miss_rate
expected_loss = expected_miss * MISS_COST_HOURS
print(f"  季度内含真实退化的回归 {REGRESS_WITH_TRUE_BUG} 次（教学假设）")
print(f"  未校准 judge 漏检率 {miss_rate:.0%} -> 期望漏检 {expected_miss:.1f} 次")
print(f"  每次漏检善后 {MISS_COST_HOURS} 人时 -> 期望损失 {expected_loss:.0f} 人时"
      f"（约 {expected_loss / DAY_HOURS:.1f} 人日），且不含客诉与商誉损失")
c_total = rows[2][4] / 60
print(f"  C 策略账面 {c_total:.1f} 人时 + 期望损失 {expected_loss:.0f} 人时 = "
      f"{c_total + expected_loss:.0f} 人时，反而最贵")

print("\n== 4) 校准是一次性保险费，不能省 ==")
calib_h = LABELS_CALIB * MIN_PER_LABEL / 60
print(f"  校准集人工标注 {LABELS_CALIB} 条 = {calib_h:.1f} 人时（一次性，judge 变更只需重跑 judge）")
print(f"  占策略 B 季度总成本的 {calib_h / (rows[1][4] / 60):.0%}——省掉它，等于把 {miss_rate:.0%} 的漏检率写进发布流程")

print("\n== 5) 预算口径 ==")
b_quarter = rows[1][4] / 60 / DAY_HOURS
print(f"  策略 B 季度 {b_quarter:.1f} 人日，摊到每周约 {b_quarter / 13:.1f} 人日")
print(f"  纯人工策略季度 {rows[0][4] / 60 / DAY_HOURS:.1f} 人日——评估成本本身会成为不评估的理由")

print("\n结论：judge 的机器成本（季度 ¥3 量级）可以忽略，它省的是人力；但校准集标注与 20% 抽检是保险费，跳过它们的「零人工」策略期望总成本最高；")
print("读法：1. 评估成本要按「校准人分 + 回归人分 + 报告人分 + 机器成本」四项记账，缺项就会低估评估阻力；2. 单次回归的可接受人工预算是 1 人日以内，超出就要提高抽检效率或缩回归范围；3. 分钟数、漏检率、事故成本均为教学假设值，接入时用本团队实测值替换，账本结构不变；4. 本示例为本地数值计算，不读取任何外部数据。")
