# spring-ch07 易错点

1. **手写 `WHERE 1=1` 拼接，条件全空时残留悬空 AND/OR** —— 用 `StringBuilder` 拼 `WHERE 1=1` 再逐个 append ` AND xxx`，只要某个分支写成 ` OR xxx` 或片段整体为空，最终 SQL 就会出现 `WHERE AND status = ?` 这类语法错误（复现见 ex01 的 `case2 naive broken : true`）。正确写法：一律用 `<where>`（等价于 `<trim prefix="WHERE" prefixOverrides="AND |OR ">`），内容为空时整条子句不生成、非空时自动加 `WHERE` 并剔除前导 `AND`/`OR`。

2. **`<trim>` 的 `prefixOverrides` 漏写空格导致修剪失效** —— `prefixOverrides` 是按 `|` 分隔的**前缀字符串**列表，`AND ` 末尾的空格是内容的一部分；写成 `AND|OR` 时 `ANDname = ?` 不会被剪掉。另外 `TrimSqlNode` 只做**首尾**修剪：中间多出来的 `AND`、中间的重复逗号（`<set>` 场景）它一概不管。正确写法：`prefixOverrides="AND |OR "`（带尾空格），并保证条件片段内部自身完整。

3. **多参数时 `<if test>` 里直接用属性名，取值恒为 null** —— `test` 的求值对象是 MyBatis 用 `ParamNameResolver` 规整出的参数 Map，单参数无注解时才能裸写属性名；多参数、集合参数不带 `@Param` 时 OGNL 取到的是 `{0: v0, 1: v1, param1: v0, ...}` 这套键，写 `name != null` 永远不成立，条件静默丢失。正确写法：接口方法签名加 `@Param("name")`，XML 里 `<if test="name != null and name != ''">`；逻辑与用 `and`（不是 `&&`），字符串相等用 `eq`（不是 `==`）。

4. **`${}` 拼接用户输入造成 SQL 注入，且以为「只是排序」就安全** —— `${}` 是**宏替换**：值被 `String.valueOf` 后拼进 SQL 文本，数据库把输入当代码重解析；`ORDER BY ${col}` 虽不能直接 UNION 拖库，却可用 `ORDER BY (SELECT ...)`/`CASE WHEN` 做布尔盲注与时间盲注，属于「可达但受限」的可利用面（注入对照见 ex05）。正确写法：值一律 `#{}`；表名/列名/排序这类**结构性位置**不得不用 `${}` 时，取值必须来自白名单枚举并在 Java 侧校验，禁止用「过滤 `--` 和 `;`」这类黑名单。

5. **`#{}` 与 `${}` 混用的两个反向坑** —— 其一是 `ORDER BY #{sort}`：`#{}` 变成 `?` 后 MySQL 把占位符解析成常量字符串 `ORDER BY 'name'`，排序**完全不生效却不报错**，排查时极易被误判为「索引失效」；其二是 `<foreach>` 里写成 `${item}`：DynamicSqlSource 遍历节点时同步产出文本与参数列表，`${}` 让文本顺序与参数顺序脱钩。正确写法：排序字段走 `${}` + 白名单，`<foreach>` 内部只用 `#{item}`。

6. **`<foreach>` 集合为空拼出 `IN ()`** —— `<foreach>` 只是把集合展开成占位符，不提供「空集合则跳过整个 IN 条件」的保护；传入 `List.of()` 时最终 SQL 是 `... WHERE id IN ()`，MySQL 直接报 `You have an error in your SQL syntax`（复现见 ex02 的 `empty in ok : false`）。正确写法：在 Java 侧判空后短路返回空结果（或干脆不进 SQL），或在动态 SQL 外套一层 `<if test="ids != null and ids.size() > 0">`。

7. **`<foreach>` 的 `collection` 名写错，报的是 NullPointerException 而不是「找不到集合」** —— 单个 `List` 参数的默认键是 `list`、数组是 `array`、Map 是键名、`@Param("ids")` 后按注解名取；名称对不上时 OGNL 取到 null，遍历处抛 `BindingException`/`NullPointerException`。正确写法：一律用 `@Param("ids")` 显式命名并与 `collection="ids"` 对应，`item`/`open`/`close`/`separator` 一并配齐。

8. **以为一级缓存是按表失效，实际是整会话全清** —— `BaseExecutor.update()` 调用的是 `clearLocalCache()`：`CacheKey` 里没有表名信息，因此同一 SqlSession 内任何一次 `insert`/`update`/`delete`（哪怕写的表与本次查询毫无关系）都会清空**整个**一级缓存；`commit()`/`rollback()`/`clearCache()`/`flushCache="true"` 同样如此。后果是「写多读少」的事务里一级缓存命中率接近 0。另外一级缓存**跨会话不共享**，两个 SqlSession 各有一份（见 ex06 的 `cross session l1 : true`）。

