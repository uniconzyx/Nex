# fund-ch10 · 操作系统：内存管理、文件与 IO · 学习目标

- 掌握**连续分配管理**的三种方式（单一连续、固定分区、动态分区）与**动态分区四类放置算法**（首次/最佳/最坏/邻近适应），能算出各自的**外部碎片量**
- 区分**内部碎片**与**外部碎片**，说明**紧凑（compaction）**与**对换（swapping）**的作用与代价
- 掌握**分页**机制：页表、页表项、逻辑地址到物理地址的**转换公式**，能算**页表大小**与**多级页表**的节省量
- 掌握 **TLB（快表）** 的作用与**有效访问时间（EAT）**计算，理解 TLB 命中率对性能的敏感性
- 掌握**分段**与**段页式**的差异（段是逻辑单位、页是物理单位），能算段页式的地址转换次数与访存次数
- 掌握**四种页面置换算法**（OPT / FIFO / LRU / Clock）的**缺页次数计算**与实现代价，能复现 **Belady 异常**
- 理解**改进型 Clock**（增加修改位）为什么能减少 I/O，能写出其两轮扫描规则
- 掌握**抖动（thrashing）**的成因与**工作集模型**（WSS），能算**缺页率**并说明「多道程序度」与缺页率的关系
- 掌握**文件逻辑结构**（顺序/索引/索引顺序）与**外存分配方式**（连续/链接/索引），能算索引结构的**最大文件大小**
- 掌握 **inode**、目录项与**硬链接 vs 软链接**的本质差异（是否共享 inode、删除语义、能否跨文件系统），能读懂 `ls -l` 的链接计数
- 掌握**空闲空间管理**（位示图 / 空闲链表 / 成组链接法），能算位示图中的**字号与位号**
- 掌握**磁盘调度算法**（FCFS / SSTF / SCAN / C-SCAN / LOOK / C-LOOK）并计算**磁头移动总距离**，说明 SSTF 的**饥饿**问题与 SCAN 的解法
- 掌握**五种 IO 模型**（阻塞 / 非阻塞 / IO 多路复用 / 信号驱动 / 异步）的阶段划分与阻塞点，理解**零拷贝**减少的拷贝次数

## 前置
- fund-ch09（进程、线程与调度）

## 学习资源（GitHub star 最高）
- [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) —— 缓存、存储与一致性
- [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) —— OS 与内存管理自学路径
- [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) —— 中文 OS 面试核心考点

## 推荐书目
- 《计算机操作系统》汤小丹 第 4~6 章
- 《现代操作系统》第 3~6 章

## 验收标准
- 给定一段动态分区分配序列，能算出首次/最佳适应各自的空闲分区链表与外部碎片
- 给定 32 位逻辑地址、4KB 页大小，能算出页内偏移位数、页号位数、页表项数；若采用两级页表，能算出所需的页目录大小
- 给定引用串与帧数，能手算 FIFO / LRU / OPT 的缺页次数
- 能构造一个 FIFO 的 Belady 异常例子（增加帧数反而缺页更多）并解释为什么 LRU 不会
- 能写出改进型 Clock 的选择流程（找 (0,0) → 找 (0,1) 并清位 → 重来）
- 能算出 `ls -l` 中链接计数为 2 时，删除其中一个文件名后 inode 是否释放
- 给定磁头初始位置与请求柱面序列，能算出 FCFS / SSTF / SCAN / C-SCAN 的移动总距离
- 能说清「一次 `read()` 从磁盘到用户缓冲区」经过了几次拷贝、几次上下文切换，以及 `sendfile` 省掉了哪几次


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 373461 | 系统设计入门：性能、一致性、可用性与面试题（408 之上的系统视野） |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 362479 | 完整的计算机科学自学计划：数据结构、算法、OS、网络全覆盖 |
| [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186393 | 中文技术面试必备：操作系统、计算机网络、组成原理、算法、数据库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 青岛大学 · 王卓 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1nJ411V7bd/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 王道考研 · 计算机组成原理 | [视频](https://www.bilibili.com/video/BV1ps4y1d73V/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 哈工大 · 李治军 操作系统 | [视频](https://www.bilibili.com/video/BV1d4411v7u7/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 湖南科技大学 · 计算机网络微课堂 | [视频](https://www.bilibili.com/video/BV1c4411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 清华 · 邓俊辉 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1jt4y117KR/) | 本学科配套视频，建议结合本章示例与习题观看 |
