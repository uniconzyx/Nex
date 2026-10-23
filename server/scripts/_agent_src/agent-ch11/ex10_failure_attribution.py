# title: 失败样本归类与归因：200 条轨迹的帕累托与防线映射
# 本地模拟：程序化生成的 200 条 Agent 轨迹（终止状态+归因+已烧步数），不调用真实 LLM/API。
import numpy as np

rng = np.random.default_rng(23)
N = 200

# 归因类别：(名称, 占比, 可被对应防线救回的比例, 防线, 对应示例, 平均已烧步数, 步数抖动)
CATS = [
    ("工具参数错",     0.12, 0.60, "schema 校验 + 语义等价修复", "ex02", 3.0, 1.5),
    ("工具执行失败",   0.10, 0.60, "重试 + 降级 + 幂等键",       "ex03", 5.0, 2.0),
    ("上下文事实丢失", 0.09, 0.55, "摘要压缩 + 检查点",          "ex04/ex06", 8.0, 3.0),
    ("规划循环超时",   0.08, 0.25, "无进展检测（止损为主）",     "ex07", 22.0, 6.0),
    ("输出格式错",     0.06, 0.75, "重试 + schema 强约束",       "ex02", 6.0, 2.5),
]
P_SUCC = 1.0 - sum(c[1] for c in CATS)
names = [c[0] for c in CATS]

# ---------- 1) 生成 200 条轨迹 ----------
draws = rng.choice(len(CATS) + 1, size=N, p=[P_SUCC] + [c[1] for c in CATS])
traces = []
for d in draws:
    if d == 0:
        traces.append({"cat": "成功", "fixable": False, "steps": 0, "tokens": 0})
    else:
        name, _, fr, _, _, mu, sd = CATS[d - 1]
        steps = max(1, int(round(rng.normal(mu, sd))))
        traces.append({"cat": name, "fixable": rng.random() < fr,
                       "steps": steps, "tokens": steps * 350})

# ---------- 2) 帕累托：按频次排序 ----------
counts = {name: 0 for name in names}
fixable = {name: 0 for name in names}
waste_steps = {name: 0 for name in names}
for t in traces:
    if t["cat"] == "成功":
        continue
    counts[t["cat"]] += 1
    fixable[t["cat"]] += t["fixable"]
    waste_steps[t["cat"]] += t["steps"]

order = sorted(names, key=lambda n: -counts[n])
succ = sum(t["cat"] == "成功" for t in traces)
print(f"== 200 条轨迹的失败归因帕累托（成功 {succ} 条 = {succ / N:.0%}） ==")
print(f"{'归因':<12}{'条数':>5}{'条形':<22}{'占失败比':>9}{'累计':>7}{'均烧步数':>9}")
cum = 0
tot_fail = N - succ
for name in order:
    c = counts[name]
    cum += c
    bar = "█" * round(c / max(counts.values()) * 20)
    avg_steps = waste_steps[name] / c if c else 0
    print(f"{name:<12}{c:>5}{bar:<22}{c / tot_fail:>8.1%}{cum / tot_fail:>7.1%}{avg_steps:>9.1f}")

# ---------- 3) 防线映射：每类失败由哪一层防线救 ----------
print("\n== 防线映射（可救回 = 加了对应防线后能转为成功的条数） ==")
print(f"{'归因':<12}{'建议修复层':<24}{'对应示例':<10}{'可救回':>7}")
rescue_total = 0
for name in order:
    cat = next(c for c in CATS if c[0] == name)
    rescue_total += fixable[name]
    print(f"{name:<12}{cat[3]:<24}{cat[4]:<10}{fixable[name]:>5}/{counts[name]}")
print(f"\n当前成功率 {succ / N:.0%}；五道防线全部就位后预期成功率 {(succ + rescue_total) / N:.0%}"
      f"（+{rescue_total / N:.0%}，残余失败 {N - succ - rescue_total} 条）")
assert rescue_total < tot_fail

# ---------- 4) 「早死比晚死便宜」：失败得越晚，烧掉的 token 越多 ----------
print("\n== 失败成本视角：哪类失败最贵（按已烧步数） ==")
waste_by_cat = sorted(names, key=lambda n: -waste_steps[n] / max(counts[n], 1))
for name in waste_by_cat:
    c = counts[name]
    print(f"{name:<12} 平均已烧 {waste_steps[name] / c:>5.1f} 步 ≈ {waste_steps[name] * 350:>7} token"
          f"（合计 {waste_steps[name] * 350:>7} token）")
tot_waste = sum(t["tokens"] for t in traces)
print(f"全部失败轨迹合计烧掉 {tot_waste} token ≈ ¥{tot_waste * 0.008 / 1000:.3f}（输入价口径）")

print("\n结论：归因表是 Agent 优化的第一张地图——先按频次定优先级，再按「烧钱位置」定止损顺序，")
print("读法：1. 帕累托前两类（工具执行失败 + 工具参数错）占失败 56.8%，且都死在早期、修复层明确（ex03/ex02），是性价比最高的投入；2. 规划循环类条数不是最多但最贵——平均烧 23 步才死，无进展检测（ex07）先止损再谈增效；3. 输出格式错可救比例最高（10/13），一道重试 + 强 schema 就能捡回；4. 上下文事实丢失救回来要靠压缩策略改对（ex04），不是加算力；5. 防线就位后成功率 52%→77%，但残余的 46 条「救不回」才是真问题——要回到数据与 prompt 层，别在工程层空转。")
