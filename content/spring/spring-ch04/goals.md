# spring-ch04 学习目标：SpringBoot 自动配置与起步依赖

## 一、本章定位

前两章分别拆开了 IoC 容器（`spring-ch01`）与 AOP 代理（`spring-ch03`）。
本章回答一个工程上最实用的问题：**为什么一个空的 SpringBoot 项目只加一个
`spring-boot-starter-web` 依赖、写一个 `main` 方法，就能跑起一个带内嵌 Tomcat 的 Web 应用？**

答案是三个机制叠加：**起步依赖（starter）替你选依赖**、**自动配置（auto-configuration）
替你写 `@Bean`**、**条件装配（`@Conditional`）决定这些 `@Bean` 到底装不装**。

## 二、知识目标

1. 能说清 `@SpringBootApplication` 是 `@SpringBootConfiguration` +
   `@EnableAutoConfiguration` + `@ComponentScan` 三个注解的复合体，以及三者的分工。
2. 掌握自动配置的 **SPI 加载机制**：从 Spring Boot 2.7 之前的
   `META-INF/spring.factories` 到 2.7+/3.x 的
   `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
   的演进原因与格式差异。
3. 掌握 **条件装配** 的语义：`@ConditionalOnClass`、`@ConditionalOnMissingBean`、
   `@ConditionalOnProperty`、`@ConditionalOnWebApplication` 分别解决什么问题，
   以及「**后定义的覆盖先定义的**」这一兜底规则（`@ConditionalOnMissingBean` 的关键）。
4. 掌握 **配置绑定**：`@ConfigurationProperties` 的松散绑定（relaxed binding）、
   `@Value` 与它的差异、配置优先级顺序、profile 覆盖规则。
5. 能独立写一个 **自定义 starter**（`xxx-spring-boot-starter` +
   `xxx-spring-boot-autoconfigure` 两模块结构），并说清为什么官方推荐拆成两个模块。

## 三、能力目标

- 能用纯 JDK 手写一个**迷你自动配置框架**：条件评估 → 候选类加载 → 拓扑排序 →
  按序注册 Bean，从而理解 SpringBoot 的启动主干。
- 能通过 `/actuator/conditions`（或启动日志 `--debug`）**定位一个 Bean 为什么没生效**，
  这是排障的核心技能。
- 能解释「依赖版本冲突」时 Maven 的**最近者优先**与 **第一声明优先**仲裁规则。

## 四、学习路径建议

1. 先读 `concept/01`，建立「启动流程」的整体图景；
2. 再读 `concept/02`，这是本章的技术核心（SPI + 条件装配）；
3. 最后读 `concept/03`，把配置绑定与自定义 starter 落到工程实践；
4. 做 `examples/` 里的 10 个纯 JDK 模拟示例，每个都能独立编译运行；
5. 用 `exercises.json` 与 `interview.json` 自测，重点看笔面高频的
   「自动配置原理」「starter 原理」「配置优先级」三类问题。

## 五、前置知识

- `spring-ch01`：IoC 容器与依赖注入（BeanDefinition、容器刷新流程）；
- `spring-ch02`：Bean 生命周期与作用域；
- `spring-ch03`：AOP 与代理（理解 `@Configuration` 的 CGLIB 增强）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「一个注解，三个职责」「`SpringApplic…」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,772 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「一个注解，三个职责」「`SpringApplic…」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,081 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「一个注解，三个职责」「`SpringApplic…」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,326 | 全章 | Spring 生态系统化教程代码；本章先读与「一个注解，三个职责」「`SpringApplic…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | 全章 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（条件装配的核心）核对 |
| 2 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | §1.2 `SpringApplic… | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex02`（SPI 清单加载）核对 |
| 3 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex03`（自动配置的顺序约束）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（松散绑定）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
