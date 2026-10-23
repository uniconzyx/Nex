# title: Agent 单任务成本与时延分解：12 步调研任务的钱花在哪一步
# 本地模拟：一条手工构造的多步任务 trace（token/时延为教学假设值），不调用真实 LLM/API。
import numpy as np

P_IN, P_OUT = 0.008 / 1000, 0.024 / 1000   # ¥/token（教学假设单价）

# (动作, prompt_tokens, completion_tokens, 模型时延ms, 工具时延ms, 是否浪费步)
TRACE = [
    ("plan 规划",        500,  200,  800,   0, False),
    ("search 查资料",    900,  100,  600, 300, False),
    ("search 重复查询", 1200,   80,  550, 250, True),   # 与上步同参数：幂等可省
    ("read_file 读文件", 1500,  150,  700, 400, False),
    ("calc 算指标",     1800,   60,  400,  50, False),
    ("think 空转一步",  2100,  300,  900,   0, True),   # 只思考不行动：无进展
    ("search 又重复",   2400,   90,  580, 260, True),   # 第三次同参数查询
    ("draft 写初稿",    2700,  600, 1500,   0, False),
    ("review 自审",     3300,  200,  800,   0, False),
    ("revise 修改",     3600,  500, 1300,   0, False),
    ("send_email 发出", 3900,  100,  500, 350, False),
    ("FINISH 收尾",    4100,  150,  600,   0, False),
]


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


print("== 12 步任务逐步账本 ==")
print(f"{'#':>3} {pad('动作', 20)}{'prompt':>7}{'output':>7}{'模型ms':>7}{'工具ms':>7}{'本步成本¥':>10}  标记")
for i, (act, p, o, ml, tl, waste) in enumerate(TRACE):
    c = p * P_IN + o * P_OUT
    print(f"{i:>3} {pad(act, 20)}{p:>7}{o:>7}{ml:>7}{tl:>7}{c:>10.4f}  {'浪费' if waste else 'ok'}")

tot_p = sum(t[1] for t in TRACE)
tot_o = sum(t[2] for t in TRACE)
tot_c = tot_p * P_IN + tot_o * P_OUT
ml_all = np.array([t[3] for t in TRACE])
tl_all = np.array([t[4] for t in TRACE])
waste_idx = [i for i, t in enumerate(TRACE) if t[5]]
waste_c = sum(TRACE[i][1] * P_IN + TRACE[i][2] * P_OUT for i in waste_idx)
waste_ms = sum(TRACE[i][3] + TRACE[i][4] for i in waste_idx)
print(f"\n合计：{tot_p + tot_o} token（prompt {tot_p} / output {tot_o}），成本 ¥{tot_c:.4f}，"
      f"时延 {ml_all.sum() + tl_all.sum():.0f} ms（模型 {ml_all.sum():.0f} + 工具 {tl_all.sum():.0f}）")
print(f"浪费步（{len(waste_idx)} 个：重复查询 2 次 + 空转 1 次）：成本 ¥{waste_c:.4f}"
      f"（{waste_c / tot_c:.0%}），时延 {waste_ms:.0f} ms（{waste_ms / (ml_all.sum() + tl_all.sum()):.0%}）")

# ---------- ASCII 堆叠条形图：每步时延 = 模型(█) + 工具(▓) ----------
print("\n== 时延分解图（█=模型 ▓=工具，1 格 ≈ 60ms） ==")
SCALE = 60
for i, (act, p, o, ml, tl, waste) in enumerate(TRACE):
    bar = "█" * round(ml / SCALE) + "▓" * round(tl / SCALE)
    print(f"{i:>3} {pad(act, 20)}{bar} {ml + tl:>5}ms{'  <- 浪费' if waste else ''}")

# ---------- 上下文累积效应：prompt 随步数线性增长 ----------
steps = np.arange(len(TRACE))
prompts = np.array([t[1] for t in TRACE], dtype=float)
print("\n== 上下文累积：第 k 步的 prompt token ==")
print("  " + " ".join(f"{p:.0f}" for p in prompts))
print(f"prompt 从第 0 步 {prompts[0]:.0f} 涨到第 11 步 {prompts[-1]:.0f}，"
      f"平均每步 +{(prompts[-1] - prompts[0]) / (len(TRACE) - 1):.0f} token——后半程每步都在为前半程买单")

# 压缩对比：早期历史换成固定 300 token 摘要（模拟，效果取上界）
new_tokens = np.diff(np.concatenate([[0], prompts]))          # 每步净新增内容
comp_prompts = 300 + new_tokens                                # 摘要 + 当步新增
comp_c = comp_prompts.sum() * P_IN + tot_o * P_OUT
print(f"\n模拟「早期历史摘要化」（摘要固定 300 token + 当步净新增）：")
print(f"prompt 总量 {tot_p} -> {comp_prompts.sum():.0f}（-{1 - comp_prompts.sum() / tot_p:.0%}），"
      f"总成本 ¥{tot_c:.4f} -> ¥{comp_c:.4f}（-{1 - comp_c / tot_c:.0%}）")

# 分位数
step_ms = ml_all + tl_all
worst = int(np.argmax(step_ms))
print(f"\n步时延 P50 = {np.percentile(step_ms, 50):.0f} ms，"
      f"P95 = {np.percentile(step_ms, 95):.0f} ms；最慢一步 = 第 {worst} 步"
      f"（{step_ms.max():.0f} ms，{TRACE[worst][0]}）")

print("\n结论：Agent 的成本不是「一次调用」而是「一条 trace」，上下文累积 + 重复动作是两大漏斗，")
print("读法：1. prompt token 随步数线性累积是结构性浪费——后半程每步都在为前半程买单，摘要化/检查点裁剪是主要对冲；2. 重复调用与空转步占了 20% 成本、23% 时延，幂等键（ex03）与无进展检测（ex07）就是拦它们的；3. 时延大头在模型侧（draft/revise 两步输出长），工具时延要单独看 P95 而不是均值；4. 记账必须按步落盘：动作/prompt/output/双时延/成本五元组，缺一项就无法归因（对应 project.json 的 trace 回放）；5. 单价为教学假设，真实以服务商为准，但账本结构一致。")
