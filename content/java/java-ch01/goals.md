# java-ch01 · 环境与基础语法 · 学习目标

- 完成 JDK 安装与开发环境配置，能编译运行第一个 Java 程序
- 理解 `public class Main` 与 `public static void main(String[] args)` 的固定签名约定
- 掌握八种基本类型（byte/short/int/long/float/double/char/boolean）及字面量规则
- 理解变量、常量（final）与作用域，掌握基本类型间的类型转换与自动提升
- 熟练使用运算符（算术/关系/逻辑/位运算）与表达式求值与优先级
- 掌握流程控制：if/else、switch、for、while、do-while 及其嵌套
- 掌握一维数组的声明、初始化、遍历与 length 属性
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | 全章 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计；本章先读与「八种基本类型」「变量与常量」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | 全章 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例；本章先读与「八种基本类型」「变量与常量」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | 全章 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务；本章先读与「八种基本类型」「变量与常量」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | 全章 | Spring 官方生态的系统化代码教程仓库；本章先读与「八种基本类型」「变量与常量」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（第一个 Java 程序）核对 |
| 2 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | 全章 | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex02`（八种基本类型）核对 |
| 3 | 黑马程序员 · Java 并发编程（JUC）<br><sub>黑马程序员</sub> | [BV16J411h7Rd](https://www.bilibili.com/video/BV16J411h7Rd/) | 全章 | synchronized 监视器、volatile 内存语义、AQS 与线程池参数逐个拆开讲，并发章的唯一主线；看完回 `ex03`（算术运算符）核对 |
| 4 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | 全章 | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex04`（if-else 分支）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
