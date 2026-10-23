# title: 样本复杂度：泛化 gap 按 1/√m 收缩
# 固定模型容量（5 次多项式），只改样本量，看训练-测试误差间距怎么变。
import numpy as np

rng = np.random.default_rng(13)
f = lambda x: np.sin(2 * np.pi * x)
DEG, REPS = 5, 40
x_pool = rng.uniform(0, 1, 20000)
y_pool = f(x_pool) + rng.normal(0, 0.25, x_pool.size)
x_te, y_te = x_pool[:5000], y_pool[:5000]

print(f"{'样本量m':>8} {'训练MSE':>9} {'测试MSE':>9} {'gap':>8} {'gap·√m':>8}")
for m in (20, 40, 80, 160, 320, 640, 1280):
    trs, tes = [], []
    for _ in range(REPS):
        idx = rng.choice(x_pool.size, m, replace=False)
        w = np.polyfit(x_pool[idx], y_pool[idx], DEG)
        trs.append(np.mean((np.polyval(w, x_pool[idx]) - y_pool[idx]) ** 2))
        tes.append(np.mean((np.polyval(w, x_te) - y_te) ** 2))
    tr, te = np.mean(trs), np.mean(tes)
    gap = te - tr
    print(f"{m:>8} {tr:>9.4f} {te:>9.4f} {gap:>8.4f} {gap*np.sqrt(m):>8.2f}")

print("\n读法：gap·√m 近似为常数 → gap ∝ 1/√m（与 VC/Rademacher 界同阶）。")
print("工程含义：数据翻 4 倍，gap 才减半。所以「离线上不去」时先判断是 gap 问题（加数据）")
print("还是偏差问题（训练误差本身就高，加数据无效，得换模型/加特征）。")
