# title: 工具 Schema 设计对比：把动作空间从「字符串」收窄成「枚举」值多少钱
# 三种设计：A 宽参数（action 自由字符串 + args 任意 dict）
#          B 枚举动作 + 类型化参数
#          C 枚举 + required + 每个枚举值一条示例
# 模拟 1000 个三步任务：每次调用可能选错动作/填错参数，失败可重试一次，仍失败可能产生副作用。
import numpy as np

rng = np.random.default_rng(9)
N_TASK, STEPS = 1000, 3
# 单次调用的错误率（经验假设）
DESIGNS = {
    "A 宽参数": {"err": 0.18, "side_effect": 0.35, "desc": "action 任意字符串，参数是 dict"},
    "B 枚举": {"err": 0.07, "side_effect": 0.12, "desc": "action 枚举，参数有类型"},
    "C 枚举+示例": {"err": 0.035, "side_effect": 0.06, "desc": "再加 required 与逐值示例"},
}
RETRY_COST, CALL_COST = 1.6, 1.0
SIDE_EFFECT_COST, HUMAN_COST = 40.0, 12.0

def run(err, side):
    calls = successes = side_effects = humans = 0
    for _ in range(N_TASK):
        ok = True
        for _s in range(STEPS):
            calls += 1
            if rng.random() >= err:
                continue
            # 第一次失败：重试
            calls += 1
            if rng.random() >= err:
                continue
            ok = False
            if rng.random() < side:
                side_effects += 1
            else:
                humans += 1
            break
        successes += ok
    cost = calls * CALL_COST + side_effects * SIDE_EFFECT_COST + humans * HUMAN_COST
    return successes, calls, side_effects, humans, cost

print("=" * 84)
print("表 1  三种 schema 的模拟结果（1000 个任务 × 3 步）")
print("=" * 84)
print(f"{'设计':<14}{'任务成功率':>10}{'总调用':>8}{'副作用':>7}{'转人工':>7}{'总成本':>10}{'每成功成本':>11}")
results = {}
for name, cfg in DESIGNS.items():
    s, c, se, h, cost = run(cfg["err"], cfg["side_effect"])
    results[name] = (s, cost, se)
    print(f"{name:<14}{s/N_TASK:>10.1%}{c:>8}{se:>7}{h:>7}{cost:>10.0f}{cost/max(s,1):>11.2f}")

print("\n" + "=" * 84)
print("表 2  典型错误长什么样（A 设计）")
print("=" * 84)
errors = [
    ("动作名幻觉", "action='deactivate_account'（实际只有 disable_user）"),
    ("参数放错层", "{'user_id': {'id': 'u_12'}}（应为字符串）"),
    ("单位混淆", "timeout=30（秒）而接口要求毫秒 → 提前超时"),
    ("危险近似", "'delete' 与 'deactivate' 语义相反，字符串相似度却很高"),
]
for kind, ex in errors:
    print(f"  {kind:<10} {ex}")

print("\n" + "=" * 84)
print("表 3  把错误率从 18% 降到 3.5% 的收益拆解")
print("=" * 84)
sA, cA, seA = results["A 宽参数"]
sC, cC, seC = results["C 枚举+示例"]
print(f"  成功率      {sA/N_TASK:.1%} → {sC/N_TASK:.1%}（+{(sC-sA)/N_TASK*100:.1f}pp）")
print(f"  副作用次数  {seA} → {seC}（-{(1-seC/max(seA,1))*100:.0f}%）")
print(f"  每成功成本  {cA/max(sA,1):.2f} → {cC/max(sC,1):.2f}（{(cC/max(sC,1))/(cA/max(sA,1))-1:+.0%}）")

print("\n结论：宽参数设计的单次错误率只高 14.5pp，但经由 3 步连乘与副作用放大后，")
print("      每成功成本高出近一倍；真正贵的不是重试，是「调错了但调用成功」。")
print("读法：schema 是第一道权限边界——能枚举就枚举、能 required 就不要可选、")
print("      危险动作单独命名并要求二次确认；优化 prompt 的收益远小于收窄动作空间。")