9. **绕过 MyBatis 直连 JDBC 写库，同一会话内读到旧值** —— 一级缓存假设「本进程、本事务是唯一写入者」；直连 JDBC 的写不经过 MyBatis 的 `update()`，`clearLocalCache()` 就不会执行，后续同名查询命中缓存返回旧行（见 ex06 的 `stale read : true`）。同时要记得 Spring 场景下一级缓存的寿命等于**一个事务**（`SqlSessionTemplate` 把会话绑在事务上），因此「事务内看不到别的事务刚提交的数据」是缓存语义强于 `READ COMMITTED` 的表现。修法：全走 MyBatis，或写完显式 `sqlSession.clearCache()`，兜底再考虑 `localCacheScope=STATEMENT`。

10. **`flushCache` / `useCache` 的默认值记反** —— 这两个是**独立开关**：`<select>` 默认 `flushCache=false` / `useCache=true`，`<insert>`/`<update>`/`<delete>` 默认 `flushCache=true`（`useCache` 对写语句无意义）。典型事故是给高频查询勾上 `flushCache="true"` 做「保险」，结果每次查询都先清缓存再落盘，缓存形同虚设；反过来忘了给必须实时的语句勾上，又读到旧值。正确写法：读懂两个开关，实时性要求高的语句用 `flushCache="true"` 或干脆 `useCache="false"`，不要两个一起乱配。

11. **跨 namespace 写表导致二级缓存脏读** —— 二级缓存的作用域是 **Mapper namespace**，失效协议是「谁拥有 namespace，谁负责清」：`OrderMapper` 里的 `UPDATE t_user` 只会清 `OrderMapper` 自己的缓存，`UserMapper` 缓存的同一行照旧被读到（见 ex07 的 `namespace isolate : true`）。发生条件只用一行就能自检：**同一张表是否被两个以上 namespace 写**。正确写法：多表写场景不开二级缓存，写操作与读操作同 namespace，或用 `@CacheNamespaceRef` 显式关联，或直接放弃二级缓存改用显式失效的应用级缓存。

12. **以为「开了 `<cache/>` 就万事大吉」，其实还有 namespace 隔离、序列化与分布式的三道坎** —— 这不是三个独立话题，而是同一份缓存的三条硬规则：其**作用域**是 namespace（不同 namespace 互不可见也不互相失效，见第 11 条）；其**对象必须可序列化**（`readOnly=false` 时用 `SerializedCache` 做序列化往返深拷贝，实体或其字段没实现 `java.io.Serializable` 会在 commit 刷缓存时抛 `NotSerializableException`）；其**冲刷时机是事务提交**（`TransactionalCache` 把结果攒到 `entriesToAddOnCommit`，`commit()` 之后其他会话才可见——「`close()` 时晋升二级」是常见误答）。三条同时满足才有正确性。

13. **多实例部署下二级缓存的失效不传播** —— 默认的 `PerpetualCache` 是**进程内**的 HashMap：A 节点更新只清 A 自己的缓存，B/C 节点继续吐旧值，表现为「单实例测正常、一上多实例就偶发脏读」，而且因为每个节点命中率都很高，比完全不开更危险。正确写法：换成 Redis 作为 `Cache` 实现（`type` 指向自定义 RedisCache，或用 MyBatis-Plus 的 `RedisCache`）并确认失效广播链路，或干脆关闭二级缓存改用 Spring Cache + Redis 的显式 `@CacheEvict`。互联网业务（写多读少 + 跨表写 + 多实例）默认不开二级缓存是行业惯例。

14. **`readOnly=true` 时把缓存取出的对象改了，污染缓存本体** —— 二级缓存返回对象引用以实现「零拷贝」，业务层一次 `setNickname()` 格式化就把缓存里的对象改了，之后所有会话拿到的都是被改过的脏对象（EO 转 VO 时尤其高发）。为什么默认如此：它不是 bug，而是「零拷贝 vs 无别名」的默认取舍——`readOnly=true` 用返回引用省掉了复制成本，代价是把不变式的维护责任交给了调用方。正确写法：`readOnly=false` 用序列化成本换「无别名」保证（付出 `O(对象图大小)` 的复制成本），或取出后立即做防御性拷贝/转 DTO。

15. **延迟加载的属性在 SqlSession 关闭后才被访问，抛异常** —— 懒加载靠的是持有创建它的 SqlSession 的代理对象；Session 关闭后再触碰代理属性，MyBatis 抛 `ExecutorException: ... no Session`（与 Hibernate 的 `LazyInitializationException` 完全同构），在 Service 返回实体、Controller/序列化层才展开关联字段时必然踩到（懒加载行为见 ex09）。另外 `aggressiveLazyLoading` 为 true 时，**访问任意一个**懒加载属性会触发该对象全部懒加载属性一次性加载，本想省的子查询一个都没省。修法：在 Session 仍开启的边界内完成取值（DTO 转换），或 `@Transactional(readOnly=true)` 包住整个读+序列化过程，或改成嵌套结果一次 join 拿全。

