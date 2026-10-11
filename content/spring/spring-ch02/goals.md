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
