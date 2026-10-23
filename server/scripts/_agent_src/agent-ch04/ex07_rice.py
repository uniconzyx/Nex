# title: RICE 需求排序：分子是收益，分母是成本，置信度是折扣
# 6 个候选需求，按 Reach × Impact × Confidence / Effort 排序，并做置信度敏感性分析。
# RICE 的价值不在小数位，而在迫使你把「感觉重要」拆成四个可争论的数。

FEATURES = [
    ("F1 退款自助办理", 1200, 3.0, 0.80, 8),
    ("F2 多轮追问", 800, 2.0, 0.60, 6),
    ("F3 会话摘要", 2000, 1.0, 0.90, 3),
    ("F4 情绪安抚话术", 600, 1.5, 0.50, 4),
    ("F5 工单自动分类", 3000, 2.0, 0.85, 5),
    ("F6 语音输入", 400, 2.5, 0.40, 10),
]


def rice(r, i, c, e):
    return r * i * c / e


print("RICE = Reach（月触达人数）× Impact（1~3）× Confidence（0~1）/ Effort（人周）\n")
rows = []
for name, r, i, c, e in FEATURES:
    rows.append((rice(r, i, c, e), name, r, i, c, e))
rows.sort(reverse=True)
print(f"{'排名':<4}{'需求':<20}{'Reach':>7}{'Impact':>7}{'Conf':>6}{'Effort':>7}{'RICE':>8}")
for k, (score, name, r, i, c, e) in enumerate(rows, 1):
    print(f"{k:<4}{name:<20}{r:>7}{i:>7.1f}{c:>6.2f}{e:>7}{score:>8.1f}")

top, second = rows[0], rows[1]
print(f"\nTop1 = {top[1]}（{top[0]:.1f}），Top2 = {second[1]}（{second[0]:.1f}），"
      f"差距 {(top[0]/second[0] - 1):.0%}")

print("\n敏感性：把 Top1 的置信度下调 20%，看排名是否翻转")
c2 = top[4] * 0.8
new_top = rice(top[2], top[3], c2, top[5])
print(f"  {top[1]}：C {top[4]:.2f} -> {c2:.2f}，RICE {top[0]:.1f} -> {new_top:.1f}")
print(f"  {'仍领先' if new_top > second[0] else '被 ' + second[1] + ' 反超'}"
      f"（Top2 = {second[0]:.1f}）")

print("\n读法：F5 的 Reach 最大但 Effort 中等，排第一；F6 的 Impact 高，但 C=0.4 与 E=10 把它压到最后。")
print("      RICE 对 Confidence 最敏感——它本质是「你有多确定」，不是「效果有多好」。")
print("结论：RICE 适合做初筛和排序沟通，不适合做精确预算；")
print("      所有输入都要标注来源（埋点/访谈/历史实验），否则只是把主观换成了小数。")
