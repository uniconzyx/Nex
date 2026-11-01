# 学习目标：Bean 生命周期与作用域

> 学科：spring · 章节：spring-ch02 · 分组：S1 Spring 核心

完成本章后，你应该能够：

1. **复述 Bean 完整生命周期**：BeanDefinition 注册 → 实例化 → 属性填充 → Aware 回调 →
   BeanPostProcessor 前置 → 初始化（@PostConstruct / InitializingBean / init-method）→ 后置处理
   → 使用 → 销毁（@PreDestroy / DisposableBean / destroy-method），并说清初始化/销毁三种方式的调用顺序。
2. **区分四种作用域语义**：singleton / prototype / request / session 的差异与适用场景，
   讲清「prototype 注入 singleton 只会拿到一次实例」的陷阱与修复（ObjectProvider / lookup-method）。
3. **讲透 BPP 与 BFPP 的时机差异**：BeanPostProcessor 在 bean 实例化后逐个 bean 介入，
   BeanFactoryPostProcessor 在容器刷新、所有 bean 定义加载后、实例化前介入。
4. **手写过迷你容器**：用纯 JDK（反射 + Map + 三级缓存）实现 BeanDefinition 注册、实例化、
   字段填充、Aware 回调、BPP 前后置、初始化与销毁方法，并解决单例循环依赖。
5. **解释三级缓存为何能解单例循环依赖**：而构造器/原型循环依赖必然失败；理解 ObjectFactory
   把「是否提前 AOP 代理」推迟到真正需要时的意义。
6. **理解 @Configuration 的 CGLIB 代理**：被增强子类覆盖 @Bean 方法，使类内 @Bean 互调也走
   容器单例缓存，保证单例共享。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 完整电商项目，最佳工程范例；本章先读与「完整生命周期阶段」「初始化与销毁的三种方式及顺序」相关的部分 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,772 | 全章 | Spring Boot 官方仓库：源码、文档与示例；本章先读与「完整生命周期阶段」「初始化与销毁的三种方式及顺序」相关的部分 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,081 | 全章 | 企业级快速开发平台：Spring Boot + MyBatis Plus 全栈实现；本章先读与「完整生命周期阶段」「初始化与销毁的三种方式及顺序」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,326 | 全章 | Spring 生态系统化教程代码；本章先读与「完整生命周期阶段」「初始化与销毁的三种方式及顺序」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | §3.1 BeanPostProce… | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（BeanDefinition 注册与反射）核对 |
| 2 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex02`（属性填充）核对 |
| 3 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | 全章 | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex03`（Aware 回调）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（BeanPostProcessor 前置）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
