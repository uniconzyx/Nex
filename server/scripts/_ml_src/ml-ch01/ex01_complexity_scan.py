# title: 复杂度扫描：训练误差单调降，测试误差是 U 形
# 目标 y = sin(2πx) + 噪声，用多项式阶数当「容量旋钮」，样本量只有 15。
# 这张表是整章的地图：过拟合不是「模型大」，而是「容量超过了数据能约束的范围」。
import numpy as np

rng = np.random.default_rng(0)
f = lambda x: np.sin(2 * np.pi * x)

n_train = 15
x_tr = rng.uniform(0, 1, n_train)
y_tr = f(x_tr) + rng.normal(0, 0.25, n_train)
x_te = np.linspace(0, 1, 300)
y_te = f(x_te) + rng.normal(0, 0.25, x_te.size)

rows = []
for deg in range(1, 13):
    w = np.polyfit(x_tr, y_tr, deg)
    tr = np.mean((np.polyval(w, x_tr) - y_tr) ** 2)
    te = np.mean((np.polyval(w, x_te) - y_te) ** 2)
    rows.append((deg, tr, te))

best_deg, best_te = min(((d, te) for d, _, te in rows), key=lambda t: t[1])

print(f"样本量 n={n_train}，噪声 σ=0.25，测试集 300 点")
print(f"{'阶数':>4} {'参数量':>6} {'训练MSE':>11} {'测试MSE':>11}  诊断")
for deg, tr, te in rows:
    if deg <= 2:
        tag = "欠拟合（高偏差）"
    elif te > 3 * best_te:
        tag = "过拟合（高方差）"
    else:
        tag = "合适"
    print(f"{deg:>4} {deg + 1:>6} {tr:>11.5f} {te:>11.4f}  {tag}")

print(f"\n测试误差最低：{best_deg} 阶（MSE={best_te:.4f}），参数量 {best_deg + 1} 已接近样本量 {n_train}。")
last = rows[-1]
print(f"最高阶：训练 MSE={last[1]:.5f}（几乎为 0），测试 MSE={last[2]:.4f}（放大 {last[2]/best_te:.0f} 倍）。")
print("\n结论：训练误差单调下降这件事本身没有信息量；容量要按验证误差选，不是按训练误差选。")
print("另外注意：参数量一旦接近样本量，测试误差会以数量级跳升——这就是「插值阈值」附近的危险区。")
