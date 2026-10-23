# title: 死循环防护三检测器：步数上限、预算上限与无进展检测谁先拉闸
# 本地模拟：三类脚本化失控 Agent + 一类正常任务，检测器纯本地判定，不调用真实 LLM/API。

# ---------- 1) 场景生成器：每步产出 (action, args, observation词集, token消耗) ----------
def gen_A(step):   # A 类：原地重复——同样的动作、同样的 observation
    return ("search", {"q": "库存"}, {"无相关结果"}, 500)

def gen_B(step):   # B 类：空转烧钱——动作在轮换、observation 永远一样
    acts = ["list_dir", "read_file", "grep"]
    return (acts[step % 3], {"path": "/data"}, {"a.txt", "b.txt", "README"}, 800)

def gen_C(step):   # C 类：只规划不动手——烧上下文不烧工具
    return (None, {}, set(), 300)

def gen_normal(step):  # 正常任务：10 步完成，中间含一次「合法重试」（连续 2 步同 observation）
    if step == 9:
        return ("FINISH", {}, {"已完成"}, 400)
    if step == 4:
        return ("search", {"q": "库存"}, {"无相关结果"}, 400)        # 合法重试：第一次
    if step == 5:
        return ("search", {"q": "库存 2024"}, {"无相关结果"}, 400)   # 合法重试：换参数再来
    acts = ["list_dir", "read_file", "grep"]
    return (acts[step % 3], {"path": f"/data/{step}"}, {f"file{step}.txt", "README"}, 400)

SCENARIOS = [("A 原地重复", gen_A), ("B 空转烧钱", gen_B),
             ("C 只规划不动手", gen_C), ("D 正常任务", gen_normal)]


# ---------- 2) 三个检测器 ----------
def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def run_with_detectors(gen, step_limit=30, token_budget=15000, no_progress_k=3, max_steps=60):
    """跑一个场景，记录三个检测器各自的触发步与触发时累计 token。"""
    fired = {"D1 步数上限": None, "D2 预算上限": None, "D3 无进展": None}
    obs_hist, tokens, no_action, done = [], 0, 0, False
    for step in range(max_steps):
        action, args, obs, tok = gen(step)
        tokens += tok
        if action is None:
            no_action += 1
        else:
            no_action = 0
        obs_hist.append(obs)
        # D3：连续 K 步无 action，或最近 K 个 observation 两两高度相似
        stagnant = no_action >= no_progress_k
        if not stagnant and len(obs_hist) >= no_progress_k:
            recent = obs_hist[-no_progress_k:]
            stagnant = all(jaccard(recent[-1], o) >= 0.9 for o in recent[:-1])
        if stagnant and fired["D3 无进展"] is None:
            fired["D3 无进展"] = (step + 1, tokens)
        if step + 1 >= step_limit and fired["D1 步数上限"] is None:
            fired["D1 步数上限"] = (step + 1, tokens)
        if tokens >= token_budget and fired["D2 预算上限"] is None:
            fired["D2 预算上限"] = (step + 1, tokens)
        if action == "FINISH":
            done = True
            break
    return fired, done, tokens


def fmt(v):
    return f"第{v[0]}步/{v[1]}tok" if v else "未触发"


print("== 三检测器在四类场景上的触发点（步数/累计token） ==")
print(f"{'场景':<14}{'D1 步数上限':>16}{'D2 预算上限':>16}{'D3 无进展':>16}{'最早拉闸':>12}")
results = {}
for name, gen in SCENARIOS:
    fired, done, toks = run_with_detectors(gen)
    results[name] = (fired, done, toks)
    order = sorted((v[0], k) for k, v in fired.items() if v)
    first = order[0][1].split()[0] if order else "无"
    print(f"{name:<14}{fmt(fired['D1 步数上限']):>16}{fmt(fired['D2 预算上限']):>16}"
          f"{fmt(fired['D3 无进展']):>16}{first:>12}")

# 失控场景必须被 D3 早早拉闸；正常任务三个检测器都不能误杀
for name in ("A 原地重复", "B 空转烧钱", "C 只规划不动手"):
    f = results[name][0]
    assert f["D3 无进展"] and f["D3 无进展"][0] == 3, f"{name} 应在第 3 步被 D3 拦下"
assert results["D 正常任务"][1] and all(v is None for v in results["D 正常任务"][0].values())

# 拉闸省下的账：D3 相对 D1 少烧多少 token
print("\n== D3 相对 D1 的止损账（失控场景） ==")
for name in ("A 原地重复", "B 空转烧钱", "C 只规划不动手"):
    f = results[name][0]
    saved = f["D1 步数上限"][1] - f["D3 无进展"][1]
    print(f"{name}: D3 第 {f['D3 无进展'][0]} 步花 {f['D3 无进展'][1]} tok 拉闸，"
          f"比 D1（第 {f['D1 步数上限'][0]} 步/{f['D1 步数上限'][1]} tok）少烧 {saved} tok"
          f"（省 {1 - f['D3 无进展'][1] / f['D1 步数上限'][1]:.0%}）")

# ---------- 3) 阈值 K 的取舍：K=2 会误杀「合法重试」 ----------
print("\n== 无进展阈值 K 的取舍（D 正常任务） ==")
for k in (2, 3, 5):
    fired, done, _ = run_with_detectors(gen_normal, no_progress_k=k)
    verdict = "误杀！" if fired["D3 无进展"] else "正常放行"
    print(f"K={k}: {verdict}（任务在第 10 步 FINISH，中间第 5/6 步有连续 2 步同 observation 的合法重试）")

print("\n结论：步数和预算上限是「兜底保险丝」，无进展检测才是「提前拉闸」的主力，且阈值要容忍合法重试，")
print("读法：1. D1/D2 结构简单必配，但它们意味着「已经烧够了才停」——A 类原地重复要烧满 30 步/15000 token 才停；2. D3（observation 相似度 + 连续无动作）在第 3 步就拉闸，省 90% 的浪费；3. K 是误杀/漏杀的权衡：K=2 把「换参数重试一次」也当死循环，K=5 放过更多真循环，工程上取 3 并要求「换参数即重置计数」（经验判断）；4. 检测器触发后应有分级动作：先提醒换策略，再熔断，不要直接杀任务；5. 真实系统里这就是 LangGraph 的 recursion_limit + 自定义 should_continue，无进展检测要自己写。")
