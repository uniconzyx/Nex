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

## 本章 GitHub 资源（实时抓取，star 最高）

- `jakevdp/PythonDataScienceHandbook` — 50114★：含 NumPy 进阶深度章节（stride、广播、性能）
- `scikit-learn/scikit-learn` — 67487★：向量化与内存友好的最佳实践范本
- `pandas-dev/pandas` — 49928★：底层基于 NumPy，C/F 布局与 stride 思维贯穿
- `microsoft/Data-Science-For-Beginners` — 37525★：微软官方 10 周数据科学课程


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |
