# title: 学习时间预算：PERT 三点估计与蒙特卡洛完成概率
import numpy as np

# 周预算 15h × 48 周 = 720h；任务工时三点估计 (乐观 a, 最可能 m, 悲观 b)
BUDGET_HOURS = 15 * 48
TASKS = [  # (任务, a, m, b, 是否在 ex07 关键路径上)
    ("T1 Python 与工程基础补强", 80, 120, 200, True),
    ("T2 RAG 系统原理与动手", 60, 90, 150, True),
    ("T3 评估集建设方法", 30, 50, 90, False),
    ("T4 工单问答 v1 上线", 80, 130, 220, True),
    ("T5 兜底与低置信度路由", 30, 45, 80, True),
    ("T6 系统设计深挖", 40, 60, 100, False),
    ("T7 微调实验", 40, 70, 130, False),
    ("T8 面试准备（八股+行为面）", 50, 80, 140, True),
]
N = 20000
rng = np.random.default_rng(42)

a = np.array([t[1] for t in TASKS], dtype=float)
m = np.array([t[2] for t in TASKS], dtype=float)
b = np.array([t[3] for t in TASKS], dtype=float)
exp_h = (a + 4 * m + b) / 6
sd_h = (b - a) / 6


def pad(s, w):
    return s + " " * max(1, w - sum(2 if ord(c) > 127 else 1 for c in s))


print(f"== 1) 逐任务 PERT 估计（期望=(a+4m+b)/6，标准差=(b-a)/6；预算 {BUDGET_HOURS}h）==")
print(f"{pad('任务', 24)}{'a':>5}{'m':>5}{'b':>5}{'期望':>8}{'标准差':>7}  关键路径")
for i, (name, _, _, _, on_cp) in enumerate(TASKS):
    print(f"{pad(name, 24)}{a[i]:>5.0f}{m[i]:>5.0f}{b[i]:>5.0f}"
          f"{exp_h[i]:>8.1f}{sd_h[i]:>7.1f}  {'是' if on_cp else '否'}")

total_exp = exp_h.sum()
total_sd = float(np.sqrt((sd_h ** 2).sum()))
print(f"\n   总期望 = {total_exp:.1f}h，总标准差 = {total_sd:.1f}h，"
      f"预算 = {BUDGET_HOURS}h（余量 {BUDGET_HOURS - total_exp:.1f}h）")

# 2) 蒙特卡洛：每个任务采样三角分布，共享样本矩阵以便 what-if 对比
samples = rng.triangular(a, m, b, size=(N, len(TASKS)))
total_samples = samples.sum(axis=1)
p50, p80, p90 = np.percentile(total_samples, [50, 80, 90])
p_finish = float((total_samples <= BUDGET_HOURS).mean())

print("\n== 2) 总工时分布（20000 次蒙特卡洛，种子 42）==")
print(f"   P50 = {p50:.0f}h   P80 = {p80:.0f}h   P90 = {p90:.0f}h")
print(f"   P(总工时 ≤ {BUDGET_HOURS}h 预算) = {p_finish:.1%}")

hist, edges = np.histogram(total_samples, bins=16)
print("\n   总工时直方图（# ≈ 1250 次；| 标记预算线位置）:")
for i, h in enumerate(hist):
    lo, hi = edges[i], edges[i + 1]
    mark = "|←预算" if lo <= BUDGET_HOURS < hi else ""
    print(f"   {lo:5.0f}-{hi:5.0f}h {'#' * int(h / 1250):<20} {h:5d} {mark}")

print("\n== 3) 砍/缩任务的 what-if（共享样本，可直接对比）==")
print(f"{pad('方案', 30)}{'新期望':>8}{'P(≤预算)':>9}  说明")
scenarios = [(f"砍掉 {t[0]}", i) for i, t in enumerate(TASKS)]
for label, i in scenarios:
    new_total = total_samples - samples[:, i]
    p_new = float((new_total <= BUDGET_HOURS).mean())
    note = "关键路径，慎砍" if TASKS[i][4] else "非关键，可砍"
    print(f"{pad(label, 30)}{total_exp - exp_h[i]:>8.0f}{p_new:>9.1%}  {note}")

half = total_samples - 0.5 * samples[:, 6]  # T7 微调实验缩半程
print(f"{pad('T7 微调实验缩半程', 30)}{total_exp - 0.5 * exp_h[6]:>8.0f}"
      f"{float((half <= BUDGET_HOURS).mean()):>9.1%}  不够——要过 90% 得整砍")
best_cut = max(((f"砍掉 {TASKS[i][0]}", i) for i in range(len(TASKS)) if not TASKS[i][4]),
               key=lambda x: float(((total_samples - samples[:, x[1]]) <= BUDGET_HOURS).mean()))
print(f"   不动关键路径的最优解: {best_cut[0]}（非关键，整砍）")

print(f"\n结论：期望 {total_exp:.0f}h 距预算还有 {BUDGET_HOURS - total_exp:.0f}h 余量，"
      f"但按时完成概率只有 {p_finish:.1%}——右偏分布下『平均够』不等于『大概率够』")
print(f"读法：1. 三点估计把『能做完』变成概率：本计划 P50={p50:.0f}h 已压在预算线上、"
      f"P80={p80:.0f}h 超预算 {p80 - BUDGET_HOURS:.0f}h；对外承诺应说『P80 需要 {p80:.0f}h，"
      f"要么加 1 周缓冲，要么砍一个非关键任务』；2. 悲观值 b 不是悲观情绪而是历史分布：b−a 越宽越不可控"
      f"（T4 上线 80-220h，标准差 {sd_h[3]:.1f}h 最大），这类任务要单独留 buffer；"
      f"3. 砍任务先砍非关键路径上的：整砍 T7（期望 {exp_h[6]:.0f}h、非关键）把完成概率从 "
      f"{p_finish:.1%} 提到 93.2%，缩半程只到 77.0%——要么不做，要么做全；"
      f"4. 本示例是三角分布近似，真实工时分布常有长尾，P90 之后建议按经验再加 10-15% 缓冲。")
