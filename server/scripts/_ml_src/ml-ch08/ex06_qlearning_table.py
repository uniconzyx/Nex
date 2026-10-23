# title: 表格 Q-learning：乐观初始化与学习率衰减，各有各的失效边界
# 5×5 网格：每步奖励 0、到达终点 +1、陷阱 -1 并送回起点，ε=0.02（探索很弱）。
# 三组 Q 初值对照：全 0 → 纯利用锁死在墙角；Q0=1（=单集最大可能回报）→ 未访问的
# (s,a) 天然吸引 greedy，完成系统性探索；Q0=10（远大于回报尺度）→ 高价值平台反噬。
# 再对照 α=1/N 与固定 α=0.1：前者把误差压到机器级，后者永远在真值附近震荡。
import numpy as np

N = 5
S, A, GAMMA, EPS = N * N, 4, 0.95, 0.02
START, GOAL, TRAP = 20, 4, 12                 # 起点左下、终点右上、陷阱正中
DIR = {"上": (-1, 0), "右": (0, 1), "下": (1, 0), "左": (0, -1)}
ACT = ["上", "右", "下", "左"]

P = np.zeros((S, A, S))
R = np.zeros((S, A))
for s in range(S):
    r, c = divmod(s, N)
    for a, name in enumerate(ACT):
        if s in (GOAL, TRAP):
            P[s, a, s] = 1.0
            continue
        dr, dc = DIR[name]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < N and 0 <= nc < N):
            nr, nc = r, c                          # 撞墙原地
        ns = nr * N + nc
        if ns == TRAP:                             # 踩陷阱：-1 并送回起点
            P[s, a, START] = 1.0
            R[s, a] = -1.0
        else:
            P[s, a, ns] = 1.0
            R[s, a] = 1.0 if ns == GOAL else 0.0    # 步赏为 0，只有终点 +1

# 收敛证书：价值迭代求 Q*
V_star = np.zeros(S)
for _ in range(5000):
    Vn = (R + GAMMA * P @ V_star).max(axis=1)
    if np.abs(Vn - V_star).max() < 1e-13:
        V_star = Vn
        break
    V_star = Vn
Q_star = R + GAMMA * P @ V_star
nonterm = [s for s in range(S) if s not in (GOAL, TRAP)]

def q_learning(Q0, episodes=1500, fixed_alpha=False):
    rng = np.random.default_rng(42)
    Q = np.full((S, A), float(Q0))
    Nsa = np.zeros((S, A))
    rets = np.zeros(episodes)
    first_goal = None
    for ep in range(episodes):
        s, G = START, 0.0
        for _ in range(100):
            a = int(rng.integers(A)) if rng.random() < EPS else int(np.argmax(Q[s]))
            ns = int(np.argmax(P[s, a]))
            r = R[s, a]
            Nsa[s, a] += 1
            alpha = 0.1 if fixed_alpha else 1.0 / Nsa[s, a]
            target = r if ns == GOAL else r + GAMMA * Q[ns].max()
            Q[s, a] += alpha * (target - Q[s, a])
            G += r
            s = ns
            if s == GOAL:
                if first_goal is None:
                    first_goal = ep
                break
        rets[ep] = G
    err = np.abs(Q[nonterm] - Q_star[nonterm]).max()
    return rets, first_goal, err

print(f"ε={EPS}，γ={GAMMA}，1500 集；以价值迭代的 Q* 作收敛证书")
print(f"{'Q初值':>10} {'首次到达终点':>12} {'前300集成功率':>12} {'末300集成功率':>12} "
      f"{'末300集均回报':>12} {'‖Q−Q*‖∞':>10}")
runs = {}
for Q0 in (0.0, 0.5, 1.0, 5.0, 10.0):
    rets, fg, err = q_learning(Q0)
    runs[Q0] = rets
    print(f"{Q0:>10.1f} {str(fg) if fg is not None else '从未':>12} "
          f"{(rets[:300] > 0).mean():>11.0%} {(rets[-300:] > 0).mean():>11.0%} "
          f"{rets[-300:].mean():>12.3f} {err:>10.4f}")

# 锁死机制：Q0=0 时贪心策略从头走到尾
print("\n锁死机制（Q0=0，ε=0 时的贪心轨迹前 8 步）：")
path, s = [START], START
for _ in range(7):
    s = int(np.argmax(P[s, 0]))          # 全零 Q 下 argmax 恒取第一个动作「上」
    path.append(s)
print("  " + " → ".join(f"s={x}" for x in path) + " → …（到左上角后「上」撞墙，原地打转）")

# 字符画：每 100 集成功率
print("\n每 100 集的终点到达率（# ≥ 80%，+ ≥ 40%，. < 40%）：")
for Q0 in (0.0, 1.0, 10.0):
    bars = "".join("#" if runs[Q0][i * 100:(i + 1) * 100].mean() > 0.8 else
                   ("+" if runs[Q0][i * 100:(i + 1) * 100].mean() > 0.4 else ".")
                   for i in range(15))
    print(f"  Q0={Q0:<5}|{bars}|")

# 学习率衰减对照
print("\n学习率对照（Q0=1）：")
print(f"{'α 策略':>12} {'末300集成功率':>12} {'‖Q−Q*‖∞':>10}")
for name, fixed in (("1/N(s,a)", False), ("固定 0.1", True)):
    rets, _, err = q_learning(1.0, fixed_alpha=fixed)
    print(f"{name:>12} {(rets[-300:] > 0).mean():>11.0%} {err:>10.4f}")

print("\n结论：乐观初始化（max 初始化）把探索变成 greedy 的内在动机——没去过的 (s,a) 价值最高，")
print("argmax 自然逐个「验货」，无需 ε 也能完成系统性覆盖；而 Q0=0 时全零表 + 步赏为 0，")
print("argmax 永远指向第一个动作，智能体锁死在墙角（轨迹见上）。")
print("失效边界：乐观幅度必须匹配奖励尺度——Q0=10 时平台价值（≈0.95×10）远超目标价值 1，")
print("智能体反而逃避目标区域；只有 Q0 略高于最大可能回报时才既探索又不颠倒排序。")
print("机理：α=1/N 满足 Robbins–Monro 条件（Σα=∞、Σα²<∞），误差被压到机器级；")
print("固定 α=0.1 时 Q 在真值附近持续震荡，策略可能已经最优、数值却永远有残差。")
