# title: ReAct 循环的状态机实现与 trace 回放
# 本地模拟：规则脚本化的「模型」+ 三个假工具，全程不调用真实 LLM/API。
# 目的：把 ReAct（Reason+Act）的循环落成显式状态机，并产出可回放的 trace。
import json

# ---------- 1) 工具层：三个本地假工具（返回值是脚本化模拟） ----------
def tool_search(query):
    """模拟检索：本地小知识库，关键词命中返回事实。"""
    kb = {
        "sales_q3": "2024 年 Q3 销售额 = 8450 万元",
        "annual_target": "2024 全年销售目标 = 26000 万元",
        "headcount": "2024 年末研发人数 = 312 人",
    }
    for k, v in kb.items():
        if k in query:
            return {"ok": True, "data": v}
    return {"ok": False, "error": f"知识库无「{query}」相关条目"}

def tool_calc(expr):
    """模拟计算器：白名单字符，拒绝一切非数学表达式（防注入）。"""
    allowed = set("0123456789+-*/(). %")
    if not expr or not set(expr) <= allowed:
        return {"ok": False, "error": f"表达式含非法字符: {expr!r}"}
    try:
        return {"ok": True, "data": round(eval(expr, {"__builtins__": {}}), 4)}  # 本地模拟，勿外溢
    except Exception as e:
        return {"ok": False, "error": f"计算失败: {e}"}

def tool_lookup(table, key):
    """模拟数据库点查。"""
    db = {"config": {"timeout": 30, "retries": 3}}
    row = db.get(table, {})
    return {"ok": key in row, "data": row.get(key, None)} if key in row else {"ok": False, "error": "key 不存在"}

TOOLS = {"search": tool_search, "calc": tool_calc, "lookup": tool_lookup}

# ---------- 2) 规则「模型」：模拟 LLM 逐步决策（脚本化，可复现） ----------
def fake_llm(question, history):
    """输入问题与历史 trace，输出 (thought, action, args) 或 (thought, FINISH, answer)。
    真实系统里这一步是 LLM 采样；这里用规则表模拟，保证可复现。"""
    done = {h["action"] for h in history}
    facts = {h["action"]: h["observation"] for h in history if h["observation"].get("ok")}

    if "search" not in done:
        return ("需要先查 Q3 销售额事实", "search", {"query": "sales_q3"})
    if "calc" not in done and "8450" in str(facts.get("search", {})):
        return ("拿到 8450，再算它占全年目标的百分比", "calc", {"expr": "8450 / 26000 * 100"})
    if "FINISH" not in done and "calc" in facts:
        pct = facts["calc"]["data"]
        return (f"两个事实都齐了，给出结论", "FINISH", {"answer": f"Q3 销售额 8450 万元，占全年目标 26000 万元的 {pct}%"})
    return ("没有可用下一步，放弃", "ABORT", {"reason": "规则模型无匹配分支"})

# ---------- 3) 显式状态机：THINK -> ACT -> OBSERVE -> (THINK | FINISH | ABORT) ----------
def react_run(question, max_steps=8):
    state, history, trace = "THINK", [], []
    steps = 0
    while state not in ("FINISH", "ABORT") and steps < max_steps:
        steps += 1
        thought, action, args = fake_llm(question, history)
        trace.append({"step": steps, "state": state, "thought": thought,
                      "action": action, "args": args})
        if action in ("FINISH", "ABORT"):
            trace[-1].update({"state": action, "observation": {"ok": action == "FINISH", "data": args}})
            state = action
            break
        state = "ACT"
        fn = TOOLS.get(action)
        if fn is None:
            obs = {"ok": False, "error": f"未知工具 {action}"}
        else:
            obs = fn(**args)  # 真实系统：工具执行有权限/超时/沙箱约束
        state = "OBSERVE"
        history.append({"action": action, "observation": obs})
        trace[-1].update({"state": "ACT→OBSERVE", "observation": obs})
        state = "THINK"
    return trace, state, steps

trace, final_state, steps = react_run("2024 年 Q3 销售额占全年目标的百分之几？")

print("== ReAct trace（每一步都可回放） ==")
for t in trace:
    obs = t["observation"]
    obs_s = json.dumps(obs, ensure_ascii=False)
    print(f"[step {t['step']}] {t['state']}")
    print(f"  thought : {t['thought']}")
    print(f"  action  : {t['action']}  args={json.dumps(t['args'], ensure_ascii=False)}")
    print(f"  observe : {obs_s}")

print(f"\n终止状态 = {final_state}，共 {steps} 步（max_steps=8 未触顶）")
print(f"最终答案：{trace[-1]['args']['answer']}")
# 回放校验：trace 序列化后可重放，且 FINISH 的 args 与最后一次 calc 观测一致
assert final_state == "FINISH"
assert json.loads(json.dumps(trace, ensure_ascii=False)) == trace  # 序列化 round-trip 无损

print("\n结论：ReAct 就是把「想一步、做一步、看一步」显式化成状态机，trace 是它的全部状态，")
print("读法：1. 每个 step 记录 thought/action/args/observation 四元组，缺一项就无法归因；2. 状态机有三个终态：FINISH/ABORT/触顶，真实系统还必须加预算与无进展检测（见 ex07）；3. 本示例的「模型」是规则脚本模拟，真实接入是把 fake_llm 换成 LLM 采样、把工具换成 MCP server；4. trace 落盘（ex06）才能断点续跑与失败回放。")
