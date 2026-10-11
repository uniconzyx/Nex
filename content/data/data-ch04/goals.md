# data-ch04 · Pandas 进阶：分组聚合、合并与时间序列

## 一、为什么这三件事是 Pandas 的分水岭

`data-ch03` 解决的是「**一张表怎么读、怎么看、怎么改**」。
但真实数据分析里，绝大多数问题都不是单表问题，而是三类问题的组合：

1. **分组聚合**：「按城市、按月份分别算均值/分位数/留存率」——`groupby`；
2. **多表合并**：「订单表 join 用户表 join 商品表」——`merge`/`concat`；
3. **时间序列**：「按月重采样、算 7 日滚动均值、看同比」——`resample`/`rolling`。

这三件事是「会用 Pandas」和「**能用 Pandas 干活**」之间的分水岭。
更关键的是，它们各自都有一个**语义陷阱**：

| 组 | 看上去的直觉 | 实际语义 | 出错的后果 |
|---|---|---|---|
| `groupby` | 「按组算一下就完事」 | split → apply → combine，**结果的索引/形状取决于聚合函数** | 对错行、丢列、形状对不上 |
| `merge` | 「和 SQL JOIN 一样」 | 键**不唯一时行数会膨胀**（笛卡尔积） | 指标虚高，且**不报错** |
| `resample`/`rolling` | 「按时间切一切」 | 依赖**索引类型与是否单调**，窗口边界是**左闭右闭**而非左闭右开 | 统计口径偏移一格 |

本章就围绕这三条主线，把它们的**心智模型、语义边界和性能特征**讲透。

## 二、学完之后你应该能做到

- 用 `split-apply-combine` 的心智模型解释任意 `groupby` 语句的结果形状；
- 准确区分 `agg` / `transform` / `apply` / `filter` 四者**返回的是标量、同长序列还是新表**；
- 徒手写出 `merge` 的四种连接语义，并说明它和 SQL `JOIN` 的**一一对应关系**；
- 识别「多对多合并导致行数膨胀」并在合并前用 `validate=` 主动拦截；
- 用 `DatetimeIndex` + `resample` + `rolling` 完成一份月度/滚动指标；
- 说清楚 `pivot_table` 与 `groupby` 的关系（**透视表就是带默认聚合的分组**）；
- 在 `apply` 与向量化之间做**有依据的**取舍，而不是凭感觉。

## 三、本章结构

| 文件 | 主题 | 核心问题 |
|---|---|---|
| `concept/01-groupby-split-apply-combine.md` | 分组聚合 | 结果形状由谁决定？`agg`/`transform`/`apply` 怎么选？ |
| `concept/02-merge-join-concat.md` | 多表连接 | 行数为什么变了？怎么防住笛卡尔积？ |
| `concept/03-time-series-resample-rolling.md` | 时间序列 | 重采样与窗口的边界、单调性、时区 |
| `concept/04-pivot-and-performance.md` | 透视与性能 | 透视表本质；`apply` 到底慢在哪 |

## 四、动手实践（建议顺序）

1. 先跑 `examples/ex01-groupby-basics-and-agg.json`，把同一个分组分别用
   `agg`/`transform`/`apply`/`filter` 做一遍，**逐字对比输出的形状**；
2. 再跑 `examples/ex05-merge-many-to-many-inflation.json`，
   亲眼看到「合并后行数比两边都多」——这是本章最重要的一次震撼教育；
3. 接着跑 `examples/ex08-resample-and-rolling.json`，注意窗口边界落在哪一行；
4. 最后跑 `examples/ex11-apply-vs-vectorized.json`，看**布尔判据**而非耗时。

## 五、自检清单

- [ ] 我能说出 `transform` 与 `agg` 返回值的形状差异，并知道什么时候只能用 `transform`；
- [ ] 我知道 `merge(how="left")` 与 `join` 默认按索引合并的区别；
- [ ] 我会在合并前跑一次 `df.groupby(key).size().max() > 1` 或 `validate="one_to_many"`；
- [ ] 我能解释为什么 `rolling(7).mean()` 的第一行是 `NaN`；
- [ ] 我知道 `resample("ME")` 与 `resample("MS")` 的标签落在月末还是月初；
- [ ] 我不会在「能用向量化搞定」的场景里用 `apply`。

> 三视角说明：本章每个 concept 文件末尾都内嵌
> **程序员视角 / 博士生视角 / 考研者视角** 三段互补解析，分别面向
> 「工程怎么落地并排错」「机制的第一性原理」「笔试面试标准问法与易错口径」。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67487 | 经典机器学习库官方仓库：算法实现与最佳实践 |
| [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50114 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib） |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49928 | Pandas 官方仓库：API 与内部机制权威来源 |
| [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37525 | 微软官方 10 周数据科学课程 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |
