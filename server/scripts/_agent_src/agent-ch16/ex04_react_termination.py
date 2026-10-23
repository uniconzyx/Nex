# title: ReAct 终止条件：三种白板实现在同一失控场景下的失效对比
# 本地模拟：一个「原地重复」的脚本化失控 Agent + 三种白板上最常见的循环写法。
# 目的：把「只写循环不写终止」的代价变成可度量的步数/token 损失。


def gen_runaway(step):
    """失控场景：同样的 action、同样的参数、同样的 observation（原地重复）。"""
    return ("search", {"q": "库存"}, {"无相关结果"}, 500)


def gen_normal(step):
    """正常任务：第 9 步 FINISH，中间第 4/5 步是一次换参数的合法重试。"""
    if step == 8:
        return ("FINISH", {}, {"已完成"}, 500)
    if step == 3:
        return ("search", {"q": "库存"}, {"无相关结果"}, 500)        # 合法重试：第一次
    if step == 4:
        return ("search", {"q": "库存 2024"}, {"无相关结果"}, 500)   # 合法重试：换参数再来
    return ("lookup", {"table": "orders", "key": f"id{step}"}, {f"row{step}"}, 500)


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a or b) else 1.0


# ---------- 三种白板实现 ----------
def impl_A_no_guard(gen, hard_kill=15):
    """写法 A：while True，没有任何终止条件。harness 只能外部强杀。"""
    steps, tokens, obs_hist = 0, 0, []
    while True:
        action, args, obs, tok = gen(steps)
        steps += 1
        tokens += tok
        obs_hist.append(obs)
        if action == "FINISH":
            return steps, tokens, "FINISH"
        if steps >= hard_kill:                       # 外部强杀，不是代码自己停
            return steps, tokens, "被外部斩断（失控）"


def impl_B_max_steps(gen, max_steps=15):
    """写法 B：只配步数上限。能停，但意味着『已经烧够了才停』。"""
    steps, tokens = 0, 0
    while steps < max_steps:
        action, args, obs, tok = gen(steps)
        steps += 1
        tokens += tok
        if action == "FINISH":
            return steps, tokens, "FINISH"
    return steps, tokens, "ABORT(max_steps)"


def impl_C_three_guards(gen, max_steps=15, token_budget=8000, k=3):
    """写法 C：步数上限 + 预算上限 + 无进展检测（K=3，换参数重置计数）。"""
    steps, tokens, obs_hist, last_args, no_progress = 0, 0, [], None, 0
    while steps < max_steps and tokens < token_budget:
        action, args, obs, tok = gen(steps)
        steps += 1
        tokens += tok
        obs_hist.append(obs)
        if action == "FINISH":
            return steps, tokens, "FINISH"
        same_args = (args == last_args)               # 换参数 = 合法重试，重置计数
        last_args = args
        if same_args:
            no_progress += 1
        else:
            no_progress = 1
        # 无进展 = 同参数连续 K 步，或最近 K 个 observation 两两高度相似
        stagnant = no_progress >= k or (len(obs_hist) >= k and all(
            jaccard(obs_hist[-1], o) >= 0.9 for o in obs_hist[-k:-1]))
        if stagnant:
            return steps, tokens, f"ABORT(无进展检测 K={k})"
    return steps, tokens, "ABORT(兜底)"


print("== 三种白板写法 × 同一失控场景（原地重复，每步 500 tok） ==")
print(f"{'实现':<26}{'停止步数':>8}{'累计token':>10}{'结局':>22}")
rA = impl_A_no_guard(gen_runaway)
rB = impl_B_max_steps(gen_runaway)
rC = impl_C_three_guards(gen_runaway)
for name, r in [("A while True（无终止）", rA), ("B 只配 max_steps=15", rB), ("C 三层检测器", rC)]:
    print(f"{name:<26}{r[0]:>8}{r[1]:>10}{r[2]:>22}")
assert rA[2].startswith("被外部斩断")
assert rB[2] == "ABORT(max_steps)" and rB[0] == 15
assert rC[2].startswith("ABORT(无进展") and rC[0] == 3

saved = 1 - rC[1] / rB[1]
print(f"\n止损账：C 在第 {rC[0]} 步花 {rC[1]} tok 拉闸，比 B（第 {rB[0]} 步/{rB[1]} tok）少烧 {rB[1]-rC[1]} tok（省 {saved:.0%}）")
print("A 更糟：它根本停不下来，只能靠外部强杀——线上等于用户看着转圈到超时。")

print("\n== 阈值 K 的取舍：无进展检测在正常任务上的误杀（任务第 9 步 FINISH，第 4/5 步有合法重试） ==")
for k in (2, 3, 5):
    steps, tokens, end = impl_C_three_guards(gen_normal, k=k)
    verdict = "误杀！" if not end == "FINISH" else "正常放行"
    print(f"K={k}: {verdict}（{end}，共 {steps} 步）")
_, _, end3 = impl_C_three_guards(gen_normal, k=3)
assert end3 == "FINISH", "K=3 不应误杀含合法重试的正常任务"

print("\n结论：max_steps 是兜底保险丝（烧够了才停），无进展检测才是提前拉闸的主力，且 K 必须容忍合法重试；")
print("读法：1. 白板上写 while True 是零分——面试官追问「模型不 FINISH 怎么办」时你必须落到终态集合；2. K=2 会把「换参数重试一次」当死循环误杀，K=5 放过更多真循环，工程上取 3 并要求换参数即重置计数（经验判断）；3. 检测器触发后的动作要分级：先注入「你在重复」提醒换策略，再熔断，不要直接杀任务；4. 这是本地脚本模拟，真实系统里对应 LangGraph 的 recursion_limit + 自定义 should_continue（ch11）。")
