# java-ch08 · JVM 与内存模型、GC、类加载 · 学习目标

- 说清 **JVM 运行时数据区**五块（程序计数器 / 虚拟机栈 / 本地方法栈 / 堆 / 方法区）各自的**线程私有性、存放内容、可能的异常**
- 掌握 **栈帧结构**（局部变量表、操作数栈、动态链接、方法返回地址）与 **`StackOverflowError` / `OutOfMemoryError` 的触发边界**
- 掌握 **对象内存布局**（对象头 Mark Word + Klass Pointer + 实例数据 + 对齐填充），理解 **指针压缩（CompressedOops）** 与 **64 位下对象大小的计算公式**
- 理解 **逃逸分析** 与 **标量替换 / 栈上分配 / 锁消除**，以及 **TLAB** 在分配路径上的作用
- 区分 **引用计数** 与 **可达性分析**，能列举 **GC Roots** 的六类来源，掌握 **四种引用**（强 / 软 / 弱 / 虚）的回收时机
- 掌握 **三大 GC 算法**（标记-清除 / 复制 / 标记-整理）的代价对比，理解 **分代收集** 为什么按对象寿命划分堆
- 掌握 **收集器谱系**：Serial / ParNew / Parallel Scavenge / Serial Old / Parallel Old / **CMS** / **G1** / **ZGC** / Shenandoah，能说清各自的**停顿模型与适用场景**
- 掌握 **G1 的 Region / Remembered Set / SATB / 混合回收** 与 **ZGC 的染色指针 + 读屏障** 设计动机
- 掌握 **类加载五阶段**（加载 → 验证 → 准备 → 解析 → 初始化）与 **类初始化的六种主动触发时机**
- 掌握 **双亲委派模型** 及 **三次被打破** 的历史（SPI / Tomcat / OSGi / 热部署），能写出自定义 `ClassLoader`
- 能读懂 **字节码文件结构**（魔数 `0xCAFEBABE`、版本号、常量池、方法表）与 `javap -c -v` 输出，区分 `invokestatic` / `invokevirtual` / `invokeinterface` / `invokespecial` / `invokedynamic`
- 掌握 **内存问题排查工具链**：`jps` / `jstat` / `jmap` / `jstack` / `jcmd` / `jinfo` / MAT / Arthas，能定位堆 OOM、元空间 OOM、线程泄漏与死锁
- 能给出**一套可落地的 JVM 参数**（堆大小、代比例、GC 选型、堆转储），并说明每一参数的理由

## 前置
- java-ch02（对象模型、`equals`/`hashCode`、`final`）
- java-ch03（多态、接口、方法分派）
- java-ch07（JMM 与 `happens-before`、`volatile`/`synchronized`）
## 推荐书目

- 《深入理解 Java 虚拟机》（周志明）第 2、3、7 章
- 《Java 性能权威指南》第 3、5 章

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | 全章 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计；本章先读与「五块运行时数据区」「堆的分代结构」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | 全章 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例；本章先读与「五块运行时数据区」「堆的分代结构」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | 全章 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务；本章先读与「五块运行时数据区」「堆的分代结构」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | 全章 | Spring 官方生态的系统化代码教程仓库；本章先读与「五块运行时数据区」「堆的分代结构」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（运行时数据区与内存池）核对 |
| 2 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | 全章 | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex02`（类初始化顺序）核对 |
| 3 | 黑马程序员 · JVM 快速入门<br><sub>黑马程序员</sub> | [BV1yE411Z7AP](https://www.bilibili.com/video/BV1yE411Z7AP/) | 全章 | 比尚硅谷短，适合先建立全局图再回头抠细节；GC 日志与调优参数讲得直给；看完回 `ex03`（双亲委派与「打破委派」）核对 |
| 4 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | 全章 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex04`（字节码文件头）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。

## 验收标准
- 能在白板上画出运行时数据区，并标出哪些是线程私有
- 能算出 `new Object()`、`new int[10]`、含 2 个 `int` + 1 个 `long` 的对象在 64 位开启指针压缩时各占多少字节
- 能说出「为什么 CMS 用标记-清除而 G1 用 Region + 复制」的取舍
- 能写出一个自定义 `ClassLoader`，并解释为什么 `loadClass` 与 `findClass` 的重写点不同
- 能读一段 `javap -v` 输出，指出 `invokedynamic` 出现在哪类语法上（lambda / 字符串拼接 / 记录类）
- 能用 `jcmd <pid> VM.flags` / `GC.heap_info` / `Thread.print` 三板斧给出一次线上问题排查顺序