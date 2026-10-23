# title: 多智能体 handoff 与成本累积账本：每一跳交接都要计价
# 本地模拟：三角色流水线（分诊/执行/审核）+ 成本账本，不调用真实 LLM/API。
import numpy as np

rng = np.random.default_rng(11)
N_TASKS = 20
MAX_WORKER_ATTEMPTS = 3

# ---------- 1) 角色与单价（教学假设价） ----------
ROLES = {
    "triage":   {"in": 200,  "out": 50,  "p_in": 0.001, "p_out": 0.002, "skill": "分类"},
    "worker":   {"in": 1200, "out": 400, "p_in": 0.008, "p_out": 0.024, "skill": "主力执行"},
    "reviewer": {"in": 800,  "out": 100, "p_in": 0.002, "p_out": 0.004, "skill": "质量审核"},
}


def spend(role, expensive_triage=False):
    r = ROLES[role]
    price = ROLES["worker"] if (role == "triage" and expensive_triage) else r
    return {"calls": 1, "tok": r["in"] + r["out"],
            "cost": r["in"] * price["p_in"] / 1000 + r["out"] * price["p_out"] / 1000}


# ---------- 2) 预生成随机源：保证「角色错配」对照只差价格、不差运气 ----------
difficulty = np.round(rng.uniform(0.1, 0.9, N_TASKS), 3)
noise = np.round(rng.normal(0, 0.05, N_TASKS), 4)
rolls = np.round(rng.random((N_TASKS, MAX_WORKER_ATTEMPTS)), 4)


def worker_quality(d, attempt, n):
    """执行质量：难度越高越低；返工有改进但边际递减。"""
    return min(0.99, 0.85 - 0.75 * d + n + 0.12 * attempt - 0.02 * attempt * attempt)


def review_pass(q):
    return min(0.98, max(0.05, 0.25 + 0.6 * q))


# ---------- 3) 跑流水线：triage -> worker -> reviewer，可返工 ----------
def run_pipeline(i, expensive_triage=False):
    d, n = difficulty[i], noise[i]
    ledger = {r: {"calls": 0, "tok": 0, "cost": 0.0} for r in ROLES}
    handoffs, last, attempts = 0, "triage", []

    def do(role):
        nonlocal last, handoffs
        s = spend(role, expensive_triage)
        ledger[role]["calls"] += s["calls"]
        ledger[role]["tok"] += s["tok"]
        ledger[role]["cost"] += s["cost"]
        handoffs += (last != role)
        last = role

    do("triage")
    for attempt in range(MAX_WORKER_ATTEMPTS):
        do("worker")
        q = worker_quality(d, attempt, n)
        do("reviewer")
        ok = rolls[i, attempt] < review_pass(q)
        attempts.append({"attempt": attempt + 1, "q": round(q, 3),
                         "cost": round(sum(v["cost"] for v in ledger.values()), 4), "ok": bool(ok)})
        if ok:
            break
    # 补齐到 MAX_WORKER_ATTEMPTS：提前成功的任务在更大上限下成本/结果不变
    while len(attempts) < MAX_WORKER_ATTEMPTS:
        attempts.append(dict(attempts[-1]))
    return {"ok": attempts[-1]["ok"], "attempts": attempts, "handoffs": handoffs,
            "cost": round(sum(v["cost"] for v in ledger.values()), 4), "ledger": ledger}


results = [run_pipeline(i) for i in range(N_TASKS)]

# ---------- 4) 账本汇总（先算总账再算占比） ----------
tot_cost = sum(r["cost"] for r in results)
tot_calls = sum(r["ledger"][x]["calls"] for r in results for x in ROLES)
tot_tok = sum(r["ledger"][x]["tok"] for r in results for x in ROLES)
print("== 三角色流水线总账本（20 个任务） ==")
print(f"{'角色':<10}{'调用次数':>8}{'总token':>10}{'成本(¥)':>10}{'成本占比':>9}")
for role in ROLES:
    c = sum(r["ledger"][role]["calls"] for r in results)
    t = sum(r["ledger"][role]["tok"] for r in results)
    k = sum(r["ledger"][role]["cost"] for r in results)
    print(f"{role:<10}{c:>8}{t:>10}{k:>10.3f}{k / tot_cost:>8.1%}")
