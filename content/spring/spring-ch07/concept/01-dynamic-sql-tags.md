# 一、动态 SQL：把拼接交给标签，把安全留给占位符

动态 SQL 是 MyBatis 最被低估的部分。它的本质只有一句话：
**在 XML 里用标签描述「SQL 文本的组装规则」，由 OGNL 表达式求值决定哪些片段留下**。
所以它不是什么「SQL 语言扩展」，而是一个**带条件的字符串拼接器**——
和你在 Java 里写 `StringBuilder` 做的是同一件事，只是把控制流从代码搬到了配置。

```text
Mapper 接口方法调用
        |
        v
MappedStatement (SqlSource)
        |
        v
DynamicSqlSource.getBoundSql(param)        <-- 在这里做「动态」求值
        |
        +--> <if test="...">  -> OGNL 求值 true/false
        +--> <where>          -> 前缀 WHERE + 去前导 AND/OR
        +--> <foreach>        -> 展开为 (?,?,?) 并扁平化参数
        +--> <include>        -> 先做 ${} 属性替换，再当普通片段插入
        |
        v
BoundSql { sql: "SELECT ... WHERE name = ? AND status = ?", parameterMappings: [...] }
```

理解这条管线，后面所有「为什么这么写才对」都能自己推出来。

## 一、条件标签：`<if>` 与 `<choose>`

`<if test="...">` 的 `test` 是 **OGNL 表达式**，不是 Java 表达式，也不是 EL。
`<choose>/<when>/<otherwise>` 是「多选一」，等价于 `switch`，只会命中**第一个**成立的 `<when>`。

```markdown
<select id="search" resultType="User">
  SELECT id, name FROM t_user
  <where>
    <if test="name != null and name != ''"> AND name = #{name} </if>
    <choose>
      <when test="type eq 'A'"> AND status = 0 </when>
      <when test="type eq 'B'"> AND status = 1 </when>
      <otherwise> AND 1 = 1 </otherwise>
    </choose>
  </where>
</select>
```

### 🧑‍💻 程序员视角

- 排查顺序固定：**先看 XML 拼出来的最终 SQL**（日志 `Preparing:` 那一行的真身要看
  `==> Parameters`，或直接开 `org.apache.ibatis` 的 DEBUG），再看参数，再看结果映射；
  90% 的「条件没生效」是 `<if>` 表达式写错而不是 SQL 写错。
- 三个高频写法事故：
  - 用 `&&` → OGNL 直接抛 `TokenMgrError`；正确是 `and`；
  - 字符串比较用 `==` → 比较的是对象引用，`type == 'A'` 在小字符串上可能偶然为真、上线后偶发为假；
    正确是 `type eq 'A'`（或 `'A'.equals(type)`）；
  - `name != ''` 看着严谨，但在 `name` 是 `String` 且值为空格时通过，业务上仍会拼出无意义的条件。
- 工程取舍：条件超过 5 个时不要继续堆 `<if>`，改用「查询条件对象 + 每个字段一个
  `<if test="cond.xxx != null">`」，把 `AND` 写在片段开头、交给 `<where>` 修剪，
  这样条件块的增删是**局部修改**，不会漏掉 `AND`。
- 上线事故典型：把 `<choose>` 写成多个并列 `<if>`，导致两个分支同时命中，
  拼出 `status = 0 AND status = 1`，查询恒空却不报错——日志里 SQL 完全合法，只有结果对不上。

### 🎓 博士生视角

- 形式化：动态 SQL 是一个映射
  `f: (SqlNode 树, 参数对象) → BoundSql(SQL 文本, 有序参数列表)`。
  `SqlNode` 有 5 种基本节点（`StaticTextSqlNode`、`IfSqlNode`、`ChooseSqlNode`、
  `ForEachSqlNode`、`TextSqlNode`），`MixedSqlNode` 是它们的组合子（Composite 模式）。
  整棵树在解析期一次构建、执行期反复遍历——**表达式求值是 O(节点数)**，与 SQL 长度线性相关。
- 为什么参数列表要单独维护：动态 SQL 的文本和参数**必须保持位置一致**。
  `ForEachSqlNode` 展开时不仅追加 `?`，还同步向 `DynamicContext` 追加
  `__frch_item_0`、`__frch_item_1` 这类绑定名，保证参数顺序与占位符顺序严格对齐。
  这也解释了为什么 `<foreach>` 里用 `${}` 拼 item 是灾难：文本顺序与参数顺序脱钩。
- OGNL 的语义陷阱有理论根源：OGNL 把 `==` 编译为 `OgnlOps.equal`，
  对 `String` 走 `equals` 还是 `==` 取决于是否开启 `OgnlRuntime` 的常量折叠路径，
  行为在不同版本间不稳定；而 `eq` 明确定义为 `equals` 语义。所以「字符串一律用 `eq`」不是习惯而是规范。

### 📚 考研者视角

- 面试标准问法：「`<if>` 的 `test` 里为什么不能用 `&&`？」标准答：`test` 是 OGNL 表达式，
  逻辑与是 `and`/`or`，`&&` 会被 OGNL 词法分析器判为非法字符而抛异常。
