# title: 留出集评估与 Bootstrap 置信区间
# 200 条留出集上 82% vs 87% 到底算不算「变好了」？点估计不够，必须给区间。
import math
import numpy as np

N = 200
rng = np.random.default_rng(42)
u = rng.random(N)
a = (u < 0.82).astype(int)                 # 模型 A
b = (u < 0.87).astype(int)                 # 模型 B（与 A 同分布抽样，高度相关）
# 少量样本上是 A 对 B 错 / A 错 B 对，制造真实分歧
flip = rng.choice(N, 24, replace=False)
for i in flip[:14]:
    a[i], b[i] = 1, 0
for i in flip[14:]:
    a[i], b[i] = 0, 1

def bootstrap_ci(x, B=4000):
    idx = rng.integers(0, len(x), size=(B, len(x)))
    accs = x[idx].mean(axis=1)
    return np.percentile(accs, [2.5, 97.5])

acc_a, acc_b = a.mean(), b.mean()
lo_a, hi_a = bootstrap_ci(a)
lo_b, hi_b = bootstrap_ci(b)
diff = b - a
idx = rng.integers(0, N, size=(4000, N))
d_boot = diff[idx].mean(axis=1)
lo_d, hi_d = np.percentile(d_boot, [2.5, 97.5])

print(f"留出集 n={N}")
print(f"A：准确率 {acc_a:.1%}，95% CI [{lo_a:.1%}, {hi_a:.1%}]，区间宽 {(hi_a-lo_a)*100:.1f}pp")
print(f"B：准确率 {acc_b:.1%}，95% CI [{lo_b:.1%}, {hi_b:.1%}]，区间宽 {(hi_b-lo_b)*100:.1f}pp")
print(f"配对差值 B−A = {acc_b-acc_a:+.1%}，95% CI [{lo_d:+.1%}, {hi_d:+.1%}]")

# McNemar：只看分歧样本
n01 = int(((a == 0) & (b == 1)).sum())
n10 = int(((a == 1) & (b == 0)).sum())
stat = abs(n01 - n10) / math.sqrt(n01 + n10) if n01 + n10 else 0.0
p = 2 * (1 - 0.5 * (1 + math.erf(stat / math.sqrt(2))))
print(f"\nMcNemar：A错B对 {n01} 条，A对B错 {n10} 条，χ²={stat**2:.2f}，p≈{p:.3f}")
print("判定：" + ("差异显著（p<0.05）" if p < 0.05 else "差异不显著，不能宣称模型 B 更好"))

# 样本量与区间宽度的关系
print(f"\n{'n':>6}{'理论 95% 半宽':>15}")
for n in (100, 200, 500, 1000, 2000):
    half = 1.96 * math.sqrt(0.85 * 0.15 / n)
    print(f"{n:>6}{half*100:>14.1f}pp")

print("\n结论：200 条样本的 95% 区间约 ±5pp，2.5pp 的提升完全落在噪声范围内。")
print("读法：")
print("1. 报告必须写「准确率 + 区间 + n」，只写 83% 无法判断可信度；")
print("2. 同一批样本上比两个模型要用**配对** bootstrap / McNemar，独立区间会低估显著性；")
print("3. 要把区间压到 ±3pp，留出集至少 700~1000 条 —— 这比换模型便宜得多；")
print("4. 若业务只关心「不退步」，还应看置信下界，而不是点估计。")
