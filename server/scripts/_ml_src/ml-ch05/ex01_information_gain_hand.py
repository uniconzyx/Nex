# title: 信息增益、增益率与基尼指数：同一份数据上的三种口径
# 手算 14 条样本的熵、条件熵、信息增益、固有值、增益率与基尼指数，
# 重点看「增益偏向多取值特征」这件事在数值上怎么发生。
import numpy as np

# (outlook, temp, humidity, wind, play)
data = [
    ("sunny", "hot", "high", "weak", "no"),
    ("sunny", "hot", "high", "strong", "no"),
    ("overcast", "hot", "high", "weak", "yes"),
    ("rain", "mild", "high", "weak", "yes"),
    ("rain", "cool", "normal", "weak", "yes"),
    ("rain", "cool", "normal", "strong", "no"),
    ("overcast", "cool", "normal", "strong", "yes"),
    ("sunny", "mild", "high", "weak", "no"),
    ("sunny", "cool", "normal", "weak", "yes"),
    ("rain", "mild", "normal", "weak", "yes"),
    ("sunny", "mild", "normal", "strong", "yes"),
    ("overcast", "mild", "high", "strong", "yes"),
    ("overcast", "hot", "normal", "weak", "yes"),
    ("rain", "mild", "high", "strong", "no"),
]
feats = ["outlook", "temp", "humidity", "wind"]
y = np.array([1 if r[4] == "yes" else 0 for r in data])


def entropy(counts):
    p = np.asarray(counts, float)
    p = p[p > 0] / p.sum()
    return float(-(p * np.log2(p)).sum())


def gini(counts):
    p = np.asarray(counts, float)
    p = p[p > 0] / p.sum()
    return float(1.0 - (p ** 2).sum())


n = len(y)
H_D = entropy([y.sum(), n - y.sum()])
G_D = gini([y.sum(), n - y.sum()])
print(f"样本 n={n}  正例={y.sum()}  负例={n-y.sum()}")
print(f"根结点：H(D)={H_D:.4f} bit   Gini(D)={G_D:.4f}")
print()
print(f"{'特征':<10}{'取值':>4}{'H(D|A)':>9}{'Gain':>8}{'IV':>8}{'GainRatio':>10}{'Gini(D|A)':>11}")
rows = []
for j, f in enumerate(feats):
    vals = [r[j] for r in data]
    H_cond = 0.0
    G_cond = 0.0
    for v in sorted(set(vals)):
        mask = np.array([x == v for x in vals])
        cnt = [int(y[mask].sum()), int((1 - y[mask]).sum())]
        w = mask.sum() / n
        H_cond += w * entropy(cnt)
        G_cond += w * gini(cnt)
    iv = entropy([sum(1 for x in vals if x == v) for v in sorted(set(vals))])
    gain = H_D - H_cond
    rows.append((f, len(set(vals)), H_cond, gain, iv, gain / iv, G_cond))
    print(f"{f:<10}{len(set(vals)):>4}{H_cond:>9.4f}{gain:>8.4f}{iv:>8.4f}"
          f"{gain / iv:>10.4f}{G_cond:>11.4f}")

print()
print("读法 1：outlook 的 Gain=0.2467 最大，但它只有 3 个取值；")
print("        'wind' 只有 2 个取值，Gain 却排第二——增益率用 IV 惩罚了取值多的特征。")
print("读法 2：outlook 的 IV=1.5774 最大，增益率把它压到 0.1564；")
print("        这正是 Quinlan 引入增益率的原因：信息增益对『把样本切得更碎』有系统性偏好。")
print("读法 3：基尼与熵在这里给出相同的特征排序，因为都是凹的纯度函数、只在端点附近曲率不同；")
print("        排序一致不等于每次分裂都一致，ex02 会给出一个排序分歧的反例。")
