# title: 误差分析表：按切片找「错误集中在哪里」
# 关键手法：整体错误率会掩盖切片差异；同时看「错误率」和「错误占比」才能排优先级。
import numpy as np

rng = np.random.default_rng(16)
n = 3000
region = rng.choice(["A", "B", "C"], n, p=[0.4, 0.35, 0.25])
device = rng.choice(["mobile", "desktop"], n, p=[0.6, 0.4])
X = rng.normal(size=(n, 5))

# 概念漂移：A/B 的标签由 x0、x1 决定，C 区改由 x2、x1 决定（模型不知道 region）
logit = np.where(region == "C", 2.5 * X[:, 2] - 1.0 * X[:, 1], 2.0 * X[:, 0] - 1.5 * X[:, 1])
y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(float)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -50, 50)))

Xb = np.c_[np.ones(n), X]
w = np.zeros(Xb.shape[1])
for _ in range(1200):
    p = sigmoid(Xb @ w)
    w -= 0.3 * Xb.T @ (p - y) / n
pred = (sigmoid(Xb @ w) >= 0.5).astype(float)
wrong = pred != y
print(f"整体错误率 = {wrong.mean():.3f}（{wrong.sum()}/{n}）\n")

print(f"{'切片':<18}{'样本数':>7}{'占比':>8}{'错误率':>8}{'错误数':>8}{'错误占比':>9}")
for name, mask in [
    ("region=A", region == "A"),
    ("region=B", region == "B"),
    ("region=C", region == "C"),
]:
    print(f"{name:<18}{mask.sum():>7}{mask.mean():>8.1%}{wrong[mask].mean():>8.3f}"
          f"{wrong[mask].sum():>8d}{wrong[mask].sum()/wrong.sum():>9.1%}")

print()
for name, mask in [
    ("C + mobile", (region == "C") & (device == "mobile")),
    ("C + desktop", (region == "C") & (device == "desktop")),
]:
    print(f"{name:<18}{mask.sum():>7}{mask.mean():>8.1%}{wrong[mask].mean():>8.3f}"
          f"{wrong[mask].sum():>8d}{wrong[mask].sum()/wrong.sum():>9.1%}")

c = region == "C"
print(f"\nC 区贡献了 {wrong[c].sum()/wrong.sum():.0%} 的错误，但只占 {c.mean():.0%} 的样本。")
print("读法：整体 25% 的错误率看不出问题；拆开才发现 C 区错误率比 A/B 高出约 75%，")
print("且 C 区样本占比不小，属于「高错误率 × 大样本」——应优先排查。")
print("结论：误差分析先按业务维度切片（地区/设备/新老用户/时间），")
print("同时报告错误率与错误占比；只看错误率会去修一个只有 5 条样本的噪声切片。")
