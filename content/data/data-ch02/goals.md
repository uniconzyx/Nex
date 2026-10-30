# data-ch02 · NumPy 进阶：广播、随机与性能

> 先修：data-ch01（ndarray / 向量化 / 广播规则基础 / 视图与拷贝）。衔接：data-ch03（Pandas）。
> 面试权重：★★★★☆（数据分析 / 算法 / 量化岗的核心硬技能，笔试常以向量化与性能为考点）

## 本章目标

学完你应该能：

1. **手工推导任意两个 shape 能否广播、广播后 shape 是什么**，并说清广播的语义：它**不复制数据**，而是把该维 stride 置 0，因此零内存、零拷贝，但一旦 `np.array(broadcast)` 物化就可能**内存爆炸**。
2. **区分新旧随机数 API**：旧式 `np.random.seed/rand/randn` 是全局可变状态，难以复现与并行；新式 `np.random.default_rng()` 返回**独立的 `Generator` 实例（PCG64 等 BitGenerator）**，可复现、可独立、可并行。
3. **把 Python 循环改写成向量化**，并能量化「为什么快」（消除解释器开销 + 连续内存局部性 + SIMD），理解 `np.einsum` 以下标标记表达任意张量收缩、避免显式中间数组。
4. **理解 stride / `as_strided` 的威力与危险**：滑动窗口、tiling 可以零拷贝实现，但重叠视图的写操作会「隔山打牛」式破坏数据。
5. **为缓存友好选择内存布局**：知道 C order 与 F order 的差异、transpose 会破坏连续性，并据此选择遍历顺序以利用 cache 局部性。
6. **对 dtype 精度与溢出有工程级警觉**：float32 累加会累积舍入误差、int8/uint8 溢出会回绕、float64 溢出变 inf，知道何时该升位。

## 性能目标（数量级直觉）

| 操作 | 相对量级（N≈10^6） |
|---|---|
| Python for 循环点积 | ~1000 ms |
| 列表推导 | ~200 ms |
| `np.dot`（向量化） | **~1 ms** |
| 说明 | 差距来自解释器开销 + 内存局部性 + SIMD |
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67,957 | 全章 | 经典机器学习库官方仓库：算法实现与最佳实践；本章先读与「广播的三条规则与形状推导」「广播的内存零拷贝本质与「内…」相关的部分 |
| 2 | [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50,229 | 全章 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib）；本章先读与「广播的三条规则与形状推导」「广播的内存零拷贝本质与「内…」相关的部分 |
| 3 | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49,928 | 全章 | Pandas 官方仓库：API 与内部机制权威来源；本章先读与「广播的三条规则与形状推导」「广播的内存零拷贝本质与「内…」相关的部分 |
| 4 | [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37,525 | 全章 | 微软官方 10 周数据科学课程；本章先读与「广播的三条规则与形状推导」「广播的内存零拷贝本质与「内…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 数据分析全套<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | 从 numpy/pandas 到清洗、可视化、案例的完整链路，配真实的电商与招聘数据集；看完回 `ex01`（广播规则）核对 |
| 2 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | API 速查：广播、索引、合并、透视各一集，10 分钟能补齐一个操作；看完回 `ex02`（广播的内存零拷贝本质与物化爆炸）核对 |
| 3 | Pandas 数据分析从入门到实战<br><sub>蚂蚁学Python</sub> | [BV1UJ411A7Fs](https://www.bilibili.com/video/BV1UJ411A7Fs/) | 全章 | 偏实战：时间序列、缺失值、多表关联这几节比教科书细；看完回 `ex03`（新式随机数 API）核对 |
| 4 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | 全章 | 数据分析绕不开 SQL：查询、聚合、窗口函数与索引，看前 1/3 足够支撑取数；看完回 `ex04`（新旧随机数 API）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《利用 Python 进行数据分析（第 3 版）》McKinney |
| 2 | 《Python 数据科学手册》VanderPlas |
| 3 | 《统计学（第 8 版）》贾俊平 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
