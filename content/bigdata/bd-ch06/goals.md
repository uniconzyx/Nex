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
## 软前置（可选，不阻断学习）

- 本章示例全部为**离线自包含的 Python 3.13 代码**，不依赖任何 Spark / Hive / 调度器，直接 `python xxx.py` 即可复现。
- 若你已有 Hive/SparkSQL 环境，可把示例中的 Python 判据换成真实 `SHOW PARTITIONS` / `EXPLAIN` / Airflow DAG 输出做对照。

## 配套示例（examples/）

14 类数仓核心机制全部用 Python 从零复刻并**真实实测**：分层依赖检查器（正反两组）、SCD Type 2 拉链表生成、SCD Type 1 vs Type 2 历史回溯差异、星型 vs 雪花的 JOIN 数与存储量、事实表粒度校验器（含 join 扇出）、指标口径一致性检查、数据质量校验器（空值率/唯一性/行数波动/枚举域）、跨层对账、调度 DAG（拓扑序 + 关键路径 + 环检测 + 最大并行度）、补数 backfill 规划器、SLA 达成判定、幂等重跑（OVERWRITE vs INTO）、数据倾斜检测与加盐打散、数据血缘的上游闭包与下游影响面。所有判据均为布尔值或计数，**不含任何机器相关量**，日期一律使用固定字符串。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46,562 | §1.2 | 讲「ODS/DWD/DWS/ADS 四层」时看 `week4-analytics/` 的数仓作业：从原始 JSON 到宽表再聚合到指标表，每一层的输入输出都是独立的表，层与层的调用关系就是分层规范的落地 |
| 2 | [apache/spark](https://github.com/apache/spark) | 44,379 | §4.3 | 讲「小文件合并」时读 `sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/` 的写入路径：`repartition` 与 `coalesce` 在写出前决定文件数，分区数乘作业批次就是「每天新增多少小文件」 |
| 3 | [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16,993 | §2.2 | 讲「维度建模与粒度」时读 `BigData-Notes` 里的数仓篇：「先声明粒度再选维度」这条顺序错了，后面所有指标口径都会漂移——文档给了「订单事实表」的完整推演 |
| 4 | [apache/hadoop](https://github.com/apache/hadoop) | 15,705 | §3.1 | 讲「调度与 SLA」时对照 `hadoop-yarn-project/` 的队列与容量调度：YARN 的 `CapacityScheduler` 决定「哪个队列先跑」，数仓的基线任务要放在高优先级队列，否则被离线任务挤掉 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（分层建模检查器）核对 |
| 2 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex02`（SCD Type 2 拉链表）核对 |
| 3 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex03`（SCD Type 1 vs Type 2）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（星型 vs 雪花模型）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
