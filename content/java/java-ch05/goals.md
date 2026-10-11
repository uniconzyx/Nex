# java-ch05 · 异常体系与泛型进阶 · 学习目标

- 掌握 **Throwable 体系**：`Error` / `Exception` → 受检异常与非受检（运行时）异常的划分，以及受检异常强加给调用方的「处理契约」
- 理解 **受检异常与函数式接口的冲突**：为何 lambda 表达式的方法不能抛受检异常，以及现代实践为何倾向非受检自定义异常
- 掌握 **try-with-resources** 与 `AutoCloseable`：资源逆序自动关闭、字节码层面的展开、异常抑制（suppressed）机制
- 认识 **异常的性能成本**：`fillInStackTrace` 捕获完整栈快照的代价，以及高频路径避免异常的控制流
- 厘清 **finally 与 return 的执行顺序陷阱**：finally 的 return 如何覆盖 try 的返回值
- 掌握 **异常链（cause）与 suppressed 异常**：如何保留根因、不丢失关闭异常
- 深入理解 **泛型擦除**：类型参数在运行时消失的本质、由此产生的限制，以及编译器生成的**桥接方法（bridge method）**
- 掌握 **通配符 PECS 原则**（`? extends` 生产者 / `? super` 消费者）、**自限定类型**与泛型方法，`@SuppressWarnings` 的克制使用

## 前置
- java-ch02（`equals`/`hashCode`、对象模型）
- java-ch03（多态、`@Override` 与覆盖、接口）

## 真题依据（真实可查）
- LeetCode 20 有效的括号（`valid-parentheses`）——用 `Deque` 作栈，本章工程实践

## 验收标准
- 能说出哪些是受检、哪些是非受检，并解释受检异常的设计权衡
- 能写出 try-with-resources 且理解 suppressed 异常
- 能解释 finally 中 return 的覆盖行为
- 能解释泛型擦除、桥接方法的存在原因，并正确运用 PECS


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
