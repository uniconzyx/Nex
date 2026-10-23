# title: 范围蔓延检测：一个变更请求的真实成本是它的传递闭包
# 6 个模块、4 个变更请求，沿依赖图传播后算增量，与 20% 预算线比较。
# 结论常常是：单个 CR 都「不大」，加起来已经吃掉半个项目。

MODULES = {
    "A 需求解析": (5, []),
    "B 检索": (8, ["A 需求解析"]),
    "C 生成": (6, ["B 检索"]),
    "D 审核": (4, ["C 生成"]),
    "E 导出": (3, []),
    "F 通知": (2, ["D 审核"]),
}
BASELINE = sum(v[0] for v in MODULES.values())
BUDGET_PCT = 0.20
BUDGET = BASELINE * BUDGET_PCT

CRS = [
    ("CR1 支持多轮追问", {"A 需求解析": 2.0}, 0.25),
    ("CR2 导出增加一列", {"E 导出": 0.5}, 0.05),
    ("CR3 增加人工审核队列", {"D 审核": 2.0}, 0.20),
    ("CR4 切换模型厂商", {"C 生成": 1.0}, 0.10),
]

DOWNSTREAM = {
    "A 需求解析": ["B 检索", "C 生成", "D 审核", "F 通知"],
    "B 检索": ["C 生成", "D 审核", "F 通知"],
    "C 生成": ["D 审核", "F 通知"],
    "D 审核": ["F 通知"],
    "E 导出": [],
    "F 通知": [],
}


def propagate(direct):
    """直接改动 + 下游回归成本（每跳按直接改动的 30% 估）。"""
    impact = dict(direct)
    frontier = list(direct)
    seen = set(direct)
    while frontier:
        cur = frontier.pop()
        for nxt in DOWNSTREAM.get(cur, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            impact[nxt] = impact.get(nxt, 0) + 0.3 * sum(direct.values())
            frontier.append(nxt)
    return impact


print(f"基线工作量 {BASELINE} 人日；变更预算 20% = {BUDGET:.1f} 人日\n")
print(f"{'变更':<20}{'直接':>6}{'传播后':>7}{'累计':>7}{'占基线':>7}  判定")
cum = 0.0
for name, direct, _risk in CRS:
    impact = propagate(direct)
    delta = sum(impact.values())
    cum += delta
    verdict = "接受" if cum <= BUDGET else "冻结/重排"
    print(f"{name:<20}{sum(direct.values()):>6.1f}{delta:>7.1f}{cum:>7.1f}"
          f"{cum/BASELINE:>7.1%}  {verdict}")

print("\nCR1 的影响面（直接 + 下游回归）：")
imp = propagate({"A 需求解析": 2.0})
for k, v in imp.items():
    print(f"  {k:<12}{v:>5.1f} 人日")

first_over = None
cum = 0.0
for name, direct, _ in CRS:
    cum += sum(propagate(direct).values())
    if first_over is None and cum > BUDGET:
        first_over = (name, cum)
print(f"\n首次越过预算线：{first_over[0]}（累计 {first_over[1]:.1f} 人日，"
      f"{first_over[1]/BASELINE:.0%}）")

print("\n读法：CR1 直接只改 2 人日，但下游 4 个模块都要回归，实际 4.4 人日；")
print("      CR2 只有 0.5 人日，是唯一可以立刻接的。")
print("结论：变更评审要看传递闭包而不是直接改动量；先冻结范围、再谈排期。")
print("      预算线应在项目启动时写死，否则每个 CR 看起来都不大，合起来一定延期。")
