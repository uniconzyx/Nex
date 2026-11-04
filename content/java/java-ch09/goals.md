# java-ch09 · 工程与框架：Maven 与 Spring Boot 入门 · 学习目标

## 前置
- `java-ch04` 集合框架（`Map`/`List` 是容器与配置绑定的基础）
- `java-ch06` IO 与 NIO（读 `pom.xml` / `application.yml`、类路径资源加载）

## 本章定位
前八章解决「Java 语言本身」，本章解决「**一个 Java 项目怎么被组织、构建并跑起来**」。
它是从「会写类」到「能交付一个可运行服务」的分水岭：Maven 负责**构建与依赖**，
Spring Boot 负责**装配与启动**。两者共同构成后端工程的最小可用底座。

> ⚠️ 本章示例**不引入 Maven / Spring 依赖**（本机无网络拉取仓库）。
> 所有机制都用纯 JDK 写「迷你实现」并真实编译运行——这正是理解原理的最佳方式：
> 你亲手实现一遍依赖调解、生命周期、条件装配，就不会再把它们当黑盒。
## 推荐书目

- 《Spring 实战》（Craig Walls）—— 第 1~3 章（依赖注入、自动配置、起步依赖）
- 《Effective Java》—— 第 2 章（创建与销毁对象）、第 8 章（方法设计），工程与 API 设计相关条款
- 《Maven 实战》—— 依赖调解与生命周期章节

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §1.2 传递依赖与依赖调解 | 读 `docs/java/basis/` 的工程化章节：最短路径优先 + 先声明优先，两条规则决定了「为什么你的 jar 版本被别人带偏」，本章的冲突排查步骤与它一致；配合 §1.3 BOM，就明白为什么统一版本管理能消掉大半这类问题 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §1.3 dependencyManagement 与 BOM：只声明「版本」，不引入依赖 | 看 `mall` 根 `pom.xml`：子模块只写 `groupId/artifactId` 不写版本，版本统一在父 POM 管——这就是「只声明版本、不引入依赖」的现成用法；读时对照 §2.3「多模块：聚合 ≠ 继承」，就分清 `modules` 与 `parent` 两个不同机制 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §3.3 自动配置的原理：SPI + 条件装配 | 对照 `docs/micro-services/` 的微服务落地文章：条件装配 + SPI 让「引入依赖即生效」，这也是 Spring Cloud starter 的组织方式；读完再回本章 §3.1「`@SpringBootApplication` 是三个注解的合成」，因果就完整了 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §3.2 SpringApplication.run 的启动阶段 | 看 `spring-boot-tutorials` 模块：一个最小 `@SpringBootApplication` 类加一个 `CommandLineRunner`，就能观察到「容器刷新完成 → 回调执行」的时序；配合 §3.7「`--debug` 之后看什么」，启动慢或 Bean 没注册时就有了排查入口 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（Maven 依赖调解）核对 |
| 2 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §1.3 dependencyMan… | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex02`（dependency）核对 |
| 3 | 黑马程序员 · Java 并发编程（JUC）<br><sub>黑马程序员</sub> | [BV16J411h7Rd](https://www.bilibili.com/video/BV16J411h7Rd/) | §4.3 Bean 作用域与线程安全 | synchronized 监视器、volatile 内存语义、AQS 与线程池参数逐个拆开讲，并发章的唯一主线；看完回 `ex03`（Scope 可见性矩阵）核对 |
| 4 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | 全章 | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex04`（BOM 与 dependencyMana）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。

## 验收标准
1. 能说清一串坐标 `groupId:artifactId:version` 在仓库中如何解析，以及**依赖调解**的两条规则。
2. 能背出 default 生命周期的主要 phase 顺序，并说明「phase 与插件 goal 是绑定关系」。
3. 能解释 `dependencyManagement` / BOM 为什么能统一版本，以及它与直接依赖的区别。
4. 能说出 `@SpringBootApplication` 由哪三个注解组成，各自负责什么。
5. 能讲清 Spring Boot **自动配置**的 SPI 加载路径与 `@Conditional` 的作用。
6. 能对比构造器注入与字段注入，并说明为什么生产代码推荐前者。
7. 能简述分层架构中 controller / service / repository 的职责边界与事务应放在哪一层。
8. 能区分单元测试、切片测试、集成测试的适用场景与代价。