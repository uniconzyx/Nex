# 二、`#{}` 与 `${}`：从解析管线到注入利用链

`spring-ch06` 给的是结论：`#{}` 是占位符、`${}` 是拼接。本章给的是**机制**：
这句话在 MyBatis 内部对应两条完全不同的代码路径，理解路径才能判断
「什么情况下 `#{}` 也救不了你」以及「`${}` 到底能用在哪儿」。

```text
                     SQL 文本（解析期就确定）
                     "SELECT * FROM t_user WHERE name = #{name} AND id = ${id}"

        TextSqlNode 判定：文本里是否含 "${" ？  -- 含则整个 SqlSource 升级为 DynamicSqlSource

        +------------------------+---------------------------+
        |                        |                           |
   #{} 路径                 ${} 路径                   静态文本
        |                        |                           |
  ParameterMapping        OGNL 取值 + String.valueOf    StaticTextSqlNode
        |                        |
  写入 parameterMappings   直接替换进 SQL 文本
        |                        |
        +----------> BoundSql: { sql, parameterMappings, additionalParameters }
                              |
                              v
                    PreparedStatement: setXxx(i, value) 绑定 ?
```

一条判据记住整件事：**`${}` 让 SQL 文本在「编译期」就依赖运行期数据，`#{}` 不让。**
文本一旦依赖数据，数据库就失去了区分「代码」与「数据」的能力。

## 一、两条路径的形式差异：ParameterMapping + TypeHandler vs OGNL 插值

`#{}` 的完整语法是 `#{property, javaType=int, jdbcType=NUMERIC, typeHandler=XxxTypeHandler, mode=IN}`，
其中除 `property` 外都可省略。省略时 MyBatis 会在 `ParameterMappingTokenHandler` 里
按参数的实际 Class 推断 `javaType`，再由 `TypeHandlerRegistry` 选出 TypeHandler。

`${}` 的完整语法是 `${property}` 或 `${property:defaultValue}`，
由 `TextSqlNode` 内的 `GenericTokenParser("${", "}", BindingTokenParser)` 处理，
求值走 OGNL，结果 `String.valueOf` 后**直接拼进 SQL 文本**。

### 🧑‍💻 程序员视角

- 判断标准只有一条：**这个位置在 SQL 语法里是「值」还是「结构」**。
  值 → `#{}`；结构（表名、列名、`ORDER BY` 字段、`ASC/DESC`）→ `${}` **且必须白名单**。
  什么都不能作为占位符？`SELECT * FROM ?` 是错的——JDBC 不允许把表名参数化。
- 白名单的实现要落在代码里而不是口头上：

```java
// 反面：黑名单式过滤（'--'、';' 、' or ' 之类），永远漏
String col = req.getColumn();
if (col.contains(";") || col.contains("--")) throw new IllegalArgumentException();

// 正面：白名单，只允许枚举里存在的列名
private static final Set<String> SORTABLE = Set.of("id", "create_time", "amount");
if (!SORTABLE.contains(sortColumn)) throw new IllegalArgumentException("illegal sort column");
```

- 一个被忽略的注入面：**`${}` 不一定来自用户**。它在 `mybatis-config.xml` 的
  `<properties>`、`<sql>` 的 `<property>`、以及 `#{}` **无法覆盖的注解位置**都可能出现。
  代码审计时直接全局搜 `${` 比找用户输入更有效。
- 混用事故：`ORDER BY #{sort}` 会在 MySQL 里被解析成 `ORDER BY 'name'`——
  一个**常量字符串**，排序完全不生效且**不报错**（在部分方言里直接语法错误）。
  「排序不生效」的第一反应应是「是不是用了 `#{}`」。

### 🎓 博士生视角

- 两条路径的**输运性质**不同：
  - `#{}` 是**参数化**（parametrization）：SQL 语法树只依赖模板，参数量与类型在
    `ParameterMapping` 里独立描述，文本与数据在 `BoundSql` 里被显式分为两个字段；
  - `${}` 是**宏替换**（macro substitution）：替换后得到的字符串必须**重新做词法/语法分析**，
    因此注入串可以改变语法树形状（加 `OR`、加 `UNION`、闭环引号）。
  这正是「同上同构」与「同构破坏」的区别：前者保持语法树同构，后者允许语法树被输入改写。
- `jdbcType` 为什么有时必须写：`setNull(i, Types.NULL)` 这类调用在 Oracle 上会抛
  `ORA-17004: Invalid column type`，因为 Oracle 无法从 `Types.NULL` 推断列类型。
  此时显式 `#{v,jdbcType=VARCHAR}` 才让驱动发出带类型的绑定。这是**协议层缺省信息**导致的，
  不是 MyBatis 的缺陷。
