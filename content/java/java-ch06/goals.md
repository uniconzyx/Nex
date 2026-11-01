# java-ch06 · IO 与 NIO

## 一、为什么单独学一章 IO

Java 的 IO 是**面试密度最高、工程出事最多**的一块：
文件句柄泄漏、编码乱码、序列化漏洞、`read()` 返回 -1 被忽略导致死循环、
大文件一次性读进内存 OOM —— 这些都不是语法问题，而是「模型没建立起来」。

本章把 IO 拆成四条主线，每条都能独立落地：

| 主线 | 核心问题 | 典型事故 |
|---|---|---|
| 字节流 / 字符流 | 编码发生在哪一层？ | 中文乱码、跨平台不一致 |
| Path / Files | 路径怎么算才对？遍历怎么不爆栈？ | 路径拼接错误、资源未关 |
| Channel / Buffer / Selector | 如何不靠线程堆并发？ | Buffer 状态用错、数据截断 |
| 序列化与 IO 模型 | 什么能序列化、什么绝不该序列化？ | 反序列化 RCE、性能踩坑 |

## 二、学习目标

### 基础层（必须达成）
1. 能说清 `InputStream`/`OutputStream` 与 `Reader`/`Writer` 的分工边界，
   并指出**编码转换发生在桥接点**（`InputStreamReader`/`OutputStreamWriter`）。
2. 熟练使用 try-with-resources 管理任意 `AutoCloseable`，理解关闭顺序与 suppressed 异常。
3. 能用 `Path` + `Files` 完成：读写文本、遍历目录、查询属性、原子移动。

### 进阶层（面试重点）
4. 讲清 `ByteBuffer` 的 position/limit/capacity 三个游标在
   `put → flip → get → clear/compact` 全过程的变化，并解释**为什么忘写 `flip()` 会读出 0 字节**。
5. 讲清 Selector 多路复用的工作方式：注册 → `select()` → 就绪集合 → 处理 → 迭代器移除。
6. 说出 `transferTo` 为什么快（避免用户态与内核态之间的重复拷贝）。

### 工程层（就业刚需）
7. 知道 `FileReader`/`FileWriter` 使用**平台默认编码**，因此线上必须显式指定 charset。
8. 知道 `ObjectInputStream.readObject()` 对不可信数据是**远程代码执行风险面**，
   并给出替代方案（JSON / Protobuf + 白名单）。
9. 能按场景选型：BIO / NIO / AIO / 虚拟线程，以及各自的适用边界。

## 三、前置

- `java-ch01` 语法与面向对象（接口、抽象类、泛型基础）
- `java-ch05` 异常与 try-with-resources（本章大量复用）

## 四、交付物（学完应能独立写出）

- 一个「逐行处理大文件且内存恒定」的工具（`BufferedReader` + 流式聚合）
- 一个「目录扫描 + 属性过滤 + 原子替换」的批处理脚本
- 一个「单线程 Selector 回显服务」的最小实现
- 一份「为什么日志里出现了乱码」的排查清单

## 五、常见误区（先立靶子）

1. 以为 `Reader` 读出来就一定是「对的」——其实取决于构造时用的 charset。
2. 以为 `BufferedReader` 只是为了快——它真正的语义价值是**按行读取**与**减少系统调用**。
3. 以为 `ByteBuffer.flip()` 是可有可无的「习惯」——它是读写模式切换的唯一开关。
4. 以为 `Serializable` 只是个空接口、随便实现——它等于对外暴露了**对象图的完全控制权**。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,300 | 全章 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计；本章先读与「主题一」「主题二」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例；本章先读与「主题一」「主题二」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,162 | 全章 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务；本章先读与「主题一」「主题二」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,326 | 全章 | Spring 官方生态的系统化代码教程仓库；本章先读与「主题一」「主题二」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | §4.2 主题二 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（字节流与字符流）核对 |
| 2 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | 全章 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex02`（缓冲流的意义）核对 |
| 3 | 黑马程序员 · Java 并发编程（JUC）<br><sub>黑马程序员</sub> | [BV16J411h7Rd](https://www.bilibili.com/video/BV16J411h7Rd/) | 全章 | synchronized 监视器、volatile 内存语义、AQS 与线程池参数逐个拆开讲，并发章的唯一主线；看完回 `ex03`（Path 四操作与目录穿越）核对 |
| 4 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | 全章 | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex04`（目录遍历）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
