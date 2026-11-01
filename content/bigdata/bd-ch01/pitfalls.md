# HDFS 易错点（高频踩坑与笔试面试易混口径）

1. **Secondary NameNode 是 NameNode 的热备** —— 错。Secondary NameNode 只做 fsimage/edits 的 checkpoint 合并，NameNode 宕机它**不能接管服务**。真正的热备是 HA 架构（Active/Standby + QJM + ZKFC）。正确写法：把「高可用」与「检查点」两个职责分清，生产环境务必启用 HA，不要用 Secondary NameNode 当备份。

2. **块到 DataNode 的映射持久化在 fsimage 里** —— 错。fsimage 只存命名空间与「文件→块列表」，**块实际存在哪些 DataNode 是 NameNode 启动后由 DataNode 的块报告动态重建的**。因此刚启动、块报告没收齐时集群处于安全模式。正确写法：回答「元数据包含哪些内容」时，明确块位置映射是运行时态、非持久化，并由此推出安全模式的存在原因。

3. **三副本放置是「本地 + 同机架 + 跨机架」** —— 错。官方策略是：**第 1 副本在客户端本地节点，第 2 副本放在不同机架，第 3 副本放在与第 2 副本同机架的另一节点**。第 2 副本即已跨机架，这是兼顾容灾与写带宽的关键。正确写法：按《Hadoop 权威指南》原话背，别把顺序搞反；并说明为何不全放不同机架（避免写放大）。

4. **HDFS 写数据时客户端同时向三个 DataNode 各发一份** —— 错。HDFS 用**流水线（pipeline）**：客户端只发一份数据，沿 `dn1→dn2→dn3` 依次推送，ACK 原路返回。这样把客户端的写放大从 O(r) 降到 O(1)。正确写法：讲清 pipeline 的「单发多传」与 ACK 回传机制，以及节点失效时剔除并重选的容错流程。

5. **安全模式（Safe Mode）是一种故障/错误状态** —— 错。它是 NameNode 启动后的**保护态**：块位置映射未收齐前只读不写，直到满足最小副本比例的块数达到阈值才自动退出。长时间卡住通常是欠副本块过多（节点没起来/磁盘坏），应先排查而非盲目 `safemode leave`。正确写法：理解它是「数据完整性闸门」，离开需谨慎，避免丢数据。

6. **小文件在 HDFS 上只是『占不满一个块』的小事** —— 错。HDFS 的瓶颈在 NameNode 内存（每文件 ~150B 元数据）与任务/寻址膨胀；百万小文件会让 NameNode 内存暴涨且读放大严重。正确写法：用 HAR、HBase、或合并成 SequenceFile/ORC/Parquet 等列式大文件治理；MapReduce 输入小文件会「一文件一 map」。

7. **小文件直接 put 进 HDFS → NameNode 内存被吃干**
   ```bash
   hdfs dfs -put /logs/2026-10-31/*.log /warehouse/raw/    # 几十万个 10KB 小文件
   ```
   每个文件、每个块、每个副本在 NameNode 里约占 150 字节元数据。1000 万个 10KB 小文件（数据总量才 100GB）就要吃掉约 3GB 堆，DataNode 磁盘还很空，NameNode 先 OOM。
   ✅ 采集侧先 roll 成大文件，或入库后合并（HAR / SequenceFile / ORC）；Hive 用 `ALTER TABLE ... CONCATENATE`。

8. **副本因子调成 1 省空间，容错一起没了**
   `dfs.replication=1` 时任一 DataNode 掉线就直接丢块；机架感知也失效（默认 3 副本是「同机架 2 + 跨机架 1」，能扛整机架断电）。
   ✅ 生产保持 ≥3；冷数据改用 Erasure Coding（RS-6-3 把 3x 开销降到约 1.5x），代价是恢复时网络与 CPU 更高、且不支持 append。

9. **单 NameNode 且不做 checkpoint → editlog 无限增长、重启小时级**
   只部署一个 NameNode，又没有 SecondaryNameNode / Standby 定期合并 fsimage，`edits` 文件会一直涨。重启时要回放几个月的 editlog，启动时间从小秒级变成小时级。
   ✅ QJM + ZKFC 做 HA（Standby 自动 checkpoint），或至少部署 SecondaryNameNode 并监控 `Last checkpoint` 时间。
