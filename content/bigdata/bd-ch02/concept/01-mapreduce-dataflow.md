# 一、Map/Shuffle/Reduce 三阶段数据流

（中立陈述）一次 MapReduce 作业由三类进程协作完成：**MapTask** 读输入分片、把每条记录映射成 `(key, value)` 中间对；**Shuffle** 负责把同 key 的 value「搬运并排序」到同一个 ReduceTask；**ReduceTask** 按 key 聚合 value 得到最终结果。三者构成「分而治之 + 归并」的经典批处理范式，输入/输出都落在 HDFS（或兼容存储）上。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### Map 阶段：文本 -> (word, 1) 中间 kv 流

```python
def mapper(line):
    for w in line.split():
        yield (w.lower(), 1)

docs = ["Hello world hello", "world of BigData", "hello bigdata world"]
kv = []
for line in docs:
    for k, v in mapper(line):
        kv.append((k, v))
for k, v in kv:
    print(f"{k}	{v}")
print(f"--total kv pairs: {len(kv)}")
```

实际输出：

```text
hello	1
world	1
hello	1
world	1
of	1
bigdata	1
hello	1
bigdata	1
world	1
--total kv pairs: 9
```

> 出处：`examples/ex01.json`。改一处再看输出变没变，比读三遍解释有用。

### Partitioner：hash(key) % R 决定 key 去哪个 reducer

```python
def partition(key, num_reduce):
    h = 0
    for ch in key:
        h = (h * 31 + ord(ch)) & 0x7fffffff
    return h % num_reduce

R = 3
words = ["hello", "world", "bigdata", "of", "data", "map", "reduce", "spark"]
for w in words:
    print(f"{w:10s} -> reducer {partition(w, R)}")
print(f"--num_reducers={R}")
```

实际输出：

```text
hello      -> reducer 1
world      -> reducer 0
bigdata    -> reducer 1
of         -> reducer 0
data       -> reducer 2
map        -> reducer 0
reduce     -> reducer 0
spark      -> reducer 2
--num_reducers=3
```

> 出处：`examples/ex02.json`。改一处再看输出变没变，比读三遍解释有用。

### 🧑‍💻 程序员视角
- 工程落地：绝大多数业务不必手写 Map/Reduce——Hive/Spark SQL 会把 SQL 翻译成底层作业；但理解数据流是**调优的前提**，否则你连「为什么慢」都看不出。
- 性能坑：Shuffle 是 job 的「性能胜负手」。Map 端吐出的中间 kv 要落本地磁盘并经网络拉取，数据量 = Map 输出总量；一旦 Map 输出过大（`mapreduce.task.io.sort.mb` 太小），就会频繁 spill 到磁盘，IO 飙升。
- 可维护性：把业务逻辑放进 Mapper 还是 Reducer 有讲究——能 Map 端本地算的就别拖到 Reduce（见 Combiner）；Reduce 数 `mapreduce.job.reduces` 设错会直接决定并行度与文件数。
- 替代方案：Shuffle 重、迭代计算慢，是 Spark 用「内存 + DAG」取代 MapReduce 做迭代/交互式分析的根本原因。

### 🎓 博士生视角
- 第一性原理：MapReduce 本质是 **「数据靠近计算」的分布式归约**——把函数（map/reduce）推到数据所在节点执行，规避把 PB 数据搬回中心节点的网络不可能的成本（移动计算比移动数据便宜）。
- 形式化：设输入集合 `S`，map 是 `S → {(k, v)}` 的函数，group 是 `⟦(k,v)⟧ → (k, [v])` 的多值分组，reduce 是 `(k,[v]) → [(k,u)]`；整体是 `reduce ∘ group ∘ map` 的复合，group 这一步的「按 key  shuffle」正是分布式正确性的关键不变量。
- 复杂度：若 map 输出规模与输入同阶 `O(n)`，且每个 key 的 value 列表可被单机内存容纳，则 reduce 阶段整体 `O(n log n)`（排序）或 `O(n)`（哈希聚合）；瓶颈在 Shuffle 的网络 `O(∑|map_out|)`。
- 与相邻理论关系：它是 BSP（Bulk Synchronous Parallel）的单超步特例；其「屏障式」Shuffle 与 MPI_Alltoall 同源，区别在容错——MapReduce 通过「任务失败重跑 + 输入不可变」实现粗粒度容错，而非消息级 checkpoint。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「MapReduce 分哪几个阶段？各阶段做什么？」标准答：**Map（切分映射成 kv）、Shuffle（分区/排序/归并，按 key 把 value 送到同一 reducer）、Reduce（按 key 聚合）**；Shuffle 横跨 Map 输出与 Reduce 输入，是连接两阶段的纽带。
- 易错口径：Shuffle 不是「Map 之后才发生」，它从 Map 写环形缓冲区就开始了；且 **Shuffle 既包含 Map 端的 partition/sort/spill/merge，也包含 Reduce 端的 copy/merge/sort**，是一个跨两端的过程。
- 关联考点：与「分治算法」「归并排序」结合考；与 Spark 的 Stage 划分（宽/窄依赖）对比，MapReduce 的 Shuffle 相当于一次全局宽依赖。

