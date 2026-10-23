# title: odds ratio 与阈值：不平衡数据下 0.5 为什么失灵
# 1% 正例时，默认阈值 0.5 几乎不预测正类；扫阈值看 P/R/F1，并用 exp(w) 解释 odds。
import numpy as np

rng = np.random.default_rng(17)
n, d = 6000, 3
X = rng.normal(size=(n, d))
X = (X - X.mean(0)) / X.std(0)
Xb = np.column_stack([np.ones(n), X])
beta = np.array([-5.5, 1.2, -0.8, 0.5])
p_true = 1.0 / (1.0 + np.exp(-Xb @ beta))
y = (rng.random(n) < p_true).astype(float)      # 正例约 2%

lam = 1e-3
w = np.zeros(d + 1)
for _ in range(50):
    p = 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -35, 35)))
    W = p * (1 - p)
    g = Xb.T @ (p - y) / n + lam * w
    H = Xb.T @ (Xb * W[:, None]) / n + lam * np.eye(d + 1)
    step = np.linalg.solve(H, g)
    w = w - step
    if np.linalg.norm(step) < 1e-10:
        break
p = 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -35, 35)))

print(f"n={n}，正例比例={y.mean():.4f}，逻辑回归 IRLS 收敛，λ={lam}")
print(f"{'阈值':>6}{'预测正例':>9}{'准确率':>8}{'精确率P':>8}{'召回率R':>8}{'F1':>7}")
best_f1, best_t = -1.0, None
for t in (0.5, 0.3, 0.2, 0.1, 0.05, 0.02):
    pred = (p >= t).astype(float)
    tp = float((pred * y).sum())
    fp = float((pred * (1 - y)).sum())
    fn = float(((1 - pred) * y).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = float((pred == y).mean())
    print(f"{t:>6.2f}{int(pred.sum()):>9}{acc:>8.3f}{prec:>8.3f}{rec:>8.3f}{f1:>7.3f}")
    if f1 > best_f1:
        best_f1, best_t = f1, t

print(f"\nF1 最优阈值 = {best_t}（F1={best_f1:.3f}）；默认 0.5 的 F1 = "
      f"{2*((p>=0.5)*y).sum() / max(((p>=0.5).sum() + y.sum()), 1e-9):.3f}")
print("\nodds ratio（特征已标准化，系数即『每增加 1 个标准差』的 log-odds 变化）：")
for j, name in enumerate(["x1", "x2", "x3"], start=1):
    print(f"  {name}: w={w[j]:+.3f}  exp(w)={np.exp(w[j]):.3f}  "
          f"→ odds 变为原来的 {np.exp(w[j]):.3f} 倍")

print("\n结论：")
print("1. 阈值 0.5 假设两类代价对称且先验均衡；1% 正例时它把几乎所有样本判负，accuracy 虚高、召回近 0；")
print("2. 降阈值提升召回、牺牲精确率，F1 在中间取得最优——阈值是业务代价参数，不是模型参数；")
print("3. odds ratio=exp(wⱼ)：其他特征不变时，xⱼ 每增 1 单位，事件 odds 乘以 exp(wⱼ)（≈ 概率变化在低概率区）；")
print("4. 不平衡下看 PR 曲线与 F1，不要只看 ROC-AUC 与 accuracy；还需先处理采样/权重问题（见 ex10）。")