succ = sum(r["ok"] for r in results)
print(f"合计：{tot_calls} 次调用 / {tot_tok} token / ¥{tot_cost:.3f}")
print(f"成功率 {succ}/{N_TASKS} = {succ / N_TASKS:.0%}，平均每任务成本 ¥{tot_cost / N_TASKS:.4f}，"
      f"平均 handoff {np.mean([r['handoffs'] for r in results]):.1f} 次")

# ---------- 5) 边际分析：把返工上限设为 1/2/3 轮时的成功率与总成本 ----------
print("\n== 返工轮次上限的边际账（同一批任务、同一批随机源） ==")
print(f"{'上限k':>6}{'成功率':>8}{'总成本(¥)':>11}{'边际成本/次成功':>16}")
prev_succ, prev_cost = 0, 0.0
for k in (1, 2, 3):
    s = sum(r["attempts"][k - 1]["ok"] for r in results)   # 前 k 轮内是否已成功
    c = sum(r["attempts"][k - 1]["cost"] for r in results)  # 跑到第 k 轮的累计成本
    delta_s = s - prev_succ
    marg = (c - prev_cost) / delta_s if delta_s else float("inf")
    print(f"{k:>6}{s / N_TASKS:>8.0%}{c:>11.3f}"
          f"{(f'¥{marg:.4f}' if delta_s else '无新增成功'):>16}")
    prev_succ, prev_cost = s, c

# ---------- 6) 难度分档：难任务的成本结构 ----------
print("\n== 按难度分档（易 d<0.35 / 中 0.35~0.65 / 难 d>0.65） ==")
for tag, lo, hi in (("易", 0.0, 0.35), ("中", 0.35, 0.65), ("难", 0.65, 1.0)):
    idx = [i for i, d in enumerate(difficulty) if lo <= d < hi]
    if not idx:
        continue
    s = sum(results[i]["ok"] for i in idx) / len(idx)
    c = np.mean([results[i]["cost"] for i in idx])
    h = np.mean([results[i]["handoffs"] for i in idx])
    print(f"{tag}（{len(idx)} 题）：成功率 {s:.0%}，平均成本 ¥{c:.4f}，平均 handoff {h:.1f} 次")

# ---------- 7) 角色错配对照：triage 也用主力贵模型（随机源完全一致） ----------
results2 = [run_pipeline(i, expensive_triage=True) for i in range(N_TASKS)]
tot2 = sum(r["cost"] for r in results2)
assert sum(r["ok"] for r in results2) == succ, "同一随机源下角色错配不应改变成功率"
print(f"\n角色错配：triage 换成主力模型后总成本 ¥{tot2:.3f} vs ¥{tot_cost:.3f}"
      f"（+{(tot2 / tot_cost - 1):.0%}），成功率不变 {succ}/{N_TASKS}")
assert tot2 > tot_cost

print("\n结论：多智能体的每一跳 handoff 都是一次全额计费的调用，成功率是用成本和交接次数买来的，")
print("读法：1. 账本必须按角色分开记：worker 占成本 89.8%（单价高、上下文长），triage/reviewer 应该用便宜模型；2. 返工的边际增益递减：上限从 1 到 2 买 +35pp 成功率花 ¥0.233，从 2 到 3 只买 +15pp 仍花 ¥0.085——轮次越深同样的钱买到的安全越少，叠加时延与人工事故成本后上限通常设 2 轮（经验判断）；3. 难任务三重地狱：成功率 75% 最低、单均成本与 handoff 却最高，分档账本让问题现形；4. 角色错配是纯浪费：triage 换贵模型 +7% 成本、成功率不变；5. 真实框架（AutoGen/CrewAI/LangGraph）的 handoff 还要传全量上下文，跨角色重复传 prompt 是隐性成本，要用共享黑板压缩（见 concept/03）。")
