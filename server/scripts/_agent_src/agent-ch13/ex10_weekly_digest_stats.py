# title: 信息流周报：分层漏斗、单位耗时产出与「砍源」决策
# 工程账本：固定构造一周 40 条信息（4 层 × 10 条），动作分 忽略/一读/精读/复现四档，
# 输出漏斗、分层效率表与基于数字的「砍源/加注」建议。数据为教学构造，统计代码可复用。

# (层级, 类型, 动作) —— 固定构造，保证周报可复现
LOG = (
    [("L1", "论文", "复现")] * 2 + [("L1", "论文", "精读")] * 4
    + [("L1", "论文", "一读")] * 3 + [("L1", "论文", "忽略")] * 1
    + [("L2", "实验室博客", "精读")] * 2 + [("L2", "实验室博客", "一读")] * 5
    + [("L2", "实验室博客", "忽略")] * 3
    + [("L3", "工程博客", "复现")] * 1 + [("L3", "工程博客", "精读")] * 1
    + [("L3", "工程博客", "一读")] * 4 + [("L3", "工程博客", "忽略")] * 4
    + [("L4", "社区", "一读")] * 2 + [("L4", "社区", "忽略")] * 8
)

MINUTES = {"忽略": 1, "一读": 10, "精读": 60, "复现": 90}   # 各动作耗时（分钟，教学值）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


tiers = ["L1", "L2", "L3", "L4"]
stats = {t: {"total": 0, "一读": 0, "精读": 0, "复现": 0, "min": 0} for t in tiers}
for t, kind, action in LOG:
    stats[t]["total"] += 1
    stats[t]["min"] += MINUTES[action]
    if action != "忽略":
        stats[t]["一读"] += 1
    if action in ("精读", "复现"):
        stats[t]["精读"] += 1
    if action == "复现":
        stats[t]["复现"] += 1

total = len(LOG)
read1 = sum(stats[t]["一读"] for t in tiers)
deep = sum(stats[t]["精读"] for t in tiers)
repro = sum(stats[t]["复现"] for t in tiers)
total_min = sum(stats[t]["min"] for t in tiers)

print("== 1) 漏斗：候选 -> 一读 -> 精读+复现 -> 复现 ==")
print(f"  候选 {total:3d}  ->  一读 {read1:3d}  ->  精读/复现 {deep:3d}  ->  复现 {repro:2d}")
print(f"  通过率：一读 {read1/total:.0%}，深读 {deep/total:.0%}，复现 {repro/total:.0%}")
print(f"  总耗时 {total_min} 分钟 = {total_min/60:.1f} 小时（含 {repro} 个复现）")

print("\n== 2) 分层效率表 ==")
print(f"{pad('层级', 6)}{'条数':>4}{'一读':>4}{'深读':>4}{'复现':>4}{'耗时min':>8}"
      f"{'深读率':>7}{'复现率':>7}{'分钟/深读':>9}")
for t in tiers:
    s = stats[t]
    deep_rate = s["精读"] / s["total"]
    repro_rate = s["复现"] / s["total"]
    per_deep = s["min"] / s["精读"] if s["精读"] else float("nan")
    per_txt = f"{per_deep:9.1f}" if s["精读"] else "      n/a"
    print(f"{pad(t, 6)}{s['total']:>4}{s['一读']:>4}{s['精读']:>4}{s['复现']:>4}"
          f"{s['min']:>8}{deep_rate:>7.0%}{repro_rate:>7.0%}{per_txt}")

print("\n== 3) 基于数字的调整建议 ==")
print(f"  a) L4 十条只产出 {stats['L4']['一读']} 条一读、0 条深读：砍到每周 3 条或只读聚合摘要，"
      f"省下 {stats['L4']['min'] - 3 * MINUTES['忽略']:.0f} 分钟")
print(f"  b) L1 深读率 {stats['L1']['精读']/stats['L1']['total']:.0%} 为四层最高：维持订阅，"
      f"复现候选优先从 L1 出")
print(f"  c) L2 无复现产出（复现率 0%）：降为「只读与当前问题相关的」，"
      f"每周节省 {stats['L2']['min'] * 0.5:.0f} 分钟（按砍半估算）")
saved = (stats['L4']['min'] - 3 * MINUTES['忽略']) + stats['L2']['min'] * 0.5
print(f"  d) 合计每周可省约 {saved:.0f} 分钟 = {saved/60:.1f} 小时，"
      f"相当于多出 {saved / MINUTES['精读']:.1f} 篇精读的预算")

print("\n结论：过滤系统的效率要用漏斗和单位耗时产出来度量，砍源决策必须来自数字而不是情绪，")
print("读法：1. 三层漏斗（候选->一读->深读->复现）任何一层塌了，先修那一层：一读率低说明打分阈值太松，深读率低说明第二遍判据失效；2. 「分钟/深读」是核心效率指标：L1 约 70 分钟/篇 vs L4 无深读——同样的时间投在不同层，产出差一个量级；3. 砍 L4 省 25 分钟只够 0.4 篇精读，说明省小源不如提阈值——预算要花在「让第一遍更狠」上；4. 复现是漏斗最窄的出口（3/40 = 7.5%），它对应 tech_load 的交付物，值得为它保留固定工时；5. 数据为教学构造，换成你的真实阅读记录即可复用全部统计代码。")
