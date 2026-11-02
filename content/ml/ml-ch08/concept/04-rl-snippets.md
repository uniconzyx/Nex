# 强化学习代码速查：凯喵的八段可运行片段

> 这一篇是配套速查。前三篇讲清了 MDP、Bellman 方程与 TD/Q-learning，这一篇把它们落成代码。每段都能在小规模环境上跑通，凯喵的用法是先在 GridWorld 上看值函数怎么逐轮收敛，再去读 DQN 的实现。

### 一、GridWorld 环境

最小可用的 MDP 环境：网格、四个动作、撞墙不动、到达终点结束。

```python
import numpy as np

class GridWorld:
    def __init__(self, n=4, goal=(3, 3), trap=(1, 1)):
        self.n, self.goal, self.trap = n, goal, trap
        self.state = (0, 0)
        self.actions = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # 上下左右

    def reset(self):
        self.state = (0, 0)
        return self.state

    def step(self, a):
        dr, dc = self.actions[a]
        r, c = self.state
        nr, nc = min(max(r + dr, 0), self.n - 1), min(max(c + dc, 0), self.n - 1)
        self.state = (nr, nc)
        if self.state == self.trap:
            return self.state, -10.0, True
        if self.state == self.goal:
            return self.state, 10.0, True
        return self.state, -0.1, False        # 每步小惩罚，鼓励走最短路径
```

每步的 `-0.1` 很重要：没有它，智能体可以在安全区域无限打转而不受惩罚，学不出「尽快到达」。

### 二、策略评估（迭代版 Bellman 期望）

给定策略，反复用 Bellman 期望方程更新值函数直到收敛。

```python
def policy_eval(env, policy, gamma=0.9, theta=1e-6):
    V = {s: 0.0 for s in [(r, c) for r in range(env.n) for c in range(env.n)]}
    while True:
        delta = 0.0
        for s in V:
            if s in (env.goal, env.trap):
                continue
            v = 0.0
            for a, p in enumerate(policy[s]):
                if p == 0: continue
                env.state = s
                ns, r, _ = env.step(a)
                v += p * (r + gamma * V[ns])
            delta = max(delta, abs(v - V[s]))
            V[s] = v
        if delta < theta:
            return V
```

`delta` 就是这一轮的最大变化量，小于阈值说明收敛。注意 `env.state = s` 这行——评估时要能把环境「拨回」任意状态，否则只能在线估计。

### 三、值迭代求最优策略

值迭代不做策略评估，直接在 Bellman 最优方程上迭代。

```python
def value_iter(env, gamma=0.9, theta=1e-6):
    states = [(r, c) for r in range(env.n) for c in range(env.n)]
    V = {s: 0.0 for s in states}
    while True:
        delta = 0.0
        for s in states:
            if s in (env.goal, env.trap):
                continue
            qs = []
            for a in range(4):
                env.state = s
                ns, r, _ = env.step(a)
                qs.append(r + gamma * V[ns])
            best = max(qs)
            delta = max(delta, abs(best - V[s]))
            V[s] = best
        if delta < theta:
            return V
```

值迭代通常比「策略迭代」收敛更快（每轮只扫一遍），但每轮的计算量相同。两者的收敛结果一致——都是最优值函数。

### 四、Q-learning（off-policy TD 控制）

```python
def q_learning(env, episodes=2000, alpha=0.1, gamma=0.9,
               eps=0.1, eps_min=0.02, eps_decay=0.995):
    Q = {}
    for ep in range(episodes):
        s = env.reset()
        done = False
        while not done:
            Q.setdefault(s, np.zeros(4))
            if np.random.rand() < eps:
                a = np.random.randint(4)
            else:
                a = int(np.argmax(Q[s]))
            ns, r, done = env.step(a)
            Q.setdefault(ns, np.zeros(4))
            target = r + (0.0 if done else gamma * Q[ns].max())   # max 是 off-policy 的标志
            Q[s][a] += alpha * (target - Q[s][a])
            s = ns
        eps = max(eps_min, eps * eps_decay)
    return Q
```

`target` 里用 `Q[ns].max()` 而不是「下一步实际采取的动作的值」，这就是 off-policy：行为策略（ε-greedy）与目标策略（greedy）不同。

### 五、SARSA（on-policy 对照）

```python
def sarsa(env, episodes=2000, alpha=0.1, gamma=0.9, eps=0.1):
    Q = {}
    for _ in range(episodes):
        s = env.reset()
        Q.setdefault(s, np.zeros(4))
        a = int(np.argmax(Q[s])) if np.random.rand() > eps else np.random.randint(4)
        done = False
        while not done:
            ns, r, done = env.step(a)
            Q.setdefault(ns, np.zeros(4))
            na = int(np.argmax(Q[ns])) if np.random.rand() > eps else np.random.randint(4)
            target = r + (0.0 if done else gamma * Q[ns][na])     # 用实际下一步动作
            Q[s][a] += alpha * (target - Q[s][a])
            s, a = ns, na
    return Q
```