---

# 二、WordCount 端到端走读

> MapReduce 把「计算」搬近「数据」，避免搬大盘：Map 在本地切片并行处理，Shuffle 按 key 归并到同 reducer，Reduce 聚合输出。YARN 负责把任务调度到数据所在的节点，做到「数据不动、计算动」。

```text
input 分片 ──▶ Map(本地,并行) ──▶ [ Shuffle: 按 key 分组 ] ──▶ Reduce ──▶ 输出
                 (k1,v1)          partition+sort       (k2, [v2..])
                 (k1,v2)   ─────────────┐
                 (k3,v1)   ───┐         │
                               ▼         ▼
                            reduce0    reduce1
                            k1→聚合    k3→聚合

  Map:  逐行转 (key, value)       例: (word,1)
  Shuffle: 同 key 进同 reducer（网络传输，最贵一步）
  Reduce: 同 key 的 values 聚合    例: word→count

  YARN: ResourceManager 调度，NodeManager 在 DataNode 本地起 Container 跑任务。
```

（中立陈述）WordCount 是 MapReduce 的「Hello World」：Mapper 把每行 `split()` 成词并 `(word, 1)`；Partitioner 用 `hash(word) % R` 决定去哪个 reducer；Reducer 把同一词的 `[1,1,...]` 求和。端到端看，2 个 map、3 个 reduce 的小作业就能体现全部数据流。

### 🧑‍💻 程序员视角
- 真实命令行：`hadoop jar mr.jar WordCount -Dmapreduce.job.reduces=3 /in /out`；reduce 数直接决定输出目录里 `part-r-00000..00002` 的个数与最终文件数。
- 踩坑：若词总量很小却设 `reduces=100`，会得到 100 个近乎空的小文件，既浪费 NN 元数据，又拖慢后续读取——**reduce 数宁少勿滥**，常按 `输入量/256MB` 估。
- 调优实战：用 `combiner` 把 Map 端的 `(word,[1,1,1])` 先聚成 `(word,3)`，能把跨网络 shuffle 的数据量压下来一截；但 Combiner 必须是可交换/可结合的（求和满足，求均值不满足）。
- 排障：想看中间过程，打开 `mapreduce.task.profile` 或翻 YARN 的 job history；数据倾斜时某些 reducer 会「长尾」卡在 99%，其余早已完成。

### 🎓 博士生视角
- 正确性不变量：只要 reduce 函数是**可结合且可交换**的（求和、计数、最值），Combiner 在任意位置插入都不会改变最终结果——这是 MapReduce 能「无限插入本地聚合」的数学基础。
- 数据流图：把作业看作一个有向无环图，`map → [partition] → spill → merge → fetch → reduce`。每个 partition 是一个「逻辑管道」，其有序性由 Map 端排序 + Reduce 端归并共同保证（多路归并保序）。
- 规模分析：设词表大小 V、总词数 N，Reducer 内存需装下「最大热的 key 对应的全部 value 列表」；当某词出现 `O(N)` 次（幂律分布）时，单 reduce 内存爆炸 → 这就是**数据倾斜**在形式化层面的来源。
- 与分布式排序的关系：WordCount 的「先分区再各自内排序」恰好是 **外部排序 / 分布式 TeraSort** 的子步骤；MapReduce 天然能排序是因为它强制了 Shuffle 的 key 有序。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「用 MapReduce 写 WordCount，各阶段输出是什么？」标准答：Map 输出 `<word,1>`；Shuffle 后 Reducer 收到的输入是 `<word, [1,1,...]>`；Reduce 输出 `<word, count>`。
- 易错口径：很多人把 Reduce 输入写成 `<word, 1>`——错，reduce 拿到的是**同一 key 的所有 value 组成的迭代器/列表**，不是单值。
- 常考计算：给定 reduce 数 R，key 经 `hash(key)%R` 分发；若问「某 key 一定去哪个 reducer」，答案是「由 Partitioner 决定，默认哈希分区」，并据此解释「相同 key 必落同一 reducer」这一保证。
- 关联考点：与「Combiner 与 Reducer 的区别」连考——Combiner 跑在 Map 端本地、可能跑 0 次或多次，Reducer 跑在 Reduce 端且每个 key 必跑一次。
