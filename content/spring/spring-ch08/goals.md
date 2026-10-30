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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「传播行为」「隔离级别、readOnly…」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,563 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「传播行为」「隔离级别、readOnly…」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,081 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「传播行为」「隔离级别、readOnly…」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,313 | 全章 | Spring 生态系统化教程代码；本章先读与「传播行为」「隔离级别、readOnly…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | §2.2 事务与 AOP 代理 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（自调用 vs 代理调用）核对 |
| 2 | 黑马程序员 · JavaWeb（含 Spring+MyBatis）<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §2.1 八类事务失效场景 | 工程视角：分层、DTO/VO、统一响应与异常处理；事务与多数据源在最后几章；看完回 `ex02`（传播行为 REQUIRED）核对 |
| 3 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | §4.2 多数据源与分布式事务 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex03`（传播行为 REQUIRES_NEW）核对 |
| 4 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex04`（传播行为 NESTED）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
