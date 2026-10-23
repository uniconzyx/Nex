# title: 二项比例的置信区间与样本量：50 条黄金集能分辨多大的变化
import numpy as np
from math import sqrt

# 固定场景：黄金集 n 条，通过率 p_hat。回答两个问题：
#   1) 这个点值的 95% 置信区间有多宽（Wilson 区间，小样本比正态近似稳）；
#   2) 要把区间半宽压到 eps，需要多少样本（样本量反解）。


def wilson(k, n, z=1.96):
    """Wilson score 区间：二项比例的 95% CI，小样本下覆盖率优于 p_hat ± z*sqrt(...)。"""
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def sample_size(p, eps, z=1.96):
    """样本量反解：n = z^2 * p(1-p) / eps^2（最坏情况 p=0.5 时最大）。"""
    return int(np.ceil(z * z * p * (1 - p) / (eps * eps)))


print("== 1) 同一批 50 条样本，不同通过率的区间宽度 ==")
print(f"{'k/n':>10}{'p_hat':>8}{'95% Wilson 区间':>24}{'半宽':>8}")
for k in (25, 40, 41, 45):
    lo, hi = wilson(k, 50)
    print(f"{k:>4}/50{k / 50:>8.2f}   [{lo:.3f}, {hi:.3f}]{'':>6}{(hi - lo) / 2:>8.3f}")
lo41, hi41 = wilson(41, 50)
print(f"41/50 = 82% 的区间是 [{lo41:.1%}, {hi41:.1%}]，半宽约 {(hi41 - lo41) / 2:.1%}")
print("-> 50 条黄金集只能分辨「巨大」变化：2~3 个百分点的提升完全在噪声里")

print("\n== 2) 82% vs 80%：点值差 2pp，在 50 条上显著吗 ==")
lo80, hi80 = wilson(40, 50)
overlap = not (lo41 > hi80 or lo80 > hi41)
print(f"40/50 区间 [{lo80:.1%}, {hi80:.1%}]；41/50 区间 [{lo41:.1%}, {hi41:.1%}]；区间重叠 = {overlap}")
# McNemar 成对检验（更灵敏）：同一批样本上「新对旧错」b 与「旧对新错」c
b, c = 6, 5
chi2 = (abs(b - c) - 1) ** 2 / (b + c)
print(f"若 6 个「新对旧错」、5 个「旧对新错」，McNemar 校正卡方 = {chi2:.2f} < 3.84 -> 不显著")

print("\n== 3) 要把区间半宽压到 eps，需要多少样本 ==")
print(f"{'eps':>6}{'p=0.8 所需 n':>14}{'p=0.5 所需 n':>14}{'说明':>20}")
for eps in (0.15, 0.10, 0.05, 0.03):
    n8, n5 = sample_size(0.8, eps), sample_size(0.5, eps)
    note = "当前规模" if n8 <= 60 else ("需扩样" if n8 <= 400 else "线上流量")
    print(f"{eps:>6.2f}{n8:>14}{n5:>14}{note:>16}")
print("eps 减半 -> n 变 4 倍（1/eps^2）：想检出 2pp 差异，样本量是检出 4pp 的 4 倍")

print("\n== 4) 50 条上真正能说的结论长什么样 ==")
print(f"「离线准确率 82%，95% CI [{lo41:.1%}, {hi41:.1%}]，与旧版本差异不具统计显著性」")
print("而不是「显著更优，达到发布标准」——后者是小样本报告最常见的过度断言")

print("\n结论：50 条黄金集的区间半宽约 ±10~13 个百分点，它的使命是抓大退化，不是分辨小改进；")
print("读法：1. 报指标必须报 Wilson 区间而非裸点值，否则 41/50 与 40/50 会被讲成两个世界；2. 样本量按 n=z^2 p(1-p)/eps^2 反解，MDE 减半样本量翻四倍；3. 同一批样本的前后对比优先用 McNemar 成对检验，方差比两比例独立检验小；4. 本示例只用 numpy 与 math，所有数字可由公式手算复核。")
