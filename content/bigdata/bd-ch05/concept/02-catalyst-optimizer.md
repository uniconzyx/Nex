# 一、Catalyst 优化器：四个阶段与规则批机制

（中立陈述）Catalyst 是 Spark SQL 的**可扩展查询优化器**。一条 SQL 或一个 DataFrame 操作链，
要依次经过四个阶段才变成真正在 Executor 上跑的代码：

```
SQL / DataFrame API
   │  ① 解析 Parsing（ANTLR 语法分析，未解析的 AST，未知列名与类型）
   ▼
Unresolved Logical Plan
   │  ② 分析 Analysis（查 Catalog / Hive Metastore 绑定列名与类型，做类型检查）
   ▼
Resolved(Analyzed) Logical Plan
   │  ③ 逻辑优化 Logical Optimization（规则批重写：谓词下推、列裁剪、常量折叠、JOIN 重排……）
   ▼
Optimized Logical Plan
   │  ④ 物理计划 Physical Planning（按代价/规则选算子：Broadcast vs SortMerge；插入 Exchange）
   ▼
Physical Plan  →  ⑤ 代码生成 Codegen（Whole-Stage Codegen 把算子链编译成一个循环）
```

**规则批（Rule / Batch）机制**：逻辑优化不是「跑一遍规则」，而是把规则分组为若干 **Batch**，
每个 Batch 内的 `Rule[LogicalPlan]` 反复应用到**不动点**（树不再变化）或达到迭代上限
（`spark.sql.optimizer.maxIterations`，默认 100）为止。火箭一样的结构让新增优化规则只需
「加一个 Rule」，这也是 Catalyst 被称为**可扩展**优化器的原因。

一个容易记的对应关系：**`AnalysisException`（列不存在、类型不匹配）来自第 ② 阶段**；
**逻辑优化没生效（没下推、没裁剪）是第 ③ 阶段**；**选了 SortMergeJoin 而不是广播是第 ④ 阶段**。

### 🧑‍💻 程序员视角
- **报错定位**：`AnalysisException: Column 'xxx' cannot be resolved` → 第 ② 阶段，
  通常是表/列名写错、视图未刷新、或 Hive Metastore 里没有该分区；与性能无关，别去调参数；
- **观察手段**：`df.explain(mode="extended")` 一次打印 Parsed / Analyzed / Optimized / Physical 四份计划，
  逐段 diff 就能看出「优化器到底替你做了什么」，以及**哪一步没做**；
- **写法规矩**：把过滤条件写在最靠近数据源的位置，只 `select` 需要的列——这两件事直接决定
  第 ③ 阶段能优化到什么程度；
- **逃生舱**：优化器选错时可用 hint（`/*+ BROADCAST(t) */`、`/*+ REPARTITION(n) */`）与
  `spark.sql.cbo.enabled`，但先用 `mode="cost"` 看清统计信息是否齐全，别盲目加 hint。

### 🎓 博士生视角
- **分层动机**：把「解析 / 绑定 / 重写 / 选算子」切成四段，本质是**关注点分离**：
  只有先完成符号绑定（②），才能做语义等价的重写（③）；只有先得到优化后的逻辑计划，
  才能做基于代价的物理算子选择（④）。混在一起就会互相污染；
- **规则批与不动点**：`Batch(name, strategy, rules*)` 的 `strategy` 决定迭代次数
  （`Once` 或 `FixedPoint(n)`）。一批规则反复重写到不动点，是**重写系统终止性**的工程近似；
  Spark 用迭代上限强制终止，不保证理论合流；
- **代价模型的局限**：物理计划阶段对同一逻辑算子可能有多个物理实现
  （`BroadcastHashJoin` / `ShuffleHashJoin` / `SortMergeJoin` / `BroadcastNestedLoopJoin`），
  选择依据是**代价 = f(输出行数, sizeInBytes, 是否需要排序, 是否已有分区)**。
  代价的输入是统计信息，因此**统计不准 → 代价失真 → 选错计划**，这是 CBO 的根本软肋。

### 📚 考研者视角
- **标准问法**：「Spark SQL 的执行流程 / Catalyst 的优化过程？」→ 按四阶段背：
  解析（AST）→ 分析（绑定元数据，报 `AnalysisException`）→ 逻辑优化（规则批重写）
  → 物理计划（代价选算子）→ 代码生成；
- **易错口径**：很多人只答「逻辑计划 → 物理计划」两步，漏掉**分析（绑定）**阶段；
  也常漏最后的**代码生成**；
- **概念辨析**：**逻辑优化是规则驱动（RBO）**，**物理计划选算子是代价驱动（CBO）**——
  两者都在 Catalyst 里，但机制不同，别混为一谈。

---

# 二、谓词下推、列裁剪、常量折叠与 JOIN 重排

（中立陈述）逻辑优化阶段最有代表性的四条规则：

