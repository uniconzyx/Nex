# title: XGBoost 分裂增益手算：G、H、λ、γ 各自在做什么
# 固定一组样本与上一轮预测，按二阶目标
#   Obj = Σ[g_i f(x_i) + ½h_i f(x_i)²] + ½λΣf² + γT
# 枚举所有切分，比较 λ=0 与 λ=1 的增益排序，并展示叶值 w*=−G/(H+λ)。
import numpy as np

x = np.array([0.10, 0.20, 0.30, 0.40, 0.55, 0.65, 0.80, 0.90])
y = np.array([0, 0, 0, 1, 0, 1, 1, 1])
F_prev = np.full(len(x), -0.85)          # 上一轮的打分（logit）
p = 1 / (1 + np.exp(-F_prev))
g = p - y                                 # 一阶导
h = p * (1 - p)                           # 二阶导

print("上一轮打分 F=-0.85 → p=%.4f，故每个样本 g=p−y, h=p(1−p)=%.4f" % (p[0], h[0]))
print(f"{'x':>6}{'y':>4}{'g':>9}{'h':>9}")
for i in range(len(x)):
    print(f"{x[i]:>6.2f}{y[i]:>4d}{g[i]:>9.4f}{h[i]:>9.4f}")

G, H = g.sum(), h.sum()
print(f"\n根结点：G={G:+.4f}  H={H:.4f}")


def gain(gl, hl, gr, hr, lam, gamma=0.0):
    return 0.5 * (gl ** 2 / (hl + lam) + gr ** 2 / (hr + lam) - G ** 2 / (H + lam)) - gamma


print(f"\n候选切分（λ=1, γ=0）")
print(f"{'阈值':>6}{'G_L':>9}{'H_L':>9}{'G_R':>9}{'H_R':>9}{'Gain':>10}")
rows = []
for i in range(1, len(x)):
    thr = 0.5 * (x[i - 1] + x[i])
    gl, hl = g[:i].sum(), h[:i].sum()
    gr, hr = g[i:].sum(), h[i:].sum()
    rows.append((thr, gl, hl, gr, hr, gain(gl, hl, gr, hr, 1.0)))
    print(f"{thr:>6.3f}{gl:>9.4f}{hl:>9.4f}{gr:>9.4f}{hr:>9.4f}{rows[-1][5]:>10.4f}")

best = max(rows, key=lambda r: r[5])
print(f"\n最优切分 x<={best[0]:.3f}，Gain={best[5]:.4f}（γ=0 时只要 Gain>0 就分裂）")

# λ 的影响：同一最优位置上的叶值与增益
print(f"\n{'λ':>5}{'w*_L':>9}{'w*_R':>9}{'Gain':>10}")
for lam in (0.0, 0.5, 1.0, 5.0, 20.0):
    gl, hl, gr, hr = best[1], best[2], best[3], best[4]
    wl, wr = -gl / (hl + lam), -gr / (hr + lam)
    print(f"{lam:>5.1f}{wl:>9.4f}{wr:>9.4f}{gain(gl, hl, gr, hr, lam):>10.4f}")
print("读法 1：λ 出现在分母，把叶值往 0 收缩；λ→∞ 时增益→0，树退化为不分裂。")
print("读法 2：λ 不是『正则化系数』这么笼统——它直接改变每个叶子的最优步长，")
print("        进而改变分裂排序：小样本/大梯度的切分会被更强的收缩压下去。")

# γ 的影响：增益门槛
print(f"\nγ 门槛（λ=1）：")
for gamma in (0.0, 0.05, 0.10, 0.20):
    gv = gain(best[1], best[2], best[3], best[4], 1.0, gamma)
    print(f"γ={gamma:>4.2f} → Gain−γ={gv:>7.4f}  {'分裂' if gv > 0 else '不分裂'}")
print("读法 3：γ 是『新增一个叶子必须赚回的最小增益』，与 λ 的作用位置不同：")
print("        λ 进目标函数、影响所有叶值；γ 只在分裂决策处做阈值，不改变已选叶值。")

# min_child_weight：用 H 而不是样本数做约束
print(f"\nmin_child_weight 约束（每个子结点 H ≥ 阈值）：")
for mcw in (0.0, 0.5, 1.0, 1.5):
    ok = best[2] >= mcw and best[4] >= mcw
    print(f"min_child_weight={mcw:>3.1f} → H_L={best[2]:.3f}, H_R={best[4]:.3f}  "
          f"{'允许' if ok else '拒绝'}")
print("读法 4：min_child_weight 约束的是 hessian 之和（≈该结点的预测不确定性），")
print("        不是样本数。类别极不平衡时，一个含很多样本但全是易分负例的结点 H 很小，")
print("        会被它挡住——这正是 XGBoost 用它替代 min_samples_leaf 的原因。")
