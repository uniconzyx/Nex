# 一、AQE 自适应执行：用运行时统计纠正编译期误判

（中立陈述）**AQE（Adaptive Query Execution，Spark 3.0 引入、3.2 起默认开启）**的核心思想是：
优化器在**编译期**只能靠统计信息猜，而 Shuffle 之后我们能拿到**真实的分区大小**。
那就把执行切成若干轮：**先执行到某个 Shuffle 边界 → 看真实统计 → 重优化剩下的计划 → 继续执行**。
AQE 落地为三大能力：

1. **动态合并 Shuffle 分区（`CoalesceShufflePartitions`）**：
   Shuffle 后把大量小分区按目标大小（`spark.sql.adaptive.advisoryPartitionSizeInBytes`，默认 64MB）
   合并成少量合适分区。注意**只合并相邻分区**，不做全局重排；
2. **动态切换 JOIN 策略（`DynamicJoinSelection`）**：
   若运行时发现某侧真实大小远小于估计（例如经过过滤后只剩几 MB），
   就把已计划好的 `SortMergeJoin` 换成 `BroadcastHashJoin`，当场消掉一次 Shuffle；
3. **动态倾斜处理（`OptimizeSkewedJoin`）**：
   判定口径为「分区大小 > `skewedPartitionFactor`（默认 5）× 中位数
   **且** > `skewedPartitionThresholdInBytes`（默认 256MB）」，
   把倾斜分区**拆分**成多个子分区，并让另一侧对应分区复制，从而打散热 key。

实测（见 `examples/ex10.json`、`ex11.json`）：7 个分区 `[8,12,16,32,64,4,20]MB` 在目标 64MB 下
被合并为 3 个分区 `[68,64,24]MB`；而 `[70,80,90]MB` 因为都已达标，一个都不合并（正反两组判据都得证）。
倾斜检测在 `[1024,40,45,50,38,42,47]` 上算出倾斜度 22.76 并触发处理，`[50,48,52,49,51]` 上倾斜度 1.04 不触发。

### 🧑‍💻 程序员视角
- **先确认开关**：Spark 3.2+ 默认 `spark.sql.adaptive.enabled=true`。
  从旧版本升级后要**重新基准测试**，别把旧的 `shuffle.partitions=200` 参数原样搬过来；
- **看最终计划**：Spark UI 的 SQL 页里 `AdaptiveSparkPlan` 节点标注 `isFinalPlan=true` 才是最终形态；
  `explain` 在 AQE 下默认打印的是**初始计划**，这点和很多人想的不一样；
- **调参次序**：先把 `advisoryPartitionSizeInBytes` 调到 64~128MB（配合集群核数），
  再考虑 `skewedPartitionFactor`；不要一上来就把分区数写死；
- **AQE 不是万能**：它纠正不了**错误的统计信息导致的 join 顺序错误**（那是 CBO 的活），
  也救不了「在 Shuffle 之前就已经倾斜的输入」——倾斜若发生在 map 端读取阶段，AQE 无从感知。

### 🎓 博士生视角
- **信息论视角**：优化质量的上限取决于**信息量**。编译期只有估计统计（可能过期、可能缺失），
  运行时有真实行数。AQE 本质是**把优化时机从编译期推迟到信息更充分的执行期**——
  这是「延迟决策（late binding）」思想在查询优化上的应用，与数据库的
  adaptive/eddy 执行、以及 JIT 的「先解释后编译」异曲同工；
- **为什么只合并相邻分区**：Shuffle 分区的数据是按 key 的哈希**有序落盘**的，
  合并相邻分区意味着「连续读取一段文件」，代价是一次顺序 I/O；
  若允许跨分区全局重排，就要再走一次 Shuffle，得不偿失——这是**收益/代价的边界**；
- **重优化的终止性**：AQE 在每一个 Shuffle 边界都可能重优化一次，
  计划树会随执行推进不断「长出新形态」。为保证终止，重优化机会被限制在
  「尚未执行的子树」上，已执行的物化结果不再改动。

### 📚 考研者视角
- **标准问法**：「AQE 是什么？解决什么问题？」→ 自适应执行：在 Shuffle 之后用**真实统计**
  重新优化剩余计划，解决「编译期统计不准导致分区数不合理 / join 策略选错 / 倾斜未处理」三个问题；
- **必背三条能力**：动态合并小分区、动态切换 join 策略（SMJ → BHJ）、动态倾斜处理（拆分倾斜分区）；
- **必背两个默认值**：倾斜判定 `factor=5`、`threshold=256MB`；
  目标分区大小 `advisoryPartitionSizeInBytes=64MB`；
