# MyBatis 实战手记：凯喵被 `${}` 坑掉一个库的十二个现场

> 这一章讲 MyBatis 的定位、`#{}` 与 `${}`、ResultMap 与驼峰映射、主键回填与配置。概念不多，但线上事故率极高——`${}` 注错、驼峰没开导致字段全 null、主键回填拿不到 id、一级缓存串数据。这篇手记用十二个现场把这条链路走一遍。

## 开场：MyBatis 是"半自动"的 ORM，这个定位决定了它的全部性格

JPA/Hibernate 是"全自动"：你写实体和注解，SQL 由框架生成。MyBatis 是"半自动"：**SQL 由你写，映射由框架做**。

这个选择带来两个后果：好处是 SQL 完全可控（能写复杂查询、能精确调优）；代价是所有 SQL 相关的坑都得自己扛（注入、N+1、字段映射、动态 SQL 拼接）。

所以学 MyBatis 的正确姿势不是背注解，而是**理解它做了什么、没做什么**：它做了参数绑定和结果映射，它没做 SQL 生成和查询优化。下面十二个现场就按这个分界铺开。

### 现场一：`${}` 拼进 SQL，一次注入删了整张表

```xml
<!-- 危险写法 -->
<select id="findByName" resultType="User">
    SELECT * FROM users WHERE name = '${name}'
</select>
```

传 `name = "' OR '1'='1"`，SQL 变成 `WHERE name = '' OR '1'='1'` — 全表返回。传 `name = "'; DROP TABLE users; --"` 就直接删表。

`${}` 是**字符串直接拼接**，相当于把用户输入原样塞进 SQL。`#{}` 是**预编译占位符**，生成 `?` 并由驱动做参数绑定，值永远不会被当成 SQL 语法。

```xml
<!-- 正确写法 -->
<select id="findByName" resultType="User">
    SELECT * FROM users WHERE name = #{name}
</select>
```

凯喵的团队约定是：**代码评审里看到 `${}` 就必须给出理由**。它只在这几种情况下合法：

```text
1. 表名/列名动态（无法用占位符）
   SELECT * FROM ${tableName} WHERE id = #{id}
   → 但 tableName 必须来自白名单枚举，绝不能直接用请求参数

2. ORDER BY 的字段名
   ORDER BY ${sortField} ${sortOrder}
   → 同样必须白名单校验（sortField ∈ {id, created_at}，sortOrder ∈ {ASC, DESC}）

3. LIKE 的模糊匹配（也不推荐，见现场二）
```

### 现场二：`LIKE '%#{keyword}%'` 编译报错，改成 `${}` 又注入

```xml
<!-- 报错：占位符不能放在引号里 -->
WHERE name LIKE '%#{keyword}%'

<!-- 危险：改成 ${} 能跑，但注入了 -->
WHERE name LIKE '%${keyword}%'

<!-- 正确：用 CONCAT 把通配符拼在 SQL 层，值仍走占位符 -->
WHERE name LIKE CONCAT('%', #{keyword}, '%')

<!-- 或者：在 Java 层拼好通配符，SQL 里只留占位符 -->
WHERE name LIKE #{keyword}     <!-- 传参时 keyword = "%" + raw + "%" -->
```

第二种做法有个副作用：如果用户输入里本身就含 `%` 或 `_`，会被当成通配符。需要精确匹配时得转义：

```sql
WHERE name LIKE CONCAT('%', REPLACE(REPLACE(#{kw}, '\\', '\\\\'), '%', '\\%'), '%') ESCAPE '\\'
```

### 现场三：驼峰映射没开，查出来字段全是 null

数据库列叫 `user_name`，实体字段叫 `userName`。查询能返回行，但 `userName` 是 `null`。

原因是 MyBatis 默认**按列名精确匹配属性名**，`user_name` 找不到 `userName`。开启驼峰映射即可：

```yaml
mybatis:
  configuration:
    map-underscore-to-camel-case: true
```

