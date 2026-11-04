# java-ch02 · 类与对象：封装、构造器、this · 学习目标

- 理解 JVM 对象模型：对象头（Mark Word / Klass Pointer）、实例数据布局与对齐填充；明确"变量持有引用、对象在堆上"
- 厘清 Java 的参数传递语义：**只有值传递**，对象参数传递的是"引用的副本"，能改状态但不能重指实参
- 掌握封装的本质：用 private 字段 + getter/setter 收窄合法状态空间、维护不变式；理解访问控制是编译期规则而非运行期保护
- 熟练使用构造器：重载、`this(...)` 链式调用、字段/实例块/构造器的初始化顺序、默认构造器的隐式存在条件
- 掌握 `equals` 与 `hashCode` 的契约：等价关系、为何必须成对重写、HashMap 查找为何依赖它
- 了解 Java 16+ `record` 如何把"不可变数据载体"的封装与等值语义一次性自动化
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §4.2 实现机制：为什么两者必须同时重写 | 读 `docs/java/basis/` 的对象基础问答：等价关系必须自反/对称/传递，哈希值必须与 equals 一致——它用 `HashMap` 查不到键的现场说明违反契约的后果；先读 §4.1「等价关系是数学约束」，再看这个现场，因果链就完整了 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §1.1 理论根基：对象是「带标签的连续内存」 | 看 `mall-common` 里的 `CommonResult`：一个只有 `code/message/data` 三个字段的返回体，字段顺序与类型决定对象头之后的内存排布，也是「为什么 DTO 要小而扁平」的现成样本；这直接对应 §4.2 里 hashCode 的计算成本——字段越多，默认哈希算得越慢 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §4.2 实现机制：为什么两者必须同时重写（哈希分布视角） | 对照 `docs/high-concurrency/` 的 HashMap 系列：它把「扰动函数 + 扩容 rehash」讲到面试深度，能解释为什么自定义 key 的 `hashCode` 分布不均会让链表变长；读时对照本章 §4.3 工程实践里用 `Objects.hash` 与手写的取舍 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §3.2 实现机制：重载、this() 链与初始化顺序 | 看 `core-java` 的构造器重载示例：`this(...)` 必须首行、`super(...)` 与它互斥，这两条限制在这份仓库里各有一个最小反例，比文字描述好记；理解它们再看 §3.1「构造器是建立不变式的契约」，就明白为什么初始化顺序不能随意调 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | 全章 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（类与对象）核对 |
| 2 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §1.3 工程实践 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex02`（构造器重载与 this 引用）核对 |
| 3 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | §1.1 对象是"带标签的连续内存" | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex03`（this 解析字段遮蔽）核对 |
| 4 | 黑马程序员 · JVM 快速入门<br><sub>黑马程序员</sub> | [BV1yE411Z7AP](https://www.bilibili.com/video/BV1yE411Z7AP/) | §1.1 对象是"带标签的连续内存" | 比尚硅谷短，适合先建立全局图再回头抠细节；GC 日志与调优参数讲得直给；看完回 `ex04`（this() 调用同类其它构造器（链式））核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
