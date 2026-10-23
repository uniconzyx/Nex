# title: 用户故事评分器：把「写得好不好」拆成四个可检查的维度
# 规则打分（角色/目标/价值/验收），不联网。分数不是目的，指出缺哪一块才是。
# 评分口径：四维各 25 分；验收维度要求 >=2 条且至少 1 条可量化。

import re

STORIES = [
    ("S1", "作为一个电商客服主管，我想要在会话侧栏看到退款原因分布，以便把本周培训重点放在高频问题上。",
     "验收：给定上周 500 条退款会话，当打开侧栏时，则按原因展示 Top5 及占比；数字与实际工单一致。"),
    ("S2", "用户希望能更快找到商品。",
     "验收：搜索要快。"),
    ("S3", "作为运营，我想要一键导出上周所有差评，以便逐个电话回访。",
     "验收：当选择时间范围后，则导出 CSV，包含订单号、评分、评论；1000 条导出在 10 秒内完成。"),
    ("S4", "作为会员，我想要系统自动生成收货评价草稿，以便节省写评价的时间。",
     "验收：生成结果要像人写的。"),
    ("S5", "作为财务，我想要把发票识别结果导出为 Excel，以便和银行流水对账。",
     "验收：给定 50 张测试发票，当点击导出时，则金额、税额、开票日期三列非空率 100%；金额误差 <= 0.01 元。"),
]

ROLE = re.compile(r"作为|作为一个")
GOAL = re.compile(r"我想要|我要|希望能|想要")
VALUE = re.compile(r"以便|从而|这样|为了")
AC = re.compile(r"验收[:：]|给定|当.+则|当.+时")
NUM = re.compile(r"\d")


def score(story, ac):
    s_role = 25 if ROLE.search(story) else 0
    s_goal = 25 if GOAL.search(story) else 0
    s_value = 25 if VALUE.search(story) else 0
    ac_items = [x for x in re.split(r"[；;]", ac.replace("验收：", "").replace("验收:", "")) if x.strip()]
    quant = sum(1 for x in ac_items if NUM.search(x))
    s_ac = 25 if len(ac_items) >= 2 and quant >= 1 else (12 if ac_items and quant else 0)
    return [s_role, s_goal, s_value, s_ac], ac_items, quant


print("评分维度：角色 25 / 目标 25 / 价值 25 / 验收 25（>=2 条且含数字才满分）\n")
print(f"{'编号':<4}{'角色':>4}{'目标':>4}{'价值':>4}{'验收':>4}{'总分':>5}  等级  最弱项")
rows = []
for sid, story, ac in STORIES:
    dims, items, quant = score(story, ac)
    total = sum(dims)
    grade = "A" if total >= 90 else ("B" if total >= 70 else ("C" if total >= 50 else "D"))
    names = ["角色", "目标", "价值", "验收"]
    weakest = "-" if min(dims) == 25 else names[dims.index(min(dims))]
    rows.append((sid, dims, items, quant, total))
    print(f"{sid:<4}{dims[0]:>4}{dims[1]:>4}{dims[2]:>4}{dims[3]:>4}{total:>5}  {grade:<4}  {weakest}")

print("\n逐条诊断：")
for sid, dims, items, quant, total in rows:
    if total >= 90:
        print(f"  {sid}: 四要素齐全，验收 {len(items)} 条（可量化 {quant} 条）→ 可进入评审")
    elif total >= 50:
        miss = [n for n, v in zip(("角色", "目标", "价值", "验收"), dims) if v == 0]
        print(f"  {sid}: 缺 {'/'.join(miss) or '可量化验收'} → 先补这一项，不要急着估工期")
    else:
        print(f"  {sid}: 只有愿望没有边界（总分 {total}）→ 退回重写，无法验收")

print("\n读法：S2 的「更快」「要快」都不是验收条件——没有对象、阈值和测量方法。")
print("      S4 有角色/目标/价值，但「像人写的」不可判定，仍然不能开工。")
print("结论：用户故事的质量下限由验收条件决定；写不出可测的「则」，说明需求还没想清楚。")