- 常考口径：「`<choose>` 与多个 `<if>` 的区别？」——`<choose>` 是**互斥多分支，命中即停**；
  多个 `<if>` 是**独立判断，可同时成立**。这一条几乎每年都会以「下列哪种写法能避免两个条件同时生效」的形式出现。
- 易混点：`<if>` 的 `test` 求值对象是**参数 Map**，不是方法参数名。
  单参数且无 `@Param` 时，OGNL 里可以直接写属性名（`name != null`）；
  多个参数或集合参数时，`name` 取不到——必须在方法签名上写 `@Param("name")`。
  这不是「语言的锅」，而是 MyBatis 用 `ParamNameResolver` 把参数规整成
  `{0: v0, 1: v1, param1: v0, param2: v1}` 这种「同时带序号与名字」的 Map 的副作用。

## 二、智能修剪：`<where>` / `<set>` / `<trim>`

这三个标签解决的是**拼接产生的不合法片段**问题：悬空的前导 `AND`、多余的尾部逗号、
不该出现的空 `WHERE`。

`<trim prefix="WHERE" prefixOverrides="AND |OR " suffixOverrides=",">` 是通用形式，
`<where>` 等价于 `prefix="WHERE" prefixOverrides="AND |OR "`，
`<set>` 等价于 `prefix="SET" suffixOverrides=","`。

关键细节：`prefixOverrides` 是**按 `|` 分隔的前缀列表**，`AND ` 后面的**空格是内容的一部分**。
把它写成 `AND|OR`（没有空格）时，`ANDname = ?` 不会被修剪——因为 `TrimSqlNode`
是「严格前缀匹配后截断」，不是按单词边界匹配。

```text
原始拼接结果        <where> 处理结果
------------------  ------------------
"AND status = ?"    "WHERE status = ?"
"AND name = ? AND status = ?"  "WHERE name = ? AND status = ?"
""                  ""              <-- 整条子句消失，没有悬空的 WHERE
```

### 🧑‍💻 程序员视角

- `<where>` 的两条保证要记死：**内容为空时整条子句不生成**；**非空时去掉前导 `AND`/`OR`**。
  有了这两条，「所有条件都为空导致 `WHERE` 后面直接跟 `ORDER BY`」这类语法错误从根上消失。
- `<set>` 只做「去掉尾部逗号」，**不做「空集合不生成」的保护**：
  所有字段都没变时，`<set>` 会拼出 `UPDATE t_user WHERE id = ?`——**合法的 SQL、致命的后果**（全列不动但仍执行）。
  工程惯例：更新前在 Java 侧校验「至少有一个非空字段」，或干脆用固定全量更新。
- 用 `<trim>` 手工实现 `<where>` 是常见重构信号：当你要在 `<where>` 之外再塞 `HAVING` 或
  `ON` 子句的前缀修剪时，`<trim>` 才能复用同一套逻辑。
- 调试口诀：**日志里看到 `WHERE AND`、`SET ,`、末尾 `, WHERE`，一定是修剪标签缺失或 `prefixOverrides` 少了空格。**

### 🎓 博士生视角

- `TrimSqlNode` 的算法是「先拼、再剪」而不是「拼的时候判断」：
  它把子节点先渲染成一个完整字符串，然后做
  `startsWith(override)` 逐个尝试 → 命中则 `substring(length)`；
  `suffixOverrides` 同理由尾部回退。因此它的复杂度是 `O(k·L)`（k 为 override 数量，L 为文本长度），
  而不是增量维护——这也是它**无法处理「中间重复的 AND」**的原因：只剪首尾。
- 为什么不设计成「拼接时不加多余的 AND」：因为动态 SQL 的片段是可组合的，
  每个 `<if>` 独立决定自己要不要带 `AND` 前缀，**局部无法知道全局是否已有条件**。
  首尾修剪把「全局信息」的需求降级成「只看首尾一个 token」，是一种刻意的设计取舍：
  牺牲表达能力（无法处理中间冗余）换取节点无状态、可任意嵌套。
- 值得注意的边界：`<where>` 的修剪发生在**所有子节点渲染完之后**，
  所以 `<if>` 内部如果拼出了一个以 `OR` 结尾的片段（`name = ? OR`），`<where>` 管不了——
  尾部修剪只有 `<trim suffixOverrides="OR">` 能做。这解释了为什么「`<where>` 万能」是错误直觉。

### 📚 考研者视角

- 面试标准问法：「`<where>` 标签解决了 `WHERE 1=1` 的什么问题？」标准答：`<where>` 在内容非空时
  自动加 `WHERE` 并**去掉开头多余的 `AND`/`OR`**，内容为空时不生成 `WHERE`；
  而 `WHERE 1=1` 是手工兜底写法，功能相同但多了一个恒真条件、无法被优化器识别为「无条件」。
