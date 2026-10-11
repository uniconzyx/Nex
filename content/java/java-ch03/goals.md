# java-ch03 · 继承与多态：extends、方法重写、抽象类与接口 · 学习目标

- 理解继承的本质：is-a 关系、`super` 指代父类、单继承限制、构造器链（子类构造器必须先完成父类初始化）
- 区分**方法重写（override）**与**方法重载（overload）**：前者运行期动态分派，后者编译期静态解析
- 深入 JVM 多态机制：`invokevirtual` 的动态分派、方法表（vtable/itable）、**字段没有多态（字段隐藏）**、静态绑定 vs 动态绑定
- 掌握抽象类（`abstract`）与接口（`interface`，含 Java 8 `default` 方法）的语义差异与**字节码差异**（`invokevirtual` vs `invokeinterface`），明确何时用哪个
- 掌握向上转型、向下转型与 `instanceof`，能用多态数组/集合统一处理不同子类
- 理解 `final` 对类/方法/变量的约束，以及 `Object` 基类核心方法（`toString/equals/hashCode/getClass/clone`）


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
