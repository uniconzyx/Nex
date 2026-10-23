# title: ε-greedy：利用-探索权衡的量化与字符画曲线
# 10 臂老虎机，ε ∈ {0, 0.01, 0.1, 0.3}：ε=0 会锁死次优臂（一旦 Argmax 错了就永远错），
# ε 过大退化成随机搜索，累计奖励在中间某个 ε 达到最高。曲线用字符画呈现。
import numpy as np

rng = np.random.default_rng(8)
K, RUNS, STEPS = 10, 60, 1000
q_star = rng.normal(0.0, 1.0, K)          # 各臂真实期望奖励（本批实验固定）
best = int(np.argmax(q_star))

def run(eps):
    Q = np.zeros(K)                        # 估计值，每个 run 独立
    N = np.zeros(K)
    curve = np.zeros(STEPS // 50)
    opt_cnt, regret = 0, 0.0
    for t in range(STEPS):
        a = int(rng.integers(K)) if rng.random() < eps else int(np.argmax(Q))
        r = q_star[a] + rng.normal(0.0, 1.0)
        N[a] += 1
        Q[a] += (r - Q[a]) / N[a]          # 样本平均，α=1/N
        curve[t // 50] += r
        opt_cnt += a == best
        regret += q_star[best] - q_star[a]
    return curve / 50.0, opt_cnt / STEPS, regret

results = {eps: run(eps) for eps in (0.0, 0.01, 0.1, 0.3)}

print(f"10 臂老虎机，最优臂是 #{best}（q*={q_star[best]:.2f}），每 RUNS={RUNS} 次独立实验取平均，"
      f"STEPS={STEPS} 步")
print(f"{'ε':>6} {'末200步平均奖励':>14} {'选中最优臂比例':>14} {'累计遗憾':>10}")
for eps, (curve, opt, reg) in results.items():
    print(f"{eps:>6.2f} {curve[-4:].mean():>14.3f} {opt:>13.0%} {reg:>10.1f}")

# 字符画：平均奖励随学习进程（每 50 步一个点，8 行高度）
print("\n平均奖励曲线（纵轴为奖励，横轴从左到右 0→1000 步，# 为奖励高于阈值的区域）：")
for eps, (curve, _, _) in results.items():
    mx, mn = curve.max(), curve.min()
    print(f"  ε={eps:<5} max={mx:5.2f}")
    for row in range(8, 0, -1):
        thr = mn + (mx - mn) * row / 9.0
        print(f"          |{''.join('#' if v >= thr else ' ' for v in curve)}|")

print("\n结论：ε=0 纯利用——初始 Q 全零时 Argmax 恒为 0 号臂，如果它不是最优臂，")
print("就永远锁死在次优臂上（表中选优比例与累计遗憾最差）；ε 越大探索越充分但跟随越慢，")
print("ε=0.3 已接近随机搜索。累计奖励最高的 ε 在 0.1 附近：探索要够、但不能喧宾夺主。")
print("机理缺陷：ε-greedy 的探索与「哪里不确定」脱钩——它均匀撒点，而不是朝着信息增益大的方向探；")
print("且探索动作不进入 Q 的估计目标，样本被浪费一半。这正是 UCB、Thompson 采样要解决的问题。")
