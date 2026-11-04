# 学习目标：Spark 核心：RDD 与惰性求值（bd-ch04）

> 学科：`bigdata`　|　分组：B3（Spark）　|　前置：bd-ch02（MapReduce 原理与 YARN 调度）

本章进入**计算引擎层**：Spark 凭什么比 MapReduce 快一个数量级？答案是「**内存计算 + DAG 调度 + 惰性求值**」。核心抽象 **RDD** 把「分布式数据集」表达为一条可重放的血缘链，用窄/宽依赖决定 Stage 与 Shuffle，用缓存与 checkpoint 在「重算代价」与「内存占用」之间取舍。学完应能回答：

1. **抽象与特性层面**：RDD 是什么、五大特性分别是什么；为什么「不可变 + 血缘」能实现容错（对比 HDFS 副本容错）。
2. **执行模型层面**：Transformation 与 Action 的区别；**惰性求值**如何避免无效计算、把多个算子融合进一个 Stage；DAG 是怎么从代码里「长」出来的。
3. **依赖与调度层面**：窄依赖 vs 宽依赖的判定；为什么宽依赖必然触发 Shuffle；Stage 以宽依赖为界如何划分；**Task 数 = 分区数**这一关键等式。
4. **性能与调优层面**：`reduceByKey` 为何比 `groupByKey` 省 Shuffle；`cache/persist` 与 `checkpoint` 的取舍；`mapPartitions` 相对 `map` 的调用次数优势；数据倾斜的成因与量化；并行度（分区数）对并发的影响。
5. **容错层面**：窄依赖失败只重算单分区、宽依赖失败需重算全部父分区；checkpoint 如何截断超长血缘。

配套可运行示例（`examples/`）用 **Python 从零模拟** Spark 核心机制并量化：血缘 DAG 构建、惰性求值（`compute_calls` 计数器证明）、窄/宽依赖判定、Stage 与 Task 数、map vs mapPartitions、reduceByKey vs groupByKey 的 Shuffle 量、缓存重算次数、checkpoint 截断、宽依赖重算范围、数据倾斜负载、并行度与 Task 数。全部打印真实模拟数字，便于没有 Spark 集群时建立直观心智模型。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46,562 | §2.1 二、Transformation 与 Action 的判别 | 读 `week5-batch/` 的 Spark 作业：`df.filter(...)` 之后不打 `show()`/`count()` 就什么都不执行，脚本里加不加 action 直接决定「有没有真的跑」；本节要练的判别方法在源码里就是「是否返回 RDD/DataFrame」——返回新 RDD 的是 transformation，返回数/列表/None 的是 action |
| 2 | [apache/spark](https://github.com/apache/spark) | 44,379 | §1.1 二、不可变性与血缘（lineage）容错 | 读 `core/src/main/scala/org/apache/spark/rdd/RDD.scala`：`getPartitions`/`compute`/`getDependencies` 三个抽象方法就是「分区列表 + 计算函数 + 依赖」的代码化，其余两个是优化信息；本节讲的 lineage 容错，本质就是「只要 `getDependencies` 还在，丢掉的 `compute` 就能重跑」 |
| 3 | [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16,993 | §3.1 二、Stage 划分与 Task 数量计算 | 读 `Spark.md`：它画出「窄依赖可流水线、宽依赖要 shuffle」的依赖图，并给出「Stage 数 = 宽依赖数 + 1」的算式；本章 §1.1 里的 `getDependencies` 是这个算式唯一的输入——所以「怎么少一个 Stage」等价于「怎么消掉一次宽依赖」 |
| 4 | [apache/hadoop](https://github.com/apache/hadoop) | 15,705 | §4.1 二、算子选择与数据倾斜（工程调优三板斧） | 读 `hadoop-hdfs-project/` 的副本机制做对照：HDFS 用「多存几份」换容错，Spark 用「血缘重算」换容错，所以 Spark 不能随意 `checkpoint`——一旦截断血缘，重算就退化成重读；这正是本节「该不该 cache」的判据，也对应本章 §5.2「收尾：Spark 调优就是守住那三条前提」 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（RDD 血缘 DAG 的构建与打印）核对 |
| 2 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex02`（惰性求值）核对 |
| 3 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex03`（窄依赖 vs 宽依赖（是否 Shuffl）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（Stage 划分（以宽依赖为界）与 Ta）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
