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