在「悬崖行走」这类环境里，SARSA 学到的是「远离悬崖」的安全路径，Q-learning 学到的是「贴着悬崖走」的最短路径——因为 Q-learning 假设后续总是走最优动作，不考虑探索时的随机性。

### 六、DQN 的两个关键部件

DQN = Q-learning + 神经网络 + 经验回放 + 目标网络。

```python
import torch, torch.nn as nn, random
from collections import deque

class QNet(nn.Module):
    def __init__(self, obs_dim, n_act):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(obs_dim, 64), nn.ReLU(),
                                 nn.Linear(64, 64), nn.ReLU(),
                                 nn.Linear(64, n_act))
    def forward(self, x):
        return self.net(x)

buffer = deque(maxlen=100000)

def train_step(online, target, opt, batch, gamma=0.99):
    s, a, r, ns, d = zip(*batch)
    s = torch.tensor(s, dtype=torch.float32)
    ns = torch.tensor(ns, dtype=torch.float32)
    a = torch.tensor(a, dtype=torch.long)
    r = torch.tensor(r, dtype=torch.float32)
    d = torch.tensor(d, dtype=torch.float32)
    q = online(s).gather(1, a[:, None]).squeeze(1)
    with torch.no_grad():
        y = r + gamma * (1 - d) * target(ns).max(1).values
    loss = nn.functional.smooth_l1_loss(q, y)
    opt.zero_grad(); loss.backward(); opt.step()
```

两个部件各解决一个问题：经验回放打破样本的时间相关性，目标网络稳定 TD 目标。缺任何一个都会导致训练震荡甚至发散。

### 七、目标网络的软更新

```python
def soft_update(online, target, tau=0.005):
    with torch.no_grad():
        for po, pt in zip(online.parameters(), target.parameters()):
            pt.data.mul_(1 - tau).add_(po.data, alpha=tau)
```

`tau` 很小时目标网络变化缓慢，等价于「延迟更新」的平滑版本。比「每 N 步硬拷贝一次」更稳，因为不会出现目标突变。

### 八、回报与折扣因子的量化

```python
def discounted_return(rewards, gamma):
    g, out = 0.0, []
    for r in reversed(rewards):
        g = r + gamma * g
        out.append(g)
    return list(reversed(out))
```

`gamma` 决定了「能看多远」：`gamma=0.9` 时，10 步后的奖励衰减到 0.35；`gamma=0.99` 时还有 0.90。任务周期越长，`gamma` 越要接近 1，但太大又会让价值估计方差变大——这是个必须按任务调节的参数。

## 三视角解析
### 🧑‍💻 程序员视角
Q-learning 是 off-policy：行为策略可以用 ε-greedy 探索，目标策略始终是贪心，因此能从旧数据学习。`γ` 越接近 1 越重视长期回报，但方差也越大、收敛越慢。探索率 ε 应随训练衰减，固定 ε 会导致收敛后在最优附近抖动。经验回放（replay buffer）打破样本相关性，是 DQN 稳定的关键——没有它，连续样本高度相关会让网络灾难性遗忘。

### 🎓 博士生视角
强化学习的核心是「在未知环境中通过交互最大化累积回报」，其数学基础是马尔可夫决策过程（MDP）与贝尔曼方程。值迭代与策略迭代是两种经典解法：前者直接迭代最优值函数，后者在「策略评估」与「策略改进」之间交替。Q-learning 的收敛性依赖「所有状态-动作对被无限次访问」与「学习率满足 Robbins-Monro 条件」。策略梯度方法（REINFORCE、PPO）直接优化策略参数，其方差可用基线（baseline）与优势函数（GAE）降低。

### 📚 考研者视角
算法岗面试高频：
1. **MDP 五元组**：状态、动作、转移、奖励、折扣因子；贝尔曼期望方程与最优方程的区别。
2. **on-policy vs off-policy**：SARSA 与 Q-learning 的更新式差异，各自适用场景。
3. **探索与利用**：ε-greedy、UCB、Thompson 采样的取舍。
4. **策略梯度**：REINFORCE 的更新式、为什么要加 baseline、PPO 的 clip 目标。

## 收尾

这八段代码覆盖了强化学习从 MDP 到 DQN 的完整骨架。凯喵的体会是，RL 的公式不多（Bellman 方程、TD 更新、策略梯度就这几个），但实现细节极多：迟到奖励的传播、探索与利用的平衡、目标网络的稳定性、经验回放的相关性。真正的门槛不在推导，而在「跑起来能收敛」——而这一步只能靠反复调参和看曲线积累手感。
