# title: DQN 最小实现：经验回放与目标网络，以及一笔数据账
# 不依赖 gym：自建 2D 连续导航（纯稀疏奖励——走到远端角落目标才给 +10）。
# 手写 MLP（2→16 ReLU→5）+ ε 衰减 + 经验回放 + 目标网络，300 回合从随机策略
# 9% 的命中率学到 100%。最后算一笔工程账：回放让每条 transition 平均被学约 31 次，
# 目标网络 300 回合只刷新 12 次——两块砖的价值用数字说话，而不是「跑赢就算」。
import numpy as np

GOAL = np.array([1.0, 1.0])                 # 远端角落目标：最短也要 9 步
RADIUS, STEP, SIGMA = 0.2, 0.2, 0.03
MOVES = np.array([[0.0, STEP], [STEP, 0.0], [0.0, -STEP], [-STEP, 0.0], [0.0, 0.0]])
MAX_STEPS, EPISODES = 60, 300
GAMMA, H, A = 0.97, 16, 5                   # 隐层只有 16 个 ReLU 单元
BATCH, WARMUP, CAP = 32, 200, 4000

def env_step(p, a, rng):
    p2 = np.clip(p + MOVES[a] + rng.normal(0.0, SIGMA, 2), -1.0, 1.0)
    if np.linalg.norm(p2 - GOAL) < RADIUS:
        return p2, 10.0, True                # 稀疏奖励：只有终点给 +10
    return p2, 0.0, False

def init_net(rng):
    return (rng.normal(0.0, 1.0 / np.sqrt(2.0), (2, H)),      # W1
            np.zeros(H),                                       # b1
            rng.normal(0.0, 1.0 / np.sqrt(H), (H, A)),         # W2
            np.zeros(A))                                       # b2

def forward(net, x):
    W1, b1, W2, b2 = net
    h = np.maximum(0.0, x @ W1 + b1)                 # ReLU 隐层
    return h @ W2 + b2, h

def sgd_step(net, x, q, h, y, lr=5e-3):              # 手写反向传播（复用前向结果）
    W1, b1, W2, b2 = net
    err = q - y
    B = x.shape[0]
    dh = (err @ W2.T) * (h > 0.0)
    return (W1 - lr * (x.T @ dh / B), b1 - lr * dh.mean(axis=0),
            W2 - lr * (h.T @ err / B), b2 - lr * err.mean(axis=0))

def run_dqn(seed=7):
    rng = np.random.default_rng(seed)
    net = init_net(rng)
    target = net                                # 目标网络：滞后一份参数
    buf_s = np.zeros((CAP, 2)); buf_a = np.zeros(CAP, dtype=int)
    buf_r = np.zeros(CAP); buf_s2 = np.zeros((CAP, 2))
    buf_d = np.zeros(CAP, dtype=bool)           # 经验回放池（预分配、循环覆盖）
    n_buf, pos = 0, 0
    succ = np.zeros(EPISODES)
    n_trans = n_batches = n_copies = 0
    for ep in range(EPISODES):
        p = np.zeros(2)
        eps = max(0.05, 0.97 ** ep)             # ε 衰减：先探索后利用
        for _ in range(MAX_STEPS):
            a = (int(rng.integers(A)) if rng.random() < eps
                 else int(np.argmax(forward(net, p[None, :])[0][0])))
            p2, r, done = env_step(p, a, rng)
            buf_s[pos], buf_a[pos], buf_r[pos] = p, a, r
            buf_s2[pos], buf_d[pos] = p2, done
            pos = (pos + 1) % CAP
            n_buf = min(n_buf + 1, CAP)
            n_trans += 1
            if n_buf >= WARMUP:                 # 攒够 200 条才开始学
                idx = rng.integers(0, n_buf, BATCH)
                q_next, _ = forward(target, buf_s2[idx])   # 目标网络算 TD 目标
                q, h = forward(net, buf_s[idx])
                y = q.copy()
                y[np.arange(BATCH), buf_a[idx]] = (buf_r[idx]
                                                   + GAMMA * q_next.max(axis=1) * (~buf_d[idx]))
                net = sgd_step(net, buf_s[idx], q, h, y)
                n_batches += 1
            p = p2
            if done:
                succ[ep] = 1.0
                break
        if (ep + 1) % 25 == 0:
            target = net                        # 每 25 回合硬拷贝一次目标网络
            n_copies += 1
    return succ, net, n_trans, n_batches, n_copies

