# 四、主键回填与 XML/注解配置

## 1. 主键回填：useGeneratedKeys 与 selectKey

插入后数据库自增主键需要回填到实体。MyBatis 提供 `useGeneratedKeys + keyProperty`（数据库自增）
与 `<selectKey>`（序列/特殊数据库）两种机制，由 KeyGenerator 在 update 之后接管。

### 🧑‍💻 程序员视角
- MySQL 自增：`<insert useGeneratedKeys="true" keyProperty="id">`，插入后 `user.getId()` 直接拿到自增主键，无需再查；
- Oracle 序列：没有自增列，用 `<selectKey order="BEFORE" keyProperty="id">SELECT seq.nextval FROM dual</selectKey>` 先取号再插入；
- 坑：`keyProperty` 必须和实体属性名一致；`useGeneratedKeys` 只对支持自增的 JDBC 驱动有效（MySQL/PG），对 Oracle 不生效需 selectKey。

### 🎓 博士生视角
- 回填底层：JDBC 的 `Statement.getGeneratedKeys()` 在 executeUpdate 后返回数据库生成的主键列，MyBatis 按 keyProperty 写回实体——依赖驱动实现 getGeneratedKeys；
- order 语义：BEFORE 用于「先取号再插入」（序列型），AFTER 用于「先插入再取回」（自增型）；
- 耦合点：在 PreparedStatementHandler.update 之后，由 Jdbc3KeyGenerator / SelectKeyGenerator 接管回填，是 Executor 流程里的一个钩子。

### 📚 考研者视角
- 笔面标准问法：「MyBatis 怎么拿到插入后的自增主键？」标准答：`<insert useGeneratedKeys="true" keyProperty="id">`，插入后实体主键被自动回填。
- 易错：以为「insert 返回值就是主键」——insert 返回的是受影响行数，主键通过 keyProperty 回填到传入对象，不是返回值。
- 关联考点：JDBC getGeneratedKeys、Oracle 序列与 selectKey 的 order=Before。

## 2. XML 映射 vs 注解：两种写法归一

SQL 可写在 XML（<mapper>）或接口注解（@Select 等）上。两种方式在解析后归一为同一份 MappedStatement 元数据。

### 🧑‍💻 程序员视角
- XML 适合复杂 SQL（动态 SQL、长查询、关联），可读、好维护；注解适合短小 CRUD，写在接口上零跳转；
- 团队约定优先：要么纯 XML 要么纯注解，混用（同一 Mapper 既 XML 又注解）易踩 statement 重复/id 冲突；
- 全局配置：`<settings>` 里 mapUnderscoreToCamelCase、cacheEnabled、lazyLoadingEnabled 等影响全局行为，必须和 Mapper 配合理解。

### 🎓 博士生视角
- 两种写法运行时归一：XML 经 XMLMapperBuilder 解析成 MappedStatement，注解经 MapperAnnotationBuilder 解析也生成 MappedStatement，最终都进 Configuration.mappedStatements——差异只在声明来源；
- 注解的 `<script>` 也能写动态 SQL，说明两种写法表达能力在 XML `<script>` 标签下等价，只是 XML 在编辑器支持与多行可读性上更友好；
- 全局 settings 本质是一组全局开关，在 Configuration 构建期写进各组件默认行为，是「约定」的集中表达。

### 📚 考研者视角
- 笔面标准问法：「XML 和注解方式怎么选？」标准答：简单 CRUD 用注解方便，复杂/动态 SQL 用 XML 清晰；二者最终都解析成 MappedStatement。
- 易错：以为「注解方式没有 MappedStatement」——错，注解同样生成 MappedStatement，只是来源不同。
- 关联考点：MyBatis 启动流程（SqlSessionFactoryBuilder → Configuration → MappedStatement 注册表）。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 自增用 useGeneratedKeys；Oracle 用 selectKey；XML/注解别混用。 |
| 博士生 | 回填依赖 getGeneratedKeys；XML 与注解归一为 MappedStatement。 |
| 考研者 | insert 返回行数非主键；注解也有 MappedStatement。 |