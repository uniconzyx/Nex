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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | SpringBoot + MyBatis 完整电商项目，最佳工程范例 |
| [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81563 | Spring Boot 官方仓库：源码、文档与示例 |
| [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 39566 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | Spring 生态系统化教程代码 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Spring 5 框架教程 | [视频](https://www.bilibili.com/video/BV1Vf4y127N5/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · SpringMVC 2021 教程 | [视频](https://www.bilibili.com/video/BV1Ry4y1574R/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · MyBatis 实战教程 | [视频](https://www.bilibili.com/video/BV1mW411M737/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 雷丰阳 · SpringBoot2 零基础入门 | [视频](https://www.bilibili.com/video/BV19K4y1L7MT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Spring Cloud 微服务 | [视频](https://www.bilibili.com/video/BV18E411x7eT/) | 本学科配套视频，建议结合本章示例与习题观看 |