用 Spring Boot 时有个高频坑：**配置写在了错误的位置**。`mybatis.configuration` 只在使用 `mybatis-spring-boot-starter` 且没有自定义 `SqlSessionFactory` 时生效；如果你自己 `new SqlSessionFactoryBean()`，必须显式设置：

```java
@Bean
public SqlSessionFactory sqlSessionFactory(DataSource ds) throws Exception {
    SqlSessionFactoryBean f = new SqlSessionFactoryBean();
    f.setDataSource(ds);
    org.apache.ibatis.session.Configuration c = new org.apache.ibatis.session.Configuration();
    c.setMapUnderscoreToCamelCase(true);      // ← 手动 new 时必须自己设
    f.setConfiguration(c);
    return f.getObject();
}
```

这类"配置不生效"的问题，排查方法是**在启动日志里打印 `configuration.isMapUnderscoreToCamelCase()`**，别靠猜。

### 现场四：以为驼峰映射能解决一切，别名和 JSON 字段还是 null

驼峰只能处理"下划线 ↔ 驼峰"这一种差异。以下三种情况仍需 ResultMap：

```text
1. 列名与属性名语义不同：db 列 is_valid → 属性 enabled
2. 关联对象：user 表 + order 表，需要映射成嵌套对象
3. 类型转换：db 存 JSON 字符串，属性是 List<Tag>
```

ResultMap 的写法：

```xml
<resultMap id="UserWithOrders" type="User">
    <id     property="id"       column="user_id"/>
    <result property="userName" column="user_name"/>
    <result property="enabled"  column="is_valid"/>          <!-- 列名语义不同 -->
    <collection property="orders" ofType="Order">            <!-- 一对多 -->
        <id     property="id"     column="order_id"/>
        <result property="amount" column="amount"/>
    </collection>
</resultMap>
```

`<id>` 标签不只是"主键标记"，它还决定**嵌套结果如何分组**——一对多查询时，`<id>` 相同的结果行会被合并成同一个对象。漏写 `<id>` 会导致每行都创建一个新对象，出现重复。

### 现场五：一对多查询写了 JOIN，结果用户被复制了 N 份

```xml
<select id="findUsersWithOrders" resultMap="UserWithOrders">
    SELECT u.id user_id, u.name user_name, o.id order_id, o.amount
    FROM users u LEFT JOIN orders o ON o.user_id = u.id
</select>
```

一个用户有 5 个订单，结果就有 5 行。如果 `resultMap` 里 `<id>` 写对了，MyBatis 会合并成 1 个 User 带 5 个 Order；写错或没写，就得到 5 个重复 User。

另一种更省事的做法是**分两次查（N+1 但可控）**：

```xml
<resultMap id="UserWithOrdersLazy" type="User">
    <id property="id" column="id"/>
    <collection property="orders" column="id"
                select="selectOrdersByUserId" fetchType="lazy"/>
</resultMap>
```

代价是 N+1 查询，但可以通过 `lazyLoadingEnabled` + 批量加载（`fetchType="lazy"` 配 `@BatchSize`）缓解。**数据量小时分两次查往往更快**，因为 JOIN 会产生大量重复数据、传输和去重都浪费。

### 现场六：`useGeneratedKeys` 没配，插入后拿不到主键

```xml
<!-- 拿不到 id：insert 之后 user.getId() 仍是 null -->
<insert id="insert">
    INSERT INTO users(name, age) VALUES (#{name}, #{age})
</insert>

<!-- 正确：开启主键回填 -->
<insert id="insert" useGeneratedKeys="true" keyProperty="id">
    INSERT INTO users(name, age) VALUES (#{name}, #{age})
</insert>
```

三个易错点：

```text
1. keyProperty 要写实体里的属性名，不是列名（是 id 不是 user_id）
2. 批量插入时 keyProperty 不支持嵌套属性（如 user.id），要用 selectKey
3. Oracle 等无自增的库要改成 <selectKey order="BEFORE"> + sequence
```

