# 三、resultMap、驼峰映射与关联映射

## 1. resultMap：列→字段映射与何时必须手写

`resultType` 让 MyBatis 自动按「属性名=列名（或驼峰）」映射；`resultMap` 是显式映射声明，
处理列名与属性名不一致、复杂类型、关联查询。二者解决的是「关系表的列」到「对象属性」的投影。

### 🧑‍💻 程序员视角
- 何时必须手写 resultMap：列名与属性名不一致（如 `user_name` ↔ `userName` 但没开驼峰）、一对多/多对一关联（`<association>`/`<collection>`）、继承/discriminator、构造器注入；
- 能自动就别手写：简单 CRUD 用 `resultType` + 驼峰配置最省事，手写 resultMap 增加维护成本；
- 性能：resultMap 启动时解析成 ResultMapping 元数据，运行时按元数据反射/setter 赋值，开销可控。

### 🎓 博士生视角
- resultMap 是「元数据驱动的投影（projection）」：把列到属性的映射描述成可解析结构，运行时由 DefaultResultSetHandler 按 ResultMap→ResultMapping 逐列取出、按类型处理器转换、按嵌套递归装配；
- 它显式解决阻抗失配里的「命名不一致」与「结构不一致（嵌套对象）」两类问题，代价是把映射从「约定」变成「声明」；
- 自动映射（autoMapping）与驼峰是同一条「约定优于配置」思路的两种粒度：autoMapping 解决同名，驼峰解决下划线命名法到驼峰命名法的系统差异。

### 📚 考研者视角
- 笔面标准问法：「resultType 和 resultMap 的区别？」标准答：`resultType` 靠自动映射（同名/驼峰），简单快捷；`resultMap` 显式声明列-字段映射，支持别名、嵌套、关联，处理列名不一致与复杂结构。
- 易错：以为「resultMap 一定比 resultType 好」——简单场景手写是过度设计；也别以为「列名不同就查不出」——开驼峰或 resultMap 都能解决。
- 关联考点：ORM 的「投影」「阻抗失配」「关联映射（1:1 / 1:N）」。

## 2. 驼峰映射与关联映射

开启 `mapUnderscoreToCamelCase` 后，`user_name` 自动映射到 `userName`，省去大量手写 resultMap。

### 🧑‍💻 程序员视角
- 开启驼峰：SpringBoot 配 `map-underscore-to-camel-case: true`，`user_name` 自动 → `userName`；
- 关联映射：`<association>` 一对一（User 嵌 Card）、`<collection>` 一对多（User 嵌 List<Order>）；嵌套查询（select 属性）易触发 N+1，推荐嵌套结果（column 前缀）一次查出；
- 常见坑：关联字段名冲突（两表都有 id），用 `<id column="u_id" .../>` 重命名避免覆盖。

### 🎓 博士生视角
- 驼峰映射是命名法转换的确定性函数：下划线命名法 → 小驼峰，是词边界（下划线）到大小写边界的机械变换，无歧义故可全自动；
- 关联映射底层是对象图的递归装配：`<collection>` 触发对子结果的迭代 grouping（按父 id 把多行聚成 List），本质是一次 group-join 在内存里完成，避免 N+1；
- 嵌套查询（select 引用另一个 statement）之所以 N+1，是被翻译成「1 次主查询 + N 次子查询」，而嵌套结果把 join 下推到 SQL 一次完成。

### 📚 考研者视角
- 笔面标准问法：「怎么解决列名和属性名不一致？」标准答：开驼峰自动映射，或手写 resultMap 用 `<result column="user_name" property="userName"/>`。
- 易错：以为「开了驼峰就不需要 resultMap」——关联/嵌套仍需 resultMap；也别把 mapUnderscoreToCamelCase 和数据库列大小写混为一谈。
- 关联考点：MyBatis 的 N+1 问题与 fetchType/嵌套结果优化。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 简单用 resultType+驼峰；关联用 resultMap；注意字段冲突与 N+1。 |
| 博士生 | resultMap 是元数据驱动的投影；驼峰是确定性命名转换；关联=内存 group-join。 |
| 考研者 | resultType vs resultMap 必考；下划线转驼峰、关联映射与 N+1。 |