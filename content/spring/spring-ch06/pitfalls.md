# spring-ch06 易错点

1. **用 `${}` 拼接前端字符串导致 SQL 注入** —— 任何来自用户的文本若经 `${}` 拼进 SQL，会被当 SQL 执行（如 `name = ${name}` 输入 `' OR '1'='1` 把全表拖出）。正确写法：值是 `#{}` 占位符；只有表名/列名/排序字段这类不能作为占位符的才用 `${}`，且 `${}` 的取值必须来自白名单。

2. **列名与属性名不一致又没开驼峰也没写 resultMap，字段查出 null** —— 数据库 `user_name`，实体 `userName`，既没开 `mapUnderscoreToCamelCase` 也没写 `<result>`，MyBatis 自动映射按同名匹配失败。正确写法：开驼峰，或用 `resultMap` 显式 `<result column="user_name" property="userName"/>`。

3. **把 `insert` 返回值当主键** —— `insert` 返回的是受影响行数（int），不是主键。正确写法：用 `useGeneratedKeys="true" keyProperty="id"`，插入后从传入实体对象 `user.getId()` 取回自增主键。

4. **在 Oracle 上用 `useGeneratedKeys` 期望自增** —— Oracle 没有自增列，`useGeneratedKeys` 对其无效。正确写法：用 `<selectKey order="BEFORE" keyProperty="id">SELECT seq.nextval FROM dual</selectKey>` 先取序列号再插入。

5. **以为没开驼峰也会自动映射下划线** —— 默认是「属性名 = 列名」严格同名，`user_name` 不会自动变成 `userName`。正确写法：显式开启 `mapUnderscoreToCamelCase=true`，或手写 resultMap。

6. **resultMap 里两表同名列（id）互相覆盖** —— 主表 `id` 与关联表 `id` 都映射到属性 `id`，后者覆盖前者，关联结果错乱。正确写法：用 `<id column="u_id" property="userId"/>` 给关联列起别名，或用 `resultMap` 的 `columnPrefix`。

7. **嵌套查询 `<association select=...>` 触发 N+1 却以为是一次查询** —— 1 次主查询 + 每行 1 次子查询 = N+1 次 SQL。正确写法：用嵌套结果（`<collection>` 一次 join 查出并按父 id 分组），或开启延迟加载并评估是否真的需要。

8. **`#{}` 传 `null` 没给 `jdbcType` 导致部分驱动报错** —— 某些 JDBC 驱动（尤其 Oracle）对 null 参数需要类型提示。正确写法：写成 `#{val,jdbcType=VARCHAR}`，显式告知列类型。

9. **同一 Mapper 既写 XML 又写注解导致 statement id 冲突/重复** —— 接口方法上的 `@Select` 与 XML 里同名 id 都会被注册成 MappedStatement，启动报「Mapped Statements collection already contains value」。正确写法：团队统一只 XML 或只注解，不混用。

10. **动态 SQL `<if test>` 里用 `&&` / `==` / 单 `&`** —— MyBatis 的 test 表达式是 OGNL，逻辑与是 `and`、相等是 `==` 但字符串比较要用 `eq`。正确写法：`<if test="name != null and age > 0">`；字符串相等用 `eq`（如 `type eq 'A'`）。

11. **`<foreach>` 的 `collection` 名写错导致 `NullPointerException`** —— 参数是 `List` 时默认名 `list`，数组是 `array`，`@Param` 后按注解名取；写错集合名取不到。正确写法：用 `@Param("ids")` 显式命名，并在 `collection="ids"` 对应；`item`/`open`/`close`/`separator` 也要配齐。

12. **一级缓存踩坑：同一 SqlSession 内绕过 MyBatis 直连 JDBC 改了库，却读到旧值** —— 一级缓存（SqlSession 级）默认开启，会话内相同查询命中缓存，外部直改库不会让缓存失效。正确写法：避免混用直连 JDBC；或显式 `sqlSession.clearCache()`；或提交/关闭会话。

13. **二级缓存返回的是对象引用，被修改后污染缓存** —— 二级缓存（namespace 级）跨 SqlSession 共享；若把取出的对象改了，缓存里的同一引用也变。正确写法：二级缓存对象需可序列化且建议只读；或返回后做防御性拷贝。

14. **Mapper 接口方法重载导致 statement 绑定歧义** —— MyBatis 用「全限定名 + 方法名」做 statementId，不支持按参数类型区分重载，重载方法会产生相同 id 冲突。正确写法：方法名唯一（如 `selectById` / `selectByCode`），不要用重载。