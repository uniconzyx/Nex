# spring-ch07 学习目标：MyBatis 进阶：动态 SQL、缓存与插件

## 一、本章定位

`spring-ch06` 解决了「一条 SQL 怎么写、参数怎么绑、结果怎么映射」。
本章解决「**一批 SQL 怎么按条件组装、结果怎么被缓存、框架怎么被改写**」——
也就是 MyBatis 从「能用」走向「可维护、可优化」的三个进阶面：

- **动态 SQL**：把拼接逻辑从 Java 字符串搬到 XML 标签，消灭 `WHERE 1=1` 与悬空 `AND`；
- **缓存**：一级（SqlSession）与二级（namespace）两级缓存的作用域与失效条件，以及它们造成的脏读事故；
- **插件**：拦截器责任链如何在不改业务代码的前提下改写 SQL（分页插件是最大用户）。

## 二、知识目标

1. 掌握动态 SQL 六个标签的语义：`<if>`、`<choose>/<when>/<otherwise>`、`<foreach>`、
   `<trim>`、`<where>`、`<set>`，以及 `<sql>` + `<include>` + `<property>` 的片段复用机制；
2. 能从**解析管线**层面说清 `#{}` 与 `${}` 的本质区别（ParameterMapping + TypeHandler 绑定 vs OGNL 取值后文本插值），
   并据此解释 SQL 注入的利用链与 `${}` 的唯一合法场景；
3. 掌握一级缓存的 Key 构成、失效触发点（增删改、`commit`/`close`、`flushCache="true"`、`clearCache()`），
   以及二级缓存「namespace 级、提交后才对其他会话可见、对象需可序列化」三条硬规则；
4. 理解延迟加载（`lazyLoadingEnabled` / `fetchType` / `aggressiveLazyLoading`）与
   「嵌套查询 N+1」和「嵌套结果一次 join」的代价差异；
5. 理解插件拦截的四大件（`Executor` / `StatementHandler` / `ParameterHandler` / `ResultSetHandler`），
   并能说明分页插件如何改写 SQL、为什么 count 查询会出错；
6. 掌握 TypeHandler 与枚举映射（`EnumOrdinalTypeHandler` / `EnumTypeHandler` / 自定义），
   以及 MapperProxy 的 JDK 动态代理绑定机制；
7. 能对 MyBatis 与 Hibernate/JPA 做出有依据的取舍。

## 三、能力目标

- 能用**纯 Java（单文件、无 Maven 依赖）复刻**动态 SQL 拼接、`#{}` / `${}` 替换与注入对照、
  L1/L2 缓存作用域与失效、LRU 淘汰、延迟加载代理、N+1 计数、分页 SQL 改写、MapperProxy 动态代理、
  枚举 TypeHandler；并用 Python 对照 JPA 脏检查与 MyBatis 显式 SQL 的差异；
- 能针对「动态 SQL 拼出悬空 AND」「`${}` 导致注入」「一级缓存读到旧值」
  「二级缓存脏读跨会话」「N+1 拖垮接口」「分页 count 数不对」「枚举 ordinal 存库后语义漂移」
  这七类真实事故给出根因与修法。

## 四、学习路径建议

1. 先读 `concept/01`（动态 SQL 标签与片段复用）与 `concept/02`（`#{}` / `${}` 的解析管线与注入）；
2. 再读 `concept/03`（一级 / 二级缓存）与 `concept/04`（延迟加载、分页插件、TypeHandler、MapperProxy）；
3. 跑 `examples/` 的 14 个示例（13 个纯 Java、1 个纯 Python），全部可独立编译运行；
   重点看 ex05（注入对照）、ex06 / ex07（缓存作用域）、ex10（N+1 计数）、ex11（分页改写）；
4. 用 `exercises.json` / `interview.json` / `project.json` 自测，重点做 `project.json` 的 MiniBatis 进阶改造。

## 五、前置知识

- `spring-ch06`：MyBatis 基础（SqlSession、Mapper 绑定、`#{}` / `${}` 入门、`resultMap`、主键回填）；
- 软前置（可选，不阻断学习）：
  - `java` 语言的反射与 JDK 动态代理（`java.lang.reflect.Proxy`）——理解 MapperProxy 与延迟加载代理的前提；
  - SQL 标准里的 `LIMIT` / `OFFSET` 与 `GROUP BY` 语义——理解分页改写与 count 偏差的前提。

## 六、本章 GitHub 资源

| 仓库 | Star | 用途 |
|---|---|---|
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | 完整的 MyBatis + SpringBoot 电商工程，动态 SQL 与分页插件的真实用法 |
| [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81563 | `mybatis-spring-boot-starter` 的自动配置与 `<settings>` 映射 |
| [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 39566 | 企业级 MyBatis-Plus 用法：多数据源、逻辑删除、分页与缓存实践 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | 大量 MyBatis 独立小例（动态 SQL、缓存、TypeHandler、插件） |


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Spring 5 框架教程 | [视频](https://www.bilibili.com/video/BV1Vf4y127N5/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · SpringMVC 2021 教程 | [视频](https://www.bilibili.com/video/BV1Ry4y1574R/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · MyBatis 实战教程 | [视频](https://www.bilibili.com/video/BV1mW411M737/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 雷丰阳 · SpringBoot2 零基础入门 | [视频](https://www.bilibili.com/video/BV19K4y1L7MT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Spring Cloud 微服务 | [视频](https://www.bilibili.com/video/BV18E411x7eT/) | 本学科配套视频，建议结合本章示例与习题观看 |
