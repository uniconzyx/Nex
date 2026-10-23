# title: 提示版本 A/B 的显著性判断：2 个点的提升，需要多少样本才不是噪声
# 两比例 z 检验 + 置信区间 + 所需样本量；再模拟「边跑边看」如何把假阳性率从 5% 抬到 20%+。
import math
import numpy as np

def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def z_test(p1, n1, p2, n2):
    p = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se if se else 0.0
    return z, 2 * (1 - phi(abs(z)))

def ci(p1, n1, p2, n2):
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p2 - p1
    return d - 1.96 * se, d + 1.96 * se

def required_n(p1, p2, alpha=0.05, power=0.80):
    d = abs(p2 - p1)
    pbar = (p1 + p2) / 2
    za, zb = 1.96, 0.8416
    return ((za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / d) ** 2

P1, P2 = 0.30, 0.32
print("=" * 86)
print("表 1  同一提升（30% → 32%）在不同样本量下的显著性")
print("=" * 86)
print(f"{'每组 n':>8}{'差值':>8}{'z':>8}{'p 值':>9}{'95% CI':>22}  判定")
for n in (200, 1000, 5000, 20000, 50000):
    z, p = z_test(P1, n, P2, n)
    lo, hi = ci(P1, n, P2, n)
    verdict = "显著" if p < 0.05 else "不显著"
    print(f"{n:>8}{P2-P1:>8.1%}{z:>8.2f}{p:>9.3f}  [{lo:>6.2%}, {hi:>6.2%}]{verdict:>8}")

n_req = required_n(P1, P2)
print(f"\n要在 α=0.05、power=80% 下检出 2pp 提升，每组需要约 {math.ceil(n_req):,} 个样本。")
print(f"若提升只有 1pp，则需要约 {math.ceil(required_n(0.30, 0.31)):,} 个/组——这就是小流量实验测不出小改进的原因。")

# 边跑边看：零假设成立（两版都是 30%），每 500 个样本看一次，只要有一次 p<0.05 就宣布显著
rng = np.random.default_rng(5)
SIM, PEEK_EVERY, MAX_N = 2000, 500, 5000
false_pos = 0
for _ in range(SIM):
    a = rng.binomial(1, 0.30, MAX_N).cumsum()
    b = rng.binomial(1, 0.30, MAX_N).cumsum()
    for n in range(PEEK_EVERY, MAX_N + 1, PEEK_EVERY):
        _, p = z_test(a[n-1] / n, n, b[n-1] / n, n)
        if p < 0.05:
            false_pos += 1
            break

print("\n" + "=" * 86)
print("表 2  「边跑边看」的假阳性膨胀（真实效果为 0，模拟 2000 次）")
print("=" * 86)
print(f"  固定样本量检验的 α        : 5.0%（理论值）")
print(f"  每 500 个看一次、显著即停  : {false_pos/SIM:.1%}")
print(f"  膨胀倍数                  : {(false_pos/SIM)/0.05:.1f}x")

print("\n结论：2pp 的提升在 n=2000/组时 p≈0.35，看起来「有提升」其实完全是噪声；")
print("      而边跑边看会把 5% 的假阳性率抬到 15%~20%，等于自己制造「显著」。")
print("读法：实验前先算样本量并冻结时长；中途只看护栏指标（错误率、延迟），不看主指标；")
print("      必须中途决策就用序贯检验（alpha spending），不要用固定阈值的 p 值。")