`selectKey` 的替代写法：

```xml
<insert id="insert">
    <selectKey keyProperty="id" resultType="long" order="AFTER">
        SELECT LAST_INSERT_ID()
    </selectKey>
    INSERT INTO users(name) VALUES (#{name})
</insert>
```

注意 `order="AFTER"`（MySQL 自增）与 `order="BEFORE"`（Oracle sequence 要先取号）的区别，写反了拿到的会是 0 或 null。

### 现场七：一级缓存导致同一事务内读到旧数据

MyBatis 有**一级缓存**（`SqlSession` 级别，默认开启）和二级缓存（`namespace` 级别，默认关闭）。

一级缓存的行为：同一个 `SqlSession` 内，相同的 `statement + 参数` 会直接返回缓存结果，**不查库**。问题在于：

```java
// 同一个 SqlSession（Spring 里默认一个事务一个 Session）
User u1 = mapper.selectById(1);      // 查库
// ……中间用别的途径改了库（比如另一条 SQL、或直接 JDBC）……
User u2 = mapper.selectById(1);      // 直接返回缓存，看到旧值
```

因为两次调用参数相同，第二次根本不会发 SQL。如果这中间数据被改了（尤其是通过非 MyBatis 的途径），就会读到脏数据。

两种处理：

```yaml
# 方案一：关掉一级缓存（几乎无性能损失，因为事务通常很短）
mybatis:
  configuration:
    local-cache-scope: statement
```

```java
// 方案二：在需要强一致的查询上强制刷新（加 flushCache）
// XML 里：<select ... flushCache="true">
```

凯喵的建议：**Spring 环境下直接把 `local-cache-scope` 设为 `statement`**。因为 Spring 的 SqlSession 生命周期短，一级缓存的收益很小，但它带来的"读到旧值"却很难排查。

### 现场八：二级缓存开了却没配事务感知，跨库读到脏数据

二级缓存按 `namespace` 生效，跨 `SqlSession` 共享。但它有严格的前提：**所有对这张表的写操作都必须经过同一个 namespace**，否则缓存不会失效。

```xml
<cache eviction="LRU" flushInterval="60000" size="1024" readOnly="false"/>
```

风险清单：

```text
1. 多表 JOIN 的查询被缓存后，任一表变更都可能让缓存失效不了
2. 其他系统（定时任务、另一个服务）直接改库 → 缓存永远不知道
3. readOnly="false" 要求实体可序列化，且返回的是副本（有序列化开销）
```

凯喵的结论：**除非能保证"单服务独占这张表"，否则不要开二级缓存**。多实例部署时更危险——每个实例各有一份缓存，A 改了库只清 A 的缓存，B 还在用旧的。真需要跨实例缓存，用 Redis。

### 现场九：动态 SQL 的 `<if>` 判断字符串用了 `!= ''`

```xml
<if test="name != null and name != ''">
    AND name = #{name}
</if>
```

看起来没问题，但几个坑：

```text
1. 单字符比较的陷阱：test="type == 'Y'" 里 'Y' 会被 OGNL 当成 char，
   type 是 String 时比较结果为 false → 条件永远不成立
   正确写法：test='type == "Y"'（外层单引号、内层双引号）或 test="'Y'.equals(type)"

2. 数字比较：test="age > 18" 里 age 是 String 时会做字符串比较，"9" > "18" 为 true
   正确写法：确保类型一致，或 test="age != null and age > 18"（配合 Integer 类型）

3. 集合判空：test="list != null and list.size() > 0"（不要写 list != ''）
```

`<if>` 之外还有 `<choose>`（相当于 switch）、`<foreach>`（批量 in / 批量插入）、`<where>`（自动处理 AND 前缀）、`<set>`（自动处理逗号）。其中 `<where>` 和 `<set>` 值得常用，因为它们能自动去掉多余的 `AND`/逗号。

### 现场十：`<foreach>` 批量插入拼出的 SQL 太长，被 MySQL 拒绝