- **易错口径**：AQE 处理倾斜的手段是**拆分倾斜分区并复制另一侧**，
  不是「加盐」——加盐是用户侧的 SQL 改写技巧，两者别混。

---

# 二、宽依赖 / 窄依赖与 Shuffle 边界

（中立陈述）沿用 bd-ch04 的定义：**窄依赖** = 一个父分区只被子分区中的一个使用
（`map`/`filter`/`union`/`coalesce`），可以 pipeline 进同一个 Stage；
**宽依赖** = 一个父分区被多个子分区使用（`join`/`groupByKey`/`reduceByKey`/`distinct`/
`sortBy`/`repartition`），必须 Shuffle。

对于 Spark SQL，判定更直接：**物理计划里每出现一个 `Exchange`，就是一次 Shuffle，就是一个 Stage 边界**。
`Scan → Filter → Project → BroadcastExchange → BroadcastHashJoin → HashAggregate → Exchange → SortAggregate`
这条链里有两个 `Exchange`，因此被切成 3 个 Stage。

实测（见 `examples/ex09.json`）：算子序列
`map → filter → join → map → reduceByKey → filter → sortBy → map` 被切成 **4 个 Stage**、
发生 **3 次 Shuffle**，且满足「Shuffle 次数 = 宽依赖算子数」「Stage 数 = Shuffle 次数 + 1」两个判据。

### 🧑‍💻 程序员视角
- **数 `Exchange` 是第一步**：拿到 `explain(mode="formatted")` 先数 `Exchange` 的个数，
  那就是 Shuffle 次数，也是主要开销来源；
- **消 Shuffle 的三板斧**：① 小表广播（BHJ，把宽依赖变窄依赖）；
  ② 预聚合（`reduceByKey` / `partial_sum`，把 Shuffle 量从「记录数」压到「key 数」）；
  ③ 分桶表 join（同 bucket 数可避免 Shuffle）；
- **分区数口径**：`spark.sql.shuffle.partitions` 决定 Shuffle 后的分区数，
  它直接等于下游 Stage 的 Task 数；配合 AQE 时可以调大初始值让 AQE 去合并；
- **广播的代价**：广播把小表物化到 Driver 再分发到每个 Executor，
  小表过大就 Driver OOM。别把 `autoBroadcastJoinThreshold` 调成几百 MB。

### 🎓 博士生视角
- **Shuffle 的代价分解**：一次 Shuffle = map 端分区排序 + 落盘
  + 网络拉取（N×M 的连接）+ reduce 端归并排序 + 可能的外排（spill）。
  它是 **O(数据量) 的磁盘 I/O + O(N×M) 的网络连接**，所以在分布式查询优化里
  「减少 Shuffle 次数」与「减少 Shuffle 数据量」是两条独立且都重要的主线；
- **宽依赖为何必然 Shuffle**：宽依赖的语义要求「同 key 的数据汇聚到同一分区」，
  而数据在物理上分散在不同节点的分区里，只能通过**按 key 重新分布**满足——
  这不是实现选择，是**语义蕴含的物理必要性**；
- **广播为何能消除 Shuffle**：广播把小表复制到每个节点，
  使「按 key 汇聚」退化为「本地哈希查找」，把网络 Shuffle 换成
  O(小表大小 × 节点数) 的广播——当小表足够小时，后者更便宜。这是**代价比较**而非绝对优劣。

### 📚 考研者视角
- **标准问法**：「什么是宽依赖和窄依赖？」→ 窄依赖：父分区只被一个子分区使用，可 pipeline；
  宽依赖：父分区被多个子分区使用，必须 Shuffle；
- **必背结论**：**Stage 以宽依赖为界划分**；**Shuffle 次数 = 宽依赖算子个数**；
  **Task 数 = 各 Stage 末态分区数之和**；
- **易错**：`coalesce`（减少分区、窄依赖）与 `repartition`（增减分区都 Shuffle、宽依赖）别搞反；
  `join` 若走广播则**不算**宽依赖。

---

# 三、执行计划读法与 Hive Metastore 集成

（中立陈述）**读计划的固定顺序**：① 找所有 `Scan`（读了哪些表、哪些列、估计多少行）；
② 数 `Exchange`（= Shuffle 次数 = Stage 边界）；③ 看 `*Join` 的类型与 build 侧；
④ 看 `Aggregate` 是 `Hash` 还是 `Sort`、有没有 `partial_`（map 端预聚合）。
读的方向是**自底向上**（叶子是数据源，根是输出）。

