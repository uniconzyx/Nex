# title: 行为锚点等级判定器：按产物类型判级，数量不跨级
import numpy as np

# 产物类型 → 能证明的最低等级（concept/01 §1 锚点表的代码化，经验判断）
LEVEL_ART = {
    "tutorial_notes": 1, "pr_fix_rerank": 2,
    "online_record": 3, "eval_report": 3,
    "design_doc": 4, "review_notes": 4,
    "team_spec": 5, "mentoring_log": 5,
}
LEVEL_NAME = {0: "无主张", 1: "L1 入门", 2: "L2 使用", 3: "L3 交付",
              4: "L4 设计", 5: "L5 定标"}


def anchor_level(artifacts):
    """按产物类型取最高可证明等级；空列表 = 0（无主张，不是 L1）。"""
    return max((LEVEL_ART.get(a, 1) for a in artifacts), default=0)


def evidence_score(claim, arts, peer):
    """有效等级 = min(声称, 产物判级, 他评确认数+1)——他评不能代替产物。"""
    return min(claim, anchor_level(arts), min(peer + 1, 5))


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


print("== 1) 同一句自评声明，产物不同 → 判定不同 ==")
claims = [
    ("熟悉 RAG，看过 20 个教程", ["tutorial_notes"] * 20, 0),
    ("熟悉 RAG，看过 1 个教程", ["tutorial_notes"], 0),
    ("给课程项目加了重排模块", ["tutorial_notes", "pr_fix_rerank"], 1),
    ("独立上线工单问答", ["tutorial_notes", "online_record", "eval_report"], 2),
    ("设计多路召回与降级", ["online_record", "eval_report", "design_doc"], 2),
]
for text, arts, peer in claims:
    lv = anchor_level(arts)
    print(f"   {pad(text, 20)}产物 ×{len(arts):<2} → {LEVEL_NAME[lv]:<8}"
          f"（驱动产物: {max(arts, key=lambda a: LEVEL_ART.get(a, 1))}）")

print("\n== 2) 数量不跨级：20 个教程产物与 1 个同级 ==")
lv20, lv1 = anchor_level(["tutorial_notes"] * 20), anchor_level(["tutorial_notes"])
print(f"   20 个 tutorial_notes → L{lv20}；1 个 tutorial_notes → L{lv1}；"
      f"同级: {lv20 == lv1}")
print("   类型才是等级的证据，堆数量只能证明『看得多』，不能证明『做得深』")

print("\n== 3) 他评校准：有效等级 = min(声称, 产物, 他评+1) ==")
rows = [("RAG 检索", 4, ["eval_report"], 1),
        ("Prompt 工程", 3, ["tutorial_notes"], 3),
        ("服务部署", 2, ["online_record", "eval_report"], 2),
        ("指标拆解", 3, ["tutorial_notes"], 0),
        ("团队规范", 5, ["team_spec", "mentoring_log"], 3)]
print(f"   {pad('条目', 12)}{'声称':>4}{'产物判级':>6}{'他评封顶':>6}{'有效':>4}  动作")
for name, claim, arts, peer in rows:
    eff = evidence_score(claim, arts, peer)
    act = "降级" if eff < claim else "保留"
    print(f"   {pad(name, 12)}{claim:>4}{anchor_level(arts):>6}{min(peer + 1, 5):>6}{eff:>4}  {act}")

# 4) 用 numpy 汇总校准前后整表的等级总量变化
before = np.array([r[1] for r in rows], dtype=float)
after = np.array([evidence_score(r[1], r[2], r[3]) for r in rows], dtype=float)
shrink = 1 - after.sum() / before.sum()
print("\n== 4) 整表校准效果（5 个条目）==")
print(f"   声称等级合计 {before.sum():.0f} → 有效等级合计 {after.sum():.0f}"
      f"（缩水 {shrink:.0%}）")
print(f"   降级条目数 {(before > after).sum()}/{len(rows)}")

print(f"\n结论：自评等级由产物类型决定、由他评封顶，本表声称等级缩水 {shrink:.0%}、"
      f"{(before > after).sum()}/{len(rows)} 条降级——缩水是常态而非异常")
print("读法：1. 判定器只认产物类型：tutorial_notes 堆到 20 个仍是 L1，这是对抗『把熟悉度当熟练度』的硬闸门；2. 空产物列表返回 0（无主张），不是 L1——没有证据就没有等级主张；3. 他评封顶 = min(peer+1,5)：0 个他评确认最多主张 L1，但他评也不能替代产物（第二行他评 3 个仍被产物摁在 L1）；4. 降级清单就是 12 个月计划的 backlog，本示例不调用任何外部服务。")
