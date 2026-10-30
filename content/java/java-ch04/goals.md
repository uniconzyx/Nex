# java-ch04 · 集合框架：List、Set、Map、Queue 与泛型集合 · 学习目标

- 建立 **Collection 体系**的整体心智模型：以 `Collection`/`Map` 为根的接口层次、各具体实现（ArrayList/LinkedList/HashSet/TreeSet/HashMap/TreeMap/PriorityQueue/ArrayDeque）的定位与取舍
- 从 **JVM 与数据结构**层面理解 `ArrayList` 的动态数组扩容（1.5 倍）与 O(1) 随机访问、`LinkedList` 的双向链表与缓存不友好
- 掌握 `HashMap` 的底层实现：数组 + 链表 + 红黑树、hash 扰动函数、`(n-1)&hash` 索引、树化阈值 8 / 退化 6、扩容 rehash 与尾插法、负载因子 0.75 的数学依据、`ConcurrentHashMap` 的分段/CAS 思路
- 理解 **`equals`/`hashCode` 契约**对散列集合的决定性作用，以及「可变键」的危害
- 掌握迭代器与 for-each 的 **fail-fast（modCount）** 机制，能写出在遍历中安全增删的代码
- 理解 **泛型集合**带来的编译期类型安全，以及类型擦除对集合运行时的影响
- 熟练使用 `Collections` 工具类（排序、二分、不可变视图、线程安全包装）

## 前置
- java-ch02（对象模型、`equals`/`hashCode` 契约、值传递）
- java-ch03（多态、`@Override` 与覆盖）

## 真题依据（真实可查）
- LeetCode 1 两数之和（`two-sum`）—— HashMap 一遍哈希
- LeetCode 49 字母异位词分组（`group-anagrams`）—— HashMap 分组
- LeetCode 347 前 K 个高频元素（`top-k-frequent-elements`）—— HashMap + 排序
- 牛客 BM50 两数之和

## 验收标准
- 能解释 ArrayList 扩容为什么是 1.5 倍、LinkedList 随机访问为什么慢
- 能画（口述）HashMap 在冲突、树化、扩容 rehash 时的行为
- 能正确重写自定义键的 `equals`/`hashCode`，并解释可变键的隐患
- 能在遍历集合时安全地增删元素（避免 `ConcurrentModificationException`）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [Snailclimb/JavaGuide](https://github.com/Snailclimb/JavaGuide) | 159,300 | 全章 | Java 面试与后端通用指南：计算机基础、数据库、分布式、高并发、系统设计；本章先读与「可运行代码」「equals/hashCo…」相关的部分 |
| 2 | [macrozheng/mall](https://github.com/macrozheng/mall) | 84,863 | 全章 | SpringBoot + MyBatis 电商实战项目，含 Docker 部署，工程范例；本章先读与「可运行代码」「equals/hashCo…」相关的部分 |
| 3 | [doocs/advanced-java](https://github.com/doocs/advanced-java) | 79,162 | 全章 | 互联网 Java 工程师进阶知识：高并发、分布式、微服务；本章先读与「可运行代码」「equals/hashCo…」相关的部分 |
| 4 | [eugenp/tutorials](https://github.com/eugenp/tutorials) | 37,313 | 全章 | Spring 官方生态的系统化代码教程仓库；本章先读与「可运行代码」「equals/hashCo…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · Java 入门（宋红康）<br><sub>尚硅谷</sub> | [BV1Kb411W75N](https://www.bilibili.com/video/BV1Kb411W75N/) | §1.1 为什么需要统一的集合抽象 | 语法主线课：每章都从「为什么这么设计」讲到字节码层面，适合边看边在 IDE 里复现；看完回 `ex01`（ArrayList 扩容机制（复刻版））核对 |
| 2 | 黑马程序员 · JavaWeb 全流程<br><sub>黑马程序员</sub> | [BV1m84y1w7Tb](https://www.bilibili.com/video/BV1m84y1w7Tb/) | §1.3 泛型集合带来的编译期类型安全 | 从 Servlet 到 Spring + MyBatis 的完整链路，Maven 与分层工程的落点在最后几章；看完回 `ex02`（数组 vs 单向链表随机访问）核对 |
| 3 | 黑马程序员 · Java 零基础（上部）<br><sub>黑马程序员</sub> | [BV17F411T7Ao](https://www.bilibili.com/video/BV17F411T7Ao/) | §1.1 为什么需要统一的集合抽象 | 练习密度最高的一套：每节配一个可提交的小任务，含力扣题与面试题讲解；看完回 `ex03`（HashMap 的 put/get 与哈）核对 |
| 4 | 黑马程序员 · Java 并发编程（JUC）<br><sub>黑马程序员</sub> | [BV16J411h7Rd](https://www.bilibili.com/video/BV16J411h7Rd/) | §3.4 线程安全 | synchronized 监视器、volatile 内存语义、AQS 与线程池参数逐个拆开讲，并发章的唯一主线；看完回 `ex04`（TreeMap 基于红黑树的排序与比较器）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Java 核心技术 卷I》Horstmann |
| 2 | 《Effective Java（第 3 版）》Bloch |
| 3 | 《深入理解 Java 虚拟机》周志明 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