- 为什么 `#{}` 不能用于表名：SQL 的 PREPARE 阶段需要完整的语法树，
  表名属于语法树的**结构位置**，参数只能出现在**叶子位置**（表达式/值位置）。
  数据库协议（MySQL 的 `COM_STMT_PREPARE`、PostgreSQL 的 Parse 消息）在语法层
  就不支持「位置参数占位标识符」，这不是 JDBC 的限制而是 SQL 语义的限制。
- 顺序性：`parameterMappings` 是一个**有序列表**，其顺序由 `#{}` 在文本中出现的顺序决定。
  动态 SQL 的 `<foreach>` 展开时会同步追加映射，因此**文本顺序与参数顺序必须由同一次遍历产出**——
  这也解释了为什么 `#{}` 不能出现在 `<sql>` 的属性位置：属性替换发生在绑定之前。

### 📚 考研者视角

- 面试标准问法：「`#{}` 和 `${}` 的区别？」标准答：`#{}` 走预编译（替换为 `?`，
  通过 `PreparedStatement` 绑定，防注入、自动类型处理）；`${}` 走字符串拼接（直接进 SQL 文本，
  有注入风险，仅用于表名/列名/排序等结构位置）。
- 常考追问：「`${}` 一定不能用吗？」——不。结构位置必须用它，但要**白名单校验**；
  这是「不能用」与「要小心翼翼地用」的区别，答题时要能区分。
- 易混点：`#{}` 防注入靠的是**参数与语句分离**（代码/数据分离），不是转义。
  把 `'` 转成 `''` 是黑名单思维，遇到不同字符集或注释符号就会漏；
  参数化是白名单（结构固定、参数只是数据）。这一条是区分「背书」与「理解」的关键。

## 二、注入利用链：从「拼进去」到「改语义」

注入的本质是**让输入参与语法分析**。`${}` 把输入拼进文本，输入于是被当代码解析。

```text
模板：  SELECT * FROM t_user WHERE name = '${name}'
输入：  ' OR '1'='1
结果：  SELECT * FROM t_user WHERE name = '' OR '1'='1'
                                      ^^^^^^^^^^^^^^^ 新增了一个恒真析取项
```

对照 `#{}`：`SELECT * FROM t_user WHERE name = ?`，参数列表里放的是**原样的**整串
`' OR '1'='1`。它被当成「一个叫 `' OR '1'='1` 的名字」，在 3 行数据里匹配 0 行。

### 🧑‍💻 程序员视角

- 判断一条 `${}` 是否危险，看三点：
  **① 值是否可达输入？② 该位置是否允许表达式？③ 拼接结果是否被二次解析？**
  三者全真就是可利用漏洞；`ORDER BY ${col}` 属于「① 可达但 ② 受限」——
  它不能直接吐数据，但可以用 `ORDER BY (SELECT ...)` 做**布尔盲注/时间盲注**（MySQL 允许子查询排序）。
  所以「`${}` 只用于排序所以没事」是错的。
- 修复的优先级：**改 `#{}`（首选）> 白名单枚举（结构位置）> 拒绝**。
  永远不要用「过滤 `--` 和 `;`」这类黑名单，`/**/`、`%00`、大小写变体、宽字节编码都能绕。
- 生产加固：数据库账号按最小权限给（只读账号禁 `DROP`/`FILE`）、
  上线前用 `sqlmap`/静态扫描（Semgrep 的 `mybatis-` 规则、`SonarQube`）扫 Mapper XML，
  把「Mapper 里出现 `${`」列入 Code Review 检查项。
- 日志取证：MyBatis DEBUG 日志里 `Preparing:` 是带 `?` 的模板，`Parameters:` 是绑定的值。
  若 `Preparing:` 里出现了**真实业务值**而不是 `?`，那一行就是 `${}` 的位置——
  这是排查注入最快的定位方式。

### 🎓 博士生视角

- 从编译原理看，注入等价于**跨层注入**：应用层的字符串被提升为 SQL 层的语法成分。
  参数化查询让两层之间保持 **parse 边界**（应用值以字节串形态穿过二进制协议），
  `${}` 取消了这条边界。
- 利用链的形态由拼接位置决定，可以形式化地区分：
  - 出现在**引号内值位置** → 需要先闭合引号（如 `' OR '1'='1`），
    受 `magic_quotes`/转义策略影响；
  - 出现在**裸标识符位置**（`ORDER BY ${col}`）→ 无需闭合，
    可利用 `CASE WHEN` 或子查询实现布尔盲注；
  - 出现在**多语句位置** → 若驱动开启多语句（MySQL `allowMultiQueries=true`），
    可执行 `; DROP TABLE ...`，破坏性最大。
