# title: 偏差-方差分解：用 Bootstrap 把三项拆开
# 关键手法：固定测试网格 + 重复抽样训练集，才能近似 E_S[·]；
# 且实测误差必须包含「测试时新抽的噪声」，否则会漏掉 σ² 这一项。
import numpy as np

rng = np.random.default_rng(1)
f = lambda x: np.sin(2 * np.pi * x)
SIGMA = 0.25
xt = np.linspace(0.05, 0.95, 50)      # 固定测试网格
f_star = f(xt)
B, n = 300, 30

def draw_train():
    x = rng.uniform(0, 1, n)
    return x, f(x) + rng.normal(0, SIGMA, n)

print(f"{'阶数':>4} {'bias²':>9} {'variance':>10} {'σ²':>7} {'三项和':>9} "
      f"{'实测误差':>10}  相对误差")
for deg in (1, 3, 5, 9, 12):
    preds = np.empty((B, xt.size))
    errs = np.empty(B)
    for b in range(B):
        x, y = draw_train()
        preds[b] = np.polyval(np.polyfit(x, y, deg), xt)
        y_test = f_star + rng.normal(0, SIGMA, xt.size)   # 测试时的新噪声
        errs[b] = np.mean((y_test - preds[b]) ** 2)
    f_bar = preds.mean(axis=0)
    bias2 = np.mean((f_star - f_bar) ** 2)
    var = np.mean(preds.var(axis=0))
    total = bias2 + var + SIGMA ** 2
    empirical = errs.mean()
    rel = abs(total - empirical) / empirical
    print(f"{deg:>4} {bias2:>9.5f} {var:>10.5f} {SIGMA**2:>7.4f} "
          f"{total:>9.5f} {empirical:>10.5f}  {rel:>7.2%}")

print("\n读法：随阶数上升，bias² 单调降、variance 单调升，总误差在最优点处最低。")
print("三项和的相对误差在几个百分点内（Monte Carlo 误差，B 越大越准）。")
print("σ²=0.0625 是任何模型都突破不了的下界 —— 它来自数据本身，不来自算法。")
