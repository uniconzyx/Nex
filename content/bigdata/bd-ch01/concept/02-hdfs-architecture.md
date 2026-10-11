# 一、NameNode 元数据与命名空间（文件系统的大脑）

（中立陈述）NameNode 是 HDFS 的**元数据管理者**，不存储实际文件数据，只保存「目录树 + 每个文件的块列表 + 每块存在哪些 DataNode」。它内存中维护 `fsimage`（命名空间的检查点快照）和 `edits`（增量操作日志），DataNode 启动时把「我有哪些块」汇报给 NameNode（块报告）。客户端读写都先向 NameNode 询问「块在哪」，再去对应 DataNode 搬数据。

### 🧑‍💻 程序员视角
- 内存约束：NameNode 是**内存瓶颈型**组件——每个文件/目录/块约 150B 元数据，1 亿文件就要 ~15GB 堆；生产用大堆 + 监控，且对小文件零容忍。
- 高可用：务必配 **HA（Active/Standby + QJM 日志同步 + ZKFC 自动切换）**，否则 NameNode 单点挂掉等于整个集群「脑死亡」。
- 运维命令：`hdfs dfsadmin -report` 看集群容量与块健康；`hdfs fsck /` 检查块丢失/欠副本；不要把 NameNode 和重负载 DataNode 混布，避免 GC 拖慢心跳处理。

### 🎓 博士生视角
- 抽象分层：HDFS 复用 UNIX 的「**路径名 → inode → 数据块**」三层解耦思想。NameNode 的 INode 相当于 inode，Block 相当于数据块指针；区别是 HDFS 的「inode」里存的是**块 ID 列表**而非直接/间接物理块指针，因为块物理位置由 DataNode 动态汇报，而非写死在元数据。
- 持久化与性能：若每次写都落盘 fsimage，随机写元数据会极慢；因此写操作只**顺序追加到 edits log**（顺序写快），fsimage 由 checkpoint 周期性合并——这是「**WAL（写前日志）+ 周期性快照**」的经典存储模式，与 LSM-Tree、数据库 redo log 同源。
- 一致性边界：edits 未合并进 fsimage 前，崩溃恢复靠「重放 edits」；这隐含一个窗口：Standby 必须实时拉取 edits 才能在切换时拿到最新状态（QJM 保证 edits 不丢）。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「NameNode 存什么、不存什么？」标准答：存**命名空间、文件到块的映射、块到 DataNode 的映射（运行时）**；**不存文件真实数据**，数据在 DataNode。
- 易错口径：常有人把「块到 DataNode 的映射」误以为持久化在 fsimage——实际它**不在 fsimage 里**，而是 NameNode 启动后由 DataNode 的块报告动态重建（所以刚启动、块报告未收齐时集群进入安全模式）。
- 对比考点：NameNode 之于 HDFS，相当于「目录服务器」之于对象存储；与 GFS 的 Master 角色一一对应，是分布式存储「中心元数据 + 去中心数据」范式的标准答案。

---

# 二、DataNode 与块存储（真正搬砖的劳工）

（中立陈述）DataNode 在本地磁盘以**块（block）文件 + 校验和（meta）文件**的形式存储数据；它周期性向 NameNode 发送**心跳（默认 3s）**与**块报告（默认 6h，增量更频繁）**；收到 NameNode 的指令（复制、删除、恢复）后执行。客户端读写直接与 DataNode 交互，NameNode 只做「指路」。

### 🧑‍💻 程序员视角
- 磁盘规划：DataNode 的 `dfs.datanode.data.dir` 常配多块盘（逗号分隔），HDFS 用**轮询/可用空间**策略把块分散到各盘，避免单盘热点；某盘满了会被标记，新块不再写入但旧块仍在。
- 故障处理：DataNode 心跳超时（默认 10 次×3s = 30s 判死），NameNode 将其上的欠副本块重新复制到其他节点；运维上「直接拔盘」要先 `decommission`（退役）让副本安全迁出。
- 校验和：读取时会校验 `blk_*.meta` 的 CRC，发现损坏块会向 NameNode 报「坏块」并触发从其他副本恢复——这是 HDFS 静默数据损坏防护。

### 🎓 博士生视角
- 存储布局：每个块在磁盘上是「`blk_<id>`（数据）+ `blk_<id>_*.meta`（校验和，按 512B 一个校验单元）」；后台 `DirectoryScanner` 周期性扫描，把磁盘真实状态与内存声明对账，发现「内存说有、磁盘没有」的块就上报。
- 心跳协议的状态机：DataNode 的心跳不仅是「我还活着」，更是 **NameNode → DataNode 的指令通道**（block command）。这是一种**拉模型（pull）**——DataNode 主动来取任务，避免 NameNode 维护海量长连接推送，扩展性更好。
- 副本恢复的数学：设某块应有 r 副本、当前 k 副本（k<r），NameNode 选 `r-k` 个目标节点，源副本用**流水线**把数据推过去（见 04 章），恢复并行度受网络与节点负载约束。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「DataNode 宕机，HDFS 如何保证数据不丢？」标准答：数据以**多副本**存放在不同节点；某 DataNode 心跳超时后，NameNode 检测其上的**欠副本块**并调度其他 DataNode 从现存副本复制补足到设定副本数。
- 易错口径：不要说「NameNode 立刻复制」——准确说法是**心跳超时判定死亡后，再调度复制**；也不要说「DataNode 自己复制」，复制由 NameNode 协调。
- 关联考点：心跳机制是分布式「故障检测」的基础，常与 ZooKeeper 的会话超时、GFS 的 chunk server 心跳一起被 comparative 提问。
