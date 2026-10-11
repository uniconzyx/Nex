# 学习目标：Hive 数据仓库与 HQL（bd-ch03）

> 学科：`bigdata`　|　分组：B2（Hive 数仓）　|　前置：bd-ch02（MapReduce 原理与 YARN 调度）

本章承接 ch02 的「计算模型」，进入**数仓落地层**：Hive 把「写 SQL」变成「跑分布式作业」，让分析人员不必手写 MapReduce。目标是让你从「会写几条 HQL」进阶到「理解 Hive 把 SQL 翻译成 MR/Tez/Spark 的完整机制、以及它在存储/分区/Join/倾斜上的工程取舍」。学完应能回答：

1. **表与生命周期层面**：内部表（MANAGED）与外部表（EXTERNAL）在 `DROP` 时元数据与数据的去留差异；什么场景该用外部表（对接外部系统、防止误删数据）。
2. **存储组织层面**：分区表（partition）如何做分区裁剪减少 I/O；分桶表（bucket）如何用 `hash(key) % N` 决定桶文件，以及它和分区的本质区别与适用边界。
3. **编译执行层面**：一条 HQL 如何从 AST → 逻辑计划 → 物理计划，最终提交到 MR/Tez/Spark；JOIN 时优化器如何在 MapJoin（广播小表）与 CommonJoin（Shuffle）之间选择。
4. **性能与调优层面**：数据倾斜的识别与处理（加盐 + 两阶段聚合、MapJoin、自定义 Partitioner）；ORC/Parquet 列式存储配合**列裁剪 + 谓词下推**为何能大幅削减 I/O；动态分区的机制与风险。
5. **SQL 表达层面**：HQL 相对标准 SQL 的差异与扩展——窗口函数、`LATERAL VIEW explode` 行列转换、GROUP BY 转 MapReduce 的数据流心智模型。

配套可运行示例（`examples/`）用 **Python 从零模拟** Hive 核心机制：内部/外部表 DROP 行为、分区裁剪、分桶哈希取模、HQL 编译（AST→逻辑→物理）、JOIN 策略选择、数据倾斜加盐两阶段聚合、ORC/Parquet 列式存储与谓词下推、动态分区、GROUP BY 转 MR 数据流、explode 行列转换、窗口函数 Top-N。全部打印真实模拟结果，便于在没有真实 Hive 集群时建立直观心智模型。


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
