# java-ch09 · 工程与框架：Maven 与 Spring Boot 入门 · 学习目标

## 前置
- `java-ch04` 集合框架（`Map`/`List` 是容器与配置绑定的基础）
- `java-ch06` IO 与 NIO（读 `pom.xml` / `application.yml`、类路径资源加载）

## 本章定位
前八章解决「Java 语言本身」，本章解决「**一个 Java 项目怎么被组织、构建并跑起来**」。
它是从「会写类」到「能交付一个可运行服务」的分水岭：Maven 负责**构建与依赖**，
Spring Boot 负责**装配与启动**。两者共同构成后端工程的最小可用底座。

> ⚠️ 本章示例**不引入 Maven / Spring 依赖**（本机无网络拉取仓库）。
> 所有机制都用纯 JDK 写「迷你实现」并真实编译运行——这正是理解原理的最佳方式：
> 你亲手实现一遍依赖调解、生命周期、条件装配，就不会再把它们当黑盒。

## 学习资源（GitHub star 最高）
- **Snailclimb/JavaGuide**（★159056）—— Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计
  <https://github.com/Snailclimb/JavaGuide>
- **macrozheng/mall**（★84863）—— SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例
  <https://github.com/macrozheng/mall>
- **doocs/advanced-java**（★79141）—— 互联网 Java 工程师进阶知识：高并发、分布式、微服务
  <https://github.com/doocs/advanced-java>
- **eugenp/tutorials**（★37326）—— Spring 官方生态的系统化代码教程仓库
  <https://github.com/eugenp/tutorials>

## 推荐书目
- 《Spring 实战》（Craig Walls）—— 第 1~3 章（依赖注入、自动配置、起步依赖）
- 《Effective Java》—— 第 2 章（创建与销毁对象）、第 8 章（方法设计），工程与 API 设计相关条款
- 《Maven 实战》—— 依赖调解与生命周期章节

## 验收标准
1. 能说清一串坐标 `groupId:artifactId:version` 在仓库中如何解析，以及**依赖调解**的两条规则。
2. 能背出 default 生命周期的主要 phase 顺序，并说明「phase 与插件 goal 是绑定关系」。
3. 能解释 `dependencyManagement` / BOM 为什么能统一版本，以及它与直接依赖的区别。
4. 能说出 `@SpringBootApplication` 由哪三个注解组成，各自负责什么。
5. 能讲清 Spring Boot **自动配置**的 SPI 加载路径与 `@Conditional` 的作用。
6. 能对比构造器注入与字段注入，并说明为什么生产代码推荐前者。
7. 能简述分层架构中 controller / service / repository 的职责边界与事务应放在哪一层。
8. 能区分单元测试、切片测试、集成测试的适用场景与代价。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159056 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计 |
| [macrozheng/mall](https://github.com/macrozheng/mall) | 84863 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例 |
| [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79141 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务 |
| [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37326 | Spring 官方生态的系统化代码教程仓库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 尚硅谷 · Java 零基础（宋红康） | [视频](https://www.bilibili.com/video/BV1Qb411g7cz/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚学堂 · 高淇 Java 300 集 | [视频](https://www.bilibili.com/video/BV1ct411n7oG/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 求知课堂 · Java 入门到精通 | [视频](https://www.bilibili.com/video/BV1CJ411m7gg/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · 谷粒商城（分布式实战项目） | [视频](https://www.bilibili.com/video/BV1np4y1C7Yf/) | 本学科配套视频，建议结合本章示例与习题观看 |
