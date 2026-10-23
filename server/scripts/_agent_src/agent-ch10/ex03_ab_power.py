# title: A/B 两比例检验：样本量、检验力曲线与「不显著」的边界
import numpy as np
from math import ceil, sqrt, erf

# 场景：客服 Agent 解决率 p1=70%，想验证新版本提升 5 个百分点（MDE=0.05）。
# 三个量决定样本量：基线率、MDE、以及 alpha/功效。偷看一眼就多一次假阳性机会。


def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def z_crit(alpha):
    """双尾检验的临界 z 值（仅内置 0.05/0.01 两档）。"""
    return 1.96 if abs(alpha - 0.05) < 1e-9 else 2.576


def z_beta(power):
    """常用功效档位的 z_beta = Phi^-1(power)；仅内置 0.50/0.80/0.90 三档。"""
    return {0.5: 0.0, 0.8: 0.84, 0.9: 1.28}.get(power, 0.84)


def sample_size(p1, mde, alpha=0.05, power=0.8):
    """两比例检验每组样本量：n = 2*pbar*(1-pbar)*(z_a+z_b)^2/delta^2，向上取整。"""
    p2 = p1 + mde
    pbar = (p1 + p2) / 2
    return ceil(2 * pbar * (1 - pbar) * (z_crit(alpha) + z_beta(power)) ** 2 / mde**2)


def power_of(n, p1, p2, alpha=0.05):
    """给定每组 n 的检验力：注意原假设用合并方差 se0，备择用独立方差 se1。"""
    pbar = (p1 + p2) / 2
    se0 = sqrt(2 * pbar * (1 - pbar) / n)            # H0 下的标准误
    se1 = sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)  # H1 下的标准误
    delta = abs(p2 - p1)
    return norm_cdf((delta - z_crit(alpha) * se0) / se1)


p1 = 0.70
print("== 1) MDE 与每组样本量（alpha=0.05, power=0.8） ==")
print(f"{'MDE':>6}{'p2':>7}{'每组 n':>10}{'总样本':>10}")
n_prev = None
mde_prev = None
for mde in (0.10, 0.05, 0.02, 0.01):
    n = sample_size(p1, mde)
    print(f"{mde:>6.2f}{p1 + mde:>7.2f}{n:>10}{2 * n:>10}")
    if n_prev:
        print(f"       ^ MDE 缩到上一档的 {mde / mde_prev:.2f} 倍，样本量约 x{n / n_prev:.1f}（约 1/MDE^2）")
    n_prev, mde_prev = n, mde
print("MDE 0.05 -> 0.025（减半）样本量约 x4：想看见更小的提升，流量要翻几倍")

print("\n== 2) 检验力曲线：p1=0.70, p2=0.75 时 n 与 power 的关系 ==")
print("power |" + "".join(f"{n:>6}" for n in (200, 500, 1000, 1400, 2000, 4000)))
for pw in (0.5, 0.8):
    need = sample_size(p1, 0.05, power=pw)
    print(f"  n={need:<5}|" + "".join(f"{power_of(n, p1, p1 + 0.05):>6.2f}" for n in (200, 500, 1000, 1400, 2000, 4000)))
n80 = sample_size(p1, 0.05)
print(f"80% 功效需要每组 n = {n80}（总 {2 * n80}）")

print("\n== 3) 样本量不足时，「不显著」意味着什么 ==")
n_small = 500
pw_small = power_of(n_small, p1, p1 + 0.05)
print(f"每组只有 {n_small} 时，对 5pp 提升的检验力只有 {pw_small:.2f}")
print(f"-> 即使新版本真的 +5pp，也有约 {1 - pw_small:.0%} 的概率被实验判成「不显著」")
print("-> 「不显著」不等于「没效果」：低功效实验中，不显著是数据不足的默认结局")

print("\n== 4) 偷看（optional stopping）的代价：每看一次就多一次中奖机会 ==")
alpha = 0.05
peeks = 10
# 上界近似：k 次独立偷看下至少一次假阳性的概率上界 1-(1-alpha)^k
print(f"名义 alpha={alpha}，偷看 {peeks} 次的假阳性率上界 ~ {1 - (1 - alpha)**peeks:.0%}")
print("-> 没到样本量就每天看指标，A/B 的假阳性率从 5% 膨胀到 40% 量级")
print("-> 纪律：先算样本量再开实验；必须提前决策时用序贯检验（alpha spending），不要反复偷看")

print("\n结论：A/B 的样本量由基线率、MDE、alpha 与功效四者决定，MDE 减半样本量翻四倍，")
print("读法：1. 样本量公式用合并方差，功效计算要区分 H0/H1 两个标准误，混用会把功效算高；2. 每组 500 样本对 5pp 提升只有约五成功效，此时「不显著」不能作为「无效果」的证据；3. 偷看是实验纪律问题不是代码问题，固定样本量或序贯检验二选一；4. 本示例为本地数值实验，无真实流量参与。")
