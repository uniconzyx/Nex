# title: 黄金集回归对比器：三列差异集、豁免式回滚判定与「总数骗人」
# 纯标准库实现：固定构造 50 条黄金样本，模拟基线版/迭代版两套规则引擎，输出三列对比。


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


import random

rng = random.Random(42)  # 固定种子：样本构造可复现

# 黄金集：50 条，按「难度类」构造。类 = 引擎行为的决定因素（本地模拟，非真实模型）
# A: 基线过/迭代过；B: 基线过/迭代多数过（7 条被模板重构打破）；C: 基线败(检索未召回)/迭代修复；D: 双双败(生成格式错)
CLASS_PLAN = {"A": 18, "B": 22, "C": 8, "D": 2}
CLASS_TAG = {"C": "检索未召回", "D": "生成格式错"}

golden = []
i = 0
for cls, n in CLASS_PLAN.items():
    for _ in range(n):
        i += 1
        golden.append({"id": f"s{i:02d}", "cls": cls,
                       "payload": f"记录片段-{rng.randrange(1000):03d}"})
assert len(golden) == 50

# 迭代版打破的 7 条 B 类样本（B 类占 s19~s40；模板重构的副作用，固定写死保证可复现）
REGRESSED = {"s20", "s23", "s27", "s31", "s35", "s37", "s39"}
EXEMPTIONS = {"s23": "模板重构的预期内变更，期望值已随 schema v2 更新"}  # 显式豁免记录


def run_baseline(s):
    """基线版规则引擎（模拟）：只处理 A/B 类。"""
    return "pass" if s["cls"] in ("A", "B") else "fail"


def run_iteration(s):
    """迭代版规则引擎（模拟）：修复 C 类检索，但模板重构打破 7 条 B 类。"""
    if s["cls"] in ("A", "C"):
        return "pass"
    if s["cls"] == "B":
        return "fail" if s["id"] in REGRESSED else "pass"
    return "fail"


prev = {s["id"]: run_baseline(s) for s in golden}
curr = {s["id"]: run_iteration(s) for s in golden}
by_id = {s["id"]: s for s in golden}


def regression_diff(prev, curr):
    fixed = sorted(k for k in prev if prev[k] == "fail" and curr[k] == "pass")
    regressed = sorted(k for k in prev if prev[k] == "pass" and curr[k] == "fail")
    still = sorted(k for k in curr if curr[k] == "fail")
    return fixed, regressed, still


fixed, regressed, still = regression_diff(prev, curr)
unexplained = [k for k in regressed if k not in EXEMPTIONS]

print("== 1) 黄金集与两版结果（本地模拟引擎，非真实模型） ==")
p_prev = sum(1 for v in prev.values() if v == "pass")
p_curr = sum(1 for v in curr.values() if v == "pass")
print(f"  50 条样本（A18/B22/C8/D2）；基线通过 {p_prev}/50，迭代通过 {p_curr}/50，净变化 {p_curr - p_prev:+d}")

print("\n== 2) 三列对比（修复/退化/未动） ==")
print(f"  修复集   {len(fixed):>2} 条: {fixed}")
print(f"  退化集   {len(regressed):>2} 条: {regressed}")
print(f"  未动失败 {len(still):>2} 条: {still}")
print(f"  其中豁免 {len(regressed) - len(unexplained)} 条，未豁免退化 {len(unexplained)} 条")

print("\n== 3) 回滚判定：退化集有未豁免样本 -> 回滚 ==")
print(f"  未豁免退化样本: {unexplained}")
print(f"  判定: {'必须回滚' if unexplained else '放行'}")
print("  豁免记录（唯一合法形式）:")
for k, why in sorted(EXEMPTIONS.items()):
    print(f"    {k}: {why}")

print("\n== 4) 退化样本明细（归因标签 + 是否豁免） ==")
print("  " + pad("样本", 8) + pad("类", 6) + pad("归因标签", 14) + "豁免")
for k in regressed:
    tag = "模板不匹配"
    print("  " + pad(k, 8) + pad(by_id[k]["cls"], 6) + pad(tag, 14)
          + ("是" if k in EXEMPTIONS else "否 <- 未豁免"))

print("\n== 5) 「总数骗人」对照 ==")
print(f"  只看总通过数: {p_prev} -> {p_curr}（{p_curr - p_prev:+d}），容易宣布「优化有效，合入」")
print(f"  看三列结构:   修复 {len(fixed)} / 退化 {len(regressed)} / 未动失败 {len(still)}，"
      f"其中 {len(unexplained)} 条退化无归因")
print(f"  净额 {p_curr - p_prev:+d} 的背后是「修好 {len(fixed)} 条、弄坏 {len(regressed)} 条」——"
      "错误结构在恶化，用户先撞上的正是原本正常的场景")

print("\n结论：黄金集回归的验收口径是三列对比 + 豁免记录，不是总通过数净额；")
print("读法：1. 修复集 = prev 败 ∩ curr 过；退化集 = prev 过 ∩ curr 败；未动失败集 = curr 仍败，三类互斥不重叠；2. 退化样本无显式豁免（样本 id + 归因 + 理由）就必须回滚，没有商量余地；3. 净额为正同样可能掩盖退化，永远先看结构再看总数；4. 本示例引擎为本地规则模拟，真实接入见 agent-ch05/ch11，方法论与引擎无关。")
