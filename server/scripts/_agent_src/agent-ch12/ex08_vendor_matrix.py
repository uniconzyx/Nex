# title: 竞品对比矩阵：加权打分与两套权重下的结论翻转
# 工程账本（示例测算）：4 个候选 × 5 维度，展示权重敏感性——总分第一只是「默认权重下第一」。

DIMS = ["集成能力", "数据可控", "成本结构", "交付速度", "定制深度"]
SCORES = {
    "自建":   [3, 5, 3, 1, 5],
    "Dify":   [4, 3, 4, 4, 3],
    "n8n":    [5, 3, 4, 4, 3],
    "云API":  [4, 1, 5, 5, 1],
}
W_DATA = [0.15, 0.35, 0.20, 0.10, 0.20]   # 数据敏感型客户（金融/政企）
W_SPEED = [0.15, 0.15, 0.20, 0.30, 0.20]  # 速度优先型客户（互联网业务）


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


def rank(weights):
    assert abs(sum(weights) - 1) < 1e-6, "权重和必须为 1"
    return sorted(((sum(w * s for w, s in zip(weights, v)), k)
                   for k, v in SCORES.items()), reverse=True)


def dim_winners(weights):
    """逐维度看谁领先：总分之外的 Pareto 信息"""
    return {d: max(SCORES, key=lambda k: SCORES[k][i]) for i, d in enumerate(DIMS)}


print("== 打分矩阵（1~5 分；示例测算，含对仓库 issue 区/发布记录的经验判断） ==")
print(f"{pad('方案', 8)}" + "".join(f"{pad(d, 10)}" for d in DIMS))
for k, v in SCORES.items():
    print(f"{pad(k, 8)}" + "".join(f"{pad(str(s), 10)}" for s in v))

for name, w in [("数据敏感型 W1", W_DATA), ("速度优先型 W2", W_SPEED)]:
    r = rank(w)
    print(f"\n== {name} 权重 {w} ==")
    for s, k in r:
        print(f"  {pad(k, 8)}{s:.2f}")
    top = r[0][1]
    print(f"  结论：在 {name} 下推荐 {top}")

w1_top, w2_top = rank(W_DATA)[0][1], rank(W_SPEED)[0][1]
print(f"\n两套权重第一名不同（{w1_top} vs {w2_top}）—— 这就是必须附翻转条件的原因")
w = dim_winners(W_DATA)
print("逐维度领先者（W1 权重下）:", {d: k for d, k in w.items()})

# 翻转点：数据可控权重降到多少，自建让出头名？
# 二分查找：谓词「自建排名第一」在权重高于边界时为真
lo, hi = 0.0, 0.35
for _ in range(50):
    mid = (lo + hi) / 2
    rest = 1 - mid
    w2 = [0.15 * rest / 0.65, mid, 0.20 * rest / 0.65, 0.10 * rest / 0.65, 0.20 * rest / 0.65]
    if rank(w2)[0][1] == "自建":
        hi = mid      # 仍第一 → 边界在更低处
    else:
        lo = mid      # 已让出头名 → 边界在更高处
print(f"翻转阈值：数据可控权重低于 {lo:.3f} 时，自建失去头名（其余四维按原比例归一化）")

print("\n结论：加权矩阵的价值不在总分第一，在权重敏感性——把选型从信仰问题变成参数问题，")
print("读法：1. 总分是线性标量化，会掩盖 Pareto 结构，必须同时给逐维度领先者与翻转阈值；2. 结论句一律写成「在 W1 下推荐 X，若数据可控权重低于约 0.235 则推荐切换」；3. 打分维度要含失败模式（升级事故史、长任务稳定性），不只功能有无；4. 分数为教学假设（示例测算），真实项目用 PoC 数据与客户访谈校准。")
