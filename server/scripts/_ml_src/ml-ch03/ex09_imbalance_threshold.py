# title: 类别不平衡下的阈值：accuracy 的假象与 P/R/F1
# 关键手法：同一组模型分数，只移动阈值；同时看 PR-AUC 与 ROC-AUC 的差异。
import numpy as np

rng = np.random.default_rng(6)
n, d = 4000, 6
y = (rng.random(n) < 0.02).astype(float)
X = rng.normal(size=(n, d))
X[y == 1] += 1.15                      # 弱信号：不做特征工程也能分开一点

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

W1 = rng.normal(0, 0.5, (d, 16)); b1 = np.zeros(16)
W2 = rng.normal(0, 0.5, (16, 1)); b2 = np.zeros(1)
for t in range(1200):
    a1 = np.tanh(X @ W1 + b1)
    p = sigmoid(a1 @ W2 + b2).ravel()
    m = n
    dp = ((p - y) / m).reshape(-1, 1)
    dW2 = a1.T @ dp; db2 = dp.sum(0)
    dz1 = (dp @ W2.T) * (1 - a1 ** 2)
    dW1 = X.T @ dz1; db1 = dz1.sum(0)
    W1 -= 0.2 * dW1; b1 -= 0.2 * db1
    W2 -= 0.2 * dW2; b2 -= 0.2 * db2

a1 = np.tanh(X @ W1 + b1)
score = sigmoid(a1 @ W2 + b2).ravel()

def prf(t):
    pred = score >= t
    tp = np.sum(pred & (y == 1)); fp = np.sum(pred & (y == 0)); fn = np.sum(~pred & (y == 1))
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn)
    F = 2 * P * R / max(1e-12, P + R)
    acc = np.mean(pred == (y == 1))
    return acc, P, R, F, int(pred.sum())

print(f"正例比例 {y.mean():.2%}（{int(y.sum())}/{n}），模型为 6-16-1 MLP")
print(f"{'阈值':>6}{'预测正例':>9}{'accuracy':>10}{'precision':>11}{'recall':>9}{'F1':>8}")
for t in (0.9, 0.5, 0.3, 0.1, 0.05, 0.02):
    acc, P, R, F, k = prf(t)
    print(f"{t:>6.2f}{k:>9d}{acc:>10.3f}{P:>11.3f}{R:>9.3f}{F:>8.3f}")

# ROC-AUC（秩和公式）与 PR-AUC（平均精度）
def roc_auc(s):
    order = np.argsort(s)
    ranks = np.empty(n)
    ranks[order] = np.arange(1, n + 1)
    npos = y.sum(); nneg = n - npos
    return (ranks[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)

def ap(s):
    order = np.argsort(-s)
    ys = y[order]
    tp = np.cumsum(ys)
    precision = tp / np.arange(1, n + 1)
    recall = tp / ys.sum()
    return np.sum(np.diff(np.r_[0, recall]) * precision)

print(f"\nROC-AUC = {roc_auc(score):.3f}   PR-AUC(AP) = {ap(score):.3f}")
print(f"全判负的 accuracy = {1 - y.mean():.3f}（0.5 阈值下 accuracy 再高也不能说明模型有用）")
print("\n读法：阈值从 0.9 降到 0.02，召回上升、精确率下降；F1 在中间某个阈值最好。")
print("结论：不平衡任务先定业务目标（宁可误报还是漏报），再用 PR 曲线选阈值；")
print("ROC-AUC 因负例极多而显得漂亮，PR-AUC 才直接暴露「查得准不准」。")
