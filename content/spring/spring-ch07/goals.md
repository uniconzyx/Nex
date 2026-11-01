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
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84995 | 完整的 MyBatis + SpringBoot 电商工程，动态 SQL 与分页插件的真实用法 |
| [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81722 | `mybatis-spring-boot-starter` 的自动配置与 `<settings>` 映射 |
| [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40149 | 企业级 MyBatis-Plus 用法：多数据源、逻辑删除、分页与缓存实践 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37308 | 大量 MyBatis 独立小例（动态 SQL、缓存、TypeHandler、插件） |
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「条件标签」「智能修剪」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,722 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「条件标签」「智能修剪」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,149 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「条件标签」「智能修剪」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | 全章 | Spring 生态系统化教程代码；本章先读与「条件标签」「智能修剪」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | 全章 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（复刻 <if> 与 <where>）核对 |
| 2 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex02`（复刻 <foreach>）核对 |
| 3 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | 全章 | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex03`（复刻 <choose>/<when>/<）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（<sql> 片段复用与 <include）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
