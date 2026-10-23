# title: 信息源分层：四层来源的「可信度 × 时效 × 相关度」打分与排序
# 口径：freshness(days) = 0.5^(days/14)（半衰期 14 天）；score = 0.5·cred + 0.3·fresh + 0.2·rel。
# 数值为教学构造的候选信息，仅用于演示排序结构，不是对任何真实论文的评价。


def pad(s, w):
    """按终端显示宽度补空格（中文按 2 列）。"""
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def freshness(days):
    return 0.5 ** (days / 14)


def source_score(cred, days, rel, w=(0.5, 0.3, 0.2)):
    return w[0] * cred + w[1] * freshness(days) + w[2] * rel


# (名称, 层级, 可信度先验, 距发布天数, 与自身问题相关度)
SOURCES = [
    ("顶会论文A：长上下文注意力改进", "L1", 0.95, 12, 0.90),
    ("顶会论文B：多模态检索新架构", "L1", 0.95, 45, 0.20),
    ("实验室博客：某旗舰模型发布", "L2", 0.85, 5, 0.80),
    ("工程博客：检索延迟优化复盘", "L3", 0.70, 2, 0.85),
    ("工程博客：训练稳定性踩坑记录", "L3", 0.70, 10, 0.40),
    ("社区热帖：某框架使用讨论", "L4", 0.40, 1, 0.60),
    ("社区转载：某论文二手解读", "L4", 0.30, 3, 0.50),
]

print("== 1) 加权总分排序（可信度 0.5 / 时效 0.3 / 相关度 0.2）==")
print(f"{pad('来源', 26)}{'层级':>4}{'可信度':>8}{'时效':>7}{'相关度':>8}{'总分':>8}")
ranked = sorted(SOURCES, key=lambda s: -source_score(s[2], s[3], s[4]))
for name, tier, cred, days, rel in ranked:
    s = source_score(cred, days, rel)
    print(f"{pad(name, 26)}{tier:>4}{cred:>8.2f}{freshness(days):>7.3f}{rel:>8.2f}{s:>8.3f}")

print("\n== 2) 排序对比：只按时效排 vs 按加权分排（前 3 名）==")
by_time = sorted(SOURCES, key=lambda s: -freshness(s[3]))
print("按时效:", " | ".join(f"{n}({t})" for n, t, *_ in by_time[:3]))
print("按总分:", " | ".join(f"{n}({t})" for n, t, *_ in ranked[:3]))
print("差异：时效排序把 L4 社区热帖顶到第一；加权排序的第一是 L1 论文——层级差追不回")

print("\n== 3) 分层过滤漏斗：按总分阈值进入「本周读」==")
for thr in (0.50, 0.60, 0.65):
    kept = [n for n, t, c, d, r in ranked if source_score(c, d, r) >= thr]
    print(f"  阈值 {thr}: 留下 {len(kept)}/{len(ranked)} 条 -> {kept}")

print("\n== 4) 层级是硬先验的量化证据 ==")
l1_old = source_score(0.95, 60, 0.8)    # 60 天前的顶会论文
l4_new = source_score(0.40, 1, 0.6)     # 当天刷屏的社区热帖
print(f"60 天前的 L1 = {l1_old:.3f} vs 当天的 L4 = {l4_new:.3f} -> L1 仍高 {l1_old - l4_new:+.3f}")
print("可信度项权重 0.5 > 时效项 0.3：先看来源，再看日期，最后才看热度")

print("\n结论：信息源分层给每条信息一个可信度先验，加权分数把「来源 × 日期 × 相关度」合成一个可排序的数，")
print("读法：1. 分层不是尊卑排序而是先验：进入选型/复现决策的结论必须溯源到 L1/L2，社区信息只作线索；2. 时效按半衰期 14 天衰减，权重 0.3 低于可信度 0.5，所以 60 天前的顶会论文仍赢当天热帖；3. 相关度是个人私有先验，同一篇论文对不同人分数不同——过滤系统必须个人化；4. 本示例的打分与来源均为教学构造，真实场景中 cred 应按「是否有代码/评审/复盘细节」校准。")
