# 学习目标：Hive 数据仓库与 HQL（bd-ch03）

> 学科：`bigdata`　|　分组：B2（Hive 数仓）　|　前置：bd-ch02（MapReduce 原理与 YARN 调度）

本章承接 ch02 的「计算模型」，进入**数仓落地层**：Hive 把「写 SQL」变成「跑分布式作业」，让分析人员不必手写 MapReduce。目标是让你从「会写几条 HQL」进阶到「理解 Hive 把 SQL 翻译成 MR/Tez/Spark 的完整机制、以及它在存储/分区/Join/倾斜上的工程取舍」。学完应能回答：

1. **表与生命周期层面**：内部表（MANAGED）与外部表（EXTERNAL）在 `DROP` 时元数据与数据的去留差异；什么场景该用外部表（对接外部系统、防止误删数据）。
2. **存储组织层面**：分区表（partition）如何做分区裁剪减少 I/O；分桶表（bucket）如何用 `hash(key) % N` 决定桶文件，以及它和分区的本质区别与适用边界。
3. **编译执行层面**：一条 HQL 如何从 AST → 逻辑计划 → 物理计划，最终提交到 MR/Tez/Spark；JOIN 时优化器如何在 MapJoin（广播小表）与 CommonJoin（Shuffle）之间选择。
4. **性能与调优层面**：数据倾斜的识别与处理（加盐 + 两阶段聚合、MapJoin、自定义 Partitioner）；ORC/Parquet 列式存储配合**列裁剪 + 谓词下推**为何能大幅削减 I/O；动态分区的机制与风险。
5. **SQL 表达层面**：HQL 相对标准 SQL 的差异与扩展——窗口函数、`LATERAL VIEW explode` 行列转换、GROUP BY 转 MapReduce 的数据流心智模型。

配套可运行示例（`examples/`）用 **Python 从零模拟** Hive 核心机制：内部/外部表 DROP 行为、分区裁剪、分桶哈希取模、HQL 编译（AST→逻辑→物理）、JOIN 策略选择、数据倾斜加盐两阶段聚合、ORC/Parquet 列式存储与谓词下推、动态分区、GROUP BY 转 MR 数据流、explode 行列转换、窗口函数 Top-N。全部打印真实模拟结果，便于在没有真实 Hive 集群时建立直观心智模型。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46,562 | §3.2 | 讲「列式存储的收益」时看 `week4-analytics/` 的查询对比：同一份数据存 CSV 与 Parquet，扫描列数少时后者快一个数量级——谓词下推与列裁剪的实测 |
| 2 | [apache/spark](https://github.com/apache/spark) | 44,379 | §4.1 | 讲「HQL 到物理计划的映射」时读 `sql/catalyst/src/main/scala/org/apache/spark/sql/catalyst/optimizer/`：`PushPredicateThroughJoin`、`ColumnPruning` 这些规则就是「谓词下推、列裁剪」在 Spark 侧的等价物 |
| 3 | [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16,993 | §2.1 | 讲「内部表 vs 外部表」时读 `Hive.md`：删内部表连数据一起删、删外部表只删元数据，这条差异在文档里配了 `LOCATION` 的对照实验，比背定义好记 |
| 4 | [apache/hadoop](https://github.com/apache/hadoop) | 15,705 | §1.3 | 讲「Hive 与 Hadoop 的关系」时读 `hive/` 模块（在 `apache/hive` 而非 hadoop 仓库）的执行计划接口：Hive 只负责把 HQL 编译成 MR/Tez 作业，真正的执行仍由 Hadoop 完成 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（内部表 vs 外部表）核对 |
| 2 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex02`（分区表的分区裁剪（partition p）核对 |
| 3 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex03`（分桶表）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（HQL 编译）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
