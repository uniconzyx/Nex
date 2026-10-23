# title: 检查点序列化与断点续跑：崩溃后从头跑还是从第 5 步接着跑
# 本地模拟：8 步 Agent 任务 + 内存文件系统 + 可注入崩溃，不调用真实 API。
import json

FS = {}          # 模拟文件系统（内存 dict）；真实系统是磁盘/对象存储


class SideEffectLog:
    """append-only 的外部副作用日志（模拟发通知/写外部系统），崩溃后不会消失。"""

    def __init__(self):
        self.entries = []

    def emit(self, step, payload):
        self.entries.append((step, payload))


def run_agent(log, total_steps=8, crash_at=None, checkpoint=False, resume=False):
    """跑一个 8 步任务。返回 (trace, 终止原因)。"""
    trace = []
    start = 0
    if resume:
        saved = json.loads(FS["ckpt.json"])       # 断点续跑：加载检查点
        trace = saved["trace"]
        start = saved["next_step"]
    for step in range(start, total_steps):
        if step == crash_at:
            return trace, f"crash@step{step}"     # 崩溃发生在副作用之前
        out = f"step-{step}-输出"
        log.emit(step, out)                       # 副作用：外部可见、不可回滚
        trace.append({"step": step, "out": out})
        if checkpoint:
            # 检查点 = 完整状态序列化：trace + 下一步指针
            FS["ckpt.json"] = json.dumps({"trace": trace, "next_step": step + 1},
                                         ensure_ascii=False)
    return trace, "done"


# ---------- 1) 基线：一次跑完（无崩溃） ----------
log_ok = SideEffectLog()
trace_ok, why = run_agent(log_ok)
assert why == "done" and len(trace_ok) == 8

# ---------- 2) 模式 A：无检查点，第 4 步崩溃，只能从头重跑 ----------
log_a = SideEffectLog()
trace_a, why_a = run_agent(log_a, crash_at=4, checkpoint=False)
# 恢复策略：从头再来
trace_a2, why_a2 = run_agent(log_a)
dup_a = len(log_a.entries) - len(trace_a2)        # 副作用总数 - 最终 trace 步数 = 重复执行次数

# ---------- 3) 模式 B：每步写检查点，第 4 步崩溃，从检查点续跑 ----------
log_b = SideEffectLog()
trace_b, why_b = run_agent(log_b, crash_at=4, checkpoint=True)
assert why_b == "crash@step4" and len(trace_b) == 4
trace_b2, why_b2 = run_agent(log_b, checkpoint=True, resume=True)   # 断点续跑
dup_b = len(log_b.entries) - len(trace_b2)

print(f"{'模式':<26}{'最终步数':>8}{'副作用执行':>10}{'重复副作用':>10}{'恢复起点':>10}")
print(f"{'A 无检查点（从头重跑）':<26}{len(trace_a2):>8}{len(log_a.entries):>10}{dup_a:>10}{'step0':>10}")
print(f"{'B 有检查点（断点续跑）':<26}{len(trace_b2):>8}{len(log_b.entries):>10}{dup_b:>10}{'step4':>10}")

# ---------- 4) 一致性验证：续跑结果与一次跑完逐元素一致 ----------
assert trace_b2 == trace_ok, "断点续跑后的 trace 必须与基线完全一致"
print(f"\n一致性：断点续跑的最终 trace 与一次跑完的基线完全相同（{len(trace_b2)} 步逐元素相等）")
print(f"检查点内容（JSON，{len(FS['ckpt.json'])} 字符）：{FS['ckpt.json'][:60]}...")

# ---------- 5) 残余风险：检查点与副作用之间的崩溃窗口 ----------
log_c = SideEffectLog()
# 场景：第 3 步副作用已执行、检查点还没写时崩溃 —— 恢复后会重做第 3 步
trace_c, _ = run_agent(log_c, total_steps=4, crash_at=4, checkpoint=True)   # 正常跑完 4 步
# 手工构造窗口：让 trace 有 3 步、日志有 4 条（第 3 步副作用已发但检查点未写）
FS["ckpt.json"] = json.dumps({"trace": trace_c[:3], "next_step": 3}, ensure_ascii=False)
log_c2 = SideEffectLog()
log_c2.entries = log_c.entries[:]                 # 副作用日志保留（外部系统不会回滚）
trace_c2, _ = run_agent(log_c2, total_steps=4, checkpoint=True, resume=True)
dup_c = len(log_c2.entries) - len(trace_c2)
print(f"窗口场景：副作用已发但检查点未写，恢复后重复副作用 {dup_c} 次 —— 必须靠幂等键兜底（见 ex03）")
assert dup_c == 1

print("\n结论：检查点把「重跑单位」从整个任务缩小到未完成的步，副作用不可回滚决定了它必须有幂等配合，")
print("读法：1. 检查点内容 = 完整状态序列化（trace + next_step），每步成功后原子写入；2. 断点续跑省的不是算力是副作用的重复——通知/下单/写库重发才是真事故；3. 续跑结果必须与基线逐元素一致，这是可回放性的最低要求；4. 检查点与副作用之间存在崩溃窗口（副作用发了、检查点没写），at-least-once 语义必须配幂等键才能变 effectively-once；5. 真实系统里检查点就是 LangGraph 的 checkpointer（如 SqliteSaver/PostgresSaver），本示例用内存 dict 模拟。")
