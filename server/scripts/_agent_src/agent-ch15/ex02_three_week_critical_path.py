# title: 三周计划求解器：拓扑排序、关键路径与「白砍」陷阱
# 纯标准库实现：Kahn 拓扑排序（含环检测）、最早/最晚时间、浮动时间与砍单模拟。


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


class Plan:
    """任务依赖图：name -> (工期天, [前置...], 分组, 砍单优先级)。"""

    def __init__(self, tasks):
        self.tasks = dict(tasks)
        self.dur = {n: t[0] for n, t in self.tasks.items()}
        self.pre = {n: list(t[1]) for n, t in self.tasks.items()}
        self.suc = {n: [] for n in self.tasks}
        for n, ps in self.pre.items():
            for p in ps:
                self.suc[p].append(n)

    def topo(self):
        indeg = {n: len(ps) for n, ps in self.pre.items()}
        queue = sorted(n for n, d in indeg.items() if d == 0)
        order = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for m in sorted(self.suc[n]):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
            queue.sort()
        if len(order) != len(self.dur):
            raise ValueError("依赖有环，Kahn 提前退出")
        return order

    def schedule(self):
        order = self.topo()
        ef, lf, ls = {}, {}, {}
        for n in order:  # 最早完成 EF：max(前置 EF) + 工期
            ef[n] = max([ef[p] for p in self.pre[n]], default=0) + self.dur[n]
        cp = max(ef.values())
        for n in reversed(order):  # 最晚完成 LF：sink 取 cp，否则 min(后继 LF - 后继工期)
            lf[n] = min([lf[s] - self.dur[s] for s in self.suc[n]], default=cp)
            ls[n] = lf[n] - self.dur[n]
        slack = {n: ls[n] - (ef[n] - self.dur[n]) for n in ef}
        return order, ef, ls, slack, cp


TASKS = {
    "T1选题与范围冻结": (1, [], "规划", None),
    "T2数据收集清洗": (4, ["T1选题与范围冻结"], "数据", None),
    "T3黄金集标注": (3, ["T2数据收集清洗"], "数据", None),
    "T4基线链路跑通": (5, ["T2数据收集清洗"], "链路", None),
    "T5检索迭代": (4, ["T4基线链路跑通"], "链路", None),
    "T6生成迭代": (3, ["T4基线链路跑通"], "链路", None),
    "T7错误分析轮2": (5, ["T5检索迭代", "T6生成迭代"], "链路", None),
    "T8UI美化": (4, ["T4基线链路跑通"], "UI", 1),
    "T9导出PDF": (3, ["T6生成迭代"], "次要功能", 2),
    "T10容器化": (2, ["T4基线链路跑通"], "部署", None),
    "T11健康检查": (1, ["T10容器化"], "部署", None),
    "T12监控面板": (3, ["T11健康检查"], "部署", None),
    "T13成本看板": (2, ["T11健康检查"], "部署", None),
    "T14README": (2, ["T11健康检查"], "文档", None),
    "T15架构图": (1, ["T14README"], "文档", None),
    "T16演示视频": (2, ["T14README"], "文档", None),
    "T17部署上线接线": (3, ["T12监控面板", "T13成本看板", "T7错误分析轮2"], "部署", None),
    "T18答辩材料排练": (2, ["T16演示视频", "T17部署上线接线"], "文档", None),
    "T19彩蛋功能": (3, ["T7错误分析轮2"], "锦上添花", 3),
}

plan = Plan(TASKS)
order, ef, ls, slack, cp = plan.schedule()

print("== 1) 拓扑序（Kahn，起点队列排序保证可复现） ==")
print("  " + " -> ".join(t.split("选")[0].split("数")[0][:4] for t in order[:8]) + " -> ...")
print(f"  共 {len(order)} 个任务，序合法：{all(all(p in order[:order.index(n)] for p in plan.pre[n]) for n in order)}")

print("\n== 2) 最早/最晚时间表（slack=0 即在关键路径上） ==")
print("  " + pad("任务", 20) + pad("工期", 6) + pad("最早完成", 10) + pad("最晚完成", 10) + pad("浮动", 6) + "关键?")
for n in order:
    mark = "CP" if slack[n] == 0 else ""
    print("  " + pad(n, 20) + pad(str(plan.dur[n]), 6) + pad(str(ef[n]), 10)
          + pad(str(ls[n]), 10) + pad(str(slack[n]), 6) + mark)
print(f"\n  关键路径长度 = {cp} 天，上限 21 天 -> {'超期 ' + str(cp - 21) + ' 天' if cp > 21 else '合格'}")

print("\n== 3) 环检测：构造 T_A->T_B->T_A ==")
try:
    Plan({"T_A": (1, ["T_B"], "x", None), "T_B": (1, ["T_A"], "x", None), "T_C": (1, [], "x", None)}).topo()
    print("  未报错（不该到这里）")
except ValueError as e:
    print(f"  正确报错：{e}（order 长度不足即退出，不会死循环）")

print("\n== 4) 第一轮砍单：按预设优先级 UI -> 次要功能 -> 锦上添花 ==")
cut_names = [n for n, t in TASKS.items() if t[3] is not None]
cut_names.sort(key=lambda n: TASKS[n][3])
for n in cut_names:
    print(f"  砍 {n}（优先级 {TASKS[n][3]}，{TASKS[n][0]} 天，浮动 {slack[n]} 天）")
plan2 = Plan({n: t for n, t in TASKS.items() if n not in cut_names})
_, ef2, _, slack2, cp2 = plan2.schedule()
print(f"  砍单后关键路径 = {cp2} 天（原 {cp} 天）")
if cp2 == cp:
    print("  结论：三个被砍任务全不在关键路径上（浮动均 >0）-> 白砍！")
    print("  砍单只减少总工作量，不减关键路径；要缩工期必须动链上任务")

print("\n== 5) 第二轮：压缩关键路径上的任务工期（收窄每轮范围） ==")
for n, delta in [("T5检索迭代", -1), ("T7错误分析轮2", -2), ("T17部署上线接线", -1)]:
    d, ps, g, c = TASKS[n]
    TASKS[n] = (d + delta, ps, g, c)
    print(f"  {n}: {d} -> {d + delta} 天（做法：只修头部一类错误/上线清单预制）")
plan3 = Plan(TASKS)
_, ef3, _, _, cp3 = plan3.schedule()
print(f"  压缩后关键路径 = {cp3} 天 <= 21 -> {'达标' if cp3 <= 21 else '仍超期'}")

print("\n结论：3 周计划的工期下限由关键路径决定，砍非关键任务（白砍）不缩一天工期；")
print("读法：1. slack=0 的任务才在关键路径上，砍单前先看浮动时间；2. 缩工期只有两招：压链上任务工期（收窄范围）或并行化（加人/任务拆分），砍游离任务只减总工作量；3. 环检测用 Kahn 退出长度判断，别写 while True；4. 本示例工期为教学假设值，真实估算应按历史速度校准。")
