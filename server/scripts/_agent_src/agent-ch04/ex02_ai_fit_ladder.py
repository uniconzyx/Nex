# title: AI 适用性四档判断：规则 / 分类 / 生成 / Agent
# 用决策树 + 8 个案例，把「要不要上大模型」变成可复盘的判断，而不是直觉。
# 四档的成本与稳定性差异是数量级的：越往后越贵、越不稳、越需要兜底。

CASES = [
    ("发票金额 = 单价 × 数量 是否一致", "规则", True, False, False),
    ("工单自动打标（8 个类目，历史 2 万条标注）", "分类", False, True, False),
    ("把会议录音转成 300 字纪要", "生成", False, False, False),
    ("退款资格判定（签收 7 天内且未拆封）", "规则", True, False, False),
    ("商品详情页文案生成（5 种语气）", "生成", False, False, False),
    ("查订单状态并修改收货地址", "Agent", False, False, True),
    ("评论情感三分类（正/中/负）", "分类", False, True, False),
    ("生成周报并发送到主管邮箱", "Agent", False, False, True),
]

TIERS = {
    "规则": {"latency": "<10ms", "cost": "0.001 元/千次", "stability": "99.99%", "risk": "规则覆盖不全"},
    "分类": {"latency": "10~50ms", "cost": "0.1 元/千次", "stability": "97%~99%", "risk": "标签漂移/长尾"},
    "生成": {"latency": "0.5~3s", "cost": "3~15 元/千次", "stability": "85%~95%", "risk": "幻觉/不可复现"},
    "Agent": {"latency": "3~30s", "cost": "20~200 元/千次", "stability": "70%~90%", "risk": "工具失败/死循环"},
}


def classify(rule_ok, labeled, needs_tool):
    """决策树：先问能不能用确定性规则，再问有没有标签，最后问要不要多步执行。"""
    if rule_ok:
        return "规则", "输出可由固定规则无歧义判定"
    if labeled:
        return "分类", "输出是封闭标签集且有标注样本"
    if needs_tool:
        return "Agent", "需要多步执行、调用外部工具或维护状态"
    return "生成", "开放文本输出，无固定标签"


print(f"决策顺序：确定性规则 → 有标注的分类 → 需要工具/多步的 Agent → 其余归生成\n")
print(f"{'案例':<34}{'判定':<6}{'依据':<28}{'延迟':>8}{'稳定性':>9}")
ok = 0
for text, expect, rule_ok, labeled, needs_tool in CASES:
    tier, why = classify(rule_ok, labeled, needs_tool)
    ok += tier == expect
    print(f"{text:<34}{tier:<6}{why:<28}{TIERS[tier]['latency']:>8}{TIERS[tier]['stability']:>9}")

print(f"\n判定一致率：{ok}/{len(CASES)}")
print(f"\n{'档位':<6}{'单次成本带':<18}{'典型失败':<18}{'必备兜底'}")
fallback = {"规则": "默认拒绝 + 人工复核", "分类": "置信度阈值 + 弃权类",
            "生成": "引用校验 + 人工抽检", "Agent": "步骤上限 + 幂等 + 转人工"}
for tier in ("规则", "分类", "生成", "Agent"):
    t = TIERS[tier]
    print(f"{tier:<6}{t['cost']:<18}{t['risk']:<18}{fallback[tier]}")

print("\n读法：同一句「AI 客服」可能落在四个档位——查订单是 Agent，判退款资格是规则，")
print("      回答政策问题是生成，工单打标是分类。选错档位，成本和稳定性会差两个数量级。")
print("结论：能用规则就别用模型；能用分类就别用生成；只有「多步 + 工具 + 状态」才上 Agent。")
