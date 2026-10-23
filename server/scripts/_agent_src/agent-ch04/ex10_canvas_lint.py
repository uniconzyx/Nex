# title: 一页纸画布体检：完整性之外，还要查一致性
# 9 个区块做「必填 + 互相矛盾」两类检查，输出阻断项与警告项。
# 画布最常见的病不是空着，而是每一格都写了，合起来互相打架。

CANVAS = {
    "用户": "所有用户",
    "场景": "电商退款咨询，发生在订单详情页",
    "输入": "用户自然语言问题",
    "输出": "退款建议",
    "失败兜底": "",
    "成本": "单次 0.08 元，预算是 0.05 元",
    "指标": "回答准确率 >= 90%",
    "不做什么": "不做支付、不做物流理赔",
    "人工接管": "置信度 < 0.6 或涉及金额 > 500 元时转人工",
}

REQUIRED = ["用户", "场景", "输入", "输出", "失败兜底", "成本", "指标", "不做什么", "人工接管"]


def lint(c):
    errors, warns = [], []

    for k in REQUIRED:
        if not c.get(k, "").strip():
            errors.append(f"{k} 为空：画布缺一块，评审无法判断边界")

    if c["用户"] in ("所有用户", "全体用户", "用户"):
        errors.append("用户写成了「所有用户」：没有具体角色，就无法定义场景与指标")

    if "订单号" not in c["输入"] and "订单" not in c["输入"]:
        warns.append("输入未提订单号：退款场景无法定位工单，需补上下文来源")

    if "格式" not in c["输出"] and "字段" not in c["输出"]:
        warns.append("输出未定义格式/字段：下游无法解析，也无法验收")

    if "置信度" not in c["输入"] and "置信度" not in c["输出"] and "置信度" in c["人工接管"]:
        warns.append("接管条件用了置信度，但输出里没有置信度字段：触发条件不可实现")

    if "预算" in c["成本"]:
        import re
        nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*元", c["成本"])]
        if len(nums) >= 2 and nums[0] > nums[1]:
            errors.append(f"成本自相矛盾：单次 {nums[0]} 元 > 预算 {nums[1]} 元，单位经济不成立")

    if "准确率" in c["指标"] and "测试集" not in c["指标"] and "抽样" not in c["指标"]:
        warns.append("指标只有准确率，没有测试集/抽样口径：无法复现，也无法判定达标")

    if "不做" not in c["不做什么"]:
        warns.append("「不做什么」未用否定句写清：范围冻结时容易被重新解释")

    return errors, warns


errors, warns = lint(CANVAS)
print("画布 9 格体检（阻断项必须改完才能立项）\n")
for k in REQUIRED:
    v = CANVAS[k]
    status = "空" if not v.strip() else "有"
    print(f"  {k:<6}{status:<3}{v if v else '（缺失）'}")

score = max(0, 100 - 20 * len(errors) - 8 * len(warns))
print(f"\n阻断项 {len(errors)} 个：")
for e in errors:
    print(f"  [ERROR] {e}")
print(f"警告项 {len(warns)} 个：")
for w in warns:
    print(f"  [WARN ] {w}")

print(f"\n完整度得分 {score}/100；上线闸门：{'不通过' if errors else '通过'}")
print("\n读法：「所有用户」不是概括，是没想清楚；「0.08 元 > 0.05 元」不是笔误，是单位经济不成立；")
print("      指标写了准确率却没写测试集，等于没写——评审时无法复现。")
print("结论：画布要先过完整性，再过一致性；阻断项清零才允许进入技术方案。")
