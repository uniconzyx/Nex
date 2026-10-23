# title: 人工接管率不是越高越好：一条有最低点的总成本曲线
# 模型：自动化成本 + 人工坐席成本（按 150 单/人/日、350 元/人/日折算）+ 漏检错误成本。
# 关键假设：接管率升高后坐席负载变重，拦截率从 95% 降到 50%（人会疲劳、会走过场）。

import math

N = 10000              # 日请求量
C_AUTO = 0.015         # 单次自动化成本（元）
AGENT_CAP = 150        # 每个坐席每天可处理量
AGENT_DAY = 350        # 坐席日成本（元）
ERR_RATE = 0.10        # 自动化错误率
ERR_COST = 60          # 一次漏检错误的总代价（赔付/流失/合规）
BASE_CATCH = 0.95      # 空载时的拦截率
LOAD_SLOPE = 0.45      # 接管率每升 100%，拦截率下降 45 个百分点


def catch(h):
    return max(0.0, BASE_CATCH - LOAD_SLOPE * h)


def total_per_request(h):
    humans = math.ceil(N * h / AGENT_CAP) if h > 0 else 0
    labor = humans * AGENT_DAY / N
    residual = ERR_RATE * (1 - h * catch(h))
    return C_AUTO + labor + residual * ERR_COST, labor, residual, humans


print(f"日请求 {N}，自动化 {C_AUTO} 元/次；坐席 {AGENT_CAP} 单/人/日、{AGENT_DAY} 元/人/日")
print(f"错误率 {ERR_RATE:.0%}，漏检一次 {ERR_COST} 元；拦截率 = {BASE_CATCH:.0%} - {LOAD_SLOPE:.2f}×接管率\n")
print(f"{'接管率':>6}{'坐席数':>5}{'坐席成本':>9}{'残余错误':>9}{'总成本/次':>10}  备注")
best = (9e9, 0)
for i in range(0, 11):
    h = i / 10
    c, labor, residual, humans = total_per_request(h)
    if c < best[0]:
        best = (c, h)
    note = "← 最低" if abs(h - 0.6) < 1e-9 else ""
    print(f"{h:>6.0%}{humans:>5}{labor:>9.3f}{residual:>9.1%}{c:>10.4f}  {note}")

c0 = total_per_request(0.0)[0]
c100 = total_per_request(1.0)[0]
print(f"\n全自动 {c0:.3f} 元/次；全人工 {c100:.3f} 元/次；最优点在接管率 {best[1]:.0%}，{best[0]:.3f} 元/次")
print(f"相对全自动降低 {(1 - best[0]/c0):.0%}，相对全人工降低 {(1 - best[0]/c100):.0%}")

print("\n读法：接管率从 0 升到 60% 时，漏检损失下降快于坐席成本上升；超过 60% 后，")
print("      每 10% 接管只减少约 0.22 元漏检损失，却增加 0.23 元坐席成本，总成本重新上升。")
print("结论：人工接管是一个可优化的运营参数，不是「越多越安全」；")
print("      上线前先用这个曲线定 SLA 与排班，比事后加人更能控制单位成本。")
