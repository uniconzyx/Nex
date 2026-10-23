# title: MDP 五元组：把一个 4×4 网格世界写成矩阵
# ⟨S, A, P, R, γ⟩ 不是五个抽象名词，而是五张具体的表。本例把一个小网格世界的
# 五元组全部构造并打印出来，逐项验证「每个 (s,a) 对应的 P(·|s,a) 是概率分布」，
# 并演示马尔可夫性：下一状态的分布只取决于 (s,a)，与怎样来到 s 无关。
import numpy as np

N = 4                          # 4×4 网格
S, A = N * N, 4                # 16 个状态、4 个动作
GAMMA = 0.9                    # 折扣因子
GOAL, TRAP = 15, 10            # 终点（右上角）与陷阱
DIR = {"上": (-1, 0), "右": (0, 1), "下": (1, 0), "左": (0, -1)}
ACT = ["上", "右", "下", "左"]

P = np.zeros((S, A, S))        # P[s, a, s']
R = np.zeros((S, A))           # R[s, a]
for s in range(S):
    r, c = divmod(s, N)
    for a, name in enumerate(ACT):
        if s in (GOAL, TRAP):              # 终止态：自环占位、零奖励
            P[s, a, s] = 1.0
            continue
        dr, dc = DIR[name]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < N and 0 <= nc < N):   # 撞墙：原地不动
            nr, nc = r, c
        ns = nr * N + nc
        P[s, a, ns] = 1.0
        R[s, a] = 1.0 if ns == GOAL else (-1.0 if ns == TRAP else -0.02)

print("== MDP 五元组 ⟨S, A, P, R, γ⟩ ==")
print(f"S: {S} 个状态（编号 = 行×4 + 列，左上角为 0，左下角 s=0 是起点）")
print(f"A: {A} 个动作 {ACT}")
print(f"γ: {GAMMA}")
print(f"终点 s={GOAL}（进入得 +1 并终止），陷阱 s={TRAP}（进入得 -1 并终止）")
print(f"P 形状 {P.shape}（P[s,a,s'] = 从 s 执行 a 转移到 s' 的概率），R 形状 {R.shape}")

# 逐项验证：每个 (s,a) 都是一个概率分布
sums = P.sum(axis=2)
print(f"\n行随机性检查：max|Σ_s' P(s'|s,a) − 1| = {np.abs(sums - 1).max():.1e}"
      "（终止态用自环占位，仍保持是分布）")

# 抽样打印若干 (s,a) 的转移
print("\n代表性转移（本环境是确定性的：每个 (s,a) 只指向一个 s'）：")
for s in (0, 5, 6):
    r, c = divmod(s, N)
    outs = []
    for a, name in enumerate(ACT):
        ns = int(np.argmax(P[s, a]))
        outs.append(f"{name}→s'={ns:>2}(R={R[s, a]:+.2f})")
    print(f"  s={s:>2}(第{r+1}行第{c+1}列): " + "  ".join(outs))

# 马尔可夫性演示
print("\n马尔可夫性：s=6 可以分别由 s=2「下」、s=5「右」、s=10「上」到达，历史各不相同；")
print("但只要当前处于 s=6 并执行「上」，下一状态分布永远一样：")
print(f"  P(s'=2 | s=6, a=上) = {P[6, 0, 2]:.1f}   —— 与「怎么来到 6」无关")

# 奖励矩阵的特殊项
special = [(s, ACT[a], R[s, a]) for s in range(S) for a in range(A)
           if R[s, a] != 0.0 and abs(R[s, a] + 0.02) > 1e-9]
print(f"\nR 的特殊项（其余 {S * A - len(special)} 个 (s,a) 统一为每步 -0.02；"
      "终止态 s=10/15 的 8 个动作项约定为 0）：")
for s, name, rv in special:
    print(f"  R(s={s:>2}, a={name}) = {rv:+.2f}")

print("\n结论：MDP 的全部信息就在 P、R、γ 这三张表里——策略、价值函数、最优性都是对它们的函数；")
print("写 RL 代码的第一步不是选算法，而是把 P 和 R 定义清楚，后面所有结论都受这两张表约束。")
