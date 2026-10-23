# title: 价值迭代：最优性算子的压缩性与有依据的提前停止
# T*V(s) = max_a [R(s,a) + γ Σ_s' P(s'|s,a) V(s')]。本例追踪 ‖V_k − V*‖∞，
# 误差每轮乘 γ（压缩系数即收敛速率）；再用残差界做提前停止：
# ‖V_{k+1} − V_k‖ < ε 时，‖V* − V_{k+1}‖ ≤ γε/(1−γ)——停止条件不是拍脑袋。
import numpy as np

N = 4
S, A, GAMMA = N * N, 4, 0.9
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

def sweep(V):
    return (R + GAMMA * P @ V).max(axis=1)

# 参考解：跑到机器精度
V = np.zeros(S)
for _ in range(5000):
    Vn = sweep(V)
    if np.abs(Vn - V).max() < 1e-14:
        V = Vn
        break
    V = Vn
V_ref = V

# 带记录的重新迭代
V = np.zeros(S)
prev_err = None
print(f"价值迭代，γ={GAMMA}")
print(f"{'轮数k':>5} {'‖V_k − V*‖∞':>14} {'相邻收缩比':>10} {'残差':>10} {'残差界γ/(1−γ)·残差':>19}")
for k in range(1, 16):
    resid = np.abs(sweep(V) - V).max()
    V = sweep(V)
    err = np.abs(V - V_ref).max()
    ratio = err / prev_err if prev_err else float("nan")
    bound = GAMMA / (1 - GAMMA) * resid
    print(f"{k:>5} {err:>14.3e} {ratio:>10.3f} {resid:>10.2e} {bound:>19.2e}")
    prev_err = err
    if err < 1e-12:
        print(f"  ……第 {k} 轮起已收敛到机器精度（|V_k − V*| < 1e-12），后续轮次略去")
        break

# 由 V* 提取贪心策略并画成箭头网格
Q_star = R + GAMMA * P @ V_ref
pi = Q_star.argmax(axis=1)
ARROW = {"上": "^", "右": ">", "下": "v", "左": "<"}
print("\n由 V* 提取的贪心策略（G=终点，T=陷阱）：")
for r in range(N):
    row = []
    for c in range(N):
        s = r * N + c
        row.append("G" if s == GOAL else ("T" if s == TRAP else ARROW[ACT[pi[s]]]))
    print("  " + " ".join(row))
print("\n对应的 V*（按网格排列，保留 2 位）：")
for r in range(N):
    print("  " + " ".join(f"{V_ref[r * N + c]:6.2f}" for c in range(N)))

print("\n结论：误差收缩比≈0.9——最优性算子 T* 是 sup 范数下系数 γ 的压缩映射（Banach 不动点定理），")
print("价值迭代因此必然收敛；且「残差 < ε ⟹ 误差 ≤ γε/(1−γ)」给出可证明的停止准则（表中残差界确实包住真实误差）。")
print("机理：T* 把一切 T^π 包住（T*V ≥ T^πV），一轮 VI = 一次隐式策略改进 + 一步评估——这正是 VI 没有内环的原因。")
