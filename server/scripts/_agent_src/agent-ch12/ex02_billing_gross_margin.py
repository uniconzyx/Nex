# title: 三种计费模式毛利曲线对比：席位、调用与效果的盈亏平衡扫描
# 全部为示例测算：固定成本/边际成本/单价均为教学假设，仅用于展示曲线形状与风险转移方向。

C_FIX = 20000.0   # 月固定成本 ¥（示例测算）
C_VAR = 0.5       # 单任务边际成本 ¥（示例测算）
SEATS, P_SEAT = 30, 1500.0   # 席位模式
P_CALL = 1.5                # 调用模式 ¥/任务
P_OUTCOME = 2.5             # 效果模式 ¥/自动解决（示例测算）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def margin(q, rev):
    return rev(q) - C_FIX - C_VAR * q


def solve_rate(q):
    """自动解决率随流量难度下滑：4 万以内 60%，之后线性下降（经验判断，示例测算）"""
    return 0.60 if q <= 40000 else max(0.30, 0.60 - 0.0035 * (q - 40000) / 1000)


MODES = {
    "按席位": lambda q: SEATS * P_SEAT,               # 与用量脱钩
    "按调用": lambda q: q * P_CALL,
    "按效果": lambda q: solve_rate(q) * q * P_OUTCOME,  # 有效单价 = 解决率×单解决价
}

print(f"== 毛利扫描（固定成本 ¥{C_FIX:,.0f}/月，边际 ¥{C_VAR}/任务；示例测算） ==")
QS = [10000, 30000, 50000, 60000, 90000]
print(f"{pad('模式', 8)}" + "".join(f"{q//10000:>8}万" for q in QS))
for name, rev in MODES.items():
    print(f"{pad(name, 8)}" + "".join(f"{margin(q, rev):>+10,.0f}" for q in QS))

# 盈亏平衡：调用/效果解 q* = C_fix/(p_eff - c_var)；席位解收入=成本的方程
p_eff = solve_rate(30000) * P_OUTCOME
q_call = C_FIX / (P_CALL - C_VAR)
q_out = C_FIX / (p_eff - C_VAR)
q_seat = (SEATS * P_SEAT - C_FIX) / C_VAR   # 超过即亏
print(f"\n盈亏平衡用量：按调用 q*={q_call:,.0f}；按效果 q*={q_out:,.0f}"
      f"（有效单价 {p_eff:.2f}）；按席位转负点 q={q_seat:,.0f}（超过即亏）")

# 席位模式重度使用演示：用量翻倍时的毛利变化
q0 = 30000
print(f"用量 3万→6万：席位毛利 {margin(q0, MODES['按席位']):+,.0f} → "
      f"{margin(2*q0, MODES['按席位']):+,.0f}；调用 {margin(q0, MODES['按调用']):+,.0f} → "
      f"{margin(2*q0, MODES['按调用']):+,.0f}")
print(f"效果模式在 6 万时解决率降到 {solve_rate(60000):.0%}，收入比调用少 "
      f"¥{(60000*P_CALL - solve_rate(60000)*60000*P_OUTCOME):,.0f} —— 归因缩水")

print("\n结论：三模式不是定价技巧而是风险分配——用量 3万→6万时席位毛利由 +10,000 转 −5,000（收入恒定、成本 +¥15,000），")
print("读法：1. 席位模式把用量不确定性整体转移给提供方，必须配公平使用条款与阶梯补差；2. 调用模式单位经济 (p−c) 恒定，盈亏平衡 q*=C_fix/(p−c)，是最透明的结构；3. 效果模式的有效单价=解决率×单解决价，且解决率随流量难度下滑（4 万后线性降），简单模型里它与调用重合，差别全在归因风险；4. 混合计费（席位保底+超量按调用+效果封顶）是给双方各一个边界的常见工程解。")
