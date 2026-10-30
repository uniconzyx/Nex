# 学习目标：Hadoop 生态与 HDFS 架构（bd-ch01）

> 学科：`bigdata`　|　分组：B1（HDFS 与 YARN）　|　前置：无

本章聚焦分布式存储的事实标准 **HDFS（Hadoop Distributed File System）**，目标是让你从「会用 `hdfs dfs -put`」进阶到「理解它在分布式系统层面到底解决了什么、为什么这么设计」。学完应能回答：

1. **动机层面**：为什么单机文件系统撑不住 PB 级数据？容量、吞吐、容错三个维度分别怎样被分布式化解。
2. **架构层面**：NameNode 与 DataNode 的职责边界；HDFS 的「元数据 / 数据」分离设计；文件如何被切成 Block、Block 如何在多个 DataNode 上冗余存放。
3. **可用性层面**：机架感知（rack awareness）下的副本放置策略为什么是「本地 + 同机架 + 跨机架」；安全模式（safe mode）的判定逻辑；心跳与块报告如何驱动副本复制恢复。
4. **持久化层面**：edits log 与 fsimage 的关系；Secondary NameNode 的 checkpoint 不是「热备」这一关键误区；启动恢复序列。
5. **读写路径层面**：写入的流水线复制（pipeline）为何能摊薄网络开销；读取的就近/短路读（short-circuit read）；小文件问题（元数据爆炸）的根因与治理思路。

配套可运行示例（`examples/`）用 Python 从零模拟 NameNode 元数据、DataNode 块存储、副本放置、fsimage/edits 合并、安全模式判定、心跳副本复制等核心机制，便于在没有真实集群时建立直观心智模型。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [DataTalksClub/data-engineering-zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) | 46,442 | 全章 | 免费 9 周数据工程课程：含 Hadoop/Spark/数仓实践 |
| 2 | [apache/spark](https://github.com/apache/spark) | 44,339 | 全章 | Apache Spark 官方仓库：RDD/SQL/调优权威来源 |
| 3 | [heibaiying/BigData-Notes](https://github.com/heibaiying/BigData-Notes) | 16,992 | 全章 | 中文大数据入门指南：Hadoop/Hive/Spark/Flink 系统笔记 |
| 4 | [apache/hadoop](https://github.com/apache/hadoop) | 15,699 | 全章 | Apache Hadoop 官方仓库：HDFS/YARN/MapReduce 实现 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Hadoop 3.x（搭建到调优）<br><sub>尚硅谷</sub> | [BV1Qp4y1n7EN](https://www.bilibili.com/video/BV1Qp4y1n7EN/) | 全章 | 主线：HDFS 读写与副本 → MapReduce 执行流程与 shuffle → YARN 资源调度 → 集群调优；看完回 `ex01`（NameNode 元数据）核对 |
| 2 | 尚硅谷 · Hive 框架详解<br><sub>尚硅谷</sub> | [BV1W4411B7cN](https://www.bilibili.com/video/BV1W4411B7cN/) | 全章 | 把 SQL 翻译成 MapReduce 的过程、分区与分桶、内部表与外部表的差别；看完回 `ex02`（DataNode 块存储与校验和防静默损）核对 |
| 3 | 尚硅谷 · Spark 从入门到精通<br><sub>尚硅谷</sub> | [BV11A411L7CK](https://www.bilibili.com/video/BV11A411L7CK/) | 全章 | RDD 的血缘与宽窄依赖、DAG 与 stage 划分、shuffle 与内存管理；DataFrame 部分接 Spark SQL；看完回 `ex03`（副本放置策略）核对 |
| 4 | 尚硅谷 · Flink 1.17 实战<br><sub>尚硅谷</sub> | [BV1eg4y1V7AN](https://www.bilibili.com/video/BV1eg4y1V7AN/) | 全章 | 流处理模型：事件时间与水印、窗口、状态与 checkpoint、精确一次语义；看完回 `ex04`（块大小与寻址）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Hadoop 权威指南（第 4 版）》White |
| 2 | 《Spark 快速大数据分析》Zaharia 等 |
| 3 | 《Streaming Systems》Akidau 等 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
