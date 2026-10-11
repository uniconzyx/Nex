# py-ch03 · 内置数据结构：list / tuple / dict / set 与推导式、深浅拷贝 · 学习目标

## 学习目标
完成本章后，你能：

1. 说出 `list` 在 CPython 中的真实结构（**动态指针数组 + 过度分配**），解释 `append` 为何摊销 O(1)、`insert(0, x)` 为何 O(n)，并能量化扩容代价。
2. 讲清 `dict` 的**开放寻址哈希表**实现：探测序列、负载因子与扩容时机、3.7+ 的紧凑化布局为何让遍历有序，以及"键必须可哈希"的底层含义。
3. 理解 `set` 基于同一套哈希机制、为何元素去重依赖 `__eq__` 与 `__hash__` 的一致性契约。
4. 区分 `tuple` 的**不可变**指的是"引用不可变"而非"内容不可变"，并规避「元组里装列表」的陷阱。
5. 熟练使用**列表/字典/集合推导式**与生成器表达式，知道何时用惰性（大数据流）何时用即时（需多次遍历）。
6. 精确区分**浅拷贝与深拷贝**：共享子对象、`copy.copy` / `copy.deepcopy` / 切片 `[:]` / `list()` 的语义差异，以及循环引用下 `deepcopy` 的备忘录机制。
7. 能根据访问模式（按下标 / 按 key / 去重 / 频繁增删两端）**选型容器**，并给出复杂度与内存占用的工程取舍。

## 前置
- py-ch01：变量与对象模型（名字绑定、可变/不可变）
- py-ch02：函数与作用域（闭包、装饰器，本章推导式会用到）

## 面试权重
- **高频**：dict 底层与哈希冲突、list.append 复杂度、浅/深拷贝、`==` 与 `is`、可变默认参数（见 ch02）。
- **中频**：tuple 不可变性、set 去重条件、生成器 vs 列表推导、`sort` 的 key 与稳定性。
- 属于「Python 岗必考 + 校招通用」的双重高频区。

## 真题依据（真实可查，仅存元数据）
- 《流畅的 Python（第2版）》第 2 章（序列）、第 3 章（字典与集合）。
- CPython 源码：`Objects/listobject.c`、`Objects/dictobject.c`。
- LeetCode 相关题见 `exercises.json`（只存元数据与链接，不复述题面）。

## 验收标准
- 能手写一个简化版哈希表并解释探测与扩容；
- 面对 `a = [[0]] * 3` 的共享陷阱能立即指出根因与修复；
- 能用 `sys.getsizeof` 说明 list 与 tuple 的内存差异。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225266 | Python 实现的全部经典算法，含详细注释 |
| [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187118 | Python 100 天从新手到大师（中文系统教程） |
| [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91310 | 微软官方 12 周机器学习入门课程，含 26 课与测验 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 600 集零基础 | [视频](https://www.bilibili.com/video/BV1ex411x7Em/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 千锋教育 · Python 700 集零基础 | [视频](https://www.bilibili.com/video/BV1R7411F7JV/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 鱼C工作室（小甲鱼）· 零基础入门学习 Python | [视频](https://www.bilibili.com/video/av52080698/) | 本学科配套视频，建议结合本章示例与习题观看 |