```xml
<insert id="batchInsert">
    INSERT INTO users(name, age) VALUES
    <foreach collection="list" item="u" separator=",">
        (#{u.name}, #{u.age})
    </foreach>
</insert>
```

一次插 5000 条时，SQL 长度可能超过 `max_allowed_packet`（默认 4MB 或 64MB），报 `Packet too large`。

正确做法是**分批**：

```java
public void batchInsert(List<User> users) {
    int batch = 500;
    for (int i = 0; i < users.size(); i += batch) {
        mapper.batchInsert(users.subList(i, Math.min(i + batch, users.size())));
    }
}
```

另一个思路是用 `ExecutorType.BATCH`（真正的 JDBC 批处理，逐条 addBatch 后 executeBatch）：

```java
SqlSession session = sqlSessionFactory.openSession(ExecutorType.BATCH);
try {
    UserMapper m = session.getMapper(UserMapper.class);
    for (User u : users) m.insert(u);      // 只是 addBatch，不发 SQL
    session.flushStatements();              // 真正执行
    session.commit();
} finally {
    session.close();
}
```

`ExecutorType.BATCH` 的优势是复用预编译语句、减少网络往返；缺点是拿不到自增主键（除非驱动支持 `getGeneratedKeys` 批量返回）。

### 现场十一：`resultType` 用了 Map，字段名大小写和类型全靠猜

```xml
<select id="stat" resultType="java.util.HashMap">
    SELECT COUNT(*) cnt, status FROM orders GROUP BY status
</select>
```

返回 `List<Map<String,Object>>`，看着方便，但三个问题：字段名大小写依赖驱动配置；数字类型是 `BigDecimal`/`Long` 不确定；没有编译期检查，改列名不会报错。

更好的做法是定义一个 DTO：

```java
public record StatusStat(long cnt, String status) {}
```

```xml
<select id="stat" resultType="StatusStat">
    SELECT COUNT(*) AS cnt, status FROM orders GROUP BY status
</select>
```

配合 `map-underscore-to-camel-case`，列名与构造参数自动对应（record 需要 MyBatis 3.5.x + 构造器映射，或显式写 `@ConstructorArgs`）。

### 现场十二：以为 MyBatis 会做查询优化，其实它只负责"翻译"

最后一个观念性现场。有人问"为什么这条 SQL 在 MyBatis 里很慢"，排查半天怀疑框架。

真相是：**MyBatis 只做三件事——把参数绑进 SQL、把结果映射成对象、管理会话与事务**。它不解析 SQL、不优化执行计划、不自动加索引。SQL 慢就是 SQL 慢，去数据库里 `EXPLAIN` 才是正解。

同理，它也不会帮你解决 N+1：`<collection select="...">` 是显式的 N+1，它只是让写法更简洁。要不要用批量加载、要不要改成 JOIN，全靠你自己判断。

凯喵的总结：**MyBatis 把"控制权"交给你，也就把"责任"交给你**。这既是它相对 JPA 的优势（复杂查询能写、能调优），也是它的门槛（所有 SQL 层面的坑都要自己扛）。

## 三视角解析
### 🧑‍💻 程序员视角
`${}` 是字符串直接拼接，`ORDER BY ${column}` 里传入 `id; DROP TABLE users` 就是一次完整的注入——所有用户输入必须走 `#{}`（预编译占位符）。`LIKE '%#{kw}%'` 编译不过，因为 `#{}` 会被替换成 `?`，正确写法是 `LIKE CONCAT('%', #{kw}, '%')`。驼峰映射没开（`map-underscore-to-camel-case`），`user_name` 映射不到 `userName`，查出来全是 `null`。

### 🎓 博士生视角
MyBatis 的本质是「SQL 与 Java 对象的映射器」：`#{}` 走 `PreparedStatement` 的参数绑定，能防注入且可复用执行计划；`${}` 走字符串替换，灵活但危险。一级缓存是 `SqlSession` 级（默认开启，同一会话内相同查询复用），二级缓存是 `Mapper` 级（需显式开启，跨会话共享，但要求结果可序列化且数据变更时失效）。理解两级缓存的边界，才能解释「为什么同一事务里改了数据、查询还是旧值」。

