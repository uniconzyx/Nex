# title: 12 个月计划：依赖拓扑排序与 CPM 关键路径
from collections import deque

# 12 个月 = 52 周预算；(任务, 周工期, 前置依赖)
TASKS = [
    ("T1", "Python 与工程基础补强", 10, []),
    ("T2", "RAG 系统原理与动手", 8, ["T1"]),
    ("T3", "评估集建设方法", 5, ["T1"]),
    ("T4", "工单问答 v1 上线", 10, ["T2", "T3"]),
    ("T5", "兜底与低置信度路由", 5, ["T4"]),
    ("T6", "系统设计深挖", 6, ["T2"]),
    ("T7", "微调实验", 6, ["T2"]),
    ("T8", "作品集 STAR-R 补齐", 6, ["T4", "T5"]),
    ("T9", "第二个含评估服务", 10, ["T5", "T6"]),
    ("T10", "实习申请与投递", 4, ["T8"]),
    ("T11", "面试准备（八股+行为面）", 7, ["T8", "T9"]),
    ("T12", "实习入职与衔接", 3, ["T10", "T11"]),
]
BUDGET_WEEKS = 52
NAME = {t[0]: t[1] for t in TASKS}
DUR = {t[0]: t[2] for t in TASKS}


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def topo(tasks):
    """Kahn 拓扑排序；返回顺序，同时可判环（长度不等即有环）。"""
    indeg = {t[0]: len(t[3]) for t in tasks}
    succ = {t[0]: [] for t in tasks}
    for t in tasks:
        for d in t[3]:
            succ[d].append(t[0])
    q = deque(sorted(n for n, v in indeg.items() if v == 0))
    order = []
    while q:
        n = q.popleft()
        order.append(n)
        for m in succ[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    return order


def cpm(tasks):
    """关键路径法：返回 (拓扑序, ES, EF, LS, LF, slack, 总工期)。"""
    dur = {t[0]: t[2] for t in tasks}
    deps = {t[0]: list(t[3]) for t in tasks}
    succ = {n: [] for n in dur}
    for n, ds in deps.items():
        for d in ds:
            succ[d].append(n)
    order = topo(tasks)
    assert len(order) == len(tasks), "依赖存在环，无法排期"
    ES, EF = {}, {}
    for n in order:
        ES[n] = max([EF[d] for d in deps[n]], default=0)
        EF[n] = ES[n] + dur[n]
    total = max(EF.values())
    LF, LS = {}, {}
    for n in reversed(order):
        LF[n] = min([LS[m] for m in succ[n]], default=total)
        LS[n] = LF[n] - dur[n]
    slack = {n: LS[n] - ES[n] for n in dur}
    return order, ES, EF, LS, LF, slack, total


def critical_path(tasks, ES, EF, slack):
    """从终点沿 slack=0 的前置回溯，得到关键路径。"""
    deps = {t[0]: list(t[3]) for t in tasks}
    end = max(EF, key=lambda n: EF[n])
    path, cur = [end], end
    while deps[cur]:
        cur = max((d for d in deps[cur] if slack[d] == 0), key=lambda d: EF[d])
        path.append(cur)
    return list(reversed(path))


order, ES, EF, LS, LF, slack, total = cpm(TASKS)
cp = critical_path(TASKS, ES, EF, slack)

print("== 1) 拓扑排序结果（依赖先于任务）==")
print("   " + " → ".join(order))

print("\n== 2) 任务表（ES/EF=最早/最晚开始与完成，slack=总浮动，周）==")
print(f"{pad('任务', 24)}{'工期':>4}{'ES':>4}{'EF':>4}{'LS':>4}{'LF':>4}{'slack':>6}  关键?")
for n in order:
    flag = "关键" if slack[n] == 0 else f"浮动{slack[n]}"
    print(f"{pad(n + ' ' + NAME[n], 24)}{dict((t[0], t[2]) for t in TASKS)[n]:>4}"
          f"{ES[n]:>4}{EF[n]:>4}{LS[n]:>4}{LF[n]:>4}{slack[n]:>6}  {flag}")

print(f"\n== 3) 关键路径与总工期 ==")
print("   " + " → ".join(f"{n}({NAME[n]})" for n in cp))
print(f"   关键路径长度 = {total} 周；12 个月预算 = {BUDGET_WEEKS} 周；"
      f"超出 {total - BUDGET_WEEKS} 周 → 必须压缩或并行化")


def total_after(mod):
    """修改某任务工期后的总工期（mod: {任务: 新工期}）。"""
    t2 = [(n, nm, mod.get(n, d), ds) for n, nm, d, ds in TASKS]
    return cpm(t2)[-1]


print("\n== 4) 压缩谁才有效（what-if 实验）==")
for n, cut in [("T8", 4), ("T11", 2)]:
    new_total = total_after({n: DUR[n] - cut})
    on_cp = "关键路径上" if slack[n] == 0 else f"非关键（浮动 {slack[n]} 周）"
    effect = "总工期不变！压缩被浮动吸收" if new_total == total else \
             f"总工期 {total} → {new_total} 周（{'仍超预算' if new_total > BUDGET_WEEKS else '进入预算'}）"
    print(f"   压缩 {n} {NAME[n]} 砍 {cut} 周（{on_cp}）: {effect}")

print("\n结论：计划总工期 53 周超出 52 周预算，但只有压缩关键路径上的任务才缩短总工期——")
print("读法：1. 非关键任务的浮动是「免费缓冲」：T8 砍 4 周总工期纹丝不动，资源砸在这里纯属浪费；2. 关键路径 = T1→T2→T4→T5→T9→T11→T12（基础→RAG→上线→兜底→第二服务→面试→入职），它决定最早完工时间；3. 超预算时的正确动作顺序：先压关键路径上的任务（T11 砍 2 周即回到预算内），再把非关键任务用浮动段并行塞入；4. 本示例只做确定性 CPM，工期本身的不确定性用 PERT+蒙特卡洛估计（示例 ex08）。")
