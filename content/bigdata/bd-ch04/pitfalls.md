# Spark 核心：RDD 与惰性求值 易错点（高频踩坑与笔试面试易混口径）

1. **以为 transformation 会立即执行（忘了惰性求值）** —— 错。`map`/`filter`/`reduceByKey` 等 transformation **只记录操作、不触发计算**，只有 `collect`/`count`/`saveAsTextFile` 等 action 才真正跑。正确写法：需要触发计算时显式调用 action；别在 transformation 链里期待「马上看到结果」，调试用 `toDebugString` 看计划而非随手 `collect`。

2. **把 reduceByKey 当 groupByKey 用，导致 Shuffle 数据量爆炸** —— 错。`groupByKey` 把**全量记录**原样搬过网络再聚合；`reduceByKey` 先在 map 端做本地预聚合，只搬「key→局部聚合值」。正确写法：聚合优先 `reduceByKey`/`aggregateByKey`/`combineByKey`，map 端 combiner 能把 Shuffle 量从「总记录数」压到「不同 key 数」。

3. **在超大 key 上滥用 groupByKey** —— 错。groupByKey 不仅 Shuffle 量大，还在 reduce 端把同 key 全量记录拉进内存做迭代，极易 OOM 与倾斜。正确写法：可结合/可交换的聚合一律用 reduceByKey；不可结合的（如取 Top-N）用 `reduceByKey`+ 本地堆或 `aggregateByKey` 控制每 key 内存。

4. **缓存用错级别 / 物化后不释放** —— 错。`cache()` 默认 `MEMORY_ONLY`，数据放不下会频繁落盘或丢弃重算；长期不用的 RDD 不 `unpersist` 会一直占内存。正确写法：内存紧张用 `MEMORY_AND_DISK`；复用结束立即 `unpersist()`；只缓存「被多个 action 复用」的中间结果，而非一上来就缓存所有 RDD。

5. **以为 cache 后永远不重算** —— 错。缓存只保留 lineage，executor 丢失或缓存被 LRU 挤出后，未 checkpoint 的分区仍沿 lineage **重算**。正确写法：对 lineage 超长或重算代价高的 RDD 用 `checkpoint()` 斩断依赖；checkpoint 前先 `cache()` 避免重复全量计算。

6. **lineage 过长不截断，Driver OOM / 重算爆炸** —— 错。成百上千个 transformation 会让 DAG 图谱与重算代价失控。正确写法：在血缘关键节点 `checkpoint()` 截断；迭代算法（如 PageRank、图计算）每若干轮 checkpoint 一次。

7. **窄依赖 / 宽依赖判断错误，Stage 与 Task 数算错** —— 错。`map`/`filter`/`union`/`mapPartitions`/`coalesce`(默认) 是窄依赖；`reduceByKey`/`groupByKey`/`join`(非广播)/`distinct`/`sortBy`/`repartition` 是宽依赖（触发 Shuffle）。正确写法：Stage 以宽依赖+action 为界切分；Task 数 = 各 Stage 末态分区数之和，别把分区数和 Stage 数混为一谈。

8. **并行度 / 分区数设太小，Task 数不足、资源浪费** —— 错。分区数直接决定每个 Stage 的 Task 数；分区远小于总核数时大量核空闲。正确写法：设 `spark.default.parallelism` 与 `spark.sql.shuffle.partitions` 为集群总核的 2~3 倍；读 HDFS 时分区≈块数的合理倍数。

9. **数据倾斜靠「加大 Reduce 数」解决** —— 错。倾斜是少数热 key 碾压其余，加大 Reduce 只改变取模基数，热 key 仍压到同一个 Reduce（长尾卡 99%）。正确写法：先定位热 key（counters/UI）；小表侧用 BroadcastHashJoin 消 shuffle；大表自身热 key 用加盐 + 两阶段聚合或自定义 Partitioner；空值 `nvl`/单独处理。

10. **把重初始化（连接 / 大对象）放进 map** —— 错。`map` 逐元素调用，每行建一次 DB 连接或加载一次模型，开销爆炸。正确写法：用 `mapPartitions`（或 `foreachPartition`）在分区内建一次连接/加载一次模型，函数调用次数从「记录数」降到「分区数」。

11. **把 action 当 transformation 链式调用，导致重复计算** —— 错。`rdd.map().filter().collect().collect()` 这类写法会让整条血缘被触发两次。正确写法：需要多次使用同一结果时先 `cache()` 再多次 action；不要在一条语句里对未缓存 RDD 多次触发 action。

12. **忽视广播变量，大维度表 join 走全量 Shuffle** —— 错。小维度表未广播时 join 是宽依赖，全量 shuffle。正确写法：小表用 `broadcast()` 走 BroadcastHashJoin 变窄依赖，彻底消 shuffle；注意广播阈值（`spark.sql.autoBroadcastJoinThreshold`）。

13. **在 Driver 端 collect 超大结果集，导致 Driver OOM** —— 错。`collect()` 把所有分区数据拉回 Driver 单点，数据大必炸。正确写法：结果大时用 `saveAsTextFile`/写数仓；只取样用 `take`/`sample`；确需全量时在 executor 侧用 `foreach`/`mapPartitions` 处理。

14. **过度 repartition 制造无谓 Shuffle** —— 错。`repartition` 必触发一次宽依赖 + 全量 shuffle，只为调分区数却付出网络代价。正确写法：能用 `coalesce`（窄依赖合并、减少分区）就别用 `repartition`（增/减都 shuffle）；确要增多分区再考虑 repartition，且评估 shuffle 成本。
