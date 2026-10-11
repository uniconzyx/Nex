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

## 学习资源（GitHub star 最高）
- [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) —— JVM 面试与调优章节
- [doocs/advanced-java](https://github.com/doocs/advanced-java) —— 高并发与 JVM 进阶
- [macrozheng/mall](https://github.com/macrozheng/mall) —— 生产级 SpringBoot 工程，参考其启动参数与部署脚本

## 推荐书目
- 《深入理解 Java 虚拟机》（周志明）第 2、3、7 章
- 《Java 性能权威指南》第 3、5 章

## 验收标准
- 能在白板上画出运行时数据区，并标出哪些是线程私有
- 能算出 `new Object()`、`new int[10]`、含 2 个 `int` + 1 个 `long` 的对象在 64 位开启指针压缩时各占多少字节
- 能说出「为什么 CMS 用标记-清除而 G1 用 Region + 复制」的取舍
- 能写出一个自定义 `ClassLoader`，并解释为什么 `loadClass` 与 `findClass` 的重写点不同
- 能读一段 `javap -v` 输出，指出 `invokedynamic` 出现在哪类语法上（lambda / 字符串拼接 / 记录类）
- 能用 `jcmd <pid> VM.flags` / `GC.heap_info` / `Thread.print` 三板斧给出一次线上问题排查顺序


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
