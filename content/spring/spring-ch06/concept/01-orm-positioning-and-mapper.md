# 一、MyBatis 定位与 Mapper 绑定

## 1. 半自动 ORM 的定位与 SqlSession / Mapper 动态代理

MyBatis 是「半自动」持久层框架：程序员写 SQL，框架负责参数绑定与结果映射，
介于原生 JDBC（全手写）与 JPA/Hibernate（全自动）之间。它把对象-关系阻抗失配里
最容易出错的两段（参数绑定、结果映射）交给框架，而把「SQL 怎么写」留给人。

### 🧑‍💻 程序员视角
- Mapper 接口不写实现类：MyBatis 用 JDK 动态代理在运行时生成代理对象，把接口方法绑定到 XML/注解里的 SQL 语句 id；
- SqlSession 是「一次数据库连接会话」的句柄，必须通过它获取 Mapper（`sqlSession.getMapper(UserMapper.class)`），用完必须 close；
- 工程惯例：SpringBoot 里用 `@MapperScan` + 注入 Mapper，别自己手动开 SqlSession；事务由 Spring 托管，SqlSession 生命周期交给框架。

### 🎓 博士生视角
- 半自动 = 在「表达力」与「自动化」之间的 Pareto 最优点：把易错的绑定/映射自动化，保留 SQL 控制权；
- Mapper 绑定本质是「接口到 SQL 元数据的一次查表」：MapperProxy 拦截方法调用，按「接口全限定名 + 方法名」拼出 statementId，到 Configuration 的 mappedStatements 注册表取 MappedStatement；
- SqlSession 内部持有一个 Executor（Simple / Reuse / Batch），所有增删改查最终归一到 `Executor.query/update`，插件（拦截器）就挂在这一层。

### 📚 考研者视角
- 笔面标准问法：「MyBatis 和 Hibernate/JPA 的区别？」标准答：MyBatis 是半自动 ORM，SQL 手写、映射自动；Hibernate 是全自动 ORM，靠对象状态自动生成 SQL，屏蔽 SQL 细节。
- 易错：认为「MyBatis 不是 ORM」是错的——它仍是对象关系映射，只是把 SQL 控制权交还开发者，属「半自动」；对比 JPA 的「全自动」。
- 关联考点：Mapper 接口为什么不需要实现类（动态代理）、SqlSession 与 Connection 的关系（一对一会话）。

## 2. 与 JDBC / JPA 的取舍

直接用 JDBC：SQL 与 Java 代码耦合、手动 ResultSet→对象、样板代码多（90% 是 try/catch/close），MyBatis 消除这些样板。JPA 适合 CRUD 重、查询简单的领域，但复杂 join/统计时生成 SQL 不可控。

### 🧑‍💻 程序员视角
- JDBC 样板：获取连接、预编译、遍历 ResultSet、关资源四步重复；MyBatis 用 Mapper 一行调用替代；
- JPA 适合快速开发的内部系统，复杂查询/深度优化时反而难调（生成的 SQL 看不到、加 hint 难）；
- 选型经验：互联网高并发业务常用 MyBatis（SQL 可控、便于 DBA 优化）；内部管理系统可用 JPA 提速。

### 🎓 博士生视角
- 取舍的底层是「声明式 vs 命令式」：JPA 声明式（描述对象，SQL 由 provider 推导），MyBatis 命令式（直接写 SQL，框架只做映射）；
- 阻抗失配（impedance mismatch）：对象图 vs 关系表的范式差异。JPA 用脏检查/延迟加载弥合，代价是复杂对象的 session 管理与 N+1；MyBatis 用 ResultMap 显式声明映射，把失配成本前置到配置；
- 两者都逃不开 N+1：JPA 是懒加载触发，MyBatis 是手写循环里调 Mapper。

### 📚 考研者视角
- 笔面标准问法：「什么场景用 MyBatis，什么用 JPA？」标准答：需精细控制 SQL、复杂查询、性能敏感 → MyBatis；快速 CRUD、领域简单 → JPA。
- 易错：以为「JPA 一定比 MyBatis 慢」或反之——性能取决于 SQL 质量与映射开销，不是框架标签；两者的 N+1 是同类问题。
- 关联考点：ORM 解决「对象-关系阻抗失配」的几种范式（ActiveRecord / DataMapper / 注解驱动）。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | Mapper 靠动态代理绑定；事务交给 Spring；高并发业务偏好 MyBatis。 |
| 博士生 | 半自动是 Pareto 最优点；绑定=接口到 MappedStatement 查表；阻抗失配处理成本前置。 |
| 考研者 | MyBatis vs Hibernate 必考题；Mapper 为何无实现类、SqlSession 与 Connection 关系。 |