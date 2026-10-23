# title: 时间序列的前向验证：随机 K 折为什么过于乐观
# 关键手法：同一组滞后特征，只换切分方式；随机切分是在「插值」，前向切分才是在「预测」。
import numpy as np

rng = np.random.default_rng(14)
T = 200
t = np.arange(T)
y = np.sin(2 * np.pi * t / 50) + rng.normal(0, 0.25, T)

# 用时间的多项式基做特征：随机切分能插值，前向切分要外推
tt = t / 100.0
Phi = np.column_stack([tt ** p for p in range(1, 4)])

def fit_predict(tr, te):
    coef, *_ = np.linalg.lstsq(Phi[tr], y[tr], rcond=None)
    return Phi[te] @ coef

def mse(a, b):
    return float(np.mean((a - b) ** 2))

K = 5
perm = rng.permutation(T)
random_folds = [perm[i::K] for i in range(K)]
rnd_mse = []
for te in random_folds:
    tr = np.setdiff1d(np.arange(T), te)
    rnd_mse.append(mse(y[te], fit_predict(tr, te)))
print("随机 K 折（打乱时间）：")
print("  各折 MSE:", [f"{v:.4f}" for v in rnd_mse], f"  平均 {np.mean(rnd_mse):.4f}")

print("\n前向验证（每块只用它之前的全部数据训练）：")
fwd_mse = []
block = T // K
for b in range(1, K):
    te = np.arange(b * block, (b + 1) * block)
    tr = np.arange(0, b * block)
    v = mse(y[te], fit_predict(tr, te))
    fwd_mse.append(v)
    print(f"  训练 [0,{b*block:>3}) -> 测试 [{b*block:>3},{b*block+block:>3})  MSE = {v:.4f}")
print(f"  平均 {np.mean(fwd_mse):.4f}")

print(f"\n前向误差 / 随机误差 = {np.mean(fwd_mse) / np.mean(rnd_mse):.1f}x（随机 CV 严重低估）")
print("读法：随机 K 折的测试点两侧都有训练点，模型只需在已知区间内插值；")
print("前向验证要求用过去外推未来，误差才反映上线后的真实表现。")
print("结论：只要样本有时间顺序（用户行为、交易、传感器），就用 TimeSeriesSplit / 滚动窗口，")
print("并且任何依赖未来的特征（滑窗统计、目标编码）都必须在每个训练窗口内重算。")
