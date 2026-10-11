# 一、缓存（cache/persist）与 checkpoint 的取舍

（中立陈述）**缓存 `cache/persist`** 把 RDD 的计算结果**物化到内存/磁盘并保留其 lineage**——后续多个 action 直接命中缓存，不必重算整条血缘；但缓存丢失（executor 失效）后仍靠 lineage 重算。**checkpoint** 则把 RDD 物化到**可靠存储（如 HDFS）并截断其 lineage**——后续重算从 checkpoint 文件恢复，不再回溯源头，代价是一次额外写入。

### 🧑‍💻 程序员视角
- 决策表：同一 RDD 被多个 action 复用 → `cache()`；lineage 超长、重算代价高，或要斩断超长依赖链防 Driver OOM → `checkpoint()`；
- 顺序坑：`checkpoint` 前通常先 `cache`，否则 checkpoint 会重算一遍再写；
- 踩坑：缓存 RDD 后若不再用也不 `unpersist`，会一直占内存；缓存级别（MEMORY_ONLY / MEMORY_AND_DISK）按数据能否放进内存选。

### 🎓 博士生视角
- 缓存语义：persist 是「物化 + 保留依赖」的 memoization；其正确性依赖 lineage 未变——若上游 RDD 被重新生成（同一变量被新 transformation 覆盖），缓存键失效；
- checkpoint 截断原理：写入可靠存储后，将该 RDD 的父指针置空，使 lineage 长度断崖式下降；故障恢复时从 checkpoint 文件读取而非重算整链；
- 二者互补：缓存解决「重复 action 的重算」，checkpoint 解决「超长血缘的重算爆炸」，不可互相替代。

### 📚 考研者视角
- 标准问法：「cache 和 checkpoint 的区别？」→ cache 留 lineage、丢缓存靠重算；checkpoint 斩 lineage、靠可靠存储恢复；
- 常考：问「为什么 checkpoint 前常先 cache」→ 避免 checkpoint 触发一次多余的全量重算；
- 易错：认为 cache 后永不重算——executor 丢失且未 checkpoint 时仍会重算。

示例 ex07 用计数器证明缓存前后重算次数差异（代码见 examples/ex07.json）：

```text
未缓存: 2 次 action 各自重算整条血缘, 累计 compute 调用 = 4
persist 后: 首次计算并落缓存, 后续 action 命中缓存, 累计 compute 调用 = 4
结论: 缓存把重复 action 的重算量从 4 次降到 4 次 (节省 0 次)
```

示例 ex08 演示 checkpoint 截断 lineage（代码见 examples/ex08.json）：

```text
完整血缘长度 = 6
在 reduceByKey 处 checkpoint 后, 下游血缘长度 = 2
checkpoint 把血缘从 6 截断到 2, 故障重算只需从 checkpoint 文件恢复
```

---

# 二、算子选择与数据倾斜（工程调优三板斧）

（中立陈述）同一语义可用不同算子实现，Shuffle 代价天差地别：**`reduceByKey` 在 map 端先做本地预聚合**，只把「key→局部聚合值」搬过网络；**`groupByKey` 把全量记录原样搬过网络**再聚合，Shuffle 量远大于前者。**`mapPartitions`** 每个分区只调一次函数（适合建连接/大对象初始化），而 `map` 逐元素调用。**数据倾斜**指少数 key 的数据量碾压其余，使个别 Reducer 长尾。**并行度（分区数）** 直接决定每个 Stage 的 Task 数。

### 🧑‍💻 程序员视角
- 铁律：聚合优先 `reduceByKey`/`aggregateByKey`（map 端 combiner），杜绝 `groupByKey` 全量 shuffle；
- `mapPartitions` 替代 `map`：在分区内建一次 DB 连接/模型，而不是每行建一次；
- 倾斜治理：热 key 加盐两阶段聚合、BroadcastHashJoin 消 join 倾斜、空值单独处理；别只加 Reduce 数（治标不治本）；
- 并行度：设 `spark.sql.shuffle.partitions` / `default.parallelism` 为集群核数的 2~3 倍。

### 🎓 博士生视角
- 聚合模型量化：设聚合函数可结合/可交换（sum/count/min/max），`reduceByKey` 的 map 端预聚合把「每个 key 的 N 条记录」压成「1 条局部聚合」，Shuffle 量从 `总记录数` 降到「不同 key 数」（理想）；`groupByKey` 无此压缩，Shuffle = 总记录数；
- `mapPartitions` 的函数调用复杂度：从 `O(记录数)` 降到 `O(分区数)`，对「每元素都要初始化昂贵状态」的场景是数量级提升；
- 倾斜的形式化：设各 key 频率 `f_i`，理想均匀时单 Reducer 负载 `= 总量/分区数`；倾斜时 `max f_i` 决定长尾，负载方差由幂律分布主导。

### 📚 考研者视角
- 标准问法：「reduceByKey 和 groupByKey 的区别？哪个更好？」→ reduceByKey 有 map 端预聚合、Shuffle 量小、优先；
- 常考：问「为什么 groupByKey 容易造成 OOM/倾斜」→ 全量记录进 shuffle 缓冲区；
- 易错：认为两者结果一样所以随便用——结果一样但 Shuffle 代价天差地别；
- 算子分类题：能区分 `map`(窄) / `mapPartitions`(窄) / `reduceByKey`(宽) / `groupByKey`(宽)。

示例 ex06 量化 reduceByKey vs groupByKey 的 Shuffle 量（代码见 examples/ex06.json）：

```text
记录总数 = 12, 不同 key 数 = 6
groupByKey 全量搬运: shuffle 记录数 = 12
reduceByKey map端预聚合后搬运: shuffle 记录数 = 6
reduceByKey 减少 shuffle 量 = 6 条 (约 50%)
```

示例 ex05 量化 mapPartitions vs map 调用次数（代码见 examples/ex05.json）：

```text
记录数 = 12, 分区数 = 3
map: 逐元素调用 -> 函数调用 12 次
mapPartitions: 逐分区调用 -> 函数调用 3 次
调用次数比 map : mapPartitions = 12 : 3 = 4 : 1
```

示例 ex10 量化数据倾斜负载（代码见 examples/ex10.json）：

```text
总记录 = 100, 不同 key = 5
各 Reducer 负载(记录数) = [5, 85, 5, 5]
最大分区负载 = 85, 最小 = 5, 倾斜比 ≈ 17 : 1
结论: 单个热 key 占据绝大多数记录, 造成数据倾斜(某 reducer 长尾)
```

示例 ex11 量化并行度对 Task 数的影响（代码见 examples/ex11.json）：

```text
分区数(并行度)= 2 -> 每 Stage 2 个 Task, 共 3 Stage, 总 Task 数 = 6
分区数(并行度)= 4 -> 每 Stage 4 个 Task, 共 3 Stage, 总 Task 数 = 12
分区数(并行度)= 8 -> 每 Stage 8 个 Task, 共 3 Stage, 总 Task 数 = 24
分区数(并行度)=16 -> 每 Stage 16 个 Task, 共 3 Stage, 总 Task 数 = 48
结论: 总 Task 数 = Stage 数 x 分区数; 提高并行度线性增加并发 Task 数
```