- 常考口径：「`<trim>` 的四个属性」——`prefix`（加前缀）、`suffix`（加后缀）、
  `prefixOverrides`（去前缀）、`suffixOverrides`（去后缀），`<where>` 与 `<set>` 都是它的特例。
- 易混点：**`<set>` 去掉的是「尾部」逗号，不是「中间」逗号**。写成
  `name = #{name}, , age = #{age},`（中间多一个逗号）时 `<set>` 不会救你，SQL 直接语法错误。

## 三、片段复用：`<sql>` / `<include>` / `<property>`

`<sql id="baseColumns">id, name, age</sql>` 定义片段，
`<include refid="baseColumns">` 引用；`<include>` 可以带 `<property name="alias" value="u"/>`，
片段内用 `${alias}` 引用——**注意，属性替换用的是 `${}` 语法，不是 `#{}`**。

处理顺序是**先属性替换、再作为普通文本参与动态拼接**。未定义的属性按 `PropertyParser`
的语义**原样保留** `${alias}`（而不是替换成空串），所以写错属性名时你会在最终 SQL 里
直接看到 `${alias}` 字面量——这是个非常好用的自检特征。

```text
<sql id="cols">${alias}.id, ${alias}.name</sql>

<include refid="cols"><property name="alias" value="u"/></include>   ->  u.id, u.name
<include refid="cols"><property name="alias" value="t"/></include>   ->  t.id, t.name
<include refid="cols"/>                                              ->  ${alias}.id, ${alias}.name
```

### 🧑‍💻 程序员视角

- 最大的收益是**列清单单点维护**：把 `INSERT` 的列、`SELECT` 的列、`resultMap` 放在同一个
  `<sql>` 里，改表结构时只改一处。真实项目里这条规则能消掉一整类「加字段忘了某个查询」的 bug。
- 属性替换用 `${}` 意味着**这里天然有注入面**：`<property name="alias" value="${外部输入}"/>`
  是自毁行为。`<property>` 的 `value` 必须是**字面量常量**，绝不能来自用户。
- 别在 `<sql>` 里放 `<if>` 做「半个条件」的复用：片段一旦带上控制流，
  复用点就从「文本复用」变成「语义复用」，很容易拼出多余 `AND`。
  工程惯例：`<sql>` 只放**无条件列表**（列名、公共 `WHERE` 片段），控制流留在调用点。
- `<sql>` 的作用域是**整个 namespace 内可见**（跨文件引用要写全限定名，且要求被引用的
  `<sql>` 先被解析，属于脆弱用法）。跨 Mapper 复用通常改用 Java 常量或代码生成，而不是全限定 `<include>`。

### 🎓 博士生视角

- `<include>` 的展开发生在**解析期**（`XMLIncludeTransformer`），不是执行期：
  `include` 节点会被**原地替换**为 `sql` 节点的子树，并携带一份变量上下文。
  因此 `<include>` 的嵌套深度会直接放大解析后的节点树；循环 include 会导致栈溢出，
  MyBatis 用 `includedSqls` 集合做环检测并在检测到重复时跳过。
- 变量上下文的作用域规则是「调用点覆盖定义点」：`<property>` 的 `refid` 可以链式传递，
  内层 include 的属性优先。这与词法作用域相反（更像宏展开的 `#define` 语义），
  是「文本替换」血脉留下的痕迹。
- 为什么属性替换用 `${}` 而不是 `#{}`：因为这一步发生在**参数绑定之前**，
  此时还没有 `ParameterMapping` 的概念，只能做纯文本替换。这也从机制上解释了
  「`<sql>` 里不能写 `#{}` 的属性名」——`#{}` 里的内容是参数名，不参与属性替换。

### 📚 考研者视角

- 面试标准问法：「`<sql>` / `<include>` 解决什么问题？」标准答：SQL 片段复用，
  通常用于抽取公共列清单或公共条件，配合 `<property>` 做参数化替换以减少重复。
- 常考口径：「`<include>` 里的 `${}` 和 SQL 里的 `#{}` 是同一种机制吗？」——
  不是。前者是**解析期的属性替换**（`PropertyParser`），后者是**执行期的参数占位**（`ParameterMapping`）。
  这一条常被用来区分「背过八股」和「看过源码」。
- 易混点：`<sql>` 的 `id` 与 `MappedStatement` 的 `id` 是两个不同命名空间的东西，
  `<sql>` 不会注册进 `mappedStatements`，因此**不参与 statementId 冲突检测**。
  真正会冲突的是两个同 `namespace` + 同 `id` 的 `<select>`。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | `<if>` 用 `and`/`eq`；`<where>` 保证「无 WHERE 也无悬空 AND」；`<set>` 不去空、不去中间逗号；`<sql>` 只放无条件文本。 |
| 博士生 | 动态 SQL = 有状态拼接器，`DynamicSqlSource` 遍历 `SqlNode` 树同时产出文本与参数列表；修剪是「先拼再剪首尾」。 |
| 考研者 | 必考：`<where>` 去前导 AND、`<set>` 去尾逗号、`<choose>` 互斥 vs `<if>` 独立、`<include>` 的 `${}` 是解析期替换。 |
