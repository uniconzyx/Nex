# title: 面试准备清单覆盖度：加权覆盖、「看过」陷阱与 ROI 排序
import numpy as np

# 信用等级：只有「被追问过」算真掌握——看过/能讲都会被追问三层穿
CREDIT = {"未开始": 0.0, "看过": 0.2, "能讲": 0.6, "被追问过": 1.0}
CHECKLIST = [
    ("八股基础", [("Python 基础", 2.0, "被追问过"), ("操作系统", 1.5, "看过"),
                  ("计算机网络", 1.5, "看过"), ("数据库与 SQL", 1.0, "能讲")]),
    ("系统设计", [("容量估算", 2.0, "能讲"), ("一致性与取舍", 2.0, "看过"),
                  ("Agent 服务设计", 2.0, "未开始"), ("限流与降级", 1.5, "未开始")]),
    ("项目深挖", [("工单自动问答", 2.5, "被追问过"), ("课程知识库问答", 1.5, "能讲"),
                  ("论文摘要工具", 1.5, "看过"), ("领域微调实验", 1.0, "未开始")]),
    ("算法编码", [("数组与字符串", 1.5, "能讲"), ("二叉树与递归", 1.5, "看过"),
                  ("动态规划", 1.0, "未开始"), ("手撕基础网络", 1.0, "看过")]),
    ("行为面", [("STAR-R 故事库", 2.0, "能讲"), ("失败与复盘", 1.5, "看过"),
                ("职业规划陈述", 1.5, "未开始"), ("反问环节准备", 1.0, "看过")]),
]


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def cat_coverage(items):
    w = np.array([i[1] for i in items], dtype=float)
    c = np.array([CREDIT[i[2]] for i in items], dtype=float)
    return float((w * c).sum() / w.sum())


print("== 1) 分类覆盖度（加权：只有被追问过=1.0，看过仅 0.2）==")
total_w = total_c = 0.0
for cat, items in CHECKLIST:
    w = np.array([i[1] for i in items], dtype=float)
    c = np.array([CREDIT[i[2]] for i in items], dtype=float)
    cov = float((w * c).sum() / w.sum())
    total_w += w.sum()
    total_c += float((w * c).sum())
    bar = "#" * int(round(cov * 20)) + "." * (20 - int(round(cov * 20)))
    print(f"   {pad(cat, 6)}{cov:>6.1%}  {bar}")
overall = total_c / total_w
print(f"   总体覆盖度 = {overall:.1%}（面试官视角：低于 70% 属于裸考区间）")

print("\n== 2) 明细表 ==")
print(f"{pad('分类', 6)}{pad('条目', 14)}{'权重':>5}{'状态':>6}{'信用':>5}")
for cat, items in CHECKLIST:
    for name, w, st in items:
        print(f"{pad(cat, 6)}{pad(name, 14)}{w:>5.1f}{st:>6}{CREDIT[st]:>5.1f}")

# 3) ROI = 权重 × (1 − 信用)，未掌握的高权重项排最前
roi = []
for cat, items in CHECKLIST:
    for name, w, st in items:
        roi.append((w * (1 - CREDIT[st]), w, f"{cat}/{name}", st))
roi.sort(key=lambda x: (-x[0], -x[1], x[2]))
print("\n== 3) 最高优先级的三个补法（ROI = 权重 × 缺口）==")
for value, w, name, st in roi[:3]:
    print(f"   {pad(name, 20)} ROI={value:.1f}（权重 {w:.1f}，当前「{st}」）")

# 4) 「看过」陷阱：停在看过区间的权重占比
seen_w = sum(i[1] for _, items in CHECKLIST for i in items if i[2] == "看过")
seen_n = sum(1 for _, items in CHECKLIST for i in items if i[2] == "看过")
all_n = sum(len(items) for _, items in CHECKLIST)
print("\n== 4) 「看过」陷阱 ==")
print(f"   {seen_n}/{all_n} 个条目停在「看过」，占总权重 {seen_w / total_w:.1%}")
print("   「看过」的典型死法：面试官往下追问三层（是什么→为什么→边界），第三层就穿")
print("   升级路径：看过→能讲（合上书复述 + 举一个自己的项目例子）；")
print("             能讲→被追问过（找人模拟追问 3 轮，或写下来自问自答）")

weak = min(((cat, cat_coverage(items)) for cat, items in CHECKLIST),
           key=lambda x: x[1])
print(f"\n结论：总体覆盖度 {overall:.1%}，最弱类别是「{weak[0]}」（{weak[1]:.1%}）——")
print("读法：1. 覆盖度按权重算不按条目数：行为面只有 4 条但权重 6.0，和系统设计同等重要；2. 「被追问过」是唯一满分状态——准备的质量单位是「扛住几层追问」，不是「看过几遍」；3. ROI 排序直接给出下一步：先补「Agent 服务设计」与「一致性与取舍」这类高权重零信用项；4. 本清单是固定构造的教学数据，方法可复用：把你的真实清单按同样四状态打分，低于 70% 不投递。")
