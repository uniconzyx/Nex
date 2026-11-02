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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,366 | §1.1 | 讲「受检与非受检异常」时读 `docs/java/basis/` 的异常问答：`Error`/`Exception`/`RuntimeException` 三分与「受检异常强制调用方决策」的取舍，它给出了「什么时候该包成运行时异常」的判断口径 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,995 | §3.1 | 讲「异常链与根因保留」时看 `mall-common` 的统一返回体与业务异常：`ApiException` 携带错误码、原异常挂在 cause 上，缺了 cause 线上就只能看到「操作失败」四个字 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,169 | §2.1 | 讲「try-with-resources」时对照 `docs/distributed-system/` 里对「资源泄漏导致雪崩」的描述：连接/句柄不释放最终表现为「Too many open files」，TWR 的 suppressed 语义正是为了防止 close 异常掩盖主异常 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,308 | §4.1 | 讲「泛型擦除」时看 `core-java` 的泛型示例：`List<String>` 与 `List<Integer>` 在运行期是同一个类，所以不能 `new T[]`、不能对泛型做 `instanceof`——样例里有一条能编译失败的反例 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | §1.1 异常是一种「错误信号的控制… | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（受检异常 vs 非受检异常）核对 |
| 2 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §1.4 工程实践 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex02`（try-with-resources 自）核对 |
| 3 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | §1.3 受检异常的调用方契约与函数… | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex03`（finally 与 return 的执行）核对 |
| 4 | 尚硅谷 · JVM 全套教程<br><sub>尚硅谷</sub> | [BV1PJ411n7xZ](https://www.bilibili.com/video/BV1PJ411n7xZ/) | §3.2 字节码层面的顺序 | 内存区域、GC 算法与收集器、类加载与双亲委派、字节码；配 jstat/jmap 实操；看完回 `ex04`（自定义异常与异常链（cause））核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
