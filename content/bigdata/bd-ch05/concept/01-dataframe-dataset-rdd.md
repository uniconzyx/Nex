# 一、从 RDD 到 DataFrame：结构化信息就是优化空间

（中立陈述）RDD 的核心抽象是「分区 + 对每个分区的计算函数 + 依赖」。当你写下 `rdd.map(lambda x: x.split(',')[2])`，
Spark **只看到一个不透明的闭包**：它不知道你取了第几列、不知道类型、不知道你最终只用了两个字段。
于是它只能忠实按你写的顺序执行，一步不落。

DataFrame 在 RDD 之上补了**两层信息**：

1. **Schema**（列名 + 类型）——Spark 知道数据有哪些列；
2. **逻辑计划**（算子语法树）——Spark 知道你**要什么**，而不是**怎么算**。

有了这两层，Spark 才可能做 RDD 时代做不到的三件事：**谓词下推**（把过滤推到数据源）、
**列裁剪**（只读取真正用到的列）、**物理算子选择**（广播 join / SortMergeJoin / ShuffleHashJoin 三选一）。
这就是「结构化信息 = 优化空间」的全部含义。

| 维度 | RDD | DataFrame | Dataset[T] |
|---|---|---|---|
| Spark 能否看到 schema | 否 | 是 | 是 |
| 优化空间 | 无（黑盒 lambda） | Catalyst 全套规则 | Catalyst 全套规则 |
| 类型检查 | 宿主语言类型，运行时 | 弱类型（`Row`） | 编译期 |
| 内存表示 | Java / Python 对象 | Tungsten 紧凑二进制 | Tungsten + Encoder |
| 典型场景 | 非结构化数据、图与迭代算法、精细控制分区 | 绝大多数 ETL / SQL | 需要编译期类型安全的复杂业务逻辑 |

### 🧑‍💻 程序员视角
- **决策树**：能用 DataFrame/SQL 表达的（过滤、投影、聚合、join、窗口函数）一律用 DataFrame；
  只有「数据结构不规则」「需要按分区自定义迭代」「要精确控制分区与数据本地性」才回退 RDD；
- **上线事故**：把 `df.rdd.map(lambda row: ...)` 当常规写法——Catalyst 全程失明，谓词下推与列裁剪全部失效，
  还要付 JVM ↔ Python 的序列化往返。同一逻辑 DataFrame 版 2 分钟、RDD 版 40 分钟，差的就是这两层信息；
- **排查顺序**：慢作业先看 `explain(mode="formatted")`——有没有 `PushedFilters`？`Scan` 后面的列是不是已经裁剪过？
  没有的话先修查询写法，再谈调参；
- **混合使用**：`df.rdd` 与 `spark.createDataFrame(rdd)` 是合法逃生舱，但**跨越一次边界就丢一次优化**。
  推荐姿势是「先用 RDD 做不规则清洗 → 转成 DataFrame → 后续全程 DataFrame」。

### 🎓 博士生视角
- **形式化**：RDD 的计算函数是 `(Iterator[T]) => Iterator[U]` 的**不透明项**；DataFrame 的算子则是
  **关系代数算子**（σ 选择、π 投影、⋈ 连接、Γ 聚合）构成的**语法树节点**。优化的本质是在
  **保持语义等价**的前提下把语法树重写为代价更低的树：`Σ ⊢ P ≡ P′ ∧ cost(P′) < cost(P)`；
- **为什么 lambda 优化不了**：优化依赖代数等价律，例如 `σ_p(A ⋈ B) ≡ σ_p(A) ⋈ B`（当 `p` 只引用 `A` 的属性）。
  而 lambda 是不可判定的黑盒——无法证明两个 lambda 等价，也就无法重写。这是
  **表达力 vs 可优化性**的经典权衡：抽象越自由，可做的等价重写越少；
- **不动点语义**：Catalyst 把规则批反复应用到树不再变化为止（不动点，fixed point）。
  理论上这要求重写系统具有**终止性**与**合流性**；工程上 Spark 不追求理论合流，
  而是用迭代上限 `spark.sql.optimizer.maxIterations`（默认 100）兜底，保证必然终止。

### 📚 考研者视角
- **标准问法**：「Spark 有了 RDD 为什么还要 DataFrame？」标准答案三条：
  ① RDD 无 schema，Spark 看不见数据结构，无法谓词下推 / 列裁剪；
  ② RDD 存 Java / Python 对象，对象头与装箱带来 GC 与序列化开销，DataFrame 用 Tungsten 紧凑二进制 + 堆外内存；
  ③ DataFrame 有逻辑计划，可做 CBO 与全阶段代码生成；
