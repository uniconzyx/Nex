# 学习目标：Hadoop 生态与 HDFS 架构（bd-ch01）

> 学科：`bigdata`　|　分组：B1（HDFS 与 YARN）　|　前置：无

本章聚焦分布式存储的事实标准 **HDFS（Hadoop Distributed File System）**，目标是让你从「会用 `hdfs dfs -put`」进阶到「理解它在分布式系统层面到底解决了什么、为什么这么设计」。学完应能回答：

1. **动机层面**：为什么单机文件系统撑不住 PB 级数据？容量、吞吐、容错三个维度分别怎样被分布式化解。
2. **架构层面**：NameNode 与 DataNode 的职责边界；HDFS 的「元数据 / 数据」分离设计；文件如何被切成 Block、Block 如何在多个 DataNode 上冗余存放。
3. **可用性层面**：机架感知（rack awareness）下的副本放置策略为什么是「本地 + 同机架 + 跨机架」；安全模式（safe mode）的判定逻辑；心跳与块报告如何驱动副本复制恢复。
4. **持久化层面**：edits log 与 fsimage 的关系；Secondary NameNode 的 checkpoint 不是「热备」这一关键误区；启动恢复序列。
5. **读写路径层面**：写入的流水线复制（pipeline）为何能摊薄网络开销；读取的就近/短路读（short-circuit read）；小文件问题（元数据爆炸）的根因与治理思路。

配套可运行示例（`examples/`）用 Python 从零模拟 NameNode 元数据、DataNode 块存储、副本放置、fsimage/edits 合并、安全模式判定、心跳副本复制等核心机制，便于在没有真实集群时建立直观心智模型。


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
