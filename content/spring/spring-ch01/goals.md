# 学习目标：Spring 核心：IoC 容器与依赖注入

> 学科：spring · 章节：spring-ch01 · 分组：S1 Spring 核心

完成本章后，你应该能够：

1. **说清 IoC 与 DI 的关系**：能用一句话解释「控制反转把对象的创建与装配交给了容器」，
   并区分 IoC（设计原则）与 DI（实现手段）。
2. **讲清 BeanFactory 与 ApplicationContext 的差异**：懒加载 vs 预实例化、
   容器能力边界（国际化 / 事件 / AOP 基础设施）。
3. **在三种注入方式间做正确取舍**：构造器注入（不可变、必填） vs Setter 注入（可选、可变）
   vs 字段注入（简洁但有可测试性代价），并能在循环依赖场景下判断可行性。
4. **理解组件扫描与 Java 配置**：@Component / @Service 等 stereotype 注解如何被扫描注册；
   @Bean + @Configuration 工厂方法如何装配第三方对象。
5. **手写过迷你 IoC 容器**：能用纯 JDK（反射 + Map）实现 Bean 注册、依赖解析与字段注入。
6. **讲透单例循环依赖与三级缓存**：为什么说三级缓存（singletonObjects / earlySingletonObjects /
   singletonFactories）能解决单例 setter 注入的循环依赖，而 prototype 循环依赖必然失败。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §2.1 | 讲「同类型多 Bean 如何选」时看 `mall-security` 模块：安全配置类与业务 Service 分属不同包，靠 `@Qualifier` 或字段名消歧；字段名恰好等于 Bean 名才能注入成功，改名即启动失败 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,722 | §1.3 | 讲「构造器注入 vs 字段注入」时读 `spring-boot-project/spring-boot/src/main/java/org/springframework/boot/` 下的自动配置类：框架自己全部用构造器注入，依赖写在 `final` 字段上——这是「不可变 + 可单测」的示范，不是风格偏好 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,149 | §3.1 | 讲「分包与组件扫描」时看 `yudao-framework/` 的 starter 划分：每个 starter 自带 `@AutoConfiguration` 与 `AutoConfiguration.imports`，业务模块只需引依赖——这是「扫描范围由 starter 决定」的工程化答案 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §4.1 | 讲「Bean 作用域」时看 `spring-boot-tutorials` 模块：`@Scope("prototype")` 注入到单例后只创建一次，样例里用 `ObjectProvider` 才能每次取新实例 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | §1.1 什么是 IoC / 控制反转 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（迷你 IoC 容器）核对 |
| 2 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | §3.2 @Bean 与 @Conf… | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex02`（反射字段注入）核对 |
| 3 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex03`（构造器注入 vs Setter 注入（不）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（组件扫描）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
