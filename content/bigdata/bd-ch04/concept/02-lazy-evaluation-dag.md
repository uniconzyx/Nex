# 一、惰性求值（Lazy Evaluation）语义

（中立陈述）Spark 中 **transformation（如 map/filter/reduceByKey）只记录「要做什么」，不立即执行**；只有遇到 **action（如 collect/count/saveAsTextFile）** 才真正触发从源 RDD 到结果的整条血缘计算。这种「**先记后算**」就是惰性求值，它让 Spark 有机会把多个连续 transformation **融合(pipline)进同一个 Stage、合并算子、削减中间物化**。

### 🧑‍💻 程序员视角
- 工程收益：写一长串 `rdd.map().filter().map()` 时，Spark 不会每步都落盘/网络传输，而是 action 时一次性 pipeline 算完，省掉中间 RDD 的物化；
- 踩坑：在 driver 端反复调用 action（如循环里 `collect`）会重复触发整条血缘重算——若中间结果要多次用，先 `cache()`；
- 调试：想看中间结果别随便 `collect`，否则整条血缘跑一遍；用 `toDebugString` 看计划更轻量。

### 🎓 博士生视角
- 语义本质：惰性求值是把「程序」与「执行」解耦——transformation 构造的是一个**延迟求值的可计算对象（thunk）**，action 才是「强制求值(force)」；对应函数式语言的 call-by-need；
- DAG 构建的正确性：因为 transformation 只是往 lineage 追加节点，所以直到 action 出现，DAG 才是完整且可被全局优化的（谓词下推、算子融合、Stage 切分都依赖这份完整 DAG）；
- 与容错的关系：惰性使「重算单元 = 分区」得以成立——只有真正求值失败的分区才重算，未触发的分支永不计算。

### 📚 考研者视角
- 标准问法：「什么是惰性求值？为什么 Spark 要这么设计？」→ transformation 不立即执行、action 才触发，便于 DAG 全局优化、减少中间物化；
- 常考计算：给一串 transformation+action，问「实际触发几次计算」——只有 action 的次数算，transformation 零次；
- 易错：认为 `map/filter` 会马上产出新数据集——错，它们只返回新 RDD 描述。

下面用 `compute_calls` 计数器证明惰性（代码见 examples/ex02.json）：

```text
仅定义 RDD 谱系，未调用 compute
collect 之前的 compute_calls = 0
只做 transformation，compute_calls 仍为 0
调用 collect（Action）触发计算 ...
collect 返回 = [1, 2, 3, 4, 5]
collect 之后的 compute_calls = 1
结论: transformation 期间 compute_calls=0，只有 action 触发计算 -> 惰性求值成立
```

---

# 二、Transformation 与 Action 的判别

（中立陈述）**Transformation** 接收 RDD、返回新 RDD，是惰性的（如 `map`、`filter`、`flatMap`、`groupByKey`、`reduceByKey`、`join`、`union`、`distinct`、`sortBy`、`persist`）。**Action** 触发实际计算并返回**非 RDD** 结果（如 `collect`、`count`、`take`、`saveAsTextFile`、`reduce`、`foreach`、`first`）。

### 🧑‍💻 程序员视角
- 经验法则：看返回值——返回 RDD 的是 transformation，返回具体值/写入外部的是 action；
- 踩坑：`rdd.map(...).collect()` 里 `collect` 才是触发点；误把 action 当 transformation 链式拼接会立刻计算；
- 性能：应尽量用「宽 transformation 之前多接窄 transformation」，让 pipeline 更长、Stage 更少。

### 🎓 博士生视角
- 类型论视角：transformation 类型为 `RDD[A] → RDD[B]`，action 类型为 `RDD[A] → C`（`C` 为标量/集合/Unit）；二者在类型上可机械区分；
- 为何 action 必须存在：惰性系统需要一个「强制求值」的锚点，否则整张 DAG 永远不被计算；action 即是这个锚点，也是 Stage 边界的终结。

### 📚 考研者视角
- 标准问法：「列举几个 transformation 和 action」→ 见上分类，并能说清「返回 RDD vs 不返回」的判别法；
- 常考：给一组算子让分类，重点区分 `reduce`(action) 与 `reduceByKey`(transformation)；
- 易错：把 `take`、`first`、`count` 当成 transformation——它们都触发计算，是 action。

示例 ex12 给出完整分类计数（代码见 examples/ex12.json）：

```text
Transformation 惰性, 返回新 RDD:
  - map
  - filter
  - flatMap
  - groupByKey
  - reduceByKey
  - join
  - union
  - distinct
  - sortBy
  - persist
Action 触发计算:
  - collect
  - count
  - take
  - saveAsTextFile
  - reduce
  - foreach
  - first
Transformation 数 = 10, Action 数 = 7
判别法则: 返回值是否为 RDD -> 是则 transformation, 否则 action
```
