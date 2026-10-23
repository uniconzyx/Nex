# title: 悬崖行走：SARSA 绕开悬崖，Q-learning 贴着悬崖走
# 同一个 4×12 悬崖环境、同一套 ε-greedy 行为策略，只差 TD 目标里的「下一步动作」：
# SARSA 用采样的 a'（on-policy），Q-learning 用 max a'（off-policy）。
# 前者评估的是自己实际会走的策略——知道 ε 手滑就会掉下去，于是绕开；
# 后者直接逼近 q*——哪怕自己很少走最优路径，也要画出悬崖边的最短路。
import numpy as np

H_, W_ = 4, 12
S = H_ * W_
START, GOAL = 36, 47                     # 左下角起点、右下角终点
CLIFF = set(range(37, 47))               # 底行中间 10 格是悬崖
MOVES = {"上": (-1, 0), "右": (0, 1), "下": (1, 0), "左": (0, -1)}
ACT = ["上", "右", "下", "左"]

def move(s, a):
    r, c = divmod(s, W_)
    dr, dc = MOVES[ACT[a]]
    nr = min(max(r + dr, 0), H_ - 1)
    nc = min(max(c + dc, 0), W_ - 1)
    ns = nr * W_ + nc
    if ns in CLIFF:                       # 掉悬崖：-100，回起点，本集继续
        return START, -100.0, False
    if ns == GOAL:                        # 踩终点也付 -1 步费，然后终止
        return ns, -1.0, True
    return ns, -1.0, False

def train(algo, episodes=1200, eps=0.1, alpha=0.5, gamma=1.0):
    rng = np.random.default_rng(7)
    Q = np.zeros((S, 4))
    rets = np.zeros(episodes)
    for ep in range(episodes):
        s, G = START, 0.0
        a = int(np.argmax(Q[s])) if rng.random() >= eps else int(rng.integers(4))
        for _ in range(200):
            s2, r, done = move(s, a)
            if algo == "sarsa":
                a2 = int(np.argmax(Q[s2])) if rng.random() >= eps else int(rng.integers(4))
                target = r if done else r + gamma * Q[s2, a2]
            else:                          # q-learning
                target = r if done else r + gamma * Q[s2].max()
            Q[s, a] += alpha * (target - Q[s, a])
            G += r
            s, a = s2, (a2 if algo == "sarsa" else
                        (int(np.argmax(Q[s2])) if rng.random() >= eps else int(rng.integers(4))))
            if done:
                break
        rets[ep] = G
    return Q, rets

def greedy_rollout(Q, n=50):
    """用学到的贪心策略（ε=0）实际走 n 集，看它自己会摔死几次。"""
    rng = np.random.default_rng(99)
    out = []
    for _ in range(n):
        s, G = START, 0.0
        for _ in range(200):
            s, r, done = move(s, int(np.argmax(Q[s])))
            G += r
            if done:
                break
        out.append(G)
    return float(np.mean(out))

Q_sarsa, r_sarsa = train("sarsa")
Q_ql, r_ql = train("qlearning")

print(f"悬崖行走 4×12，ε=0.1，α=0.5，γ=1，各训练 1200 集")
print(f"{'算法':>10} {'训练期每100集平均回报（末5段）':>30} {'贪心策略实际回报':>16}")
seg_s = " ".join(f"{r_sarsa[i*100:(i+1)*100].mean():6.1f}" for i in range(7, 12))
seg_q = " ".join(f"{r_ql[i*100:(i+1)*100].mean():6.1f}" for i in range(7, 12))
print(f"{'SARSA':>10}  {seg_s:>28} {greedy_rollout(Q_sarsa):>15.1f}")
print(f"{'Q-learning':>10}  {seg_q:>28} {greedy_rollout(Q_ql):>15.1f}")

ARROW = {"上": "^", "右": ">", "下": "v", "左": "<"}
def show(Q, name):
    print(f"\n{name} 学到的贪心策略（C=悬崖，G=终点，S=起点）：")
    for r in range(H_):
        row = []
        for c in range(W_):
            s = r * W_ + c
            row.append("C" if s in CLIFF else
                       ("G" if s == GOAL else ("S" if s == START else ARROW[ACT[int(np.argmax(Q[s]))]])))
        print("  " + " ".join(row))

show(Q_sarsa, "SARSA")
show(Q_ql, "Q-learning")

print("\n结论：同一个环境、同一套 ε-greedy 行为策略，两条路走出完全不同的策略——")
print("SARSA 的路径贴着悬崖上方一格（安全），Q-learning 的路径沿着悬崖边缘（最短但危险）。")
print("机理：SARSA 的 TD 目标里是采样得到的 a'，它评估的是「实际执行的 ε-greedy 策略」——")
print("知道手滑就会掉下去，所以给边缘状态的价值打了折；Q-learning 的目标是 max_a' Q(s',a')，")
print("逼近的是不依赖行为策略的 q*，于是画出理论最优但对自己太危险的路线。")
print("工程含义：on-policy 学到的是「带着探索噪声的安全策略」，适合在线试错代价高的场景；")
print("off-policy 学到的是「最优策略」，但训练期行为策略会频繁采坑——离线数据上只能训 off-policy。")
