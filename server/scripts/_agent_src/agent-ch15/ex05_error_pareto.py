# title: 错误分析帕累托：头部 50% 类型识别与「同时修三类」的归因失效
# 标准库 + numpy：失败样本按错误类型计数、累计占比曲线（ASCII）与单改动归因对比。


import numpy as np
from collections import Counter


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


# 黄金集上轮结束后的 50 条失败样本及其归因标签（人工标注，本地模拟数据）
fail_tags = (
    ["检索未召回"] * 30 + ["生成格式错"] * 12 + ["事实错误"] * 6 + ["范围外拒答失败"] * 2
)
total = len(fail_tags)
cnt = Counter(fail_tags)
tags = [t for t, _ in cnt.most_common()]
counts = np.array([cnt[t] for t in tags])
cum = np.cumsum(counts)
cum_pct = cum / total

print("== 1) 错误类型分布与帕累托累计 ==")
print("  " + pad("错误类型", 16) + pad("条数", 6) + pad("占比", 8) + pad("累计占比", 10) + "帕累托条")
for t, n, cp in zip(tags, counts, cum_pct):
    bar = "#" * int(n / 2)
    mark = " <== 头部50%" if cp <= 0.5 or (cp - n / total) < 0.5 <= cp else ""
    print("  " + pad(t, 16) + pad(str(int(n)), 6) + pad(f"{n / total:6.1%}", 8)
          + pad(f"{cp:8.1%}", 10) + bar + mark)

head = [t for t, cp in zip(tags, cum_pct) if cp <= 0.5]
# 边界修正：累计首次跨过 50% 的那个类型也属于头部（差一两条不重要，边界归入头部）
cross = next(i for i, cp in enumerate(cum_pct) if cp >= 0.5)
if tags[cross] not in head:
    head.append(tags[cross])
print(f"\n  头部 50% 类型 = {head}（覆盖 {cum_pct[cross]:.0%} 的失败样本）")
print(f"  本轮只修：{head[0]}（单一改动，修完必须回归）")

print("\n== 2) 反模式：同时修三类，归因失效 ==")
# 假设三类错误各有针对性改动，单改效果（黄金集通过数增量）如下：
solo = {"改 chunk 策略": 8, "加 schema 校验重试": 3, "换更大模型": -2}
print("  " + pad("单独改动", 22) + "单独效果（通过数增量）")
for k, v in solo.items():
    print("  " + pad(k, 22) + f"{v:+d}")
combined = sum(solo.values())
print(f"  三者一起上：合计 {combined:+d} —— 如果混在一轮里，你无法回答：")
print("    - 「换更大模型」到底贡献了什么？（它单改是 -2，可能被前两个的正收益掩盖）")
print("    - 下轮该继续投哪个方向？（没有单改数据就没有方向）")
print("    - 回归出现新失败时，该回滚哪一个？（三个改动缠在一起，只能全回）")
print("  正确做法：每轮只改头部一类，用三列对比证明「该类下降且无新增失败」")

print("\n== 3) 头部类型修完后的下一轮（模拟修复效果） ==")
after = counts.copy()
after[0] -= 24          # 修复检索未召回的 24/30
after[1] -= 9           # 修复生成格式错的 9/12
cum2 = np.cumsum(after)
print("  " + pad("错误类型", 16) + pad("修复前", 8) + pad("修复后", 8) + "剩余累计占比")
for t, b, a, cp in zip(tags, counts, after, cum2 / total):
    print("  " + pad(t, 16) + pad(str(int(b)), 8) + pad(str(int(a)), 8) + f"{cp:8.1%}")
print(f"  失败样本 {total} -> {int(after.sum())} 条；剩余头部位「{tags[2]}」是下一轮唯一目标")
print("  注意：修头部两类也允许（强耦合改动），但绝不允许「感觉都不好，一起改」")

print("\n结论：错误分析把「下轮改什么」从感觉题变成排序题——按损失占比降序，每轮只修头部一类；")
print("读法：1. 帕累托头部 = 累计占比首次达到 50% 前的类型集合，通常 1~2 类；2. 单改动才能归因，合并改动的收益/回归都无法定位到具体改动；3. 修完一类必须重跑帕累托，头部位会转移，下轮目标随之改变；4. 本示例数据为本地模拟构造，真实项目里标签由人工逐条标注。")