16. **把延迟加载当性能优化用，反手造出 N+1** —— `<association select="...">` / `<collection select="...">` 的语义是「主查询 1 次 + 每行触发 1 次子查询」：实际发送的 SQL 条数是 1 + N（ex10 的 5 个部门场景共发 6 条，而不是大多数人以为的 2 条。延迟加载只是把子查询的**触发时机**推迟到真正访问时，并没有减少**总量**，一旦后续遍历必然访问，总 SQL 数一模一样。正确写法：列表/报表这类必然遍历每行的场景改用**嵌套结果**（`<resultMap>` 一次 join 后按父 id 分组，ex10 的 `nestedResult sql=1 rows=20`）；只有详情页这种「加载主对象后大概率不访问关联」的场景，延迟加载才有价值。

17. **分页插件的 count 查询处错：复杂 SQL 改写少了一层子查询** —— 分页插件需要总数来算总页数，但对带 `GROUP BY` / `DISTINCT` / `UNION` 的原 SQL，直接把列替成 `count(0)` 得到的是「分组后的行数」而不是「总记录数」，而且 count 结果集不是一行（见 ex11 的 `naive count sql` 与 `naive wrong : true`）。正确的 count 改写是把原 SQL 包一层再 count（ex11 的 `groupby count` / `union count`）。同时要注意：count 分支应当剔除与原查询无关的 `ORDER BY`/`LIMIT`——列表上常见做法是齐全保留，白白多一次排序。

18. **`PageHelper.startPage()` 与查询之间插了别的语句，分页落到了错误的 SQL 上** —— `startPage` 靠 `ThreadLocal` 传递分页参数，生效范围严格是「**紧随其后**的那一次查询」：中间穿插一次查询后，分页参数要么被消费掉（接下来的目标查询不分页，返回全表），要么落到不期望的语句上；线程池复用线程时还可能携带上一请求残留的分页参数。正确写法：`PageHelper.startPage(pageNum, pageSize);` 与 mapper 查询**紧密相邻**（同一方法内、中间不插其他 mapper 调用），并在 `finally` 里 `PageHelper.clearPage()`；更好的做法是用 MyBatis-Plus 的 `Page` 对象显式传参，不依赖 ThreadLocal。

19. **`EnumOrdinalTypeHandler` 存枚举序号，改一次枚举顺序就全库错乱** —— 默认枚举 TypeHandler 把 `ordinal()`（从 0 开始的声明序号）入库；在枚举中间插入一个新值，后面所有常量的序号整体位移，历史数据全部语义漂移（见 ex13 的 `ordinal corrupted: true`，V1→V2 换声明顺序后 `read by ordinal` 从 ACTIVE 变成 NEW）。正确写法：用 `EnumTypeHandler` 存 `name()`（可读、允许中间插入，代价是列宽更大），或自定义 TypeHandler 存**业务 code**（如 10/20/30）并保持「code 一经上线永不重排」的约定；出问题的从来不是 TypeHandler，而是「顺序」本身。

20. **Mapper 接口方法重载导致 statement 冲突** —— statementId 是「接口全限定名 + 方法名」，不含参数列表，因此 `select(String)` 与 `select(Integer)` 会注册成同一个 id，先/后解析器覆盖幅度取决于注册顺序，被调用的 SQL 可能与预期相反（见 ex12 的 `overload conflict : true` 与 `kept statement`）。同类地，同一 namespace 下 XML 与注解写了同名 id 也会启动报「Mapped Statements collection already contains value」。正确写法：方法名唯一（`selectById` / `selectByCode`），团队统一只用 XML 或只用注解。

21. **`<include>` 的 `${}` 属性替换写错时不会报错，只是原样保留** —— `<sql>` 片段里的 `${alias}` 是**解析期**的 `PropertyParser` 替换（不是 `#{}` 的**执行期**参数占位），未定义的属性会被原样输出成字面量 `${alias}`，最终 SQL 里带着花括号跑，某些方言下直接语法错误、某些方言下变成一列名为 `${alias}` 的列。正确写法：把 `<property>` 的 `value` 固定为**字面量常量**（绝不来自用户输入——那是注入面），并利用「写错属性名会在 SQL 里原样出现」这一特征做自检。

---

> 相关回顾：`spring-ch06` 的 `pitfalls.md` 已覆盖 `${}` 的基础用法、`resultMap` 映射与自增主键回填；本章陷阱对准动态 SQL、两级缓存、延迟加载与插件四个进阶面。
