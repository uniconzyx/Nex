# 随机数：新旧 API 与可复现性

## 一、旧式 `np.random` 全局 API 与新式 `Generator`

旧式接口（`np.random.seed` / `np.random.rand` / `np.random.randn`）操作一个**进程级全局 RandomState**；
新式接口（`np.random.default_rng()`）返回一个**独立的 `Generator` 实例**，底层是 `PCG64` 等 BitGenerator。

```
# 旧式：全局可变状态，任何地方调用都会推进同一条流
np.random.seed(0)
a = np.random.randn(3)

# 新式：封装在 Generator 实例里，互不干扰
rng = np.random.default_rng(42)
b = rng.standard_normal(3)
c = rng.integers(0, 10, size=5)
```

### 🧑‍💻 程序员视角
- **工程首选新式 API**：`default_rng()` 返回的对象自带 `standard_normal / normal / integers / choice / permutation / shuffle`，功能更全（如 `integers` 支持开区间 `endpoint`）。
- **全局状态的灾难**：旧式 `np.random.seed` 改的是全局流，多线程 / 多模块各自 reseed 会互相踩踏，CI 里一处测试改了种子，另一处随机测试就「玄学」失败。新式的 `Generator` 把状态**封进对象**，可显式传递、可独立复现。
- **生产落地**：训练脚本、A/B 分流、采样推理都要把 `rng` 作为显式依赖注入，禁止依赖全局随机态；`np.random.default_rng(seed)` 是事实标准写法。

### 🎓 博士生视角
- 旧式背后也是 `RandomState`（Mersenne Twister，周期 2^19937-1），但它是**单例全局**的；新式把「**随机比特生成器（BitGenerator）**」与「**消耗比特产生分布的 Generator**」解耦——`PCG64` 负责产比特，`Generator` 负责把比特转成高斯/均匀/整数。
- 解耦带来的架构收益：可替换 BitGenerator（如 `MT19937`、`Philox` 用于 GPU 并行、`SFC64`），且 `Generator` 的方法做了类型与边界的严格校验（旧式常静默接受浮点参数）。
- PCG64 在统计质量与速度上均优于旧 MT19937，且状态更小、可种子化更精细；这对需要**可重现并行随机流**的仿真 / 分布式训练至关重要。

### 📚 考研者视角
- 数据分析岗笔面不考 408，但「**随机数可复现 / 随机种子**」是机器学习岗**笔面标准题**：常问「怎么保证实验可复现」「`np.random.seed` 和 `default_rng` 区别」。
- **标准答法**：可复现要固定**所有**随机源（Python `random`、NumPy、PyTorch、环境变量 `PYTHONHASHSEED`），且优先用 `default_rng(seed)` 而非全局 `seed`。
- **易错口径**：以为 `np.random.seed(0)` 后 `np.random.default_rng()` 也受影响——**不会**，两者是两套独立机制；新式 `Generator` 不吃旧式全局种子。

## 二、可复现性、随机流与并行

同一个种子产生**同一条随机流**；不同种子产生**相互独立**的流；`Generator` 实例各自维护游标，调用顺序决定后续值。

```
rng_a = np.random.default_rng(7)
rng_b = np.random.default_rng(7)
rng_a.standard_normal(3) == rng_b.standard_normal(3)   # True（同流）

g1 = np.random.default_rng(1); g2 = np.random.default_rng(2)
g1.standard_normal(3) != g2.standard_normal(3)         # True（异流）
```

### 🧑‍💻 程序员视角
- **复现 bug 的刚需**：线上模型跑出诡异结果，最先怀疑随机性不可复现。把 `seed` 写进配置文件并在日志里打印，是工程基本功。
- **并行采样**：为 worker 分配 `default_rng(base_seed + worker_id)`，保证「彼此独立、整体可复现」。不要用全局 seed 在多线程里共享，那是数据竞争与相关性隐患。
- **`spawn` 好用**：`PCG64` 支持 `BitGenerator.spawn(n)` 生成 n 个互不重叠的子流，是并行仿真的首选。

### 🎓 博士生视角
- 可复现性本质是**确定性状态机**：`state_{t+1} = f(state_t)`，给定初始 state（seed）与调用序列，输出序列唯一确定。这与分布式系统中的「确定性回放」同源。
- 并行时若各 stream 来自同一 MT 序列的不同偏移，会存在**长程相关性**；`spawn` 使用跳跃（jump-ahead）产生**代数独立**的子流，规避了该问题。这是「如何安全并行化随机源」的核心理论。
- 统计独立性 ≠ 可复现性：独立流保证采样无偏，可复现保证调试可得；两者要分开设计。

### 📚 考研者视角
- **笔面标准问法**：「两个 `default_rng(same_seed)` 得到的序列是否相等？两个不同 seed 呢？」标准答：**同 seed 同流相等，异 seed 独立不等**。
- **易错口径**：有人以为「重新 `default_rng` 同一 seed 会接着上次的流」——**不会**，每次调用都从 seed 重建初始状态，所以连续 `default_rng(0).random()` 两次得到**相同**值（这常是面试挖的坑）。
- 关联考点：随机化算法（快排 pivot、哈希扰动）里的「随机种子决定结果」也是高频问，与这里的可复现概念一致。
