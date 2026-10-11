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
