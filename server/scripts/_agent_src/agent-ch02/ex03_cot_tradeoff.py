# title: CoT 的反噬：简单任务上 token 涨 7 倍，准确率反而降
# 用「每步正确率 ^ 步数」的可靠度模型对比 Direct 与 CoT：
# 简单任务 1 步就够，CoT 引入 4 个额外步骤，每步 0.5% 的出错概率累积成净损失。
# 最后算「错误成本阈值」：一次错误值多少钱，才值得为 CoT 多付的 token 买单。
TASKS = [
    # 名称, 直接准确率, CoT 步数, CoT 每步正确率, 直接输出 token, CoT token
    ("简单（格式转换）", 0.990, 4, 0.995, 60, 420),
    ("中等（多条件判断）", 0.800, 6, 0.975, 80, 620),
    ("困难（多跳计算）", 0.450, 9, 0.960, 120, 980),
]
PRICE_IN, PRICE_OUT = 2.0, 8.0      # 元 / 百万 token
OUT_RATIO = 0.7                     # 假设 70% 的 token 是输出

def cost(tokens):
    return (tokens * (1 - OUT_RATIO) * PRICE_IN + tokens * OUT_RATIO * PRICE_OUT) / 1e6

print("=" * 78)
print("表 1  准确率与成本：CoT 只在困难任务上换到准确率")
print("=" * 78)
print(f"{'任务':<20}{'Direct':>9}{'CoT':>9}{'Δ准确':>8}{'Δtoken':>8}{'每正确单成本':>14}")
rows = []
for name, acc_d, steps, p_step, tok_d, tok_c in TASKS:
    acc_c = p_step ** steps
    cd, cc = cost(tok_d), cost(tok_c)
    per_d, per_c = cd / acc_d, cc / acc_c
    rows.append((name, acc_d, acc_c, cd, cc))
    print(f"{name:<20}{acc_d:>9.1%}{acc_c:>9.1%}{(acc_c-acc_d)*100:>+7.1f}pp"
          f"{tok_c/tok_d:>7.1f}x{per_c/per_d:>13.1f}x")

print("\n" + "=" * 78)
print("表 2  什么时候 CoT 才划算：一次错误的总代价 C（相对单次 token 成本）")
print("=" * 78)
print(f"{'任务':<20}" + "".join(f"{'C=' + str(c):>10}" for c in (0, 5, 20, 100)) + "  结论")
for name, acc_d, acc_c, cd, cc in rows:
    line = f"{name:<20}"
    verdict = ""
    for C in (0, 5, 20, 100):
        # 期望总成本 = token 成本 + 错误概率 × 错误代价（以 Direct 的 token 成本为单位）
        ed = cd + (1 - acc_d) * C * cd
        ec = cc + (1 - acc_c) * C * cd
        line += f"{'CoT' if ec < ed else 'D':>10}"
    # 求盈亏平衡的 C：cc + (1-acc_c)*C*cd = cd + (1-acc_d)*C*cd
    denom = acc_c - acc_d            # CoT 带来的准确率增益
    Cstar = (cc - cd) / (cd * denom) if denom > 1e-9 else float("inf")
    verdict = f"  C*={Cstar:.0f}" if Cstar != float("inf") else "  CoT 永不划算"
    print(line + verdict)

print("\n结论：简单任务上 CoT 的准确率从 99.0% 掉到 98.0%，token 却是 7 倍——两头都亏；")
print("      困难任务上准确率 +24pp，但要把「一次错误」定价到 C* 以上才回本。")
print("读法：CoT 不是默认开关，而是一个按任务难度与错误代价分流的策略；")
print("      简单/高频/低错误代价 → Direct；困难/低频/高错误代价 → CoT，并压短推理链。")
