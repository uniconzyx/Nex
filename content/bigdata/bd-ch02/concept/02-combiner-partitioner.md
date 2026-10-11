# 一、Combiner：本地 Reduce 与它的语义边界

（中立陈述）Combiner 是 Map 端可选的「本地聚合函数」，逻辑上与 Reducer 相同，但在**每个 MapTask 内部、溢写前/归并后**对 `(key, [v])` 先做一轮聚合，从而削减需要跨网络 shuffle 的 kv 数量。它必须满足**可结合、可交换**，否则会改变最终结果。

### 🧑‍💻 程序员视角
- 工程惯例：只要 Reducer 是可结合的（sum/count/min/max），就**无脑给 Combiner 设成同 Reducer 的类**——零成本降网络量。WordCount 设了 Combiner，shuffle 数据量能从 N 个 `(w,1)` 降到约 V 个 `(w,局部和)`，V 是词表大小。
- 调用次数不确定：Combiner 可能跑 0 次（map 输出极小、未触发 spill）、1 次或多次（每次 spill 后都合），所以**它绝不能做「有副作用」或「依赖运行次数」的逻辑**（例如发一条消息、累加全局计数器——那要在 Reducer 里做）。
- 踩坑：把「求平均值」直接当 Combiner 会算错——`avg(avg(a,b), avg(c,d)) ≠ avg(a,b,c,d)`。正确做法是用 Combiner 输出 `(sum, count)`，Reducer 再相除。
- 与 Spark 对比：Spark 的 `reduceByKey` 默认就带 map 端 combine（等效 Combiner），而 `groupByKey` 不带——这也是为什么前者快。

### 🎓 博士生视角
- 代数基础：Combiner 合法 ⟺ reducer 函数 `⊕` 在半群（semigroup）上满足结合律与交换律。此时任意「树状局部归约再全局归约」都等于「全量归约」，即 `⊕` 满足在分块聚合下的一致性（map-reduce 一致性定理）。
- 信息论视角：Combiner 不丢信息的前提是「聚合可逆/可叠加」；一旦聚合不可逆（如取 top-K、去重），本地预聚合只能近似（例如每 map 先取 local top-K，再全局 top-K），这催生了「单机草图 + 全局合并」的近似算法家族（Count-Min、HyperLogLog）。
- 系统边界：Combiner 的收益上限 = 「同一 key 在同一 map 内重复出现」的比例。若数据已高度分散（每个 key 每 map 只出现一次），Combiner 几乎无收益，反而白耗能。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Combiner 和 Reducer 的区别？是不是一定要用？」标准答：Combiner 是 **Map 端的本地 Reducer**，用于减少 shuffle 数据量；它**不是必须**，且前提是聚合函数可结合/可交换。
- 易错口径：① Combiner 的输出类型必须和 Reducer 的输入类型兼容（通常是 `(k, v)` → `(k, v')`）；② Combiner **不能替代** Reducer——它只在本地合并，跨 map 的最终合并仍由 Reducer 完成；③ 它运行次数不定，不能承载有状态副作用。
- 高频错例：求平均用 Combiner 直接算均值 → 错；应改传 `(sum, count)`。

---

# 二、Partitioner：决定 Reduce 数与数据分布

（中立陈述）Partitioner 在 Map 端对每个 `(key, value)` 计算目标 reduce 编号 `p = getPartition(key, value, R)`，默认实现是 `hash(key) % R`。它同时决定了两件事：**作业有几个 Reduce（由 `R` 指定）**，以及**每个 key 去哪个 Reduce（由分区函数决定）**。分区不均匀直接造成数据倾斜。

### 🧑‍💻 程序员视角
- 设错 R 的代价：`mapreduce.job.reduces` 既决定并行度也决定输出文件数。设太小 → 单 reduce 处理过多、易 OOM、慢；设太大 → 小文件爆炸、任务调度开销大。经验值：每 reduce 处理 128MB~1GB。
- 自定义 Partitioner：当默认哈希把某个超大 key（如 `"vip_user"`）和别的 key 撞到同一分区，就手写 `getPartition` 把它单独分走，或配合「加盐」把热 key 打散到多 reduce。
- 典型错误：自定义 Partitioner 返回的分区号超出 `[0, R)` 会直接抛 `IOException` 让任务失败；返回负数同理——务必对 R 取模并 `% R` 保证非负（Java 的 `%` 对负哈希可能为负，需 `& Integer.MAX_VALUE` 或 `+R)%R`）。
- 与 Hive/Spark 联动：Hive 的 `DISTRIBUTE BY`、Spark 的 `partitionBy` 底层都是 Partitioner 语义；理解它才能写好「避免 shuffle 倾斜」的 SQL。

### 🎓 博士生视角
- 负载均衡的度量：理想 Partitioner 让各 reduce 的输入量方差最小。对 key 分布 `{p_k}`（频率），分区函数是把 key 空间映射到 `[0,R)` 的散列；当 key 频率呈**幂律**（少数 key 占大多数）时，任何与 key 值无关的哈希都无法均衡——必须引入**值相关的特殊路由**（把热 key 单独/拆分处理）。
- 一致性哈希视角：默认哈希分区是「取模」而非「一致性哈希」，因此 R 改变会导致**几乎所有 key 重新分区**（全量 shuffle）。这是 MapReduce 中 reduce 数一旦定下就最好别改的工程原因，也是 Spark 用固定分区数 + AQE 动态调整的改进点。
- 正确性约束：Partitioner 必须保证「相同 key 永远进同一分区」，否则 Reducer 拿不全某个 key 的全部 value，聚合结果错误——这是比负载均衡更高优先级的**正确性不变量**。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Partitioner 的作用是什么？默认怎么实现？」标准答：决定**每条记录去哪个 Reduce**；默认 `hash(key) % numReduceTasks`，且**相同 key 必去同一 Reduce**（正确性的前提）。
- 易错口径：① 是 Partitioner 而非 Reducer 决定「key 的去向」；② reduce 数由作业配置指定，Partitioner 负责在 `[0,R)` 内分配；③ 哈希取模遇到负哈希值要处理，否则分区越界报错。
- 关联考点：常与「数据倾斜」连考——「为什么某个 reduce 跑了很久？」「怎么解决？」答案链：默认哈希撞车 → 自定义 Partitioner / 加盐 / MapJoin（小表广播）。
