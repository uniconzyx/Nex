# title: 选题评分卡：三维加权、一票否决与两套权重下的排序变化
# 本地确定性模拟：不调用任何外部服务，仅演示「选题决策」的判定逻辑。


def dw(s):
    """终端显示宽度：中文按 2 列。"""
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


DIMS = ("痛感", "可行", "差异")
WEIGHTS = {"学习型(可行优先)": (0.40, 0.35, 0.25), "作品集(差异优先)": (0.25, 0.30, 0.45)}
FLOOR = 3.5

# 四个候选选题（分均为人工评估值：1=不可用 5=优秀）
IDEAS = {
    "周报助手": (4, 5, 3),
    "文档问答": (5, 4, 2),
    "通用聊天框": (2, 5, 1),
    "代码审查机器人": (4, 3, 5),
}


def evaluate(dims, weights):
    veto = [n for n, v in zip(DIMS, dims) if v <= 2]
    total = sum(v * w for v, w in zip(dims, weights))
    if veto:
        verdict = "否决(" + ",".join(veto) + ")"
    else:
        verdict = "通过" if total >= FLOOR else "低于阈值,建议换题"
    return total, verdict


print("== 1) 两套权重下的选题排序（一票否决项永远垫底） ==")
for profile, w in WEIGHTS.items():
    print(f"\n  [{profile}]  权重 痛感{w[0]:.2f}/可行{w[1]:.2f}/差异{w[2]:.2f}")
    print("  " + pad("选题", 18) + pad("痛感", 8) + pad("可行", 8) + pad("差异", 8)
          + pad("加权分", 10) + "判定")
    rows = sorted(IDEAS.items(), key=lambda kv: (bool(evaluate(kv[1], w)[1].startswith("否决")),
                                                 -evaluate(kv[1], w)[0]))
    for name, dims in rows:
        total, verdict = evaluate(dims, w)
        cells = [pad(name, 18)] + [pad(str(v), 8) for v in dims] + [pad(f"{total:.2f}", 10), verdict]
        print("  " + "".join(cells))

print("\n== 2) 一票否决 vs 纯加权：为什么否决必须先于加权 ==")
name, dims = "文档问答", IDEAS["文档问答"]
pure = sum(v * w for v, w in zip(dims, WEIGHTS["学习型(可行优先)"]))
total, verdict = evaluate(dims, WEIGHTS["学习型(可行优先)"])
print(f"  {name}: 纯加权 {pure:.2f}（floor={FLOOR}，看似可过）")
print(f"  {name}: 一票否决后 -> {verdict}")
print("  差异=2 意味着做出来与现成方案拉不开差距，加权补救不了致命短板")

print("\n== 3) 权重敏感性的正确用法：换项目就换权重，而不是换结论 ==")
a, b = "周报助手", "代码审查机器人"
for profile, w in WEIGHTS.items():
    ta, va = evaluate(IDEAS[a], w)
    tb, vb = evaluate(IDEAS[b], w)
    lead = a if ta > tb else b
    print(f"  {profile}: {a}={ta:.2f}({va}) vs {b}={tb:.2f}({vb}) -> {lead} 领先")
print("  同一批候选在不同权重下换头名 = 权重必须在选题前写定，不能看结果再调")

print("\n结论：选题评分卡把「感觉不行」变成可复核的判定——任一维 <=2 一票否决，其余按预设权重加权；")
print("读法：1. 否决必须先于加权：致命短板（没人要/做不完/没差别）不能用高分维度补救；2. 阈值 <=2 而不是 <3：3 分是勉强及格可补救，2 分是硬伤；3. 权重按项目性质（学习型/作品集）预先写定，看结果再调权重是自欺；4. 本示例为纯本地模拟，真实评分需要 3 个真实用户的痛点反馈作输入。")
