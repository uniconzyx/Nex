# data-ch01 · NumPy 基础：ndarray 与向量化

> 先修：py-ch01（Python 语法基础）。衔接：data-ch02（Pandas）、data-ch03（爬虫与数据清洗）。
> 面试权重：★★★☆☆（数据分析岗必考，后端岗常考向量化思维与内存意识）

## 本章目标

学完你应该能：

1. **解释为什么 ndarray 比 list 快 10~100 倍**，而且能说清这是三个独立因素的叠加：
   同构连续内存、消除类型分派（无需逐元素查 PyObject 类型）、SIMD 向量化指令。
2. **在「视图」与「拷贝」之间做正确选择**：能用 `base` 与 `np.shares_memory` 判定，
   知道哪些操作是 view（切片、reshape、transpose）、哪些一定拷贝（花式索引、astype、ravel 非连续时）。
3. **不查文档写出广播规则**：三条规则 + 从尾维对齐，能手工推导任意两个 shape 是否可广播。
4. **用 strides 解释 transpose 为什么几乎免费**，以及为什么「转置后再 ravel」会偷偷拷贝。
5. **把显式循环改写成向量化表达**：识别 reduce / map / mask 三类模式，并用 `np.where` 取代 Python 层 if。

## 性能目标（要有数量级直觉）

| 操作 | 相对耗时（N = 10^6） |
|---|---|
| Python for 循环 | ~100 ms |
| list comprehension | ~50 ms |
| `np.sum(a)`（向量化） | **~1 ms** |
| 说明 | 差距来自解释器开销 + 内存局部性 + SIMD |

## 本章 GitHub 资源（star 最高，实时抓取）

- `scikit-learn/scikit-learn` — 67487★：NumPy/SciPy 生态的最佳实践范本
- `numpy/numpy` — 官方源码，`ndarray` 的 strides 机制读源码最能理解
- `jakevdp/PythonDataScienceHandbook` — 数据科学手册，含 NumPy 深度章节


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）
- Python 语法基础（py-ch01）：本线**独立自足**，若你已会用 Python 写循环/函数/列表，可直接从本章开始；若不熟悉，建议先花 1~2 小时过一遍 Python 基础语法，本章不依赖其进阶内容。