- **易错口径**：DataFrame **不是** RDD 的替代品，而是**建立在 RDD 之上**的高层 API，`df.rdd` 能拿到底层 RDD；
- **陷阱题**：`DataFrame` 在 Scala 里就是 `Dataset[Row]`；**PySpark 没有 Dataset**（Python 无编译期类型），
  答题时别说「PySpark 的 Dataset」。

---

# 二、Dataset 的类型安全与编码器（Encoder）

（中立陈述）`Dataset[T]` 在 `DataFrame`（即 `Dataset[Row]`）之上加了一层**编译期类型**：
每行是一个 JVM 对象 `T`（case class / Java Bean），列访问变成字段访问，字段名写错**编译不通过**。
代价是 Spark 必须在「JVM 对象 ↔ 内部二进制行 `UnsafeRow`」之间来回转换，这个转换器就是 **Encoder**。

Encoder 做两件事：① 生成 `T → InternalRow` 的序列化代码（按 schema 把对象字段写进紧凑二进制行）；
② 生成 `InternalRow → T` 的反序列化代码。注意：Catalyst 的优化**仍然发生在 `InternalRow` 这一层的逻辑计划上**——
所以 `ds.filter(_.age > 30)` 里的 lambda 依然是黑盒，而 `ds.filter(col("age") > 30)` 是可优化的表达式。

用 `explain` 能直接看出你有没有「离开快车道」：计划里一旦出现
`DeserializeToObject` / `SerializeFromObject`，就说明这一段在做逐行对象操作。

### 🧑‍💻 程序员视角
- **取舍**：Dataset 换来「编译期字段名检查 + 强类型 lambda」，代价是 Encoder 转换开销与退出列式表示的风险；
- **性能信号**：`explain` 里出现 `DeserializeToObject → MapElements → SerializeFromObject` 三连，
  意味着这段逻辑失去了代码生成与堆外布局的收益；如果它出现在数据还很大（行数百万级）的阶段，就是优化点；
- **工程惯例**：ETL 与聚合一律用 DataFrame 列表达式；只有「用类型系统表达业务不变量」
  （领域对象转换、状态机、复杂校验）才上 Dataset，并尽量把它放在数据已经被过滤得很小的阶段；
- **排查手法**：`ds.explain(true)` 对比 `.filter(col(...))` 与 `.filter(p => ...)` 两版计划，
  后者会多出 Serialize/Deserialize 两个节点——这是最直观的「类型安全的账单」。

### 🎓 博士生视角
- **Encoder 的本质是代码生成**：Spark 用 Scala 反射在运行时为 `T` 生成 `ExpressionEncoder`，
  把字段访问编译成对 `UnsafeRow` 的**偏移量读写**，避免通用反射序列化每字段的元数据查找；
- **与 Java 序列化的对比**：Java 序列化把类名、字段名、类型信息都写进字节流（冗余 + 反射反序列化）；
  Encoder 的 schema 是**编译期已知**的，字节流里只有数据，反序列化退化为「按偏移量取值」，
  复杂度从「解析 + 查找」降为「一次内存读」；
- **能力边界**：Encoder 只能覆盖**schema 封闭且已知**的数据结构（case class、JavaBean、
  基本类型及其组合）；任意嵌套、多态、带自定义构造逻辑的类型无法自动推导，必须手写 Encoder——
  这是「类型系统表达力 vs 数据布局可控性」的边界。

### 📚 考研者视角
- **标准问法**：「DataFrame 和 Dataset 的区别？」→ DataFrame = `Dataset[Row]`，**弱类型**，
  列名写错要到运行时的 Analysis 阶段才抛 `AnalysisException`；Dataset[T] **强类型**，
  字段名写错编译期就报错；
- **易错点一**：Dataset 的编译期检查**只管类型，不管列名**。
  `ds.filter("agee > 30")` 这种字符串表达式仍然只有运行时才报错；
- **易错点二**：**PySpark 没有 Dataset**，只有 DataFrame。这是笔试高频陷阱；
- **追问常客**：「Dataset 一定比 DataFrame 快吗？」→ 不一定。Dataset 的类型安全与 JVM 对象转换
  是额外成本，纯列式聚合场景 DataFrame 更快。

---

## 三视角小结

| 主题 | 程序员关注 | 博士生关注 | 考研/笔试口径 |
|---|---|---|---|
| RDD → DataFrame | 决策树、UDF 黑盒事故、先看 explain 再调参 | 关系代数重写、等价律、不动点与终止性 | 「为什么要 DataFrame」三条标准答案 |
| Dataset 与 Encoder | Serialize/Deserialize 节点是性能信号 | Encoder 即代码生成、偏移量读写、能力边界 | DataFrame = Dataset[Row]；PySpark 无 Dataset |
