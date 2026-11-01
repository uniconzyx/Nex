# 学习目标：Spark SQL、DataFrame 与 Catalyst（bd-ch05）

> 学科：`bigdata`　|　分组：B3（Spark）　|　前置：bd-ch04（Spark 核心：RDD 与惰性求值）

上一章的 RDD 把「分布式数据集」抽象为血缘链，但它有一个致命短板：**Spark 看不见你在 lambda 里干了什么**，因此只能按你写死的步骤逐步执行。本章进入 **Spark SQL 层**：DataFrame/Dataset 带上了 **schema 与逻辑计划**，于是 Spark 可以先「看全局」再动手——这就是 **Catalyst 优化器**、**Tungsten 内存与代码生成**、**AQE 自适应执行**三件套的舞台。学完应能回答：

1. **抽象取舍层面**：RDD / DataFrame / Dataset 三者的语义差异；为什么「结构化信息 = 优化空间」；RDD 只见 lambda 黑盒、DataFrame 带 schema 与逻辑计划的本质区别；Dataset 的类型安全与编码器（Encoder）代价。
2. **Catalyst 层面**：优化器的四个阶段（解析 → 分析/绑定 → 逻辑优化 → 物理计划 → 代码生成）各自做什么；规则批（Rule / Batch）与「跑到一个不动点」的执行机制；`AnalysisException` 报的是哪一阶段。
3. **优化规则层面**：**谓词下推**（Predicate Pushdown）与**列裁剪**（Column Pruning）的触发条件与失效条件（nondeterministic 谓词不可下推、引用列不在投影内不可下推）；常量折叠；`JOIN` 重排与 CBO。
4. **执行引擎层面**：**Tungsten** 的堆外内存管理与紧凑二进制布局（消除对象头与装箱）；**全阶段代码生成**（Whole-Stage Codegen）如何消除虚函数调用与装箱；**AQE** 如何在运行时用真实统计动态合并小分区、动态切换 join 策略、动态处理倾斜。
5. **可观测性层面**：`explain(mode="formatted")` 的输出读法（自底向上看 Scan、按缩进看父子）；从 `Scan / Exchange / *Join / Aggregate` 反推 shuffle 边界与瓶颈。
6. **集成与调优层面**：与 Hive Metastore 的集成（表元数据从哪来、为什么要 `ANALYZE TABLE`）；宽/窄依赖与 shuffle 边界；广播 join 的触发条件与三个陷阱。
## 软前置（可选，不阻断学习）

- 本章示例全部为**离线自包含的 Python 3.13 代码**，不依赖任何 Spark 集群或 PySpark 包，直接 `python xxx.py` 即可复现。
- 若你手边有真实 Spark 环境，可对照执行 `df.explain(mode="formatted")` 与 Spark UI 的 SQL 标签页，把模拟数字换成真实数字。

## 配套示例（examples/）

12 类机制全部用 Python 从零复刻并**真实实测**：DataFrame 惰性求值、EXPLAIN 计划格式化器、谓词下推（正例 + nondeterministic 反例）、列裁剪（5 列 → 2 列）、常量折叠与计划裁剪、执行计划代价估算器、CBO JOIN 重排（左深 vs 右深）、宽窄依赖与 Shuffle 边界判定器、AQE 小分区合并（正反两组）、数据倾斜检测器（正反两组）、广播 JOIN 判定器（正反两组）、Tungsten 行式 vs 紧凑布局字节数、全阶段代码生成的虚调用计数。所有判据均为布尔值或操作计数，不含机器相关量。

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46,562 | 全章 | 免费 9 周数据工程课程：含 Hadoop/Spark/数仓实践 |
| 2 | [apache/spark](https://github.com/apache/spark) | 44,379 | 全章 | Apache Spark 官方仓库：RDD/SQL/调优权威来源 |
| 3 | [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16,993 | 全章 | 中文大数据入门指南：Hadoop/Hive/Spark/Flink 系统笔记 |
| 4 | [apache/hadoop](https://github.com/apache/hadoop) | 15,705 | 全章 | Apache Hadoop 官方仓库：HDFS/YARN/MapReduce 实现 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（DataFrame 惰性求值）核对 |
| 2 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex02`（EXPLAIN 计划格式化器）核对 |
| 3 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex03`（谓词下推）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（谓词下推的两个反例）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
