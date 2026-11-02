# Spark 实战手记：凯喵的十二次「跑了一夜还在 Shuffle」复盘

> 这一篇来自凯喵把一个 Hive SQL 迁移到 Spark 的过程。作业从「跑 40 分钟」到「跑 4 小时」，中间炸了十二次：Executor OOM、Shuffle 落盘 800GB、某个 Task 卡在 99%、以及最后发现结果根本不对。每一次都指向 RDD 执行模型里的一个具体机制。这篇按「血缘 → 惰性 → Stage → 调优」的顺序还原。

## 开场：为什么 Spark 比 MapReduce 快，又为什么有时候更慢

教科书答案是「内存计算」。凯喵第一次听到这话时以为 Spark 不落盘，后来发现 Shuffle 阶段照样落盘，而且落得比 MapReduce 还猛。

真正的原因是三条叠加：**DAG 调度让多个窄依赖算子融合成一个 Stage，避免中间结果落盘**；**惰性求值让优化器看到完整计划后才决定怎么执行**；**内存缓存让多次复用的数据集不必重算**。这三条都成立时，Spark 快一个数量级；任何一条被破坏，性能就退回甚至不如 MapReduce。

理解这个前提，后面十二个现场就都能归位了——它们几乎全是「不小心破坏了这三条中的某一条」。

### 现场一：RDD 的五大特性，只有第一个是真抽象

RDD 的五大特性：分区列表、计算函数、依赖列表、分区器（可选）、优先位置列表（可选）。凯喵背了很久才明白，其中真正决定行为的是**依赖列表**和**分区器**这两条。

依赖决定容错方式和 Stage 划分；分区器决定 Shuffle 时数据往哪个分区走。分区列表和计算函数是「怎么算」，优先位置是「在哪算」——后者是调度优化，前者是数据布局。

```scala
// 从并行集合创建：分区数和优先位置都由本地决定
val rdd = sc.parallelize(1 to 1000, numSlices = 8)

// 从 HDFS 创建：优先位置来自文件块所在节点
val logs = sc.textFile("hdfs:///logs/2026-11-01/*.log")

// 关键：分区数决定了后续 task 的并行度
println(logs.getNumPartitions)
```

凯喵的体会是：**把这五条当成五个「可调参数」来理解，比当成五个「定义」有用得多**。分区数影响并行度、依赖影响 Stage、分区器影响 Shuffle 的数据分布，每一条都直接对应一个调优旋钮。

### 现场二：不可变 + 血缘，是容错方案不是限制

RDD 不可变，任何 transformation 都产生新 RDD。这在写代码时很别扭（不能原地改），但它是容错的根基：**某个分区丢了，只要重放它的血缘链就能重算**，不需要副本。

这和 HDFS 的思路完全不同。HDFS 用「存三份」换容错，代价是三倍存储；Spark 用「记住怎么算」换容错，代价是重算时间。所以 RDD 适合「计算便宜、数据量大」的场景，不适合「计算极贵」的场景——后者要靠 checkpoint 把血缘截断。

```scala
val base = sc.textFile("hdfs:///logs").filter(_.nonEmpty)
val parsed = base.map(parseLine)          // 血缘：base → parsed
val agg = parsed.map(r => (r.userId, 1)).reduceByKey(_ + _)

// 血缘链：textFile → filter → map → map → reduceByKey
// agg 的分区丢了，会重放整条链
```

凯喵踩过的坑是：血缘链太长时（几百个 transformation），一次失败重算要几分钟。这时候必须 checkpoint，把链条截断。

### 现场三：惰性求值不是「延迟执行」，是「延迟到看见全貌」

Transformation 不触发计算，Action 才触发。这条人人都知道，但真正的价值在于：**因为没执行，优化器才能看到完整计划并重写它**。

比如连续三个 `map` 会被融合成一个 Stage，中间不产生数据落盘；`filter` 会被下推到数据源，减少读入量。这些优化只有在「先看到全部再决定怎么跑」的前提下才可能。

```scala
val r = sc.textFile("hdfs:///big")     // 什么都不发生
  .filter(_.contains("ERROR"))          // 什么都不发生
  .map(_.split("\t")(0))                // 什么都不发生
// 直到这一行才真正开始跑
r.count()
```

凯喵遇到的坑是反过来的：有人在循环里对同一个 RDD 反复调用 `count()` 做「进度显示」，结果每次都完整重算一遍整条链，作业跑了六小时。**惰性求值的另一面是：不缓存就会重算**。

### 现场四：窄依赖与宽依赖，判定标准是「父分区被几个子分区使用」

窄依赖：一个父分区最多被一个子分区使用（`map`、`filter`、`union`、`coalesce`）。宽依赖：一个父分区被多个子分区使用（`groupByKey`、`reduceByKey`、`join`、`repartition`）。

