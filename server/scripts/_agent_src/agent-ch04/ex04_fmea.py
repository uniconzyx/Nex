# title: 失败模式 FMEA：RPN = 严重度 × 发生度 × 可检测性
# 8 个 AI 客服失败模式的排序与整改前后对比。RPN 不是精确科学，是排序工具。
# 关键：可检测性 D 越高表示越难发现（10 = 用户投诉了才知道）。

MODES = [
    ("编造退款政策", 9, 4, 6, "答案附条款链接，无引用则拒答"),
    ("上下文截断丢关键信息", 7, 6, 5, "槽位单独存储，不参与截断"),
    ("答非所问", 7, 6, 4, "意图置信度 < 0.7 时澄清"),
    ("泄露他人订单信息", 10, 2, 7, "按用户 ID 强制过滤 + 审计"),
    ("情绪激化", 6, 5, 5, "检测负面情绪升级，主动转人工"),
    ("退款金额算错", 8, 3, 3, "金额走规则引擎，不让模型计算"),
    ("超时无响应", 6, 5, 2, "首字 2s 超时即降级到 FAQ"),
    ("工具调用死循环", 5, 4, 3, "步数上限 6 + 重复动作检测"),
]


def rpn(s, o, d):
    return s * o * d


print("评分 1~10；RPN > 150 视为必须整改，> 250 视为上线阻断项\n")
print(f"{'失败模式':<22}{'S':>3}{'O':>3}{'D':>3}{'RPN':>5}  处置")
rows = []
for name, s, o, d, fix in MODES:
    val = rpn(s, o, d)
    rows.append((val, name, s, o, d, fix))
    flag = "阻断" if val > 250 else ("整改" if val > 150 else "观察")
    print(f"{name:<22}{s:>3}{o:>3}{d:>3}{val:>5}  {flag}：{fix}")

rows.sort(reverse=True)
print("\n按 RPN 排序（Top 4）：")
print(f"{'排名':<4}{'失败模式':<22}{'RPN':>5}{'S×O×D':>12}")
for i, (val, name, s, o, d, fix) in enumerate(rows[:4], 1):
    print(f"{i:<4}{name:<22}{val:>5}{f'{s}×{o}×{d}':>12}")

print("\n整改模拟（对 Top3 加一道可检测/可拦截的闸门）：")
total_before = sum(r[0] for r in rows)
after = 0
for val, name, s, o, d, fix in rows:
    if name == "编造退款政策":
        s2, o2, d2 = s, 3, 2      # 有引用校验，发生率与不可检测性都降
    elif name == "上下文截断丢关键信息":
        s2, o2, d2 = s, 2, 3      # 槽位结构化，不再被截断
    elif name == "答非所问":
        s2, o2, d2 = s, 4, 3      # 澄清降低发生与漏检
    else:
        s2, o2, d2 = s, o, d
    after += rpn(s2, o2, d2)
    if (s2, o2, d2) != (s, o, d):
        print(f"  {name:<22}{val:>4} -> {rpn(s2,o2,d2):>4}（S{s2} O{o2} D{d2}）")

print(f"\n总 RPN：{total_before} -> {after}，降幅 {1 - after/total_before:.0%}")
print("读法：编造政策 S=9 但 D=6——它危险且难发现，所以整改优先级高于 S 更高的信息泄露（O=2）。")
print("结论：RPN 只用来排序，不用来做绝对判断；三个因子必须分别打分，否则会把「严重但罕见」")
print("      和「常见但无害」混为一谈。")
