# fund-ch20 · 文件管理

> 一句话引出：为什么你「删了 20GB 文件」磁盘却没变空，而另一次「只删了 1KB」反而腾出 20GB？

## 一、知识目标

1. **说清文件系统的三层抽象**：**文件**（命名 + 属性 + 数据）→ **目录**（名字到文件控制块的映射）→ **超级块/挂载点**（整个文件系统的入口）。能解释"文件名其实不在文件里，而在目录里"这句话。
2. **掌握文件的逻辑结构**：无结构（流式）、顺序文件、索引文件、索引顺序文件、直接（散列）文件；能用**平均查找次数**比较它们的查询成本。
3. **掌握文件的物理结构（分配方式）**：连续分配、链接分配（**隐式**链接 vs **显式**链接/FAT）、索引分配（单级/多级/**混合索引**）；能算"读第 k 个逻辑块需要几次磁盘 I/O"。
4. **会做混合索引计算题**：UNIX inode 10 个直接 + 一级/二级/三级间接，给定块大小与块号长度，求**最大文件大小**、某偏移落在哪个区域、访问它要读几个索引块。这是 408 的必考题型。
5. **掌握目录结构**：单级、两级、树形、无环图目录；目录项与 **FCB**（文件控制块）的关系；**inode** 与 FCB 的区别（Linux 把文件名与 inode 分离，目录项只是一对 `(名字, inode号)`）。
6. **掌握文件共享与保护**：**硬链接**（多个目录项指向同一 inode，`link_count` 计数）与**软链接/符号链接**（独立文件，内容为目标路径，可能悬空）；访问控制（ACL、口令、加密）。
7. **掌握空闲空间管理**：空闲表、空闲链表、**位示图**（字号/位号换算）、**成组链接法**（UNIX）；能算每种方式的内存开销。
8. **理解文件系统层次与 VFS**：用户接口 → 逻辑文件系统 → 文件组织模块 → 基本文件系统 → I/O 控制；**挂载**做了什么；**VFS** 如何让 ext4/XFS/NFS 用同一套系统调用。
9. **理解一致性与日志**：为什么直接写会在掉电时产生不一致（需 `fsck`）；**日志（journaling）** 的 write-ahead + commit + redo 如何保证"要么全做要么全不做"；`data=writeback/ordered/journal` 三档的取舍。
10. **了解现代文件系统要点**：ext4 的 extent 与 htree 目录、XFS 的 B+ 树、Btrfs/ZFS 的写时复制与校验和。

## 二、能力目标

- 拿到 `df -i` 报 `No space left on device` 但 `df -h` 还有空间时，能立刻判断是 **inode 耗尽**而不是磁盘满。
- 能用 `ls -li` / `stat` 看 `link_count`，解释"删了没释放"（进程持有 + `lsof | grep deleted`）。
- 能估算一个文件系统在给定块大小下的 **元数据开销**（FAT 表大小、位示图大小、inode 数量），做容量规划。
- 能读懂 `dumpe2fs`/`tune2fs` 的关键字段（块大小、inode 数、日志模式），并说明调大/调小的影响。

## 三、三视角导航

| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | `open/read/write/fsync` 背后是"目录查找 + inode 读 + 索引块读 + 数据块读"；小文件碎片化让随机读变慢；`fsync` 与 `O_DIRECT` 决定你的持久化语义；大量小文件会先撞 inode 上限。 |
| 🎓 博士生 | 命名与元数据的分离（directory entry vs inode）是 POSIX 语义的核心设计；日志与写时复制代表两种崩溃一致性范式（undo/redo vs copy-on-write）；fsync 与磁盘写缓存屏障（barrier）的硬件语义。 |
| 📚 考研者 | 408 文件管理是计算题富矿：混合索引最大文件、位示图字号位号、FAT 表大小、连续/链接/索引的 I/O 次数、目录检索次数、硬链接计数；概念题爱考 inode 与 FCB、VFS、成组链接。 |

## 四、前置

本章前置：**fund-ch19（操作系统概述与运行机制）** —— 需要知道系统调用与内核态；**fund-ch10（内存管理）** 中的页缓存概念有助于理解"文件读写为什么先经过内存"。后续：fund-ch21（I/O 管理与磁盘）承接本章的磁盘调度与 I/O 层次。

## 五、本章与相邻章节的分工

| 章节 | 讲什么 | 本章不重复 |
|---|---|---|
| fund-ch10（内存管理） | 页表、置换算法、虚拟内存 | 本章只讲**页缓存**与文件读写的配合 |
| **fund-ch20（本章）** | 文件的逻辑/物理结构、目录、inode、空闲空间、VFS、日志 | —— |
| fund-ch21（I/O 管理与磁盘） | 四种 I/O 控制方式、缓冲、磁盘调度、RAID、SSD | 本章只在"读一次文件要几次 I/O"时引用磁盘概念 |

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 GitHub 星数（2026-10-29 经 GitHub REST API 实取）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [torvalds/linux](https://github.com/torvalds/linux) | 253833 | §inode 与索引 + §目录查找 | 两处对照读：`fs/ext4/inode.c` 的 `ext4_map_blocks` 把「逻辑块号」翻成「物理块号」（extent 树就是混合索引的工业版）；`fs/namei.c` 的 `link_path_walk` 把 `/a/b/c` 逐段解析成 dentry，配合 `fs/dcache.c` 看 dentry 缓存 |
| 2 | [mit-pdos/xv6-public](https://github.com/mit-pdos/xv6-public) | 9716 | §目录结构 + §日志一致性 | `fs.c` 里 `dirlookup`/`namei`/`ialloc` 三个函数就讲完「目录是特殊文件」与 inode 分配；`log.c` 只有几百行，begin_op / log_write / commit 就是最小可读的 write-ahead 日志 |
| 3 | [remzi-arpacidusseau/ostep-code](https://github.com/remzi-arpacidusseau/ostep-code) | 4474 | §全章实验 | 《操作系统导论》配套代码的文件系统实验：自己实现一遍 inode 分配与位示图，计算题就不再是背公式 |
| 4 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186408 | §考前速记 | 中文「文件系统」一节：把本章的计算题套路（混合索引、位示图、FAT 大小）浓缩成几页，适合考前 30 分钟过一遍 |

## 本章 B 站视频路线

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | 文件管理全章 | 逻辑结构 → 目录 → 物理结构（连续/链接/索引）→ 空闲空间管理；混合索引计算题在这里讲得最细 |
| 2 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | §磁盘与I/O | 配合看磁盘结构与访问时间，理解"读一块"的物理代价 |
| 3 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | §网络文件系统 | 看 NFS 一节，理解 VFS 为什么能把远端文件系统挂进来 |

## 本章配套论文与书

| # | 文献 / 章节 |
|---|---|
| 1 | 《操作系统概念（第 9 版）》Silberschatz 等 —— 第 11 章 "File-System Interface"、第 12 章 "File-System Implementation" |
| 2 | 《现代操作系统（第 4 版）》Tanenbaum & Bos —— 第 4 章 "File Systems" |
| 3 | 《操作系统导论》Arpaci-Dusseau —— 第 39-41 章（Files and Directories / File System Implementation / Fast File System） |
| 4 | 《UNIX 环境高级编程（第 3 版）》Stevens —— 第 4 章 "Files and Directories"（硬链接/软链接的 POSIX 语义） |