这个判定标准很机械，但它决定了三件事：能否流水线执行（窄依赖可以，父分区算完直接喂给子分区）、失败重算的代价（窄依赖只重算对应分区，宽依赖可能要重算多个父分区）、以及 Stage 的边界（宽依赖必然切 Stage）。

```scala
val a = sc.parallelize(1 to 100, 4)
val b = a.map(_ * 2)          // 窄依赖：一对一
val c = a.filter(_ % 2 == 0)  // 窄依赖：一对零或一
val d = a.map(x => (x % 3, x)).groupByKey()  // 宽依赖：多对多
```

凯喵的记法：**看输出分区是否需要「跨分区聚合」，需要就是宽依赖**。所有 `ByKey` 操作、所有 `join`、所有 `repartition` 都是宽的，因为它们的语义就是「把相同 key 的数据聚到一起」。

### 现场五：Stage 以宽依赖为界，Task 数等于分区数

一个 Job 被切分成若干 Stage，切分点就是宽依赖。每个 Stage 内部是一串窄依赖，可以流水线执行；Stage 之间要通过 Shuffle 交换数据。

Stage 里的 Task 数 = 该 Stage 最后一个 RDD 的分区数。这个等式非常重要，因为它解释了「为什么调分区数就是调并行度」。

```text
Job
├─ Stage 0（读文件 → filter → map）      16 tasks
│     ↓ Shuffle（reduceByKey）
└─ Stage 1（聚合 → 输出）                8 tasks
```

凯喵遇到「某个 Task 卡在 99%」时，第一反应就是看这个 Stage 的分区数：如果只有 8 个分区却有 800GB 数据，那每个 Task 要处理 100GB，当然卡。修法是提前 `repartition` 到更多分区，让每个 Task 的数据量降到合理范围。

### 现场六：reduceByKey 与 groupByKey，差的不只是性能

这两个算子的语义看起来一样（都是按 key 分组），但执行方式完全不同。

`groupByKey` 会把同一个 key 的所有 value 原样搬到一起，形成一个迭代器；`reduceByKey` 会在 map 端先做一次局部聚合（combiner），只把聚合结果传过去。

```scala
// 坏：所有 value 都要过网络
rdd.groupByKey().mapValues(_.sum)

// 好：map 端先 sum，网络上传的是局部结果
rdd.reduceByKey(_ + _)
```

假设一个 key 有 100 万条记录，每条 100 字节。`groupByKey` 要传 100MB，`reduceByKey` 只传一个数字。差了六个数量级。

凯喵的规矩是：**能用 `reduceByKey` / `aggregateByKey` / `combineByKey` 就不要用 `groupByKey`**。只有确实需要「保留全部原始 value」时才用后者，而且要考虑加盐打散。

### 现场七：cache 与 persist 的存储级别选择

`cache()` 等价于 `persist(StorageLevel.MEMORY_AND_DISK)`，把 RDD 的计算结果存下来，后续复用不再重算。但存哪里、存几份、是否序列化，都有讲究。

```scala
import org.apache.spark.storage.StorageLevel

rdd.persist(StorageLevel.MEMORY_ONLY)          // 纯内存，放不下就重算
rdd.persist(StorageLevel.MEMORY_AND_DISK)      // 内存优先，溢出落盘
rdd.persist(StorageLevel.MEMORY_ONLY_SER)      // 序列化存，省空间但费 CPU
rdd.persist(StorageLevel.DISK_ONLY)            // 只落盘，适合超大数据
```

凯喵的选择顺序：先 `MEMORY_AND_DISK` 保正确性，测出实际占用后再考虑 `MEMORY_ONLY_SER` 省空间。纯 `MEMORY_ONLY` 在数据量大时会静默退化成重算，反而更慢，而且很难发现。

另一个高频错误是「缓存了但忘了释放」。一个长驻的 Spark 应用反复 cache 不同数据集，最后 Executor 内存被缓存占满，任务开始 OOM。**用完就 `unpersist()`**，这是个必须养成的习惯。

### 现场八：checkpoint 截断血缘，代价是写 HDFS

`checkpoint` 把 RDD 物化到可靠存储（通常是 HDFS），并把血缘链截断——之后如果这个 RDD 的分区丢了，直接从 checkpoint 读，不用重放整条链。

它和 `cache` 的区别是：`cache` 存的是「计算结果」，血缘还在；`checkpoint` 存的是「新起点」，血缘被切断。所以 `checkpoint` 适合「血缘极长」或「迭代算法」的场景。

```scala
sc.setCheckpointDir("hdfs:///checkpoint")
val iters = rdd.map(expensiveFn)
iters.checkpoint()          // 注意：checkpoint 是惰性的，要有个 action 触发
iters.count()               // 触发物化
```

凯喵踩的坑是：忘了 `checkpoint` 是惰性的，声明完直接进入循环，结果第一次迭代触发了完整的双份计算（一份算 checkpoint、一份算正常流程）。正确做法是声明后立刻加一个 action 强制物化。

