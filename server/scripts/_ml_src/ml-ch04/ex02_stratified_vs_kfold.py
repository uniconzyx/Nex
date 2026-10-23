# title: 分层 vs 普通 K 折：稀有类别在折间怎么分布
# 关键手法：同一份不平衡数据，只换切分方式，统计每折的正例数与正例率。
import numpy as np

rng = np.random.default_rng(12)
n, K = 600, 5
y = np.zeros(n)
pos = rng.choice(n, size=12, replace=False)   # 2% 正例
y[pos] = 1
idx = np.arange(n)

def kfold_plain(y, K):
    order = rng.permutation(len(y))
    return [order[i::K] for i in range(K)]

def kfold_stratified(y, K):
    folds = [[] for _ in range(K)]
    for cls in (0, 1):
        ids = np.where(y == cls)[0]
        ids = rng.permutation(ids)
        for i, chunk in enumerate(np.array_split(ids, K)):
            folds[i].extend(chunk.tolist())
    return [np.array(sorted(f)) for f in folds]

def report(name, folds):
    counts = np.array([int(y[f].sum()) for f in folds])
    rates = counts / np.array([len(f) for f in folds])
    print(f"\n{name}：")
    print("  每折样本数:", [len(f) for f in folds])
    print("  每折正例数:", counts.tolist())
    print("  每折正例率:", np.round(rates, 4).tolist())
    print(f"  正例率 std = {rates.std(ddof=1):.4f}，含 0 正例的折数 = {int((counts == 0).sum())}")

report("普通 K 折（只打乱样本）", kfold_plain(y, K))
report("分层 K 折（按类别分层）", kfold_stratified(y, K))

print("\n读法：普通 K 折把 12 个正例随机撒进 5 折，会出现某折只有 0~1 个正例；")
print("该折上的 recall/F1 要么无法计算，要么方差极大，折平均会被少数折主导。")
print("结论：分类任务默认用 StratifiedKFold；类别极稀有（<1%）时还要增加折数或重复分层 CV，")
print("并在报告里给出每折的正例数——只报一个平均分是在掩盖切分噪声。")
