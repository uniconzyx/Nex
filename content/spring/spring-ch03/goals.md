# 学习目标：AOP 与代理机制

> 学科：spring · 章节：spring-ch03 · 分组：S1 Spring 核心

完成本章后，你应该能够：

1. **说清 AOP 的核心术语与动机**：横切关注点（日志/事务/鉴权）为何要从业务代码中剥离；
   切面（Aspect）、连接点（Join Point）、切点（Pointcut）、通知（Advice）、织入（Weaving）
   的定义与相互关系；AOP 与 OOP 是互补而非替代。
2. **手写 JDK 动态代理**：用 `Proxy.newProxyInstance` + `InvocationHandler`
   实现前置 / 环绕 / 后置返回 / 异常四类通知，理解「代理对象在接口方法上拦截调用、
   委派给真实对象」的机制（见示例 ex01~ex03）。
3. **理解 CGLIB 子类代理原理**：用「继承 + 方法覆写」模拟 CGLIB 增强器，
   说清它**不要求目标有接口**、通过生成子类重写方法织入通知（ex05、ex12），
   并讲清 `final` 类 / `final` 方法、private 方法为何无法被代理。
4. **讲透 JDK 与 CGLIB 的适用边界**：有接口优先 JDK 动态代理（基于接口、无 final 限制之外更轻）；
   无接口或代理具体类用 CGLIB；Spring 默认「有接口用 JDK，无接口用 CGLIB」的择优策略与演进
   （Spring Boot 2.x 起默认强制 CGLIB）。
5. **实现简化版 execution 切点匹配器**：自己解析 `execution(ret pkg.Cls.method(args))`
   通配符与包/类/方法/参数匹配（ex07），理解真实 AspectJ 切点表达式是同一思想的超集。
6. **理清通知执行顺序**：`@Around` 包裹 `@Before`/`@After`/`@AfterReturning`，
   以及多拦截器责任链的「先进后出」嵌套（ex04、ex11）。
7. **区分 `this` 与 `target`**：`this` 指向「代理对象」、`target` 指向「被代理的真实对象」，
   以及为什么同类内部方法自调用（self-invocation）会绕过代理、导致通知失效（ex08、ex09）。
8. **能解释 AOP 在事务/日志/鉴权中的落地**，并识别「代理失效」这一最高频的生产坑。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §4.2 同类内部自调用导致代理失效 | 看 `mall-admin` 的 Service 实现：同类方法内部互调不经过代理，`@Transactional`/`@Cacheable` 直接失效，解法是注入自身或拆到另一个 Bean；理解它要先读 §4.1「this 与 target 的语义区别」——`this` 是原始对象，`target` 才是被代理的实例 |
| 2 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,722 | §2.2 JDK 与 CGLIB 的适用边界 | 读 `spring-boot` 的 `AopAutoConfiguration`：`proxyTargetClass` 决定用 CGLIB 还是 JDK 代理，而 CGLIB 无法代理 `final` 类/方法——这就是「注解失效」的框架级原因；对照 §1.1 JDK 动态代理的工作机制，就明白为什么「实现了接口」会改变默认代理方式 |
| 3 | [YunaiV/ruoyi-vue-pro](https://github.com/YunaiV/ruoyi-vue-pro) | 40,149 | §3.2 通知执行顺序 | 看 `yudao-framework/yudao-spring-boot-starter-*` 里的日志与权限切面：用 `@Around` 包住方法、用 `@Order` 控制顺序，比散落的拦截器更好维护；读时注意多个切面套在同一个方法上时，`@Order` 小的在外层——这决定了权限校验能不能挡住日志切面里的参数打印 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §1.1 JDK 动态代理的工作机制 | 看 `spring-boot-tutorials` 的 AOP 示例：目标类实现接口时默认走 JDK 代理，注入时必须按接口类型，否则 `ClassCastException`；配合 §1.2 `InvocationHandler` 与反射委派，就明白「代理对象不是目标对象的子类」这条推断 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Spring 框架（源码级）<br><sub>尚硅谷</sub> | [BV1Vf4y127N5](https://www.bilibili.com/video/BV1Vf4y127N5/) | 全章 | IoC 容器启动流程、Bean 生命周期、AOP 代理与事务传播：每节都对着源码讲，看完能回答「@Autowired 到底怎么注进去的」；看完回 `ex01`（JDK 动态代理）核对 |
| 2 | 黑马程序员 · SSM 框架全套<br><sub>黑马程序员</sub> | [BV1WZ4y1P7Bp](https://www.bilibili.com/video/BV1WZ4y1P7Bp/) | 全章 | Spring + SpringMVC + MyBatis 三件套打通：MyBatis 的 Mapper 代理绑定与动态 SQL 在这里最清楚；看完回 `ex02`（JDK 动态代理）核对 |
| 3 | 尚硅谷 · SpringBoot 2 零基础<br><sub>尚硅谷</sub> | [BV19K4y1L7MT](https://www.bilibili.com/video/BV19K4y1L7MT/) | 全章 | 自动配置原理（@Conditional 家族 + imports 文件）、起步依赖、内嵌容器与配置优先级；看完回 `ex03`（JDK 动态代理）核对 |
| 4 | 尚硅谷 · SpringCloud 微服务<br><sub>尚硅谷</sub> | [BV18E411x7eT](https://www.bilibili.com/video/BV18E411x7eT/) | 全章 | 分布式事务、服务治理与配置中心；只在讲「多数据源/分布式」时选看，不必通读；看完回 `ex04`（通知嵌套顺序）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Spring 实战（第 6 版）》Walls |
| 2 | 《Spring Boot 编程思想》小马哥 |
| 3 | 《MyBatis 从入门到精通》刘增辉 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
