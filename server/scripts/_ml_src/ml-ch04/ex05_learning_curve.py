# title: 学习曲线：加数据到底有没有用
# 关键手法：固定验证集，扫训练集大小；看「训练-验证间隙」随样本量怎么变。
import numpy as np

rng = np.random.default_rng(15)
f = lambda x: np.sin(2 * np.pi * x)
SIG = 0.2
Xva = np.linspace(0.05, 0.95, 400)
yva = f(Xva) + rng.normal(0, SIG, len(Xva))

sizes = (20, 40, 80, 160, 320)
REPS = 20

print(f"目标 y = sin(2πx) + N(0, {SIG}²)，验证集固定 400 条，每个设置重复 {REPS} 次")
print(f"{'模型':>8}{'训练量':>8}{'训练 MSE':>10}{'验证 MSE':>10}{'间隙':>9}")
for deg in (1, 9):
    for n in sizes:
        trs, vas = [], []
        for _ in range(REPS):
            x = rng.uniform(0, 1, n)
            y = f(x) + rng.normal(0, SIG, n)
            coef = np.polyfit(x, y, deg)
            trs.append(np.mean((np.polyval(coef, x) - y) ** 2))
            vas.append(np.mean((np.polyval(coef, Xva) - yva) ** 2))
        tr, va = np.mean(trs), np.mean(vas)
        print(f"{'1 次' if deg == 1 else '9 次':>8}{n:>8}{tr:>10.4f}{va:>10.4f}{va - tr:>9.4f}")
    print()

print("读法：")
print("  1 次多项式：训练/验证都停在 0.2 左右，间隙很小——高偏差，加数据几乎不变好。")
print("  9 次多项式：小样本时间隙巨大；样本增加时间隙收窄、验证误差下降——高方差。")
print("结论：学习曲线先回答「这是偏差问题还是方差问题」，再决定加数据还是加容量。")
print("高偏差该加特征/换更强模型；高方差才值得加数据、加正则或做集成。")
