# title: SLA 承诺档位与违约成本：可用性模拟、credit 敞口与降级预案
# 工程账本（示例测算）：用蒙特卡洛模拟月可用率，给每个 SLA 承诺档位定价。

import numpy as np

rng = np.random.default_rng(11)
M = 20000           # 模拟月份数
MIN_MONTH = 30 * 24 * 60
LAMBDA = 3.0        # 月均故障次数（泊松，示例测算）
MTTR_MEAN = 20.0    # 单次故障平均恢复分钟（指数分布，示例测算）
MRR = 150000.0      # 客户月费 ¥（示例测算）
DEGRADE_COST = 8000.0  # 每次触发降级预案的额外成本 ¥（兜底上调/换模型，示例测算）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def simulate():
    """返回 (可用率数组, 是否触发降级的数组)"""
    n_fail = rng.poisson(LAMBDA, M)
    total_dt = np.zeros(M)
    degrade = np.zeros(M, bool)
    for i, k in enumerate(n_fail):
        if k:
            dts = rng.exponential(MTTR_MEAN, k)
            total_dt[i] = dts.sum()
            degrade[i] = dts.max() > 60      # 单次超 60 分钟触发降级预案
    avail = 1 - total_dt / MIN_MONTH
    return avail, degrade


avail, degrade = simulate()
print(f"== 月可用率分布（{M:,} 个月模拟，月均 {LAMBDA:.0f} 次故障、MTTR {MTTR_MEAN:.0f} 分钟；示例测算） ==")
print(f"P50={np.percentile(avail, 50):.4%}  P10={np.percentile(avail, 10):.4%}  "
      f"P5={np.percentile(avail, 5):.4%}  P1={np.percentile(avail, 1):.4%}")

print("\n== 承诺档位定价（credit = 未达标月按月费比例退还；示例测算） ==")
print(f"{pad('承诺档位', 10)}{'违约概率':>9}{'期望credit¥':>13}{'期望降级¥':>11}{'期望总成本¥':>13}")
TIERS = [("99.0%", 0.990, 0.10), ("99.5%", 0.995, 0.15),
         ("99.9%", 0.999, 0.25), ("99.99%", 0.9999, 0.30)]
for name, target, credit_pct in TIERS:
    breach = (avail < target).mean()
    exp_credit = breach * credit_pct * MRR
    exp_degrade = degrade.mean() * DEGRADE_COST
    print(f"{pad(name, 10)}{breach:>9.1%}{exp_credit:>13,.0f}"
          f"{exp_degrade:>11,.0f}{exp_credit + exp_degrade:>13,.0f}")

# 反推：期望违约成本 ≤ 月费 2% 的最高可承诺档位
print("\n== 选档判据：期望违约成本 ≤ 月费 2%（¥3,000） ==")
for name, target, credit_pct in TIERS:
    total = (avail < target).mean() * credit_pct * MRR + degrade.mean() * DEGRADE_COST
    tag = "可承诺" if total <= 0.02 * MRR else "风险敞口过大"
    print(f"{pad(name, 10)}: ¥{total:,.0f} → {tag}")

print("\n结论：SLA 承诺是用历史可用率数据定价的「看跌期权」，承诺越高 credit 敞口指数上升，99.99% 在此故障结构下期望成本失控，")
print("读法：1. 违约概率 = P(模拟可用率 < 承诺档)，承诺档从 99.5% 提到 99.99% 时违约概率约翻数倍而 credit 比例同步上升，双重放大；2. 期望总成本 = 违约概率 × credit比例 × 月费 + 降级触发率 × 降级成本，选档要使期望成本 ≤ 收入的可承受比例（经验判断 2%）；3. 降级预案（砍 top-k/换小模型/兜底上调）要把成本算进 SLA 账本，没演练过的预案等于没有；4. 参数为教学假设（示例测算），真实项目用自家故障历史重标定 λ 与 MTTR。")
