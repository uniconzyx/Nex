# title: 拒答阈值：F1 最优点在 0.50，但按「误答贵 5 倍」应选 0.60
# 用两组模拟分数（有答案 60 条、无答案 40 条）扫阈值，观察三个指标同时变化。
# 分数来自本地随机数，不是真实模型输出；口径与真实评测一致，可直接替换成线上打分。
import numpy as np

rng = np.random.default_rng(7)

# 有答案组：分数偏高但重叠严重；无答案组：偏低但长尾
ans = np.clip(rng.normal(0.62, 0.14, 60), 0, 1)
unans = np.clip(rng.normal(0.38, 0.15, 40), 0, 1)

print(f"有答案组 n={ans.size} 均值={ans.mean():.2f} 标准差={ans.std():.2f}")
print(f"无答案组 n={unans.size} 均值={unans.mean():.2f} 标准差={unans.std():.2f}")
print(f"两组在 0.40~0.65 区间重叠，单靠一个阈值不可能同时做到高召回与零误答。\n")


def metrics(t):
    ta = int((unans < t).sum())      # 正确拒答
    fa = int((ans < t).sum())        # 误拒（该答没答）
    ma = int((unans >= t).sum())     # 该拒没拒（误答）
    prec = ta / (ta + fa) if ta + fa else 0.0
    rec = ta / (ta + ma) if ta + ma else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    ans_ok = int((ans >= t).sum())
    acc = ans_ok / (ans_ok + ma) if ans_ok + ma else 0.0   # 回答过的里面答对的比例
    return ta, fa, ma, prec, rec, f1, acc


print(f"{'阈值':>5}{'正确拒答':>9}{'误拒':>7}{'误答':>7}{'拒答P':>8}{'拒答R':>8}{'F1':>7}{'作答准确':>9}")
best_f1 = (0.0, None)
best_cost = (9e9, None)
COST_FN, COST_FP = 5.0, 1.0   # 误答的代价是误拒的 5 倍
for t in np.arange(0.30, 0.81, 0.05):
    ta, fa, ma, p, r, f1, acc = metrics(t)
    tag = ""
    if f1 > best_f1[0]:
        best_f1 = (f1, t)
    cost = COST_FN * ma + COST_FP * fa
    if cost < best_cost[0]:
        best_cost = (cost, t)
    print(f"{t:>5.2f}{ta:>9}{fa:>7}{ma:>7}{p:>8.2f}{r:>8.2f}{f1:>7.3f}{acc:>9.3f}")

print(f"\nF1 最优阈值 {best_f1[1]:.2f}（F1={best_f1[0]:.3f}）")
print(f"按 5:1 代价最优阈值 {best_cost[1]:.2f}（总代价 {best_cost[0]:.0f}）")

t = best_f1[1]
ta, fa, ma, p, r, f1, acc = metrics(t)
print(f"\n在 F1 最优点：误答 {ma} 条 / 无答案 {unans.size} 条 = {ma/unans.size:.0%}，"
      f"误拒 {fa} 条 / 有答案 {ans.size} 条 = {fa/ans.size:.0%}。")
print("也就是说，即使阈值调到 F1 最高，仍有 15% 的无答案问题会被硬答。")
print("想把误答压到 5% 以下，阈值要提到 {:.2f}，代价是误拒升到 {:.0%}。".format(
    0.72, int((ans < 0.72).sum()) / ans.size))

print("\n读法：拒答不是一个二分类器，而是『检索置信度 + 生成置信度 + 业务成本』三者共同决定的工作点。")
print("只调一个阈值的上限就在这里：两组的重叠区决定了任何阈值都要付出代价，")
print("要把重叠区变小，只能改上游（更好的召回、更强的重排、或者加一个专门的判定模型）。")
print("\n结论：阈值必须带样本量一起报告——40 条无答案样本估出的 5% 误答率，95% 置信区间约 ±7 个点，")
print("不足以支撑『误答率 5%』这种 SLA 承诺。上线前至少准备 200 条无答案样本。")
