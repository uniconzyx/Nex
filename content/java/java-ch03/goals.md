# java-ch03 · 继承与多态：extends、方法重写、抽象类与接口 · 学习目标

- 理解继承的本质：is-a 关系、`super` 指代父类、单继承限制、构造器链（子类构造器必须先完成父类初始化）
- 区分**方法重写（override）**与**方法重载（overload）**：前者运行期动态分派，后者编译期静态解析
- 深入 JVM 多态机制：`invokevirtual` 的动态分派、方法表（vtable/itable）、**字段没有多态（字段隐藏）**、静态绑定 vs 动态绑定
- 掌握抽象类（`abstract`）与接口（`interface`，含 Java 8 `default` 方法）的语义差异与**字节码差异**（`invokevirtual` vs `invokeinterface`），明确何时用哪个
- 掌握向上转型、向下转型与 `instanceof`，能用多态数组/集合统一处理不同子类
- 理解 `final` 对类/方法/变量的约束，以及 `Object` 基类核心方法（`toString/equals/hashCode/getClass/clone`）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,300 | 全章 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计；本章先读与「可运行代码」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例；本章先读与「可运行代码」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,162 | 全章 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务；本章先读与「可运行代码」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,326 | 全章 | Spring 官方生态的系统化代码教程仓库；本章先读与「可运行代码」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（继承与 super）核对 |
| 2 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | §2.2 JVM 如何做动态分派 | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex02`（方法重写）核对 |
| 3 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §1.3 工程实践 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex03`（多态动态分派）核对 |
| 4 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | §1.1 继承是"子类型化"而非"代… | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex04`（抽象类与抽象方法）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
