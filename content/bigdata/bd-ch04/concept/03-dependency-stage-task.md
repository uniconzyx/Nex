# 一、窄依赖 vs 宽依赖（依赖模型）

（中立陈述）RDD 间的依赖分为两类：**窄依赖（narrow dependency）**——子 RDD 的每个分区只依赖父 RDD 的**至多一个**分区（如 `map`、`filter`、`union`、`mapPartitions`）；**宽依赖（wide/shuffle dependency）**——子 RDD 的每个分区依赖父 RDD 的**所有**分区（如 `reduceByKey`、`groupByKey`、`join`（未广播时）、`distinct`、`sortBy`、`repartition`）。宽依赖必然发生 **Shuffle**：数据按 key 跨节点重新分区。

### 🧑‍💻 程序员视角
- 工程决策：窄依赖可 pipeline 在同一个 Stage、同一台机器连续算，零网络；宽依赖必须落盘+网络 shuffle，是性能杀手；
- 调优：能用 `map-side` 预聚合（reduceByKey）就别用 groupByKey；join 小表优先广播成窄依赖（BroadcastHashJoin）；
- 踩坑：误以为 `join` 一定是宽依赖——小表广播后是窄依赖，反而是优化的目标形态。

### 🎓 博士生视角
- 图论定义：把 RDD 当顶点、依赖当边，若子分区到父分区的映射函数是**单射/局部**（每个子分区只连一个父分区）则为窄依赖；若为**满射到全体**（子分区连所有父分区）则为宽依赖；
- Shuffle 的排序-聚合模型：宽依赖在 map 端按 Partitioner 把记录哈希到桶并（可选）排序溢写，reduce 端拉取各 map 的对应桶做归并+聚合——这正是 MapReduce Shuffle 的继承与优化；
- 为什么宽依赖无法 pipeline：子分区需要父的所有分区数据到位才能计算，破坏了「一进一出」的流式局部性。

### 📚 考研者视角
- 标准问法：「窄依赖和宽依赖的区别？哪些算子产生宽依赖？」→ 看子分区依赖父分区数；宽依赖=Shuffle 类（reduceByKey/groupByKey/join/distinct/sortBy/repartition）；
- 常考：让判断某段代码里哪一步是宽依赖，并指出 Shuffle 发生处；
- 易错：把 `map`、`filter`、`union` 当成宽依赖——它们都是窄依赖。

示例 ex03 给出算子依赖判定（代码见 examples/ex03.json）：

```text
map          -> 窄依赖 无Shuffle
filter       -> 窄依赖 无Shuffle
mapValues    -> 窄依赖 无Shuffle
union        -> 窄依赖 无Shuffle
reduceByKey  -> 宽依赖 需Shuffle
groupByKey   -> 宽依赖 需Shuffle
join         -> 宽依赖 需Shuffle
sample       -> 窄依赖 无Shuffle
结论: 8 个算子中有 5 个窄依赖, 3 个宽依赖; 宽依赖是唯一触发 Shuffle 的来源
```

---

# 二、Stage 划分与 Task 数量计算

（中立陈述）Spark 以 **宽依赖（及最终的 action）为边界** 把 DAG 切成一个个 **Stage**：一个 Stage 内的所有算子都是窄依赖，可流水线执行；遇到宽依赖就切断，前后分属不同 Stage（宽依赖两端各形成一个 Shuffle 边界）。**每个 Stage 内的 Task 数 = 该 Stage 最后一个 RDD 的分区数**；一个 job 的总 Task 数 = 各 Stage Task 数之和。

### 🧑‍💻 程序员视角
- 实战：Task 数低于 executor 总核数 → 资源浪费；远高于核数 → 调度开销大。分区数（并行度）是直接旋钮；
- 调优：存在宽依赖时，尽量让宽依赖前的窄 transformation 多 pipeline，减少 Stage 数；
- 踩坑：`repartition` 会强制一个宽依赖+Shuffle，只为改分区数时要算清代价。

### 🎓 博士生视角
- 拓扑排序依据：DAG 的Stage 划分等价于「以宽依赖边为割集的最长路径分层」——每个 Stage 是依赖图中一个**无宽依赖的极大连通子图（其实是一条窄依赖链）**，其层号 = 到 source 的最长路径上的宽依赖个数 +1；
- Task 数 = 分区数 的正确性：窄依赖中父子分区一一对应，一个分区由一个 Task 计算，故 Task 数严格等于该 Stage 末态 RDD 的分区数。

### 📚 考研者视角
- 标准问法：「一个 job 有多少个 Stage / Task？」→ Stage 以宽依赖+action 切分；Task 数 = 各 Stage 末态分区数之和；
- 常考计算：给定 `sc.parallelize(n).map().filter().reduceByKey().map().collect()`，问 Stage 数与总 Task 数（设分区=p）——Stage=2，Task=2p；
- 易错：把「分区数」和「Stage 数」混为一谈——二者不同维度。

示例 ex04 展示 Stage 划分与 Task 数（代码见 examples/ex04.json）：

```text
Stage 划分（每个宽依赖/Action 切断一次）:
  Stage1: ['A', 'B', 'C']
  Stage2: ['D', 'E']
Stage 数 = 2
每个 Stage 内 Task 数 = 分区数 = 4; 总 Task 数 = 8
```

下面量化「宽依赖失败重算范围」——窄依赖只重算单分区，宽依赖需重算全部父分区（代码见 examples/ex09.json）：

```text
场景: 第 3 个分区计算结果丢失, 需重算
窄依赖(map/filter): 只需重算父 RDD 的 1 个对应分区 -> 重算分区数 = 1
宽依赖(reduceByKey): 需重算父 RDD 全部 4 个分区 -> 重算分区数 = 4
宽依赖失败重算成本是窄依赖的 4 倍
```
