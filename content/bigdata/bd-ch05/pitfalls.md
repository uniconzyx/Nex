# Spark SQL、DataFrame 与 Catalyst 易错点（高频踩坑与笔面易混口径）

1. **以为 DataFrame 的 `filter`/`select` 会立刻执行** —— 错。DataFrame 与 RDD 一样是**惰性**的：transformation 只往逻辑计划里挂节点，只有 `show`/`collect`/`count`/`write` 等 action 才触发。正确写法：调试用 `df.explain()` 看计划，别在链式调用中间插 `print(df.count())` 之类的 action，那会**重复触发整条计划**。

2. **把 RDD 的 `map(lambda ...)` 习惯带进 DataFrame，用 UDF 包一切** —— 错。lambda / Python UDF 对 Catalyst 是**黑盒**：无法谓词下推、无法列裁剪、还要付出 JVM ↔ Python 的序列化往返。正确写法：优先用内置函数（`when/col/upper/substring` 等）；必须用 UDF 时优先 Scala/Java UDF 或 Pandas UDF（向量化），并把它放在计划的**最后**以减少输入行数。

3. **以为谓词下推一定会发生** —— 错。两条硬约束任一不满足就不下推：① 谓词必须**确定性**（含 `rand()`、`current_timestamp()` 的谓词不下推，因为下推会改变每行求值次数）；② 谓词引用的列必须在下方算子的输出列中（写在 `Project` 之后的过滤列若已被投影掉，则推不下去）。正确写法：把过滤尽量贴着数据源写，别先 `select` 掉过滤列再 `filter`。

4. **把 `where` 写在子查询/视图之外，指望优化器救你** —— 错。Catalyst 确实会做谓词下推，但**跨聚合（`GROUP BY`/`DISTINCT`）、跨 `LIMIT`、跨窗口函数**的谓词下推受限，且一旦中间有 UDF、非确定性表达式或 `outer join` 的 null 侧，下推链就会断。正确写法：过滤条件尽量写在最靠近数据源的那一层；`LEFT JOIN` 里对右表的过滤条件写在 `ON` 后与写在 `WHERE` 后**语义不同**（后者会把外连接退化成内连接）。

5. **`SELECT *` 导致列裁剪完全失效** —— 错。Catalyst 的列裁剪依赖「顶层真正需要哪些列」自顶向下传播；`SELECT *` 使所有列都被标记为需要，Parquet 的向量化读就退化成全列读取。正确写法：只写需要的列；中间层视图也别 `SELECT *`。

6. **以为分区裁剪自动生效** —— 错。**分区裁剪（Partition Pruning）只对分区列生效**，且要求过滤条件是「分区列 与 常量」的直接比较；`dt = substr(other_col,1,10)`、`dt + 1 = '20260101'` 这类**对分区列做了变换**的写法会让裁剪失效（Catalyst 无法反解）。正确写法：过滤条件写成 `dt = '2026-01-01'` 或 `dt BETWEEN ...`，别对分区列套函数。

7. **用 `explain()` 默认模式看计划，看不到关键细节** —— 错。`df.explain()` 默认只打印物理计划（且无格式化缩进），看不出逻辑计划优化前后的差异，也看不出 `sizeInBytes` 统计。正确写法：`df.explain(mode="formatted")` 看缩进树；`mode="extended"` 看 Parsed / Analyzed / Optimized / Physical 四份计划；`mode="cost"` 看统计与代价。

8. **读计划从上往下读** —— 错。执行计划树**叶子是数据源、根是输出**，物理执行自底向上。正确读法：① 先找所有 `Scan`（读了哪些表、哪些列、多少行）；② 看 `Exchange`（= 一次 Shuffle，是 Stage 边界）；③ 看 `*Join` 的类型与 build 侧；④ 最后看 `Aggregate` 与输出。

9. **把 `Exchange` 当成可有可无的一行** —— 错。计划里每出现一个 `Exchange` 就代表**一次 Shuffle**（落盘 + 网络 + 排序），是作业的主要开销来源与 Stage 分界线。正确写法：数一数 `Exchange` 的个数；能消掉的用广播 join 或bucket join；`shuffle.partitions` 别用默认 200 硬套超大或超小数据量。

10. **关掉 AQE 或不知道 AQE 已默认开启** —— 错。Spark 3.2+ 默认 `spark.sql.adaptive.enabled=true`，它会在运行时**动态合并小分区、动态把 SortMergeJoin 换成 BroadcastHashJoin、动态拆分倾斜分区**。正确写法：升级后重新基准测试，别沿用旧参数；排查时先确认 `spark.sql.adaptive.enabled`，再看 Spark UI 的 `AdaptiveSparkPlan` 节点（`isFinalPlan=true` 才是最终计划）。

