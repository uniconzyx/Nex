# 一、RDD 的本质与五大特性

（中立陈述）RDD（Resilient Distributed Dataset，弹性分布式数据集）是 Spark 的核心抽象：一个**只读、分区、可并行计算**的数据集合。Spark 官方给出的五大特性是：① 一组**分区**（partition）列表，即数据集的并行度单元；② 对每个分区施加的**计算函数**（compute）；③ 对其他 RDD 的**依赖**列表（lineage）；④（键值 RDD）一个**分区器**（Partitioner，如 hash / range）；⑤ 每个分区优先的**数据位置**（preferred locations，移动计算而非数据）。RDD 本身是**不可变**的：任何 transformation 都返回一个**新** RDD，而不修改旧 RDD。

### 🧑‍💻 程序员视角
- 工程落地：分区数直接决定 Task 并发数，读取 HDFS 时默认 = HDFS 块数（常设为 2~3 倍核数），别用默认 2 分区跑大作业；
- 不可变性带来天然线程安全：同一 RDD 可被多个 action 共享而不互相干扰；
- 踩坑：以为 `rdd1 = rdd.map(...)` 会改 rdd 本身——不会，必须 `rdd = rdd.map(...)` 重新赋值，否则后续用的是旧 RDD。

### 🎓 博士生视角
- 形式化：RDD 可建模为 `(P, f, D, π, L)`，其中 `P` 为分区集合、`f` 为分区计算函数、`D⊆RDD` 为依赖集、`π` 为分区器、`L` 为 locality 偏好；不可变性使 `(P,f,D,π,L)` 一旦创建即恒定，所有变换是纯函数 `T: RDD → RDD`；
- 容错第一性原理：因为依赖集 `D` 完整记录了「如何从父 RDD 算出来」，所以**任意分区丢失都可由其依赖链重算**——这是 lineage 容错的数学基础，无需副本（对比 HDFS 三副本）；
- 为什么「弹性(Resilient)」：丢失分区通过 lineage 重算恢复，集群部分节点失效不影响整体语义。

### 📚 考研者视角
- 标准答（笔面）：RDD 五大特性 = 分区列表 / 计算函数 / 依赖关系 / 分区器(可选) / 首选位置(可选)；
- 常考：问「RDD 为什么容错」→ 答「lineage + 不可变 + 依赖重算」，而不是「副本」；
- 易错口径：把「分区器」说成必选项——只有键值型 Shuffle RDD 才有 Partitioner，普通 map 结果没有。

---

# 二、不可变性与血缘（lineage）容错

（中立陈述）每个 RDD 只记录「我是怎么由父 RDD 算出来的」（依赖 + 算子），这个谱系称为 **lineage / DAG**。因为 RDD 不可变，lineage 是一条**单向、无环、可重放**的因果链：出错时沿链回溯即可精确重算丢失的分区，而不必做全量 checkpoint。

### 🧑‍💻 程序员视角
- 实战：lineage 过长（成百上千个 transformation）会让重算代价飙升、Driver 持有超长图谱内存压力大——此时用 `checkpoint` 截断；
- 不要把 RDD 当可变变量反复 append 计算，RDD 不支持原地改，要链式返回新 RDD；
- 故障演练：杀掉一个 executor，看 Spark 是否只重算该 executor 持有的分区（窄依赖只重算 1 个父分区）。

### 🎓 博士生视角
- 不可变性证明：设 `T` 为 transformation，对任意旧 RDD `R`，`T(R)=R'`，由定义 `R'` 的依赖集含 `R` 且 `R` 自身不变，故 `R` 在 `T` 后状态恒定——不存在「写后读」竞争，证明并行安全；
- DAG 无环性：Spark 的 transformation 只产生「父→子」边，action 终止，无回边，故 lineage 是 DAG 而非一般图；Stage 划分正是基于此 DAG 的拓扑切分；
- 容错边界：lineage 重算正确性的前提是**算子确定性**（同输入同输出），非确定性算子（如 `random`、取系统时间）会导致重算结果不一致——这是为什么 Spark 要求 transformation 幂等/确定。

### 📚 考研者视角
- 标准问法：「RDD 怎么保证容错？」→ 血缘(lineage)记录依赖、分区丢失按依赖重算、无需副本；
- 对比考：HDFS 用副本容错、Spark RDD 用 lineage 重算容错，二者思路不同（空间换时间 vs 计算换空间）；
- 易错：认为「RDD 存了数据副本」——错，RDD 默认不存数据，只存「怎么算」，数据在 action 时才物化。

下面是血缘 DAG 的真实模拟构建（代码见 examples/ex01.json）：

```text
血缘 DAG（自下而上，缩进=父级依赖）:
        RDD#1 [parallelize 分区=4]
      RDD#2 [map x=>x*2]
    RDD#3 [filter x%2==0]
  RDD#4 [reduceByKey 宽依赖]
RDD#5 [collect Action]
血缘节点总数 = 5
构建 5 个 RDD 谱系，但全程未触发一次数据计算（惰性）
```
