# 学习目标：离线数仓实战：分层建模与调度（bd-ch06）

> 学科：`bigdata`　|　分组：B4（离线数仓）　|　前置：bd-ch05（Spark SQL、DataFrame 与 Catalyst）

上一章回答的是「**一条 SQL 在 Spark 里怎么被优化、怎么被执行**」。它是**算子视角**：一张表进来，一张表出去。当你把它放大到一个公司的全部数据资产——每天上千张表、上百个调度任务、几十个业务方各自出报表——问题就变成了「**谁能读谁、口径谁来定、挂了怎么补、重跑会不会翻倍**」。本章进入**工程视角**：离线数据仓库（Offline Data Warehouse）的**分层建模**、**维度建模**、**指标治理**、**数据质量**与**调度运维**。学完应能回答：

1. **分层层面**：ODS / DWD / DWS / ADS 四层的职责边界分别是什么；为什么必须分层（**解耦、复用、口径统一、问题定位**）；「DWS 不得直接读 ODS」「ADS 不得反向写 DWD」这类硬约束为什么存在，以及如何用程序自动检查出来。
2. **维度建模层面**：**事实表**（谁、何时、何地、何事、多少）与**维度表**（谁/什么/哪里）的分工；**粒度（grain）**为什么必须先声明再建模，粒度被违背（重复粒度键、join 扇出）会造成什么后果；**星型模型** vs **雪花模型**在 JOIN 次数与存储量上的定量取舍。
3. **缓慢变化维层面**：为什么维度属性会变、变了为什么要留痕；**SCD Type 1**（覆盖）/ **Type 2**（拉链表）/ **Type 3**（新增列）三种策略各自的适用包袱；为什么 Type 1 **无法回答历史属性问题**，以及拉链表的 `start_date / end_date / is_current` 是如何构造与时间轴严格无缝的。
4. **指标治理层面**：**原子指标**与**派生指标**的规范化定义（度量字段 + 聚合方式 + 业务限定 + 时间口径四要素）；为何同一指标在不同 ADS 表会算出不同数字（**口径漂移**）以及如何自动检出。
5. **数据质量层面**：四类常驻校验（**空值率、唯一性、行数波动、枚举域**）与**跨层对账**（用 DWD 重算去核对 DWS 汇总）；为什么质量为题要在入库前拦截而不是在报表上被业务方发现。
6. **调度层面**：**DAG** 与拓扑排序、**关键路径（makespan）**、**循环依赖检测**、**最大并行度**；**补数 backfill** 的分区规划与分批策略；**SLA** 达成判定与瓶颈链定位；**幂等与重跑安全**（`INSERT OVERWRITE` 分区覆盖 vs `INSERT INTO` 追加这一经典坑）。
7. **端到端层面**：把一条完整离线链路拆成「**采集 → 清洗 → 聚合 → 报表**」四段，并清楚每一段产出落在哪一层、谁调度它、失败了怎么重跑。
8. **性能与治理层面**：**数据倾斜**的量化定位（最大分区 / 中位数）、**加盐打散 + 两阶段聚合**为何既不改变结果又能均衡 reducer 负载；**元数据**与**数据血缘**（上游传递闭包与下游影响面）如何支撑「改一张表会炸谁」的评估。


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

- 本章示例全部为**离线自包含的 Python 3.13 代码**，不依赖任何 Spark / Hive / 调度器，直接 `python xxx.py` 即可复现。
- 若你已有 Hive/SparkSQL 环境，可把示例中的 Python 判据换成真实 `SHOW PARTITIONS` / `EXPLAIN` / Airflow DAG 输出做对照。

## 配套示例（examples/）

14 类数仓核心机制全部用 Python 从零复刻并**真实实测**：分层依赖检查器（正反两组）、SCD Type 2 拉链表生成、SCD Type 1 vs Type 2 历史回溯差异、星型 vs 雪花的 JOIN 数与存储量、事实表粒度校验器（含 join 扇出）、指标口径一致性检查、数据质量校验器（空值率/唯一性/行数波动/枚举域）、跨层对账、调度 DAG（拓扑序 + 关键路径 + 环检测 + 最大并行度）、补数 backfill 规划器、SLA 达成判定、幂等重跑（OVERWRITE vs INTO）、数据倾斜检测与加盐打散、数据血缘的上游闭包与下游影响面。所有判据均为布尔值或计数，**不含任何机器相关量**，日期一律使用固定字符串。
