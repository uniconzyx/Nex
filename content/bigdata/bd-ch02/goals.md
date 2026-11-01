# 学习目标：MapReduce 原理与 YARN 调度（bd-ch02）

> 学科：`bigdata`　|　分组：B1（HDFS 与 YARN）　|　前置：bd-ch01（Hadoop 生态与 HDFS 架构）

本章承接 ch01 的「数据放得下」，聚焦「数据算得动」：即 **MapReduce 计算模型**与 **YARN 资源调度**。目标是让你从「会写 `hadoop jar` 跑 WordCount」进阶到「理解一次作业从提交到出结果的完整数据流，以及它在集群上如何被调度、如何因倾斜而慢、如何调优」。学完应能回答：

1. **数据流层面**：一次 MapReduce 作业如何走过 Map → Shuffle → Reduce 三阶段；中间 key-value 是怎么产生、怎么跨网络搬、怎么聚合出结果的（端到端 WordCount 走读）。
2. **Shuffle 层面**：为什么 Shuffle 是「性能与瓶颈的胜负手」；分区（Partitioner）如何决定 reduce 数、排序（sort）与溢写（spill）如何在内存/磁盘间往返、归并（merge）如何把多路有序流合成一路。
3. **优化原语层面**：Combiner 是什么、为什么它只是「本地 reduce」、它不能改变语义的边界；Partitioner 与数据倾斜的关系。
4. **资源调度层面**：YARN 的三类角色 ResourceManager / NodeManager / ApplicationMaster 各自的职责，以及作业从提交到容器分配的状态机；FIFO / Capacity / Fair 三种调度器的取舍与适用场景。
5. **实战调优层面**：如何识别数据倾斜（某 key 一家独大），以及 Combiner、加盐（salting）、自定义 Partitioner、MapJoin 等缓解手段的适用边界。

配套可运行示例（`examples/`）用 **Python 从零模拟**：Map 的 kv 中间输出、Shuffle 的分区/排序/溢写/归并、Reduce 聚合、Combiner 优化对比、Partitioner 决定 reduce 数、YARN 的角色状态机与容器分配、三种调度器对比、AM 资源申请循环、数据倾斜识别与加盐缓解。全部打印真实模拟结果，便于在没有真实 Hadoop 集群时建立直观心智模型。
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
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（Map 阶段）核对 |
| 2 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex02`（Partitioner）核对 |
| 3 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex03`（Shuffle 排序）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（Shuffle 溢写与多路归并（外部排序）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