### 现场九：数据倾斜是「少数 key 太大」，量化方法很具体

倾斜的表现是：大部分 Task 几秒完成，少数几个 Task 跑几十分钟，甚至 OOM。根因是某些 key 的记录数远超其他 key。

量化方法很直接：把 key 的分布打出来，看最大分区和平均分区的比值。超过 3 倍就值得处理，超过 10 倍必须处理。

```scala
// 采样统计 key 分布
val sample = rdd.sample(false, 0.01).map(x => (x.key, 1)).reduceByKey(_ + _)
val counts = sample.map(_._2).collect().sorted
println(s"max=${counts.last} p99=${counts((counts.length * 0.99).toInt)}")
```

处理手段有三种：**加盐打散**（给热 key 加随机前缀，聚合两次）、**广播小表**（join 时把小表广播出去，避免 Shuffle）、**拆分热 key 单独处理**（把 null、空串这类异常值过滤掉再 union 回来）。

凯喵的经验是：倾斜问题八成来自 null 或空值。先看看是不是某个字段大量为 null，可能一行 filter 就解决了。

### 现场十：mapPartitions 比 map 少一次函数调用开销

`map` 对每条记录调用一次函数，`mapPartitions` 对每个分区调用一次，传入一个迭代器。

```scala
// 每条记录一次：如果函数里要建数据库连接，就是灾难
rdd.map { r => val conn = openConn(); val v = query(conn, r); close(conn); v }

// 每个分区一次：连接复用，开销降两个数量级
rdd.mapPartitions { iter =>
  val conn = openConn()
  try iter.map(r => query(conn, r)) finally close(conn)
}
```

这个差别在「函数内部有重资源初始化」时是决定性的。凯喵见过一个作业在 `map` 里创建 HTTP 客户端，每秒创建几万个连接，把下游服务打挂了。改成 `mapPartitions` 之后连接数降到分区数量级。

代价是内存：`mapPartitions` 一次处理整个分区的迭代器，如果实现里不小心 `toList`，就可能 OOM。要保证是流式处理。

### 现场十一：并行度不是越大越好

分区数决定 Task 数，Task 数决定并发度。直觉上分区越多越快，但实际有三个上界：Executor 核数（同时能跑多少 Task）、单 Task 的调度开销（通常几毫秒）、以及 Shuffle 的文件数（每个分区一个文件）。

典型配置是「分区数 = 总核数 × 2 到 4」。太少则并行度不足，太多则调度开销和文件数爆炸。

```scala
// 读文件时的默认分区可能远小于集群能力，要显式调整
val rdd = sc.textFile("hdfs:///big", minPartitions = 200)

// 聚合后分区数会缩到 shuffle 分区数（默认 200），大作业要调大
spark.conf.set("spark.sql.shuffle.partitions", "1000")
```

凯喵见过一个作业有 10000 个分区但只有 20 个核，结果调度开销比计算还长。**先看集群有多少核，再定分区数**，别凭感觉写个大数。

### 现场十二：结果不对，八成是 Shuffle 时丢了分区器

最隐蔽的一类问题。某些操作会保留分区器（如 `map`），某些会破坏它（如 `mapValues` 之外的键变换）。分区器丢了之后，后续的 `join` 会变成全量 Shuffle，性能骤降；更糟的是如果代码假设了分区器的存在，结果可能不对。

```scala
val a = rdd.reduceByKey(_ + _)          // HashPartitioner(200)
val b = a.map { case (k, v) => (k, v * 2) }   // 保留分区器
val c = a.map { case (k, v) => (v, k) }       // 键变了，分区器失效
```

凯喵的排查方法是：用 `rdd.partitioner` 打印检查，用 `rdd.getNumPartitions` 确认分区数。凡是发现「应该很快的 join 变慢了」，先看两边的分区器是否一致。

另一个相关坑是：两个用相同 `HashPartitioner` 且分区数相同的 RDD 做 join，可以不触发 Shuffle（叫「map-side join」）；分区数不同就必须 Shuffle。这个细节在大作业里能省下几十分钟。

## 收尾：Spark 调优就是守住那三条前提

凯喵最后总结：Spark 快的三条前提——**窄依赖融合、惰性求值看见全貌、缓存避免重算**——对应三类调优动作：

守住窄依赖：少用 `groupByKey`，多用 `reduceByKey`；能用 `coalesce` 就别 `repartition`；`join` 时优先广播小表。

守住惰性：不在循环里反复触发 action；需要多次复用的 RDD 一定要 cache；长血缘要及时 checkpoint。

守住缓存：`unpersist` 及时释放；根据数据量选存储级别；监控缓存占用比例。

剩下的倾斜、并行度、序列化，都是在这三条之上的微调。而所有微调的前提是**先量再调**——看 Spark UI 的 Stage 耗时、Shuffle 读写量、Task 的时间分布，找到真正的瓶颈。凭感觉加参数，通常只是把问题从一处挪到另一处。
