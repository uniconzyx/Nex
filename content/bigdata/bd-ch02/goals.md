# 学习目标：MapReduce 原理与 YARN 调度（bd-ch02）

> 学科：`bigdata`　|　分组：B1（HDFS 与 YARN）　|　前置：bd-ch01（Hadoop 生态与 HDFS 架构）

本章承接 ch01 的「数据放得下」，聚焦「数据算得动」：即 **MapReduce 计算模型**与 **YARN 资源调度**。目标是让你从「会写 `hadoop jar` 跑 WordCount」进阶到「理解一次作业从提交到出结果的完整数据流，以及它在集群上如何被调度、如何因倾斜而慢、如何调优」。学完应能回答：

1. **数据流层面**：一次 MapReduce 作业如何走过 Map → Shuffle → Reduce 三阶段；中间 key-value 是怎么产生、怎么跨网络搬、怎么聚合出结果的（端到端 WordCount 走读）。
2. **Shuffle 层面**：为什么 Shuffle 是「性能与瓶颈的胜负手」；分区（Partitioner）如何决定 reduce 数、排序（sort）与溢写（spill）如何在内存/磁盘间往返、归并（merge）如何把多路有序流合成一路。
3. **优化原语层面**：Combiner 是什么、为什么它只是「本地 reduce」、它不能改变语义的边界；Partitioner 与数据倾斜的关系。
4. **资源调度层面**：YARN 的三类角色 ResourceManager / NodeManager / ApplicationMaster 各自的职责，以及作业从提交到容器分配的状态机；FIFO / Capacity / Fair 三种调度器的取舍与适用场景。
5. **实战调优层面**：如何识别数据倾斜（某 key 一家独大），以及 Combiner、加盐（salting）、自定义 Partitioner、MapJoin 等缓解手段的适用边界。

配套可运行示例（`examples/`）用 **Python 从零模拟**：Map 的 kv 中间输出、Shuffle 的分区/排序/溢写/归并、Reduce 聚合、Combiner 优化对比、Partitioner 决定 reduce 数、YARN 的角色状态机与容器分配、三种调度器对比、AM 资源申请循环、数据倾斜识别与加盐缓解。全部打印真实模拟结果，便于在没有真实 Hadoop 集群时建立直观心智模型。


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
