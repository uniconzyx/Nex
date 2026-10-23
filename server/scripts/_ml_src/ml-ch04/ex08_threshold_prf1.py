# title: 阈值与 P/R/F1：同一组分数，不同业务选择
# 关键手法：先固定分数分布，再扫阈值；同时算 ROC-AUC 与 PR-AUC，比较两者在不平衡下的可读性。
import numpy as np

rng = np.random.default_rng(18)
n_pos, n_neg = 200, 2000
score = np.r_[1 / (1 + np.exp(-rng.normal(1.2, 1.0, n_pos))),
              1 / (1 + np.exp(-rng.normal(0.0, 1.0, n_neg)))]
y = np.r_[np.ones(n_pos), np.zeros(n_neg)]
P, N = n_pos, n_neg

def confusion(t):
    pred = score >= t
    tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0)); fn = np.sum(~pred & (y == 1))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-12, prec + rec)
    acc = np.mean(pred == (y == 1))
    return acc, prec, rec, f1, int(pred.sum())

print(f"正例率 {n_pos/(n_pos+n_neg):.1%}（{n_pos} 正 / {n_neg} 负）")
print(f"{'阈值':>6}{'判正数':>8}{'accuracy':>10}{'precision':>11}{'recall':>9}{'F1':>8}")
for t in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3):
    acc, prec, rec, f1, k = confusion(t)
    print(f"{t:>6.1f}{k:>8d}{acc:>10.3f}{prec:>11.3f}{rec:>9.3f}{f1:>8.3f}")

# 全阈值扫描：ROC 与 PR
order = np.argsort(-score)
ys = y[order]
tp = np.cumsum(ys); fp = np.cumsum(1 - ys)
tpr = np.r_[0, tp / P]; fpr = np.r_[0, fp / N]
auc = np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2)
precision = tp / np.maximum(1, tp + fp)
recall = tp / P
ap = np.sum(np.diff(np.r_[0, recall]) * precision)

# 最佳 F1 阈值
best_f1, best_t = -1, None
for t in np.unique(np.round(score, 4)):
    _, _, _, f1, _ = confusion(t)
    if f1 > best_f1:
        best_f1, best_t = f1, t

print(f"\nROC-AUC = {auc:.3f}    PR-AUC(AP) = {ap:.3f}")
print(f"最佳 F1 = {best_f1:.3f}，对应阈值 = {best_t:.3f}")
print(f"全判负的 accuracy = {1 - P/(P+N):.3f}；阈值 0.5 的 accuracy = {confusion(0.5)[0]:.3f}")
print("\n读法：阈值右移 → precision 升、recall 降；左移相反。F1 只在某一小段最优。")
print("ROC 的横轴 FPR 分母是 2000 个负例，负例越多曲线越稳、数值越好看；")
print("PR 的基线是正例率 9.1%，模型只比随机好多少一眼可见。")
print("结论：阈值不是模型参数，是业务成本参数——漏判和误判代价不同，阈值就该不同；")
print("不平衡时用 PR 曲线沟通，用混淆矩阵确认最终阈值下的绝对错误数。")