1. **谓词下推（Predicate Pushdown / `PushDownPredicates`）**：把 `Filter` 往数据源方向移，
  最好一路推进 `Scan`（Parquet 的列式过滤、Hive 的分区裁剪），让**更少的数据进入后续算子**。
  两条硬约束：① 谓词必须**确定性**（含 `rand()`、`current_timestamp()` 的不推，
  因为下推会改变每行的求值次数）；② 谓词引用的列必须在下方算子的输出列中；
2. **列裁剪（`ColumnPruning`）**：自顶向下传播「父节点真正需要哪些列」，
  `Scan` 只读取这些列，配合 Parquet 的向量化读可大幅减少 I/O；
3. **常量折叠（`ConstantFolding` / `SimplifyConditionals`）**：`(1+2)*salary` 折叠为 `3*salary`、
   `x AND true` 化为 `x`；极端情况 `WHERE 1=0` 会被折叠成恒假，整棵子树替换为 `LocalRelation(空)`；
4. **JOIN 重排（`ReorderJoin` / CBO）**：多表 join 时按基数估计选择中间结果最小的连接顺序，
  避免把「笛卡尔积」或「大中间结果」放在前面。

实测（见 `examples/ex03.json`、`ex04.json`、`ex05.json`、`ex06.json`、`ex08.json`）：
同样的查询，谓词下推并融合进 `Scan` 后，参与计算的记录数从 **2000300100 降到 2200100**（约 909 倍）；
列裁剪把 orders 的扫描列从 **5 列降到 2 列**；CBO 选中右深树后中间结果行数从 **101000 降到 3000**（33.67 倍）。

### 🧑‍💻 程序员视角
- **写法规矩**：`filter` 尽量贴数据源、只 `select` 需要的列、过滤条件写成
  `dt = '2026-01-01'` 而不是 `substr(dt,1,7) = '2026-01'`（对分区列套函数会让分区裁剪失效）；
- **LEFT JOIN 语义坑**：对右表的过滤条件写在 `ON` 后与写在 `WHERE` 后**语义不同**——
  后者会把外连接退化成内连接（因为右表补的 NULL 会被 `WHERE` 过滤掉），这不是优化器的问题；
- **验证手段**：`explain` 输出里 `Scan` 节点后面的列就是裁剪结果，`PushedFilters` 显示已下推到数据源的谓词；
  看不到这两项就说明优化没生效，回去改写法；
- **CBO 前置条件**：多表 join 前先 `ANALYZE TABLE ... COMPUTE STATISTICS FOR COLUMNS`，
  否则 Spark 只能按 sizeInBytes 走启发式左深树。

### 🎓 博士生视角
- **谓词下推的代数依据**：`σ_p(A ⋈ B) ≡ σ_p(A) ⋈ B` 成立的前提是 `attr(p) ⊆ attr(A)`；
  非确定性谓词为何不能推？因为 `σ` 的语义是「对每一行求值谓词」，
  把它移到 `⋈` 之下会改变**求值次数**与随机数序列，破坏等价性——这不是实现偷懒，是语义约束；
- **列裁剪为何自顶向下**：需求是从根节点（`Output`/`Aggregate`）向下传播的，
  本质是求每个算子的**属性闭包 `attr(P)` 与父需求的交集**；`SELECT *` 使需求集 = 全属性集，裁剪立即失效；
- **JOIN 重排是 NP 难**：`n` 张表的连接顺序（`n!` 种左深树 × 多种树形）是 NP-hard，
  Spark 的做法是**限制搜索空间**：表数 ≤ `spark.sql.cbo.joinReorder.dp.threshold`（默认 12）时用
  动态规划（DP）穷举，超过就退回启发式（按基数排序 + 左深树）。这是「最优性 vs 优化器自身开销」的取舍。

### 📚 考研者视角
- **标准问法**：「什么是谓词下推 / 列裁剪？」→ 谓词下推：把过滤条件下移到离数据源更近的位置，
  减少参与计算的数据量；列裁剪：只扫描查询真正需要的列，减少 I/O；
- **高频追问**：「什么时候谓词下推不生效？」→ ① 谓词含非确定性函数（`rand()`）；
  ② 谓词引用的列不在下方输出中；③ 中间隔了 UDF 等黑盒算子；④ 对分区列做了函数变换（分区裁剪失效）；
- **易混对比**：**分区裁剪**只对分区列生效（Hive/Spark 的目录级过滤），
  **谓词下推**可作用于任意列（文件/行组级过滤）——二者层次不同，别混用名词。

---

## 三视角小结

| 主题 | 程序员关注 | 博士生关注 | 考研/笔试口径 |
|---|---|---|---|
| Catalyst 四阶段 | `AnalysisException` 定位、extended 模式 diff | 分层动机、不动点与终止性、CBO 软肋 | 四阶段顺序必须背全，别漏「分析」与「代码生成」 |
| 谓词下推/列裁剪/JOIN 重排 | `PushedFilters` 与裁剪列验证、ANALYZE TABLE | 代数等价律、属性闭包、NP 难与 DP 阈值 | 下推失效的四种情形；分区裁剪 ≠ 谓词下推 |