### 📚 考研者视角
面试高频：
1. **`#{}` 与 `${}`**：预编译 vs 字符串拼接，前者防注入。`${}` 只能用于表名、列名等无法参数化的位置，且必须白名单校验。
2. **一级/二级缓存**：作用域、默认开关、失效时机。
3. **动态 SQL**：`<if>`、`<choose>`、`<foreach>`、`<where>` 的用法与 `where 1=1` 的替代。
4. **resultMap**：字段映射、关联查询（`association`/`collection`）、延迟加载。

## 收尾：凯喵的 MyBatis 五条铁律

**铁律一 · 禁用 `${}`** —— 除非是表名/列名/排序字段，且必须白名单校验。看到就要问理由。

**铁律二 · 映射显式化** —— 开驼峰解决 90%，剩下的用 ResultMap 明确写；嵌套查询必须有 `<id>`。

**铁律三 · 主键回填要验** —— `useGeneratedKeys` + `keyProperty` 写对，插入后断言 id 不为空。

**铁律四 · 缓存慎开** —— 一级缓存设 `statement` 作用域；二级缓存只在单服务独占表时考虑，多实例用 Redis。

**铁律五 · 慢查询去数据库查** —— MyBatis 不背这个锅，`EXPLAIN` 是唯一正解。

最后说一句方法上的话。MyBatis 的坑有个共同特征：**它们都不会在启动时报错，只会在某个特定数据、特定并发、特定配置下悄悄出错**。`${}` 平时跑得好好的，直到有人输入了单引号；驼峰没开时字段全 null，但接口不报错；一级缓存读到旧值，日志里连 SQL 都没有。

所以最好的防御不是记住这十二条，而是**建立"显式"的习惯**：映射显式写、配置显式验证（启动时打印关键配置）、SQL 显式审查（评审必看 `#{}` 和索引）。MyBatis 给你的是控制权，而控制权只有配合纪律才有价值——这也是所有"半自动"工具的共同性格。

### 补充：把配置显式化，是 MyBatis 项目最值得的一次投资

最后补一条关于工程实践的建议。MyBatis 的问题有个共同特征：**大部分不会在启动时报错**，只在特定数据或特定配置下悄悄出错。所以最好的防御不是记住这十二条，而是在项目初始化时就把关键配置**显式化并且可验证**。

具体做法是在启动时打印一份"生效配置快照"，包含五个最常出错的项：

```java
@Component
public class MyBatisConfigPrinter implements ApplicationRunner {
    private final SqlSessionFactory factory;
    public MyBatisConfigPrinter(SqlSessionFactory factory) { this.factory = factory; }

    @Override
    public void run(ApplicationArguments args) {
        var c = factory.getConfiguration();
        log.info("mapUnderscoreToCamelCase = {}", c.isMapUnderscoreToCamelCase());
        log.info("localCacheScope          = {}", c.getLocalCacheScope());
        log.info("defaultExecutorType      = {}", c.getDefaultExecutorType());
        log.info("defaultStatementTimeout  = {}", c.getDefaultStatementTimeout());
        log.info("jdbcTypeForNull          = {}", c.getJdbcTypeForNull());
    }
}
```

这份快照的价值在于：**把"我以为配了"变成"日志里确实生效了"**。凯喵排查过的 MyBatis 事故里，有相当一部分根因是"配置文件放错位置"或"自定义 SqlSessionFactory 覆盖了 starter 的配置"——这类问题看代码永远看不出来，只有把运行时值打出来才能发现。

再配一条静态检查：在 CI 里 grep 所有 Mapper XML，出现 `${` 就报警。这条规则的成本几乎为零，但能挡住最常见也最危险的一类事故。工具的价值从来不在于它多强大，而在于它把纪律变成了默认行为。
