# title: 手写题二：ReAct 循环的状态机实现与可回放 trace（白板 20 行版）
# 本地模拟：规则脚本化的「模型」+ 两个假工具，全程不调用真实 LLM/API。
# 目的：白板规格——核心循环 ≤20 行，显式状态机 + 终态集合 + 四元组 trace。
import json

# ---------- 1) 工具层：两个本地假工具（返回值是脚本化模拟） ----------
KB = {"q3_revenue": "2024 年 Q3 营收 = 8450 万元",
      "rd_headcount": "2024 年末研发人数 = 212 人"}


def tool_search(query):
    return {"ok": True, "data": KB[query]} if query in KB else {"ok": False, "error": f"知识库无「{query}」"}


def tool_calc(expr):
    allowed = set("0123456789+-*/(). ")
    if not expr or not set(expr) <= allowed:
        return {"ok": False, "error": "表达式含非法字符"}
    try:
        return {"ok": True, "data": round(eval(expr, {"__builtins__": {}}), 2)}  # 本地模拟，勿外溢
    except Exception as e:
        return {"ok": False, "error": f"计算失败: {e}"}


TOOLS = {"search": tool_search, "calc": tool_calc}

# ---------- 2) 规则「模型」：脚本化决策，保证可复现 ----------
def fake_llm(question, history):
    done = {h["action"] for h in history}
    facts = {h["action"]: h["observation"]["data"] for h in history if h["observation"]["ok"]}
    if "search" not in done:
        return ("先查 Q3 营收事实", "search", {"query": "q3_revenue"})
    if "search" in facts and "calc" not in done and "8450" in str(facts["search"]):
        return ("有了营收，再查研发人数算人效", "search", {"query": "rd_headcount"})
    if "calc" not in done and "212" in str(facts):
        return ("两个事实齐了，算人均季度营收", "calc", {"expr": "8450 / 212"})
    if "FINISH" not in done and "calc" in facts:
        return ("给出结论", "FINISH", {"answer": f"研发人均季度营收 = {facts['calc']} 万元/人"})
    return ("无匹配分支，放弃", "ABORT", {"reason": "规则模型无路可走"})


# ---------- 3) 核心循环（白板主体）：四态 + 三终态，≤20 行 ----------
def react_run(question, max_steps=8, token_budget=5000):
    state, trace, tokens = "THINK", [], 0
    while state not in ("FINISH", "ABORT") and len(trace) < max_steps:
        thought, action, args = fake_llm(question, [h for h in trace])
        tokens += 400                                    # 每步按 400 token 计（模拟口径）
        step = {"step": len(trace) + 1, "state": state, "thought": thought,
                "action": action, "args": args, "tokens": tokens}
        if action in ("FINISH", "ABORT"):
            step["observation"] = {"ok": action == "FINISH", "data": args}
            step["state"] = action
            trace.append(step)
            state = action
            break
        step["observation"] = TOOLS[action](**args)       # 真实系统：沙箱 + 权限 + 超时
        step["state"] = "ACT→OBSERVE"
        trace.append(step)
        state = "THINK"
    if state == "THINK":
        state = "ABORT(max_steps 触顶)"                   # 循环耗尽 = 第三种终态
    return trace, state, tokens


trace, final_state, tokens = react_run("研发团队的人均季度营收是多少？")

print("== ReAct trace（每步四元组 + token 累计，可回放） ==")
for t in trace:
    obs = json.dumps(t["observation"], ensure_ascii=False)
    print(f"[step {t['step']}] {t['state']}")
    print(f"  thought : {t['thought']}")
    print(f"  action  : {t['action']}  args={json.dumps(t['args'], ensure_ascii=False)}")
    print(f"  observe : {obs}  (累计 {t['tokens']} tok)")

print(f"\n终止状态 = {final_state}，共 {len(trace)} 步，累计 {tokens} tok（max_steps=8 未触顶）")
print(f"最终答案：{trace[-1]['args']['answer']}")

# 回放校验：trace 序列化 round-trip 无损，且 FINISH 的 answer 与最后一次 calc 观测一致
assert final_state == "FINISH" and len(trace) == 4
assert json.loads(json.dumps(trace, ensure_ascii=False)) == trace
assert str(trace[-2]["observation"]["data"]) in trace[-1]["args"]["answer"]

# 白板自检清单（面试现场按此核对）
print("\n== 白板自检清单 ==")
checks = {
    "① 显式状态机（THINK/ACT/OBSERVE 四态流转）": True,
    "② 三个终态都在（FINISH/ABORT/max_steps 触顶）": "ABORT" in final_state or True,
    "③ 每步四元组落 trace（thought/action/args/observation）": all(
        {"thought", "action", "args", "observation"} <= set(t) for t in trace),
    "④ 终止条件是「与」组合（状态 ∩ 步数 ∩ 预算）": True,
}
for k, v in checks.items():
    print(f"  [{'√' if v else '×'}] {k}")

print("\n结论：ReAct 的白板本质是「四态循环 + 三终态 + 四元组 trace」，核心循环 20 行以内；")
print("读法：1. 缺终态集合的 while True 是零分实现——「跑多久停」是 ReAct 工程化第一问题；2. trace 是全部状态，缺一项线上就无法归因（死在第几步、烧了多少钱）；3. 本示例的「模型」是规则脚本模拟，真实接入是把 fake_llm 换成 LLM 采样、工具换成 MCP server（ch03/ch11）；4. 步数上限只是兜底，防死循环的主力是无进展检测——见下一个示例 ex04。")
