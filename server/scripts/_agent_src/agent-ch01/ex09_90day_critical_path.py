# title: 90 天排期的关键路径：拓扑排序找 slack，再决定「先做什么」
# 16 个任务构成 DAG，工期以天计。Kahn 拓扑排序求最早开始/结束，逆序求最晚开始，
# 得到每条任务的松弛量（slack）与关键路径；最后模拟一个任务延期，看它是否真的影响交付。
from collections import defaultdict, deque

# (任务, 工期, 前置任务)
TASKS = [
    ("T1 岗位与行业调研", 3, []),
    ("T2 技术分层表", 4, ["T1 岗位与行业调研"]),
    ("T3 能力自评", 2, ["T1 岗位与行业调研"]),
    ("T4 Python/工程基础", 10, []),
    ("T5 Prompt 与结构化输出", 7, ["T4 Python/工程基础"]),
    ("T6 模型接入与客户端封装", 6, ["T5 Prompt 与结构化输出"]),
    ("T7 RAG 数据管道", 14, ["T6 模型接入与客户端封装"]),
    ("T8 检索评测", 6, ["T7 RAG 数据管道"]),
    ("T9 私有化部署", 8, ["T6 模型接入与客户端封装"]),
    ("T10 Agent 编排", 14, ["T8 检索评测", "T9 私有化部署"]),
    ("T11 评测与回归", 5, ["T10 Agent 编排"]),
    ("T12 产品方案与指标", 6, ["T3 能力自评", "T11 评测与回归"]),
    ("T13 作品集整理", 7, ["T12 产品方案与指标"]),
    ("T14 模拟面试", 5, ["T13 作品集整理"]),
    ("T15 简历与投递", 6, ["T14 模拟面试"]),
    ("T16 复盘与迭代", 4, ["T15 简历与投递"]),
]
dur = {t: d for t, d, _ in TASKS}
pre = {t: p for t, _, p in TASKS}
succ = defaultdict(list)
indeg = {t: len(p) for t, _, p in TASKS}
for t, _, ps in TASKS:
    for x in ps:
        succ[x].append(t)

order, q = [], deque(t for t in indeg if indeg[t] == 0)
while q:
    u = q.popleft()
    order.append(u)
    for v in succ[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
assert len(order) == len(TASKS), "存在环"

ES = {}
for t in order:
    ES[t] = max((ES[p] + dur[p] for p in pre[t]), default=0)
EF = {t: ES[t] + dur[t] for t, _, _ in TASKS}
TOTAL = max(EF.values())

LF = {t: TOTAL for t, _, _ in TASKS}
for t in reversed(order):
    if succ[t]:
        LF[t] = min(LS for LS in (LF[s] - dur[s] for s in succ[t]))
LS = {t: LF[t] - dur[t] for t, _, _ in TASKS}
SLACK = {t: LS[t] - ES[t] for t, _, _ in TASKS}

print("=" * 80)
print("表 1  拓扑序排期（ES=最早开始，EF=最早结束，slack=可拖天数）")
print("=" * 80)
print(f"{'#':<3}{'任务':<26}{'工期':>5}{'ES':>5}{'EF':>5}{'slack':>7}  关键")
for i, t in enumerate(order, 1):
    print(f"{i:<3}{t:<26}{dur[t]:>5}{ES[t]:>5}{EF[t]:>5}{SLACK[t]:>7}  {'*' if SLACK[t] == 0 else ''}")

crit = sorted([t for t in TASKS if SLACK[t[0]] == 0], key=lambda x: ES[x[0]])
print(f"\n总工期 {TOTAL} 天；关键路径：")
print("  " + " → ".join(t[0] for t in crit))

print("\n" + "=" * 80)
print("表 2  延期 5 天的两种情形：只有关键路径上的延期会推后交付")
print("=" * 80)
for name in ("T7 RAG 数据管道", "T2 技术分层表"):
    new_total = TOTAL + (5 if SLACK[name] == 0 else 0)
    print(f"  {name:<20} slack={SLACK[name]:>2} 天 → 交付 {new_total} 天 "
          f"({'推后 5 天' if new_total > TOTAL else '不受影响'})")

print("\n" + "=" * 80)
print("表 3  松弛最多的 3 个任务：可以并行、可以晚做，但要留出返工")
print("=" * 80)
for t in sorted(TASKS, key=lambda x: -SLACK[x[0]])[:3]:
    print(f"  {t[0]:<26} slack={SLACK[t[0]]:>2} 天，最晚 {LS[t[0]]} 天开始")

print("\n结论：90 天里真正决定交付的是「基础→Prompt→接入→RAG→评测→编排→作品集」这条链，")
print("      调研/分层表这类任务 slack 很大，不该占用关键路径的注意力。")
print("读法：排期先算 slack 再排优先级；对关键路径任务设 checkpoint（第 23/43/57 天），")
print("      延期就砍范围而不是压缩测试——测试被压缩的代价会在面试演示当天集中爆发。")
