# title: 自评 vs 他评偏差量化：过宣称条目、相关系数与校准动作
import numpy as np

# (条目, 维度, 自评, mentor他评, 可出示产物数)
ROWS = [
    ("RAG 检索", "工程", 5, 3, 2),
    ("服务部署", "工程", 4, 2, 3),
    ("Prompt 工程", "模型", 4, 3, 1),
    ("微调实验", "模型", 3, 2, 1),
    ("需求拆解", "产品", 2, 2, 2),
    ("指标对齐", "产品", 2, 1, 2),
    ("客户沟通", "业务", 2, 2, 1),
    ("行业知识", "业务", 2, 2, 1),
]


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def calibrate(self_lv, peer_lv, n_arts):
    """校准规则：自评高 2 级以上先降级；他评高 2 级且产物足则补证；其余保留。"""
    d = self_lv - peer_lv
    if d >= 2:
        return "降级"
    if d <= -2 and n_arts >= 2:
        return "补证"
    return "保留"


print("== 1) 逐条偏差表（Δ = 自评 − 他评）==")
print(f"{pad('条目', 12)}{pad('维度', 5)}{'自评':>4}{'他评':>4}{'Δ':>4}{'产物':>4}  校准动作")
deltas = []
for name, dim, s, p, a in ROWS:
    d = s - p
    deltas.append(d)
    print(f"{pad(name, 12)}{pad(dim, 5)}{s:>4}{p:>4}{d:>+4}{a:>4}  {calibrate(s, p, a)}")

self_v = np.array([r[2] for r in ROWS], dtype=float)
peer_v = np.array([r[3] for r in ROWS], dtype=float)
delta = self_v - peer_v
print("\n== 2) 汇总统计 ==")
print(f"   平均绝对偏差 |Δ| = {np.abs(delta).mean():.2f} 级")
print(f"   过宣称条目（自评 ≥ 他评+2）= {(delta >= 2).sum()}/{len(ROWS)}")
print(f"   低报条目（他评 ≥ 自评+2）= {(delta <= -2).sum()}/{len(ROWS)}")
corr = float(np.corrcoef(self_v, peer_v)[0, 1])
print(f"   自评/他评 Pearson 相关 = {corr:.3f}（同向但幅度不同：自评范围更宽）")

print("\n== 3) 按维度聚合（找系统性偏差维度）==")
for dim in ["工程", "模型", "产品", "业务"]:
    idx = [i for i, r in enumerate(ROWS) if r[1] == dim]
    mean_d = delta[idx].mean()
    flag = " ← 系统性过宣称" if mean_d >= 1.0 else (" ← 可能低报" if mean_d <= -1.0 else "")
    print(f"   {pad(dim, 4)} 平均 Δ = {mean_d:+.2f}{flag}")

worst = sorted(range(len(ROWS)), key=lambda i: -abs(delta[i]))[:3]
print("\n== 4) 偏差最大的三个条目（补证/降级优先级）==")
for i in worst:
    print(f"   {pad(ROWS[i][0], 12)} Δ={delta[i]:+.0f} → {calibrate(*ROWS[i][2:])}")

print(f"\n结论：自评与他评整体同向（相关 {corr:.2f}）但系统性偏高——本表 8 条里 "
      f"{(delta >= 2).sum()} 条过宣称、{(delta <= -2).sum()} 条低报，")
print("读法：1. 过宣称不是态度问题而是测量问题：没有他评数据源，自评的宽大误差无法暴露；2. 校准动作有优先级——自评高 2 级先降级（面试现场再升回来比现场崩掉便宜），他评高 2 级且产物足才补证（他评可能没见过你的产物）；3. 维度级平均 Δ 暴露系统性偏差（本例工程维 +2.0、模型维 +1.0，是「看过教程当会做实验」的重灾区）；4. 相关系数高说明排序大致可信、绝对值不可信——自评适合排序，不适合当等级主张。")
