# 一、副本放置策略与机架感知（rack awareness）

（中立陈述）HDFS 默认副本因子为 3，放置规则为：**第 1 副本放在客户端所在节点（或随机节点）；第 2 副本放在「不同机架」的节点；第 3 副本放在「与第 2 副本同机架但不同节点」**。机架感知依赖管理员配置的 `rack topology`（网络位置脚本），使 NameNode 知道每个 DataNode 属于哪个机架（如 `/rack1/dn1`）。

### 🧑‍💻 程序员视角
- 配置坑：没配机架感知时，所有节点被当成同一机架（`/default-rack`），副本会「同机架三份」，一旦该机架交换机故障，三副本全灭——**跨机架容灾形同虚设**。
- 写放大：机架感知让「1 本地 + 2 跨机架/同机架」在「容灾」与「写带宽」间折中：跨机架只 1 跳（第 2 副本），其余在同机架内，避免每次写都跨机架两次。
- 调优：跨区域（跨 AZ）部署时用 `Block Placement Policy` 自定义；冷热分层可用 `Storage Policy`（SSD/ARCHIVE）让副本按策略落不同介质。

### 🎓 博士生视角
- 容灾的拓扑约束：设机架故障独立、机架内节点故障相关（共交换机/供电）。放置 `本地 + 跨机架 + 同第2机架` 等价于「**保证任意单机架故障不丢数据，且任意两副本不共机架**」，在 r=3 下是最优的故障域隔离方案。
- 写路径的带宽成本：若三副本全跨机架需 2 次跨机架传输，聚合写放大高；本策略把跨机架限制为 1 次（第1→第2），第2→第3 在同机架，把「容灾收益 / 网络代价」压到最优比。
- 形式化：放置本质是约束满足——`loc(i) ≠ loc(j)` 当 i,j 在不同故障域层级；机架感知就是把「节点」映射进「树状拓扑」再据此剪枝候选节点。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「HDFS 三副本怎么放？」标准答：**第1副本在客户端本地节点；第2副本放在不同机架的节点；第3副本放在与第2同机架的另一节点**（经典原话）。也常被问「为何不全放不同机架」——答：兼顾容灾与写带宽。
- 易错口径：有人背成「1 本地、2 同机架、3 跨机架」——这是**错误**的，正确是第 2 副本即跨机架。考试/面试按官方《Hadoop 权威指南》口径答。
- 关联考点：机架感知常与「故障域（fault domain）」「副本策略与 EC 纠删码对比」一起考，要能说明 3 副本 vs 纠删码在存储成本与恢复带宽上的取舍。

---

# 二、fsimage / edits 与 checkpoint（安全模式）

（中立陈述）NameNode 启动时先加载 `fsimage`（命名空间快照），再重放 `edits`（增量日志）得到最新状态。随运行 edits 越来越大，**Secondary NameNode（或 Standby 的 Checkpointer）** 周期性把「旧 fsimage + 新 edits」合并成新 fsimage（checkpoint），避免 edits 无限增长。刚启动时，由于**块到 DataNode 的映射尚未从块报告收齐**，集群进入**安全模式（safe mode）**——只读不写，直到满足条件的块比例达标才自动退出。

### 🧑‍💻 程序员视角
- 致命误区：Secondary NameNode **不是 NameNode 的热备**！它只做 checkpoint，NameNode 挂了它不能顶上（HA 才是热备，靠 QJM + Standby）。很多人被名字误导。
- 安全模式卡住：集群重启后长时间「Safe mode is ON」，通常是**欠副本块过多**（如磁盘损坏、节点没起来），用 `hdfs dfsadmin -safemode get` 看，必要时 `hdfs dfsadmin -safemode leave`（强制离开有丢数据风险，先排查）。
- 调优参数：`dfs.namenode.safemode.threshold-pct`（默认 0.999）控制「多少比例的块满足最小副本数才退出」；`dfs.namenode.checkpoint.period` 控制 checkpoint 周期。

### 🎓 博士生视角
- 快照 + 日志的不变式：fsimage 是状态 `S` 的持久化；edits 是 `Δ1..Δn`；checkpoint 计算 `S' = apply(S, Δ1..Δn)`。这保证「**崩溃恢复 = 加载最近 fsimage + 重放其后 edits**」，重放代价随 checkpoint 频率降低——是 WAL 系统的标准不变式。
- 安全模式的收敛证明：设总块数 N，已汇报且达最小副本的块数 M(t) 随 DataNode 块报告单调不减；当 `M(t)/N ≥ p`（阈值）时退出。由于块报告最终覆盖全量，若集群健康则 `M(t)→N`，安全模式必然终止；不健康则永不达阈值——这正是它作为「数据完整性闸门」的意义。
- 与 LSM 的关系：edits+fsimage 等同于 LSM-Tree 的 WAL + SSTable compaction；checkpoint = minor/major compaction，思想同源。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「fsimage 和 edits 有什么区别？checkpoint 做什么？」标准答：fsimage 是**命名空间全量快照**，edits 是**操作增量日志**；checkpoint 由 Secondary NameNode 把二者合并生成新 fsimage，防止 edits 过大、启动重放过慢。
- 易错口径：① Secondary NameNode ≠ 备份/热备（高频错题）；② 安全模式**不是错误状态**而是保护态，期间只读；③ 块到 DataNode 映射**不存 fsimage**，靠启动时块报告重建——这点极易错。
- 关联考点：常把 checkpoint 与「数据库检查点」「Redis AOF 重写」类比，能说出「快照 + 日志重放」的统一范式是加分项。
