# title: 策略迭代 vs 价值迭代：迭代次数与工程账本
# 同一个 MDP，两条路线都收敛到同一个 V*：PI 的外层轮数（策略改进次数）通常只有个位数，
# 但每轮要把内环评估跑到精度；VI 每轮只是一次 max 扫描、没有内环，
# 代价是轮数随 γ→1 按 log(1/ε)/(1−γ) 膨胀。
import numpy as np

N = 4
S, A = N * N, 4
GOAL, TRAP = 15, 10
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
            nr, nc = r, c
        ns = nr * N + nc
        P[s, a, ns] = 1.0
        R[s, a] = 1.0 if ns == GOAL else (-1.0 if ns == TRAP else -0.02)

# 再构造一个随机 MDP：12 状态、4 动作、随机转移与随机奖励
rng = np.random.default_rng(21)
S2, A2 = 12, 4
P2 = rng.dirichlet(np.ones(S2), size=(S2, A2))
R2 = rng.normal(0.0, 1.0, (S2, A2))

def value_iteration(P, R, gamma, tol=1e-10):
    S, A = R.shape
    V = np.zeros(S)
    for k in range(1, 100000):
        Vn = (R + gamma * P @ V).max(axis=1)
        if np.abs(Vn - V).max() < tol:
            return Vn, k
        V = Vn
    return V, k

def policy_iteration(P, R, gamma, tol=1e-10):
    S, A = R.shape
    pi = np.zeros(S, dtype=int)
    outer, eval_sweeps = 0, 0
    while True:
        outer += 1
        Ppi = P[np.arange(S), pi]                 # 当前策略的转移矩阵
        Rpi = R[np.arange(S), pi]
        V = np.zeros(S)
        for _ in range(100000):                   # 内环：完整策略评估
            Vn = Rpi + gamma * Ppi @ V
            eval_sweeps += 1
            if np.abs(Vn - V).max() < tol:
                V = Vn
                break
            V = Vn
        new_pi = (R + gamma * P @ V).argmax(axis=1)   # 策略改进
        if (new_pi == pi).all():
            return V, outer, eval_sweeps
        pi = new_pi

print(f"{'MDP':>14} {'γ':>6} {'VI轮数':>7} {'PI外层轮数':>10} {'PI评估总轮数':>12} {'‖V_PI−V_VI‖∞':>13}")
for name, (Pm, Rm) in (("4×4 网格", (P, R)), ("随机MDP(12态)", (P2, R2))):
    for g in (0.9, 0.99):
        V_vi, k_vi = value_iteration(Pm, Rm, g)
        V_pi, outer, inner = policy_iteration(Pm, Rm, g)
        print(f"{name:>14} {g:>6.2f} {k_vi:>7} {outer:>10} {inner:>12} "
              f"{np.abs(V_pi - V_vi).max():>13.1e}")

print("\n读法：两条路线收敛到同一个 V*（最后一列差异在容差 1e-10 量级）；")
print("PI 外层轮数只有个位数——策略往往几次改进就到最优，但计算量集中在内环评估；")
print("VI 每轮只做一次 max 扫描、没有内环，实现最简单，轮数却随 γ→1 显著变长。")
print("工程账本：VI 可以看作「内环评估只跑 1 步」的 PI（广义策略迭代家族）；")
print("状态空间一大，两者的瓶颈都从「轮数」变成「单次扫描 O(S²A)」，那时该上采样或函数逼近。")
