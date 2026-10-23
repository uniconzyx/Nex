# title: 三遍读法：时间盒、双阈值止损与每周预算分配
# 口径：三遍耗时累加（第一遍 10min / 前两遍 40min / 三遍共 160min）；
# 双阈值：score<0.5 止损于第一遍，score<0.7 止损于第二遍。候选论文分数沿用 ex01 的打分结构。

BUDGET_MIN = 420          # 每周可支配的论文阅读预算（分钟）
PASS_COST = {1: 10, 2: 40, 3: 160}   # 读到第 n 遍的累计耗时


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def passes_for(score):
    """三遍读法决策：返回读到第几遍（1/2/3）。"""
    if score < 0.5:
        return 1          # 摘要读完就止损，只留卡片
    if score < 0.7:
        return 2          # 图表读完就止损，只记存疑清单
    return 3              # 进入方法精读，产出复现计划


# 8 篇候选论文的加权分（构造值，覆盖三档区间）
PAPERS = [
    ("论文A：与手头检索延迟直接相关", 0.91),
    ("论文B：同一问题的新解法", 0.85),
    ("论文C：相邻方向，可能有用", 0.78),
    ("论文D：图表存疑，结论可能有用", 0.66),
    ("论文E：摘要一般，先记卡片", 0.62),
    ("论文F：相关度低的热点", 0.48),
    ("论文G：社区转载的二手解读", 0.44),
    ("论文H：完全无关的顶会论文", 0.38),
]

print(f"== 1) 分配方案（每周预算 {BUDGET_MIN} 分钟，按分数降序）==")
print(f"{pad('论文', 24)}{'分数':>6}{'读到第几遍':>10}{'耗时':>6}  状态")
used = 0
included, deferred = [], []
for name, s in PAPERS:
    p = passes_for(s)
    t = PASS_COST[p]
    if used + t <= BUDGET_MIN:
        used += t
        included.append(name)
        print(f"{pad(name, 24)}{s:>6.2f}{p:>10}{t:>6}  纳入")
    else:
        deferred.append(name)
        print(f"{pad(name, 24)}{s:>6.2f}{p:>10}{t:>6}  预算不足，延期")

print(f"\n== 2) 预算汇总 ==")
print(f"纳入 {len(included)} 篇 / 延期 {len(deferred)} 篇；总耗时 {used} / {BUDGET_MIN} 分钟"
      f"（占预算 {used / BUDGET_MIN:.0%}）")
full = sum(PASS_COST[3] for _ in PAPERS)
print(f"对比：若 8 篇全部读到第三遍 = {full} 分钟 = 预算的 {full / BUDGET_MIN:.1f} 倍"
      f"——不过滤的系统第三周必崩")
print(f"漏斗：8 篇候选 -> 止损第一遍 {sum(1 for _, s in PAPERS if s < 0.5)} 篇，"
      f"第二遍 {sum(1 for _, s in PAPERS if 0.5 <= s < 0.7)} 篇，"
      f"第三遍 {sum(1 for _, s in PAPERS if s >= 0.7)} 篇")

print("\n== 3) 双阈值的分工 ==")
print("阈值 0.5 回答「与我的问题相关吗」（第一遍的输出）")
print("阈值 0.7 回答「图表结论可信、值得细读吗」（第二遍的输出）")
print("两个阈值合并成一个 if，就会把「读完摘要觉得一般」和「看完图表决定深挖」混为一谈")

print("\n结论：三遍读法把「读不读、读到多深」变成带时间盒的逐级决策，每周预算先分配再订阅，")
print("读法：1. 三遍耗时是累加制（10/40/160 分钟），第三遍 = 前两遍 + 120 分钟精读；2. 每遍都有止损判据，闹钟响就停，防止「读了两小时还在第 2 节」；3. 预算不足的正确动作是「延期/分期」，不是砍掉第三遍——第三遍产出复现计划，恰是价值最高的部分；4. 本示例的候选分数为构造值，真实场景用 ex01 的打分公式计算。")
