# title: 验收条件可测性检查：模糊词一票否决
# 用词表 + 可量化信号（数字、阈值、时间窗、测试集）给每条验收条件打分。
# 目标不是自动改写，而是让评审时能指着具体词说「这句没法测」。

import re

CRITERIA = [
    ("C1", "响应要快。"),
    ("C2", "当用户点击退款时，3 秒内展示退款金额，误差不超过 0.01 元。"),
    ("C3", "回答要友好且专业。"),
    ("C4", "在 500 条测试集上，意图识别准确率 >= 92%。"),
    ("C5", "尽量在用户等待时给出提示。"),
    ("C6", "超时 10 秒时转人工，并展示工单号。"),
]

VAGUE = ["友好", "快速", "快", "尽快", "合理", "尽量", "适当", "流畅", "智能", "稳定",
         "好用", "及时", "完善", "优化", "专业", "像人写的", "等等"]
MEASURABLE = re.compile(r"\d+(?:\.\d+)?\s*(?:秒|ms|毫秒|元|%|条|次|分钟)|>=\s*\d+|测试集|工单号")


def check(text):
    hits = [w for w in VAGUE if w in text]
    quant = [m for m in MEASURABLE.findall(text) if m.strip()]
    score = 100 - 22 * len(hits) + 8 * min(3, len(quant))
    score = max(0, min(100, score))
    return hits, quant, score


print("评分：基础 100；每个模糊词 -22；每个可量化信号 +8（最多 3 个），下限 0\n")
print(f"{'编号':<4}{'分数':>4}  {'模糊词':<18}{'可量化信号':<22}判定")
for cid, text in CRITERIA:
    hits, quant, score = check(text)
    verdict = "可验收" if score >= 80 else ("需补测法" if score >= 50 else "不可验收")
    print(f"{cid:<4}{score:>4}  {('/'.join(hits) or '-'):<18}{('/'.join(quant) or '-'):<22}{verdict}")

print("\n逐条意见：")
for cid, text in CRITERIA:
    hits, quant, score = check(text)
    if score >= 80:
        print(f"  {cid}: 保留。判据是「{quant[0] if quant else '阈值'}」，可直接写进测试用例。")
    else:
        print(f"  {cid}: 「{hits[0] if hits else '缺少阈值'}」没有测量方法；"
              f"补成「指标 + 阈值 + 测量对象 + 时间窗」。")

print("\n改写示例：")
print("  原：C1 响应要快。")
print("  改：给定 100 条真实用户问题，从发送到首字展示的 P95 <= 2 秒、P99 <= 4 秒；")
print("      超时则展示「正在处理」并允许取消。")

print("\n读法：模糊词不是文风问题，是无法判定通过/失败——它让验收变成事后扯皮。")
print("结论：每条验收条件都必须能写出「怎么测、测多少条、达到多少算过」；")
print("      写不出测试集与阈值，说明需求还停留在愿望层。")
