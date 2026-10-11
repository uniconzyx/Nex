# 一、HQL 的编译：AST → 逻辑计划 → 物理计划

（中立陈述）一条 HQL 经过：① **词法/语法分析（Antlr）** 生成 AST；② **语义分析（SemanticAnalyzer）** 绑定元数据、做类型检查，生成**逻辑计划**（Relation 代数树：TableScan / Filter / Aggregate / Project）；③ **逻辑优化器**（谓词下推、列裁剪、常量折叠、CBO 基于代价重写）得到优化后逻辑计划；④ 翻译成**物理计划**（具体算子与执行引擎：Map → Shuffle → Reduce，或 Tez DAG / Spark RDD），最终提交执行。整条链路是「声明式 SQL → 等价、更优的执行方案」的自动转换。

### 🧑‍💻 程序员视角
- 看计划：`EXPLAIN <sql>` 是排障第一工具——能看到是否触发 MapJoin、有没有分区裁剪、Shuffle 量多大。上线前必 `EXPLAIN` 一遍。
- 优化顺序：Hive 先「逻辑优化（与引擎无关）」再「物理优化（选 MR/Tez/Spark）」。CBO（`hive.cbo.enable`）开启后能用列统计选更优 join 顺序，对多表 join 效果明显。
- 引擎选择：`hive.execution.engine` 设 `mr/tez/spark`；新集群基本用 Tez/Spark，MR 已边缘化（慢在每次落盘）。

### 🎓 博士生视角
- 编译即「程序等价变换」：AST 是语法结构的树；逻辑计划是**关系代数**表示（σ/π/γ），与具体执行解耦；优化器在其上施加等价规则（选择下推、投影下推、结合律重排 join 顺序）。物理计划则是把逻辑算子映射到「带数据流动向的分布式执行原语」。
- CBO 的数学基础：用列级统计（min/max/cardinality/NDV）估计每个物理计划的**代价函数**（I/O + CPU + 网络 shuffle），选代价最小的。这是经典「基于代价的查询优化（Selinger 模型）」在分布式上的扩展。
- 不变量：无论怎么优化，逻辑语义必须保持——尤其谓词下推不能改变结果集、列裁剪不能删掉被聚合/被输出的列。优化器靠「等价变换」保证这一点。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「一条 HQL 在 Hive 里经历了哪几个阶段？」标准答：语法分析生成 AST → 语义分析生成逻辑计划 → 逻辑优化（谓词下推/列裁剪）→ 物理计划（选 MR/Tez/Spark）→ 提交执行。
- 易错口径：很多人把「逻辑计划」和「物理计划」混为一谈。逻辑计划描述**做什么（关系代数）**，与引擎无关；物理计划描述**怎么做（具体算子与执行引擎）**。
- 关联考点：与「谓词下推/列裁剪为什么能提速」「CBO 代价估计」连考；与 Spark Catalyst（同构：逻辑→优化→物理）对比。

---

# 二、执行引擎与 JOIN 策略选择（MapJoin vs CommonJoin）

（中立陈述）Hive 早期只把 SQL 翻成 MapReduce；现支持 Tez / Spark。JOIN 是核心算：当一张表足够小（默认 ≤ 约 25MB，由 `hive.mapjoin.smalltable.filesize` 控制）时，优化器自动选 **MapJoin**——把小表广播到各 Map 任务的内存，大表在 Map 端直接关联，**彻底没有 Shuffle/Reducer 阶段**；否则走 **CommonJoin（Reduce 端 Shuffle Join）**：两表按 join key 哈希分区、跨网络 shuffle、Reducer 端做关联。

### 🧑‍💻 程序员视角
- 选型口诀：能 MapJoin 就 MapJoin（直接消 shuffle，最快）；小表超限或两表都大时退回 CommonJoin；大表自身倾斜再辅以加盐/分桶。
- 开关与 Hint：`hive.auto.convert.join=true` 自动转；不生效时可用 `/*+ MAPJOIN(dim) */` 强制（但小表真放不下内存会 OOM）。
- 监控：CommonJoin 在界面上表现为「Reducer 阶段」，MapJoin 表现在「Map 阶段完成即出结果」——看 job 有没有 Reducer 即可判断走了哪条路。

### 🎓 博士生视角
- MapJoin 的本质：**把「广播变量 + 本地哈希关联」搬到数据所在节点**，用「移动小表（可放进内存）而非移动大表（不可行）」规避跨网络 shuffle——仍是「移动计算/小数据比移动大数据便宜」的第一性原理。
- 代价模型：CommonJoin 的网络代价 = 两表按 key 重分区的 shuffle 量（可能 = 全表）；MapJoin 的网络代价 = 小表大小 × 节点数（广播）。当小表 ≪ 大表时，广播代价远低于 shuffle，故择优。
- 边界条件：MapJoin 受限于「小表可放进单机/单 Map 内存」；一旦小表膨胀，广播的 OOM 风险与重算成本超过 shuffle，优化器应退回 CommonJoin——这是阈值存在的根本原因。

### 📚 考研者视角（大数据方向笔面考点）
- 标准问法：「Hive 的 MapJoin 是什么？为什么能提速？」标准答：小表广播到各 Map 端、大表在 Map 端直接关联，省去 Shuffle 与 Reducer，避免大表跨网络重分区。
- 易错口径：MapJoin 不是「永远更快」——小表必须能放进内存，否则 OOM；且只有一表小、或能用分桶/SMB 时才适用。大表 JOIN 大表不能靠 MapJoin。
- 关联考点：与「数据倾斜处理（加盐/两阶段）」「分桶 JOIN（SMB Join）」连考；阈值参数 `hive.mapjoin.smalltable.filesize`。
