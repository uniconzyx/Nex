# title: 分组泄漏：同一实体的样本同时出现在训练和测试里
# 关键手法：用 1-NN 放大泄漏；统计「最近邻是否同组」与准确率，一眼看出虚高来自哪。
import numpy as np

rng = np.random.default_rng(13)
G, per, K = 50, 8, 5
group = np.repeat(np.arange(G), per)
# 50 个实体排成 10x5 的网格，每个实体有自己的中心；样本在中心附近抖动
gx, gy = np.meshgrid(np.arange(10), np.arange(5))
centers = np.c_[gx.ravel(), gy.ravel()].astype(float)
label = rng.integers(0, 2, G)             # 标签由实体决定，与位置无关（不可泛化）
X = centers[group] + rng.normal(0, 0.12, (len(group), 2))
y = label[group]
n = len(y)

def knn_predict(Xtr, ytr, Xte, k=1):
    d2 = ((Xte[:, None, :] - Xtr[None, :, :]) ** 2).sum(-1)
    nn = np.argsort(d2, axis=1)[:, :k]
    return (ytr[nn].mean(1) >= 0.5).astype(float), nn[:, 0]

def eval_folds(folds, name):
    accs, same = [], []
    for te in folds:
        tr = np.setdiff1d(np.arange(n), te)
        pred, nn = knn_predict(X[tr], y[tr], X[te])
        accs.append(np.mean(pred == y[te]))
        same.append(np.mean(group[tr][nn] == group[te]))
    print(f"\n{name}：")
    print("  每折准确率:", np.round(accs, 3).tolist())
    print(f"  平均准确率 = {np.mean(accs):.3f} ± {np.std(accs, ddof=1):.3f}")
    print(f"  测试样本的最近邻同组比例 = {np.mean(same):.1%}")
    return np.mean(accs)

# 普通 K 折：打乱样本，同一实体会被切到两边
perm = rng.permutation(n)
folds_plain = [perm[i::K] for i in range(K)]
acc_plain = eval_folds(folds_plain, "普通 K 折（按样本切）")

# 分组 K 折：整组进同一折，测试实体完全没见过
gperm = rng.permutation(G)
folds_group = [np.where(np.isin(group, gperm[i::K]))[0] for i in range(K)]
acc_group = eval_folds(folds_group, "分组 K 折（按实体切）")

print(f"\n准确率差（普通 - 分组）= {acc_plain - acc_group:+.3f}")
print("读法：普通 K 折下最近邻几乎总是同组，模型只是把训练时见过的实体标签抄过来；")
print("分组切分后，新实体的位置不再对应任何已知标签，准确率回落到随机水平。")
print("结论：样本不独立（同一患者多次就诊、同一用户多条行为、同一设备多天数据）时，")
print("必须按实体分组切分；否则 CV 分数再高也不代表能泛化到新实体。")
