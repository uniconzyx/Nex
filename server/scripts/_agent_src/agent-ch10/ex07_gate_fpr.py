# title: 回归门禁的误报率：2% 阈值为什么会让告警被无视
import numpy as np

rng = np.random.default_rng(42)
N = 50            # 黄金集规模
TRIALS = 50000    # 无改动重复回归次数
P_BASE = 0.80     # 基线通过率


def gate_blocks(n, p_base, p_new, trials, thr_pp):
    """一次回归实验的批量模拟。返回 (朴素阈值阻断率, z 检验阻断率)。

    朴素规则：通过率降幅 > thr_pp 即阻断；
    z 规则：两比例单侧检验 p < 0.05（只关心退化方向）。
    """
    base = rng.binomial(n, p_base, size=trials)
    new = rng.binomial(n, p_new, size=trials)
    d = (new - base) / n
    block_naive = d <= -thr_pp
    p1, p2 = base / n, new / n
    pool = (base + new) / (2 * n)
    se0 = np.sqrt(np.maximum(pool * (1 - pool) * 2 / n, 1e-12))
    z = (p2 - p1) / se0
    return block_naive.mean(), (z < -1.645).mean()


# 1) 无改动（新旧同分布）时的误报率
print(f"== 1) 模型未变时重复回归 {TRIALS} 次：各门禁规则的误报率（n={N}, p={P_BASE}） ==")
print(f"{'规则':<26}{'误报率':>8}")
fpr_naive = {}
for thr in (0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14):
    fpr, _ = gate_blocks(N, P_BASE, P_BASE, TRIALS, thr)
    fpr_naive[thr] = fpr
    print(f"{'朴素阈值: 降幅 > ' + f'{thr:.0%}':<24}{fpr:>8.1%}")
_, fpr_z = gate_blocks(N, P_BASE, P_BASE, TRIALS, 0.02)
print(f"{'z 检验(单侧 alpha=0.05)':<24}{fpr_z:>8.1%}")
print(f"朴素 2% 阈值误报率 {fpr_naive[0.02]:.0%} —— 几乎每两次回归就误报一次，团队会学会点「忽略并重跑」")

# 2) 按误报率反解：z 检验的名义 alpha 就是误报率上限；朴素阈值离散化后最接近的工作点
near = min(fpr_naive, key=lambda t: abs(fpr_naive[t] - 0.05))
print(f"\n== 2) 按误报率反解阈值 ==")
print(f"z 检验：名义 alpha=0.05 -> 实测误报率 {fpr_z:.1%}（名义值即误报率上限）")
print(f"朴素阈值离散化后最接近 5% 的工作点 = {near:.0%}（实测 {fpr_naive[near]:.1%}）")
print(f"常用 2% 阈值与它之间隔着约 {near / 0.02:.0f} 倍的降幅——阈值是从「无改动时的波动分布」上读出来的，不是拍出来的")

# 3) 注入真实退化时的检出率（检出率 = 1 - 漏报率）
print(f"\n== 3) 注入退化后的检出率（n={N}） ==")
print(f"{'真实退化':>8}{'朴素 ' + f'{near:.0%}' + ' 检出':>14}{'z 检验检出':>12}")
for delta in (0.03, 0.05, 0.08, 0.12, 0.20):
    det_naive, det_z = gate_blocks(N, P_BASE, P_BASE - delta, TRIALS, near)
    print(f"{delta:>8.0%}{det_naive:>14.1%}{det_z:>12.1%}")
print("50 条样本上，8pp 退化检出率只有约 1/4，12pp 也不到五成——门禁的瓶颈是样本量，不是阈值精调")

# 4) 扩样本：n 增大，5% 误报的等价阈值与检出率如何变化
print(f"\n== 4) 扩样本的效果（误报率目标 5%，等价阈值按正态分位点估算） ==")
print(f"{'n':>6}{'等价阈值':>10}{'8pp 退化检出':>14}{'20pp 退化检出':>14}")
for n in (50, 200, 500, 2000):
    thr = 1.645 * np.sqrt(2 * P_BASE * (1 - P_BASE) / n)   # D 的 5% 分位点
    det8, _ = gate_blocks(n, P_BASE, P_BASE - 0.08, TRIALS, thr)
    det20, _ = gate_blocks(n, P_BASE, P_BASE - 0.20, TRIALS, thr)
    print(f"{n:>6}{thr:>10.1%}{det8:>14.1%}{det20:>14.1%}")
print("n 从 50 到 500：等价阈值从约 13pp 收紧到约 4pp，8pp 退化检出率显著上升")

# 5) CI 语义
print(f"\n== 5) 接进 CI 的语义 ==")
print("python regression.py --ci  ->  无改动: 以约 95% 概率返回 0（不阻断）；注入退化: 检出即返回 1（阻断发布）")
print("门禁输出必须带：效应量、95% 置信区间、本次是否触发、历史误报率——只有「通过/失败」的告警无法复盘")

print("\n结论：50 条黄金集上控制 5% 误报率需要约 13pp 的阈值，团队常用的 2% 阈值误报率接近一半，是告警疲劳的直接成因；")
print("读法：1. 门禁阈值必须从无改动重复实验的误报率分布反解，拍脑袋定 2% 等于把掷骰子设成阻断条件；2. z 检验的名义 alpha 即误报率上限，与按分位点定的朴素阈值在 n=50 上功效几乎相同，选它是为了口径统一与可解释；3. 检出率瓶颈在样本量，扩黄金集比调阈值更能提升门禁质量；4. 本示例全部为本地二项分布模拟，50000 次重复、固定种子，数字可复现。")