- 一个容易被忽略的第二类风险：`${}` 拼接还会**破坏执行计划缓存**。
  参数化查询的计划键是「模板 + 参数类型」，拼接后每次 SQL 文本都不同，
  数据库侧每次都是硬解析（hard parse），在 QPS 高的接口上是实打实的 CPU 损耗。
  也就是说 `${}` 同时是**安全漏洞**与**性能漏洞**。

### 📚 考研者视角

- 面试标准问法：「SQL 注入的根因是什么？怎么防？」标准答：根因是
  **用户输入被当作 SQL 代码参与解析**；防御的核心手段是参数化查询（预编译），
  辅以最小权限、输入白名单、错误信息不外泄。
- 常考口径：「`PreparedStatement` 为什么能防注入？」——因为 SQL 的语法结构在
  `prepare` 阶段就固定并生成了执行计划，后续只传参数值，**参数不会被重新做语法分析**。
- 易混点：「转义单引号」与「参数化」的区别要能说清：前者是针对特定字符的黑名单修补，
  后者是结构上的代码/数据分离。考试里若问「下列哪种措施最彻底」，答案是参数化。

## 三、与 JDBC 协议的边界：预编译到底预编译了什么

`#{}` 并非必然带来「服务端预编译」。是否真预编译取决于**驱动与连接参数**：

| 数据库 / 驱动 | `useServerPrepStmts` | 行为 |
|---|---|---|
| MySQL（默认 `false`） | 否 | 客户端把 `?` 替换为转义后的字面量再发文本 SQL——**仍是客户端转义**，但转义由驱动统一实现且带字符集信息 |
| MySQL（`true`） | 是 | 发 `COM_STMT_PREPARE`，服务端返回 statement handle，后续 `COM_STMT_EXECUTE` 只传二进制参数 |
| PostgreSQL（默认） | 是 | 走 Parse/Bind/Execute 三段式 |

### 🧑‍💻 程序员视角

- 高并发下 `useServerPrepStmts=true` + `cachePrepStmts=true` 通常有明显收益
  （省掉重复的 Preparsed 开销），但要配合 `prepStmtCacheSize`（MySQL Driver 默认 25）一起调。
- MyBatis 的 `ReuseExecutor` 会在 SqlSession 内按 SQL 文本缓存 `PreparedStatement`；
  但它与二级缓存的交互容易出意外——**不建议在同一项目里既开 `ReuseExecutor` 又重度依赖二级缓存**。
- 排错时注意：开启了 `useServerPrepStmts` 后，`Parameters:` 日志里仍是值，
  但抓包看到的是二进制协议——不要因为抓包看不到明文 SQL 就以为没执行。

### 🎓 博士生视角

- 「预编译」在协议层的两种落地（文本协议 vs 二进制协议）带来的**性能差异是 O(解析成本)**：
  服务端预编译把 parse/analyze/plan 三段各做一次，
  客户端替换则在每次执行时重做 parse（但 plan 可能被 plan cache 命中）。
  因此小结果集、低 QPS 场景下两者差距可忽略，高 QPS 场景下差距显著。
- 值得强调：**客户端替换 ≠ 客户端拼接**。驱动做的是「把参数按协议类型序列化成字面量并转义」，
  转义逻辑由驱动统一持有且带着连接的字符集信息，因此不存在「应用员漏转义」的可能。
  这是它能防注入的机制基础。
- 复杂度视角：参数化查询的解析复杂度与「模板长度」相关且**只做一次**；
  拼接查询的解析复杂度与「模板 + 全部参数值长度」相关且**每次都要做**。
  当参数含大文本字段时，后者不仅更慢，还会让 plan cache 迅速膨胀并被 LRU 淘汰。

### 📚 考研者视角

- 面试标准问法：「MyBatis 的 `#{}` 一定走服务端预编译吗？」——不一定。
  MyBatis 只是生成 `?` 占位并调用 `PreparedStatement`；
  是否真在服务端 PREPARE 由驱动与连接参数决定（MySQL 默认是客户端替换）。
  能答出这一层的人比只会背「预编译防注入」的人高一个档次。
- 常考口径：「连接池 + `PreparedStatement` 缓存」的收益点：减少
  PREPARE/PARSE 次数与网络往返。
- 易混点：`Statement`（拼接）、`PreparedStatement`（参数化）、
  `CallableStatement`（存储过程调用）三者的关系与适用场景，常以选择题形式出现。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 值是 `#{}`、结构是 `${}` 且必须白名单；`ORDER BY ${col}` 仍有盲注面；CR 里把 Mapper 出现 `${` 设为必查项。 |
| 博士生 | `#{}` 是参数化（保持语法树同构），`${}` 是宏替换（允许输入改写语法树）；前者还顺带保住 plan cache。 |
| 考研者 | 必答「`#{}` 预编译 + 类型处理，`${}` 拼接有注入风险」；追问要能说出「是否真预编译取决于驱动配置」。 |
