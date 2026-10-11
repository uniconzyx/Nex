# 学习目标：Spark 核心：RDD 与惰性求值（bd-ch04）

> 学科：`bigdata`　|　分组：B3（Spark）　|　前置：bd-ch02（MapReduce 原理与 YARN 调度）

本章进入**计算引擎层**：Spark 凭什么比 MapReduce 快一个数量级？答案是「**内存计算 + DAG 调度 + 惰性求值**」。核心抽象 **RDD** 把「分布式数据集」表达为一条可重放的血缘链，用窄/宽依赖决定 Stage 与 Shuffle，用缓存与 checkpoint 在「重算代价」与「内存占用」之间取舍。学完应能回答：

1. **抽象与特性层面**：RDD 是什么、五大特性分别是什么；为什么「不可变 + 血缘」能实现容错（对比 HDFS 副本容错）。
2. **执行模型层面**：Transformation 与 Action 的区别；**惰性求值**如何避免无效计算、把多个算子融合进一个 Stage；DAG 是怎么从代码里「长」出来的。
3. **依赖与调度层面**：窄依赖 vs 宽依赖的判定；为什么宽依赖必然触发 Shuffle；Stage 以宽依赖为界如何划分；**Task 数 = 分区数**这一关键等式。
4. **性能与调优层面**：`reduceByKey` 为何比 `groupByKey` 省 Shuffle；`cache/persist` 与 `checkpoint` 的取舍；`mapPartitions` 相对 `map` 的调用次数优势；数据倾斜的成因与量化；并行度（分区数）对并发的影响。
5. **容错层面**：窄依赖失败只重算单分区、宽依赖失败需重算全部父分区；checkpoint 如何截断超长血缘。

配套可运行示例（`examples/`）用 **Python 从零模拟** Spark 核心机制并量化：血缘 DAG 构建、惰性求值（`compute_calls` 计数器证明）、窄/宽依赖判定、Stage 与 Task 数、map vs mapPartitions、reduceByKey vs groupByKey 的 Shuffle 量、缓存重算次数、checkpoint 截断、宽依赖重算范围、数据倾斜负载、并行度与 Task 数。全部打印真实模拟数字，便于没有 Spark 集群时建立直观心智模型。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46045 | 免费 9 周数据工程课程：含 Hadoop/Spark/数仓实践 |
| [apache/spark](https://github.com/apache/spark) | 44136 | Apache Spark 官方仓库：RDD/SQL/调优权威来源 |
| [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16979 | 中文大数据入门指南：Hadoop/Hive/Spark/Flink 系统笔记 |
| [apache/hadoop](https://github.com/apache/hadoop) | 15681 | Apache Hadoop 官方仓库：HDFS/YARN/MapReduce 实现 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Hadoop 3.x 教程 | [视频](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Hive 3.x 教程 | [视频](https://www.bilibili.com/video/BV1W4411B7cN/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Spark 教程 | [视频](https://www.bilibili.com/video/BV11A411L7CK/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Kafka 教程 | [视频](https://www.bilibili.com/video/BV1a4411B7V9/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Flink 实战教程 | [视频](https://www.bilibili.com/video/BV1qy4y1q728/) | 本学科配套视频，建议结合本章示例与习题观看 |