**与 Hive Metastore 的集成**：Spark SQL 通过 `spark.sql.catalogImplementation=hive`
加上 `hive.metastore.uris` 连接 Hive Metastore，从而复用 Hive 里已有的库表元数据
（schema、分区、存储格式、Location、SerDe）。也就是说：

- Spark 从 Metastore 拿到的**只是元数据**，真实数据仍按 `Location` 指向的 HDFS/S3 路径读取；
- Metastore 里的表既可以是 Hive 建的，也可以是 Spark 建的（Spark 建的表同样登记进 Metastore）；
- **统计信息也走 Metastore**：`ANALYZE TABLE` 算出的行数与 `sizeInBytes` 会写回 Metastore，
  供 CBO 与广播判断使用。

**分区登记制**：直接往分区目录 `hdfs dfs -put` 文件**不会**自动登记分区，
需要 `MSCK REPAIR TABLE` 或 `ALTER TABLE ADD PARTITION`，Spark 侧也可用
`REFRESH TABLE` / `spark.catalog.refreshTable` 刷新缓存的元数据。

### 🧑‍💻 程序员视角
- **读计划的顺序别搞反**：很多人从上往下读，结果先看到 `Output` 一头雾水；
  记住「叶子是数据，根是结果」，自底向上才是执行顺序；
- **集成排障**：`SHOW TABLES` 能列出 ≠ 能读。用 `DESCRIBE FORMATTED t` 看
  `Location` 与 `InputFormat`，再验证 Spark（而非 Hive）对该路径有读权限、SerDe 依赖在 classpath 上；
- **新分区读不到的第一反应**：先 `MSCK REPAIR TABLE` / `REFRESH TABLE`，再查权限，最后才怀疑 Spark 缓存；
- **统计信息**：写入作业结束后补一条 `ANALYZE TABLE`，让下游 join 能走 CBO；
  大表按分区增量 `ANALYZE TABLE t PARTITION(dt) COMPUTE STATISTICS`，别全表重算。

### 🎓 博士生视角
- **元数据与数据分离的意义**：Metastore 只存「数据的描述」，
  使同一份物理数据可以被 Spark、Hive、Presto、Flink 等多个引擎共享——
  这正是**数据湖（data lake）**架构的基础：存储层（对象存储/ HDFS）
  + 文件格式层（Parquet/ORC）+ 元数据层（Metastore）+ 引擎层（多引擎），四层解耦；
- **为什么分区要「登记」**：分区是**目录约定 + 元数据记录**的双重产物。
  文件系统只看见目录，语义（该目录对应 `dt=2026-01-01`）必须由元数据层显式记录，
  否则引擎只能全目录扫描。这是「约定 vs 声明」的取舍：Hive 选择显式声明以换取分区裁剪能力；
- **统计信息的时效性**：统计数据是**快照**，会随写入而过期。
  CBO 的全部结论都建立在统计之上，因此「统计新鲜度」是 CBO 可用性的硬约束——
  这也是为什么自动化的数据平台要把 `ANALYZE` 作为写入流水线的固定一步。

### 📚 考研者视角
- **标准问法**：「Spark 怎么读 Hive 的表？」→ 通过 Hive Metastore 拿元数据
  （`spark.sql.catalogImplementation=hive` + `hive.metastore.uris`），
  数据按 Location 直接从 HDFS/S3 读；元数据与数据是分离的；
- **高频追问**：「为什么新写入的分区读不到？」→ 分区是登记制，
  需要 `MSCK REPAIR TABLE` / `ALTER TABLE ADD PARTITION` / `REFRESH TABLE`；
- **概念辨析**：**Metastore 存元数据（schema + 分区 + Location），不存数据**；
  **内部表 vs 外部表**的区别在 `DROP TABLE` 时是否删除数据——这条与 bd-ch03 的 Hive 考点是同一口径。

---

## 三视角小结

| 主题 | 程序员关注 | 博士生关注 | 考研/笔试口径 |
|---|---|---|---|
| AQE 自适应执行 | 确认开关、`isFinalPlan`、先调目标分区大小 | 延迟决策、只合并相邻分区的原因、重优化终止性 | 三条能力 + 三个默认值（5 / 256MB / 64MB） |
| 宽窄依赖与 Shuffle | 数 `Exchange`、消 Shuffle 三板斧 | Shuffle 代价分解、宽依赖的物理必然性 | Stage 以宽依赖为界；Task 数 = 分区数之和 |
| 计划读法与 Metastore | 自底向上读、`MSCK REPAIR`、ANALYZE | 四层解耦的数据湖、登记制、统计新鲜度 | Metastore 只存元数据；分区需显式登记 |
