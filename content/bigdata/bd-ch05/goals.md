# 学习目标：Spark SQL、DataFrame 与 Catalyst（bd-ch05）

> 学科：`bigdata`　|　分组：B3（Spark）　|　前置：bd-ch04（Spark 核心：RDD 与惰性求值）

上一章的 RDD 把「分布式数据集」抽象为血缘链，但它有一个致命短板：**Spark 看不见你在 lambda 里干了什么**，因此只能按你写死的步骤逐步执行。本章进入 **Spark SQL 层**：DataFrame/Dataset 带上了 **schema 与逻辑计划**，于是 Spark 可以先「看全局」再动手——这就是 **Catalyst 优化器**、**Tungsten 内存与代码生成**、**AQE 自适应执行**三件套的舞台。学完应能回答：

1. **抽象取舍层面**：RDD / DataFrame / Dataset 三者的语义差异；为什么「结构化信息 = 优化空间」；RDD 只见 lambda 黑盒、DataFrame 带 schema 与逻辑计划的本质区别；Dataset 的类型安全与编码器（Encoder）代价。
2. **Catalyst 层面**：优化器的四个阶段（解析 → 分析/绑定 → 逻辑优化 → 物理计划 → 代码生成）各自做什么；规则批（Rule / Batch）与「跑到一个不动点」的执行机制；`AnalysisException` 报的是哪一阶段。
3. **优化规则层面**：**谓词下推**（Predicate Pushdown）与**列裁剪**（Column Pruning）的触发条件与失效条件（nondeterministic 谓词不可下推、引用列不在投影内不可下推）；常量折叠；`JOIN` 重排与 CBO。
4. **执行引擎层面**：**Tungsten** 的堆外内存管理与紧凑二进制布局（消除对象头与装箱）；**全阶段代码生成**（Whole-Stage Codegen）如何消除虚函数调用与装箱；**AQE** 如何在运行时用真实统计动态合并小分区、动态切换 join 策略、动态处理倾斜。
5. **可观测性层面**：`explain(mode="formatted")` 的输出读法（自底向上看 Scan、按缩进看父子）；从 `Scan / Exchange / *Join / Aggregate` 反推 shuffle 边界与瓶颈。
6. **集成与调优层面**：与 Hive Metastore 的集成（表元数据从哪来、为什么要 `ANALYZE TABLE`）；宽/窄依赖与 shuffle 边界；广播 join 的触发条件与三个陷阱。


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

## 软前置（可选，不阻断学习）

- 本章示例全部为**离线自包含的 Python 3.13 代码**，不依赖任何 Spark 集群或 PySpark 包，直接 `python xxx.py` 即可复现。
- 若你手边有真实 Spark 环境，可对照执行 `df.explain(mode="formatted")` 与 Spark UI 的 SQL 标签页，把模拟数字换成真实数字。

## 配套示例（examples/）

12 类机制全部用 Python 从零复刻并**真实实测**：DataFrame 惰性求值、EXPLAIN 计划格式化器、谓词下推（正例 + nondeterministic 反例）、列裁剪（5 列 → 2 列）、常量折叠与计划裁剪、执行计划代价估算器、CBO JOIN 重排（左深 vs 右深）、宽窄依赖与 Shuffle 边界判定器、AQE 小分区合并（正反两组）、数据倾斜检测器（正反两组）、广播 JOIN 判定器（正反两组）、Tungsten 行式 vs 紧凑布局字节数、全阶段代码生成的虚调用计数。所有判据均为布尔值或操作计数，不含机器相关量。
