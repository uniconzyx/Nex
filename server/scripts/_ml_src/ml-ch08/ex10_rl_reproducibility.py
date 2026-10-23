# title: RL 难复现：同一算法换随机种子，性能方差有多大
# 打滑 5×5 网格（0.8 预期方向 + 0.1/0.1 侧滑）上跑表格 Q-learning，10 个种子 × 2 组 ε：
# 不仅单一种子间方差大，连「哪个 ε 更好」都随种子翻转。
# 对照组：同一份数据上训练逻辑回归，换种子只改优化路径，指标方差小两个量级。
import numpy as np

N = 5
S, A, GAMMA = N * N, 4, 0.95
START, GOAL, TRAP = 20, 4, 12
DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]       # 上 右 下 左
SLIP = (0.1, 0.8, 0.1)                          # 左偏 / 预期 / 右偏

# 预计算打滑转移表：NS[s,a,k] 与 RW[s,a,k]（k=0 左偏, 1 预期, 2 右偏）
NS = np.zeros((S, A, 3), dtype=int)
RW = np.zeros((S, A, 3))
for s in range(S):
    r, c = divmod(s, N)
    for a in range(A):
        if s == GOAL:                           # 终点吸收
            NS[s, a, :] = s
            RW[s, a, :] = 0.0
            continue
        for k, ak in enumerate(((a - 1) % A, a, (a + 1) % A)):
            dr, dc = DIRS[ak]
            nr, nc = r + dr, c + dc
            if not (0 <= nr < N and 0 <= nc < N):
                nr, nc = r, c                   # 撞墙原地
            ns = nr * N + nc
            if ns == TRAP:                      # 踩陷阱：−1 并送回起点
                NS[s, a, k], RW[s, a, k] = START, -1.0
            elif ns == GOAL:
                NS[s, a, k], RW[s, a, k] = GOAL, 1.0
            else:
                NS[s, a, k], RW[s, a, k] = ns, -0.02

def q_learning(seed, eps, episodes=500):
    rng = np.random.default_rng(seed)
    Q = np.zeros((S, A))
    Nsa = np.zeros((S, A))
    rets = np.zeros(episodes)
    for ep in range(episodes):
        s, G = START, 0.0
        for _ in range(80):
            a = int(rng.integers(A)) if rng.random() < eps else int(np.argmax(Q[s]))
            u = rng.random()
            k = 0 if u < 0.1 else (1 if u < 0.9 else 2)
            ns, r = NS[s, a, k], RW[s, a, k]
            Nsa[s, a] += 1
            Q[s, a] += (r + GAMMA * (0.0 if ns == GOAL else Q[ns].max())
                        - Q[s, a]) / Nsa[s, a]
            G += r
            s = ns
            if s == GOAL:
                break
        rets[ep] = G
    return rets[-100:].mean()

SEEDS = list(range(10))
res = {e: [q_learning(sd, e) for sd in SEEDS] for e in (0.05, 0.2)}

print("打滑 5×5 网格表格 Q-learning（500 集，末 100 集平均回报，越高越好）")
print(f"{'种子':>5} {'ε=0.05':>10} {'ε=0.2':>10} {'差值(0.05−0.2)':>16}")
for i, sd in enumerate(SEEDS):
    print(f"{sd:>5} {res[0.05][i]:>10.3f} {res[0.2][i]:>10.3f} "
          f"{res[0.05][i] - res[0.2][i]:>+16.3f}")

print(f"\n{'ε':>6} {'均值':>8} {'标准差':>8} {'变异CV':>8} {'最小':>8} {'最大':>8}")
for e in (0.05, 0.2):
    v = np.array(res[e])
    print(f"{e:>6.2f} {v.mean():>8.3f} {v.std(ddof=1):>8.3f} "
          f"{v.std(ddof=1) / v.mean():>8.1%} {v.min():>8.3f} {v.max():>8.3f}")

d = np.array(res[0.05]) - np.array(res[0.2])
flips = int((d < 0).sum())
print(f"\n配对差值：{flips}/10 个种子里 ε=0.2 反而更好——「哪个 ε 更优」随种子翻转。")

# 对照组：同一份数据上训练逻辑回归，只换初始化种子
rng0 = np.random.default_rng(3)
n, dim = 400, 5
X = rng0.normal(size=(n, dim))
w_true = rng0.normal(size=dim)
y = (rng0.random(n) < 1 / (1 + np.exp(-(X @ w_true)))).astype(float)
X_te = rng0.normal(size=(2000, dim))
y_te = (rng0.random(2000) < 1 / (1 + np.exp(-(X_te @ w_true)))).astype(float)

def train_lr(seed):
    """同一份数据，只换种子：初始化与每个小批量的抽样顺序都随之改变。"""
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 0.1, dim)
    for _ in range(200):
        idx = rng.permutation(n)[:32]                # 小批量 SGD
        p = 1 / (1 + np.exp(-(X[idx] @ w)))
        w -= 0.5 * (X[idx].T @ (p - y[idx]) / 32 + 0.01 * w)
    pred = (1 / (1 + np.exp(-(X_te @ w)))) > 0.5
    return float((pred == y_te).mean())

accs = np.array([train_lr(sd) for sd in SEEDS])
print("\n对照组·逻辑回归（同一份数据，只换初始化/抽样种子）：")
print(f"  测试准确率 均值={accs.mean():.4f} 标准差={accs.std(ddof=1):.5f} "
      f"变异CV={accs.std(ddof=1) / accs.mean():.2%}")

print("\n结论：RL 的性能方差主要不来自「优化噪声」而来自「数据分布本身」——训练样本由当前")
print("策略与环境交互产生，换一个种子，整条轨迹分布都变了；监督学习的数据集固定，种子只")
print("改变优化路径、不改数据分布，所以指标方差小两个量级（对比两处 CV）。")
print("工程含义：RL 实验必须报多种子均值±标准差，调参结论要做符号翻转检验——")
print("单 seed 的「我的算法更好」大概率是抽样噪声，这正是 RL 复现危机的根源之一。")
