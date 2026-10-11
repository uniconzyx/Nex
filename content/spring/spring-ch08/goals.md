# spring-ch08 学习目标：事务管理与工程实践

## 一、本章定位

`spring-ch03` 讲清了 AOP 与代理机制，`spring-ch07` 讲清了动态 SQL、缓存与插件。
`spring-ch08` 把两者拧成一根绳：**声明式事务**。它表面只是一个 `@Transactional` 注解，
背后却牵着 AOP 代理、连接绑定、隔离级别、传播行为、异常回滚规则与分布式一致性。
本章的目标是让你既能「用对」，也能在出事故时「查清」。

## 二、知识目标

1. 掌握 `@Transactional` 的完整语义：7 种传播行为（REQUIRED / REQUIRES_NEW / NESTED /
   SUPPORTS / NOT_SUPPORTED / MANDATORY / NEVER）、5 种隔离级别、`readOnly`、`timeout`、
   `rollbackFor` / `noRollbackFor`，尤其记住「**默认只对 RuntimeException / Error 回滚**」；
2. 掌握事务失效的典型场景：同类自调用不走代理、非 public 方法、异常被 catch 吞掉、
   非运行时异常不回滚、多线程/异步、数据库引擎不支持事务、传播行为用错；
3. 理解事务与 AOP 代理的关系：JDK 动态代理 vs CGLIB、`AopContext.currentProxy()` 与
   `@EnableAspectJAutoProxy(exposeProxy = true)` 的作用，以及「代理可见性」决定注解是否生效；
4. 理解 ThreadLocal 保存事务状态的原理（`TransactionSynchronizationManager` + `ConnectionHolder`），
   以及线程池复用导致上下文串号、异步导致事务丢失的根因；
5. 掌握分层架构中 Entity / DTO / VO 的职责边界（Mapper 层 vs Service 层的转换时机）；
6. 了解多数据源与分布式事务方案概览：2PC/XA、TCC、Saga、本地消息表、Seata 的 AT 模式。

## 三、能力目标

- 能用**纯 Java**复刻一套迷你事务框架（注解 + 动态代理拦截器 + 事务管理器 + 保存点），
  真实演示 REQUIRED / REQUIRES_NEW / NESTED 的嵌套回滚结果差异，以及自调用、
  非 public、异常被吞、checked 异常、ThreadLocal 串号、隔离级别读现象等**布尔判据**；
- 能用 **sqlite3** 真实演示事务的 ACID 原子性与 `SAVEPOINT` 实现 NESTED 语义；
- 能用 **2PC 模拟**说明「协调者崩溃 → 参与者阻塞 → 状态不一致」的经典失败场景；
- 能针对「事务没回滚」「金额对不平」「异步后数据丢了」这类真实事故给出根因与修法。

## 四、学习路径建议

1. 先读 `concept/01`（@Transactional 完整语义）、`concept/02`（失效场景 + AOP 代理）；
2. 再读 `concept/03`（ThreadLocal 与并发）、`concept/04`（分层与分布式事务）；
3. 跑 `examples/` 的 15 个示例（12 个 Java 复刻 + 3 个 Python 实测），每个都可独立运行；
4. 用 `exercises.json` / `interview.json` / `project.json` 自测。

## 五、前置知识

- `spring-ch03`：AOP、JDK 动态代理与 CGLIB、通知与切点——事务拦截器的底座；
- `spring-ch07`：动态 SQL、缓存与插件——事务通常与持久层操作一起出现；
- 软前置（可选，不阻断学习）：Java 并发基础（ThreadLocal / 线程池 / Future），若已掌握可跳过。


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