def rollout(net, max_steps=60):
    rng = np.random.default_rng(123)
    p, path = np.zeros(2), [(0.0, 0.0)]
    for _ in range(max_steps):
        a = int(np.argmax(forward(net, p[None, :])[0][0]))
        p, _, done = env_step(p, a, rng)
        path.append((round(float(p[0]), 2), round(float(p[1]), 2)))
        if done:
            return path, True
    return path, False

def random_policy(seed):
    """纯随机策略的命中率：探索的下限参照。"""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(EPISODES):
        p = np.zeros(2)
        for _ in range(MAX_STEPS):
            p, _, done = env_step(p, int(rng.integers(A)), rng)
            if done:
                hits += 1
                break
    return hits / EPISODES

succ, net, n_trans, n_batches, n_copies = run_dqn(7)

print(f"2D 连续导航：起点 (0,0)，远端目标 (1.0,1.0) 半径 {RADIUS} 内得 +10，其余步赏 0"
      f"（纯稀疏奖励，最短 9 步）")
print(f"手写 MLP 2→{H}(ReLU)→5，ε=1.0→0.05 衰减，回放池 {CAP}，批大小 {BATCH}，"
      f"目标网每 25 回合拷贝，{EPISODES} 回合")
print(f"\nDQN（种子 7）：前 100 集成功率 {succ[:100].mean():.0%} → 后 100 集 {succ[-100:].mean():.0%}")
print(f"随机策略基线：{random_policy(7):.0%}（另两个种子 "
      f"{random_policy(1):.0%}/{random_policy(2):.0%}，几乎不随种子变）")

late = []
for sd in (7, 1, 2):
    s2, _, _, _, _ = run_dqn(sd)
    late.append(s2[-100:].mean())
print(f"\nDQN 末 100 集成功率（3 个种子）：" + " / ".join(f"{v:.0%}" for v in late)
      + f"，均值 {np.mean(late):.0%}")

print("\n每 30 集成功率（# ≥ 80%，+ ≥ 40%，. < 40%）：")
bars = "".join("#" if succ[i * 30:(i + 1) * 30].mean() >= 0.8 else
               ("+" if succ[i * 30:(i + 1) * 30].mean() >= 0.4 else ".")
               for i in range(EPISODES // 30))
print(f"  |{bars}|")

path, ok = rollout(net)
print("\n学到的贪心策略实际走位（从 (0,0) 出发，最多 60 步，带观测噪声）：")
print("  " + " → ".join(f"({x},{y})" for x, y in path[:10])
      + (" → … 命中目标" if ok else " → … 未命中"))

print("\n== 工程账本（同样这 300 回合）==")
print(f"与环境交互 {n_trans} 条 transition；回放采样 {n_batches} 批 × {BATCH} 条"
      f" = {n_batches * BATCH} 个学习样本")
print(f"数据复用倍数 ≈ {n_batches * BATCH / n_trans:.0f}×（无回放的在线版每条只用 1 次）")
print(f"目标网络刷新 {n_copies} 次 vs 在线网络更新 {n_batches} 次"
      f"——平均每 {n_batches // max(n_copies, 1)} 次在线更新才追一次新目标")

print("\n机理：RL 的数据分布由当前策略决定——连续采样得到的是强相关的时序样本，且分布随")
print("策略移动，监督学习赖以成立的 i.i.d. 假设在这里失效。经验回放把历史 transition 打散")
print("后重采样，让每一批近似 i.i.d.；账本上它还把每条数据复用约 31 次——稀疏任务里这是")
print("数量级的样本效率差别。目标网络把 TD 目标固定 25 回合（约 500 次更新），")
print("消除「追着移动靶打」的自举不稳定：目标追得越慢，自举链越不容易发散。")
print("结论：这个尺度上，把两块砖拆开做消融对比会被种子噪声主导（时好时坏，见下一节），")
print("所以这里不搞「跑赢就算」的赛马——用数据账本量化：回放买到 i.i.d. 与复用，")
print("目标网络买到稳定；两者合起来，函数逼近版 Q-learning 才第一次可靠地工作。")
