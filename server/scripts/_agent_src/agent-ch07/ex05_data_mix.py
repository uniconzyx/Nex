# title: 数据配比实验：目标分布要在可行域里搜，不能凭来源比例拍
# 三个来源池的类别分布不同，按不同比例混合 1000 条，看落地分布、L1 距离与重复率。
import numpy as np

CATS = ["退款", "物流", "发票", "闲聊"]
TARGET = np.array([0.30, 0.30, 0.30, 0.10])
TARGET2 = np.array([0.25, 0.25, 0.40, 0.10])
POOLS = {
    "A 通用对话": (10000, np.array([0.05, 0.05, 0.05, 0.85])),
    "B 业务客服": (2000,  np.array([0.35, 0.30, 0.25, 0.10])),
    "C 小类精标": (80,    np.array([0.05, 0.05, 0.90, 0.00])),
}
MIXES = [
    ("A 单池",       {"A 通用对话": 1.0}),
    ("A+B 7:3",      {"A 通用对话": 0.7, "B 业务客服": 0.3}),
    ("A+B 5:5",      {"A 通用对话": 0.5, "B 业务客服": 0.5}),
    ("A+B+C 5:4:1",  {"A 通用对话": 0.5, "B 业务客服": 0.4, "C 小类精标": 0.1}),
]
N = 1000

def realized(mix):
    dist = np.zeros(len(CATS))
    unique = 0.0
    for pool, ratio in mix.items():
        size, pool_dist = POOLS[pool]
        k = int(round(N * ratio))
        dist += ratio * pool_dist
        unique += ratio * min(1.0, size / max(k, 1))
    return dist, unique

print(f"目标分布：退款 30% / 物流 30% / 发票 30% / 闲聊 10%，总样本 {N}\n")
print(f"{'配比':<14}{'退款':>7}{'物流':>7}{'发票':>7}{'闲聊':>7}"
      f"{'L1 距离':>9}{'唯一率':>8}")
for name, mix in MIXES:
    d, u = realized(mix)
    print(f"{name:<14}" + "".join(f"{v:>7.1%}" for v in d) +
          f"{np.abs(d-TARGET).sum():>9.3f}{u:>8.1%}")

def search(target, min_unique=0.0):
    best = (9.9, None, None, 0.0)
    for a in np.arange(0, 1.001, 0.05):
        for b in np.arange(0, 1.001 - a, 0.05):
            c = 1 - a - b
            mix = {"A 通用对话": a, "B 业务客服": b, "C 小类精标": c}
            d, u = realized(mix)
            l1 = np.abs(d - target).sum()
            if u >= min_unique and l1 < best[0]:
                best = (l1, mix, d, u)
    return best

print(f"\n{'目标':<22}{'约束':<16}{'A/B/C':>14}{'L1':>7}{'唯一率':>8}")
for tname, target in (("30/30/30/10", TARGET), ("25/25/40/10", TARGET2)):
    for label, mu in (("无约束", 0.0), ("唯一率≥99%", 0.99)):
        l1, mix, d, u = search(target, mu)
        abc = f"{mix['A 通用对话']:.2f}/{mix['B 业务客服']:.2f}/{mix['C 小类精标']:.2f}"
        print(f"{tname:<22}{label:<16}{abc:>14}{l1:>7.3f}{u:>8.1%}")

l1, mix, d, u = search(TARGET)
print(f"\n目标 30/30/30/10 的最优解落到：" +
      " ".join(f"{k} {v:.0%}" for k, v in zip(CATS, d)))
print(f"注意 A 被压到 {mix['A 通用对话']:.0%} —— 通用池 85% 是闲聊，对目标几乎只有噪声贡献。")
print(f"C 占 {mix['C 小类精标']:.0%} 时整体唯一率 {u:.0%}（C 池内部 100 抽 80，只有 80 条不同样本）。")

print("\n结论：配比是在「来源 × 类别」的可行域里搜出来的，不是按直觉分配来源比例。")
print("读法：")
print("1. 拍脑袋的 A+B+C 5:4:1，L1 是 0.73；穷举最优 0.07，差一个数量级；")
print("2. 唯一率约束会改变最优解：小类池只有 80 条时，硬拉到 10% 必然重复；")
print("3. 报表要同时给「来源比例 / 类别比例 / 唯一率」，只看来源比例会掩盖小类缺口；")
print("4. 若目标继续往发票倾斜（40%），约束后的 L1 会明显变差 —— 这时该补数据，不是调比例。")
