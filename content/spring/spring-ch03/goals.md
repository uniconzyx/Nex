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
