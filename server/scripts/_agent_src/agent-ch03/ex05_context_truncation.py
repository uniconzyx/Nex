# title: 上下文截断策略对比：截头、截尾、头尾各半、抽取式摘要
# 用 12 轮对话、5 个「决策必需事实」做受控实验：预算 80 token，测保留率与可答性。
# 这不是「哪个策略更好」的问题，而是「你的任务把信息放在哪」的问题。

TURNS = [
    ("system", "你是售后客服。退款规则：签收 7 天内可无理由退。", 14, ["F1"]),
    ("user", "耳机坏了，订单号 A123，金额 899 元。", 15, ["F2", "F3"]),
    ("assistant", "已记录。请问是质量问题还是不喜欢？", 12, []),
    ("user", "右耳没声音，试过换设备了。", 11, []),
    ("assistant", "了解。需要我帮您申请退货吗？", 10, []),
    ("user", "可以，但我想先确认截止日期。", 12, []),
    ("assistant", "按签收日算，最晚 10 月 28 日提交。", 13, ["F4"]),
    ("user", "那运费谁出？", 8, []),
    ("assistant", "质量问题由我们承担，上门取件。", 12, []),
    ("user", "好，另外怎么联系人工？", 10, []),
    ("assistant", "可拨打 400-800-1234 转 2。", 11, ["F5"]),
    ("user", "行，帮我提交吧。", 8, []),
]

FACTS = {
    "F1": "7 天无理由",
    "F2": "订单 A123",
    "F3": "金额 899",
    "F4": "截止 10-28",
    "F5": "人工 400-800-1234",
}
QUESTIONS = [
    ("Q1 能不能退", {"F1"}),
    ("Q2 订单号", {"F2"}),
    ("Q3 退多少", {"F3"}),
    ("Q4 截止日", {"F4"}),
    ("Q5 人工电话", {"F5"}),
]
BUDGET = 80


def pack(selected):
    return sum(TURNS[i][2] for i in selected), {f for i in selected for f in TURNS[i][3]}


def take_head(budget):
    idx, used = [], 0
    for i, t in enumerate(TURNS):
        if used + t[2] > budget:
            break
        idx.append(i)
        used += t[2]
    return idx


def take_tail(budget):
    idx, used = [], 0
    for i in range(len(TURNS) - 1, -1, -1):
        if used + TURNS[i][2] > budget:
            break
        idx.append(i)
        used += TURNS[i][2]
    return idx


head = take_head(BUDGET)
tail = take_tail(BUDGET)
head_half = take_head(BUDGET // 2)
tail_half = take_tail(BUDGET - sum(TURNS[i][2] for i in head_half))
KEY = ("规则", "订单", "金额", "截止", "人工")
keep = [i for i, t in enumerate(TURNS) if t[3] or any(k in t[1] for k in KEY)]

strategies = {
    "截头 head": pack(head),
    "截尾 tail": pack(tail),
    "头尾各半": pack(sorted(set(head_half + tail_half))),
    "抽取式摘要": pack(sorted(keep)),
}

print(f"预算 {BUDGET} token，共 {len(TURNS)} 轮；5 个事实分布在首轮、第 2 轮、第 7 轮、第 11 轮")
print(f"（token 为模拟计数；真实接入要用厂商 tokenizer 复核，见 ex06）\n")
print(f"{'策略':<12}{'使用token':>9}{'保留事实':>8}{'可答问题':>8}{'信息损失':>8}  丢失的事实")
for name, (tok, facts) in strategies.items():
    answerable = sum(1 for _, need in QUESTIONS if need <= facts)
    loss = 1 - len(facts) / len(FACTS)
    missing = ",".join(sorted(FACTS.keys() - facts)) or "-"
    print(f"{name:<12}{min(tok, 999):>9}{len(facts):>8}{answerable:>8}{loss:>8.0%}  {missing}")

print("读法：截头保住了规则但丢掉了截止日与人工电话；截尾保住了结尾却把系统规则一起丢了；")
print("      头尾各半是通用兜底；抽取式摘要用同样的预算保住了全部 5 个事实，但依赖你预先知道槽位。")
print("结论：截断策略必须由「任务把关键信息放在哪」决定；")
print("      系统提示与安全规则永远不要参与截断，先固定保留，再对历史做压缩。")