11. **`spark.sql.shuffle.partitions=200` 一把梭** —— 错。200 是「没有 AQE 时」的通用默认：小数据产生 200 个空任务，大数据每个分区过大导致 OOM 或 spill。正确写法：按 shuffle 数据量 / 目标分区大小（默认 64MB）估算，或直接交给 AQE 动态合并（把 `advisoryPartitionSizeInBytes` 调到 64~128MB）。

12. **广播 join 不生效，却只盯 `autoBroadcastJoinThreshold`** —— 错。触发广播有三个前置条件：① 是**等值**连接；② 小表**统计大小** `sizeInBytes <= 阈值`（默认 10MB）；③ 该统计**存在**。若表没有 `ANALYZE TABLE` 或统计过期，`sizeInBytes` 为缺省值/巨大值，就不广播。正确写法：`ANALYZE TABLE t COMPUTE STATISTICS`，或用 `/*+ BROADCAST(t) */` hint 强制；同时确认 join 是等值连接。

13. **无脑把 `autoBroadcastJoinThreshold` 调到很大** —— 错。广播表会**先在 Driver 端物化成 HashedRelation 再分发到每个 Executor**，表一大就 Driver OOM 或广播超时。正确写法：阈值调到 100MB 以内通常安全；超大维度表改用 bucket join 或 map-side 预聚合；广播前确认小表经过**列裁剪 + 谓词下推**后才被统计（Spark 统计的是优化后计划的 sizeInBytes，这点是它对你的隐性帮助）。

14. **数据倾斜只靠加 `repartition` 或加大 reduce 数** —— 错。倾斜的根因是**少数 key 的记录数碾压其余**，哈希分区下热 key 永远落到同一个分区，加大分区数只改变取模基数。正确写法：先量化（最大分区 / 中位数 > 5 且 > 256MB 即为倾斜分区）；能广播就广播；大表热 key 用**加盐两阶段聚合**；或开 AQE 的 `skewJoin` 让 Spark 自动拆分倾斜分区。

15. **Dataset 的 `map`/`flatMap` 以为还是「强类型零成本」** —— 错。Dataset 的类型安全靠 **Encoder** 在「JVM 对象 ↔ 内部二进制行」之间转换；一旦用 `map` 做逐行对象操作，就退出 Tungsten 的紧凑表示（反序列化 → 操作 → 再序列化），丢掉代码生成与堆外布局的收益。正确写法：能用列表达式就用列表达式；确需强类型逻辑时接受这一层成本，并把它放在数据量已经很小的阶段。

16. **以为 `Dataset[Person]` 的编译期检查能防住所有错误** —— 错。Dataset 只保证**类型**正确；列名、聚合函数、表是否存在等仍在**分析（Analysis）阶段**才解析，运行前照样可能抛 `AnalysisException`。正确写法：别把 Dataset 当「SQL 免检牌」，列名写错仍然报错；用 `spark.sql("...")` 时该校验的还是要校验。

17. **不做 `ANALYZE TABLE`，却抱怨 CBO 选错 join 顺序** —— 错。CBO（Cost-Based Optimization）的输入是**表与列的统计信息**（行数、sizeInBytes、直方图、列 distinct 数）；没有统计就退回启发式（按 sizeInBytes 排序、左深树）。正确写法：对参与多表 join 的事实表定期 `ANALYZE TABLE ... COMPUTE STATISTICS FOR COLUMNS`；数据大幅变化后重算。

18. **与 Hive Metastore 集成时以为「看到表 = 能用」** —— 错。Spark 通过 `spark.sql.catalogImplementation=hive` + `hive.metastore.uris` 连 Metastore 只拿到**元数据**；真实数据要 Spark 能访问其 HDFS/S3 路径，且 SerDe、输入格式、权限都要对得上。正确写法：`spark.sql("SHOW TABLES")` 能列出 ≠ 能读；先 `DESCRIBE FORMATTED` 看 Location 与 InputFormat，再验证 Spark 有该路径读权限。

19. **在 Hive 里建的表，Spark 读不到新写入的分区** —— 错。Metastore 里的分区元数据是**登记制**：直接往分区目录 `hdfs dfs -put` 文件不会自动登记分区。正确写法：写完后 `MSCK REPAIR TABLE t` 或 `ALTER TABLE t ADD PARTITION (...)`；Spark 侧也可 `spark.catalog.refreshTable("t")` / `REFRESH TABLE`。

20. **把 `cache()` 当 Spark SQL 的万能提速键** —— 错。缓存的是**物理计划物化结果**，但 Spark SQL 的 `InMemoryRelation` 以列式压缩块存储，若后续查询用到的列很少却缓存了全表，反而占内存；且缓存命中依赖计划完全匹配。正确写法：先 `explain` 确认缓存被复用；大宽表缓存前先 `select` 出需要的列；用完 `uncacheTable`。
