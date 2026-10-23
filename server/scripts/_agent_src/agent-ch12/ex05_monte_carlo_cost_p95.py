# title: Monte Carlo 成本区间：P95 超支概率与报价安全边际
# 数值实验（示例测算）：对 token 量与兜底率抽样，输出成本分布区间与超支概率。

import numpy as np

rng = np.random.default_rng(42)
N = 20000          # 抽样次数
Q = 30000          # 月任务量（示例测算）
C_FIX = 20000.0
P_IN, P_OUT = 0.008 / 1000, 0.024 / 1000
GPU, VEC = 0.012, 0.004
HUMAN = 8.0        # 单次人工全价 ¥（示例测算）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def sample_cost(n):
    """单任务成本抽样：上下文 token 对数正态、兜底率 Beta（均值 0.4）"""
    tok_in = rng.lognormal(mean=np.log(3000), sigma=0.25, size=n)
    tok_out = rng.normal(400, 60, size=n).clip(100)
    fb_rate = rng.beta(4, 6, size=n)
    tok = tok_in * P_IN + tok_out * P_OUT
    return tok + GPU + VEC + fb_rate * HUMAN, fb_rate * HUMAN, tok + GPU + VEC


costs, fb_part, tech_part = sample_cost(N)
p50, p90, p95 = np.percentile(costs, [50, 90, 95])
print(f"== 单任务成本分布（{N:,} 次抽样，固定种子；示例测算） ==")
print(f"P50=¥{p50:.3f}  P90=¥{p90:.3f}  P95=¥{p95:.3f}  "
      f"均值=¥{costs.mean():.3f}  最大=¥{costs.max():.3f}")

# 区间宽度来源分解：兜底项 vs 技术项（同一次抽样的两个分量）
print(f"兜底项 P95=¥{np.percentile(fb_part, 95):.3f}，技术项(token+卡时+向量库) P95="
      f"¥{np.percentile(tech_part, 95):.3f} —— 区间宽度主要由兜底贡献")

print("\n== 报价安全边际：超支概率 vs 报价（含固定成本摊薄 ¥%.2f） ==" % (C_FIX / Q))
print(f"{pad('报价¥', 8)}{'期望月毛利¥':>13}{'P95超支概率':>13}")
for price in (3.0, 3.38, 3.8, 3.92, 4.55, 5.5, 6.82):
    m_unit = price - C_FIX / Q - costs
    over = (m_unit < 0).mean()
    print(f"{pad(f'{price:.2f}', 8)}{m_unit.mean()*Q:>+13,.0f}{over:>13.1%}")

# 定价口径：price = 成本P95 + 固定摊薄 → 超支概率 ≈ 5%
target_price = p95 + C_FIX / Q
print(f"\n按「P95 成本 + 固定摊薄」定价 = ¥{target_price:.2f}/任务（此时超支概率约 5%）")

print("\n结论：点估计报价必然踩中长尾，按 P95 成本定价把超支概率压到约 5%，安全边际买的是尾部风险，")
print("读法：1. 成本区间主要由兜底率分布决定（Beta 抽样），技术项方差小一个量级——优化兜底率同时收窄区间；2. 期望毛利为正≠安全：报价贴近期望成本（约 ¥3.92）时期望≈0，而 ¥3.0~¥3.92 区间超支概率 48%~76%，单月亏损是常态；3. 定价口径：price = 成本P95 + 固定摊薄（若还要 70% 毛利则再除以 (1−0.7)）；4. 固定种子保证可复现，参数为教学假设（示例测算）。")
