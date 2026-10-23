# title: 面试覆盖度与复习优先级：从题库自评到三轮失分点收敛
# 本地模拟：内置题库 + 自评掌握度 + 三轮模拟失分记录，不调用任何外部服务。
# 目的：把「复习计划」变成可度量的工程问题——覆盖率、优先级分、失分点收敛曲线。


# ---------- 1) 题库：按面试出现频率给权重（1-5），自评掌握度（0-1，固定值模拟） ----------
QUESTION_BANK = [
    # (类别, 题目, 出现频率权重, 自评掌握度)
    ("Transformer", "Q/K/V 为什么是三个矩阵", 5, 0.9),
    ("Transformer", "注意力复杂度与显存占用", 5, 0.6),
    ("Transformer", "RoPE 位置编码的原理", 4, 0.4),
    ("Transformer", "LayerNorm 的位置与为什么", 3, 0.8),
    ("RAG", "切分策略与重叠窗口的代价", 5, 0.5),
    ("RAG", "混合检索与分数融合", 4, 0.3),
    ("RAG", "召回率 90% 但答案错先改哪层", 5, 0.7),
    ("RAG", "重排模型值不值得加一跳", 4, 0.6),
    ("RAG", "RAG 评估怎么做", 4, 0.2),
    ("Agent", "ReAct 状态机与 trace", 5, 0.8),
    ("Agent", "死循环防护三检测器", 5, 0.9),
    ("Agent", "工具 schema 与幂等", 4, 0.5),
    ("Agent", "上下文压缩策略", 4, 0.4),
    ("Agent", "多智能体什么时候值得上", 3, 0.6),
    ("Agent", "记忆的写入与衰减", 3, 0.3),
    ("部署", "显存账本怎么估", 5, 0.7),
    ("部署", "vLLM 连续批处理原理", 4, 0.3),
    ("部署", "量化对精度的影响", 4, 0.5),
    ("部署", "限流与降级设计", 4, 0.6),
    ("部署", "灰度与回滚", 3, 0.7),
    ("系统设计", "企业知识库 Agent 容量账", 5, 0.5),
    ("行为面", "一次冲突的处理", 4, 0.6),
    ("行为面", "一次失败与复盘", 4, 0.7),
    ("行为面", "多任务优先级取舍", 4, 0.5),
]

MASTERED = 0.8      # 掌握度阈值：能四段式答完（结论/机制/数字/边界）算掌握
print("== 1) 覆盖率总览 ==")
cats = {}
for cat, _, _, c in QUESTION_BANK:
    a, m = cats.get(cat, (0, 0))
    cats[cat] = (a + 1, m + (1 if c >= MASTERED else 0))
total = len(QUESTION_BANK)
total_m = sum(m for _, m in cats.values())
print(f"{'类别':<12}{'题数':>5}{'已掌握':>7}{'覆盖率':>8}")
for cat, (n, m) in cats.items():
    print(f"{cat:<12}{n:>5}{m:>7}{m/n:>8.0%}")
print(f"{'合计':<12}{total:>5}{total_m:>7}{total_m/total:>8.0%}")

# ---------- 2) 复习优先级 = 权重 × (1 - 掌握度) ----------
print("\n== 2) 复习优先级 Top-8（权重 × 未掌握度） ==")
ranked = sorted(QUESTION_BANK, key=lambda t: -t[2] * (1 - t[3]))
print(f"{'优先级':<6}{'类别':<12}{'权重':>4}{'掌握度':>7}  题目")
for i, (cat, q, w, c) in enumerate(ranked[:8], 1):
    print(f"{w*(1-c):<6.1f}{cat:<12}{w:>4}{c:>7.1f}  {q}")
top1 = ranked[0]
assert top1[0] == "RAG" and top1[1] == "RAG 评估怎么做", top1
print(f"  优先级最高：「{top1[1]}」——高频（权重 {top1[2]}）且掌握度仅 {top1[3]}")

# ---------- 3) 三轮模拟面试的失分点收敛 ----------
print("\n== 3) 三轮模拟面试：同类失分点收敛（验收口径） ==")
rounds = [
    ("第一轮", {"答非所问": 3, "缺数字": 2, "无边界": 2, "抢话": 2}),
    ("第二轮", {"答非所问": 1, "缺数字": 1, "无边界": 1, "抢话": 1}),
    ("第三轮", {"答非所问": 0, "缺数字": 0, "无边界": 0, "抢话": 0}),
]
print(f"{'轮次':<8}{'失分点总数':>10}  明细")
prev = None
for name, misses in rounds:
    n = sum(misses.values())
    detail = "、".join(f"{k}×{v}" for k, v in misses.items() if v) or "同类失分点清零"
    print(f"{name:<8}{n:>10}  {detail}")
    if prev is not None:
        assert n <= prev, "失分点应逐轮收敛（不增）"
    prev = n
first_total = sum(rounds[0][1].values())
last_total = sum(rounds[2][1].values())
print(f"\n  收敛率：第一轮 {first_total} 个 -> 第三轮 {last_total} 个（同题复测，验收标准 = 清零）")
assert last_total == 0 and first_total > 0

# ---------- 4) 复习计划的工程判据 ----------
print("\n== 4) 计划自检 ==")
weak_high_freq = [q for _, q, w, c in QUESTION_BANK if w >= 4 and c < MASTERED]
print(f"  高频未掌握题 {len(weak_high_freq)} 道 —— 这是复习计划的全部范围（低频题不进计划）")
plan_hours = len(weak_high_freq) * 1.5
print(f"  按每题 1.5h（学 + 白板写 + 录像自测）估：约 {plan_hours:.0f} 小时，两周内可完成")
assert len(weak_high_freq) > 0

print("\n结论：面试准备是覆盖率问题不是感觉问题——覆盖率按「能四段式答完」计，优先级 = 频率 × 未掌握度；")
print("读法：1. 掌握度阈值定在 0.8（结论/机制/数字/边界四段齐），自评低于它就是没掌握，与「看过」无关；2. 复习范围只收高频未掌握题，低频题进计划是时间浪费；3. 三轮录像的验收口径是同类失分点清零，不是「感觉越来越好」——失分点要按轮次可对比；4. 本示例的权重与掌握度是固定模拟值，真实计划按自己的题库自评表填写（对应 project.json 任务三）。")
