# fund-ch17 学习目标：I/O 系统

> 一句话引出：CPU 怎么和外部世界（磁盘/网卡/键盘）打交道？

> 学科：`fundamentals`（408 考研 · 计算机组成原理）
> 前置：`fund-ch13`（计算机系统概述）
> 独立线说明：本章只依赖**同一条线**的 ch13（数据表示、CPU 基本结构、总线），不依赖其他计组子模块以外的学科；中断概念与 fund-ch13 的「异常/中断」基础衔接。

## 一、知识目标
1. 说清 **I/O 接口**的功能与结构：为什么 CPU 不能直接连外设、接口里有哪些寄存器（数据/状态/控制）、接口如何做速度匹配与电平转换。
2. 区分 **I/O 端口编址**的两种方式——独立编址（Isolated I/O）与统一编址（Memory-Mapped I/O），能说出各自的指令、地址空间、优缺点与典型代表（x86 vs ARM/RISC-V）。
3. 对比 **四种 I/O 方式**：程序查询方式、程序中断方式、DMA 方式、通道方式，能按下述维度判断「什么时候该用哪种」——CPU 参与度、能否并行、适用数据量、硬件开销。
4. 复述 **中断响应与处理全过程**：关中断 → 保存断点 → 引出中断服务程序（向量中断），理解单级/多级中断、中断屏蔽与优先级、多重中断与中断嵌套的区别。
5. 描述 **DMA 传送三阶段**（预处理 / 数据传送 / 后处理），说清 DMA 控制器与 CPU 如何争夺访存（停止 CPU 访存 / 周期挪用 / 交替访存），以及 DMA 和中断的关系。
6. 理解 **通道与 I/O 处理器**：通道程序（CCW）、三种通道类型（字节多路 / 选择 / 数组多路），以及 **I/O 软件层次**（中断处理程序 / 设备驱动 / 与设备无关 / 用户层）的自底向上分工。

## 二、能力目标
- 给定一个外设场景（低速键盘 / 高速网卡 / 大块磁盘读写），能**选出合适的 I/O 方式**并解释理由。
- 能画出**中断处理流程**并确定「关中断、保存断点、中断向量表、开中断、中断返回」的先后次序。
- 能根据**中断优先级和屏蔽字**，手算实际的中断响应顺序与嵌套深度（408 高频计算/分析题）。
- 能推导 **DMA 传送所节省的 CPU 周期 / CPU 占用率**，区分「DMA 接管总线时不需 CPU，但结束仍需中断通知」。
- 能把硬件的 I/O 机制与**操作系统的软件层次**（驱动、缓冲、中断底半部）对应起来，建立软硬件协同的全局观。

## 三、三视角导航
| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | 你在代码里能碰到什么：select/poll/epoll 与中断的关系、零拷贝（sendfile/splice）如何减少 DMA 次数、中断风暴与 CPU 软中断（softirq）排查、为什么 `mmap` 写磁盘也要等 DMA。 |
| 🎓 博士生 | 形式化与历史：中断优先级仲裁的硬件实现（ Daisy Chain / 并行优先级编码 / 中断控制器）、访存仲裁的排队模型、通道 I/O 的发展历程（从 IBM 大机的通道到现代 I/O 处理器）、数据搬运的 DMA 一致性（cache coherency）问题。 |
| 📚 考研者 | 408 高频考点：四种 I/O 方式对比表、中断全流程五步、DMA 三阶段、通道类型辨析、I/O 软件四层、以及「给定中断屏蔽字求响应顺序」「比较四种方式耗时」这类分析/计算题。 |

## 四、前置
本章前置：`fund-ch13`（计算机系统概述）。建议已经理解：CPU 基本组成、指令执行（取指—译码—执行）、总线的基本概念、以及「异常/中断」的初步含义。

## 本章 GitHub 学习路线（按阅读顺序）
> ★ 为 GitHub 星数（2026-10-28 经 GitHub REST API 实取，非估算）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376373 | §I/O 与背压 | 读异步 I/O 与队列/背压那一节：外设永远是慢速生产者，本章的四种 I/O 方式就是「怎么让快 CPU 不被慢外设拖死」的四代答案 |
| 2 | [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 363641 | §中断与 DMA | 看 OS 部分的 interrupts 与 I/O 条目，把「中断 / DMA / 缓冲」三件套当成一个整体来记 |
| 3 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186408 | §I/O 高频考点 | 中文速记：计组 I/O 与 OS 设备管理两节交叉看，重点是四种 I/O 方式的 CPU 占用对比表 |
| 4 | [torvalds/linux](https://github.com/torvalds/linux) | 253833 | §中断处理 | 读 `kernel/irq/manage.c` 与 `request_threaded_irq`：上半部（硬中断）与下半部（软中断/线程化）的分工，正是本章「中断处理过程」的工程版 |
| 5 | [qemu/qemu](https://github.com/qemu/qemu) | 13951 | §DMA 与设备 | 看 `hw/block/virtio-blk.c`：一次 virtio 请求如何经 DMA 搬数据并注入中断，是本章 DMA 三阶段最完整的真实样本 |
| 6 | [chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip) | 3895 | §接口编址 | 读 `src/main/scala/diplomacy/`：外设地址映射与中断线如何在生成 RTL 时被自动连线，理解「统一编址」在硬件侧的落地 |
| 7 | [zephyrproject-rtos/zephyr](https://github.com/zephyrproject-rtos/zephyr) | 16942 | §中断控制器 | 读 `drivers/interrupt_controller/`：GIC/NVIC 的优先级、屏蔽、嵌套是怎么被抽象成 `irq_enable/irq_lock` 的，最贴近「I/O 软件四层」 |

## 本章 B 站视频路线
| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 数据结构（考研） | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | 全章 | 体系总览：先建立「计算机组成—操作系统—网络」中 I/O 的位置感 |
| 2 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | 全章 | I/O 方式与中断：程序查询/中断/DMA/通道对比，中断全流程，DMA 三阶段（本章主线课） |
| 3 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | 全章 | 中断与驱动类比：把计组的「硬件中断」与 OS 的「设备驱动/上半部下半部」对照看 |
| 4 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 网卡 I/O 类比：DMA 收包、中断通知 CPU、软中断处理协议栈，最贴近工程实战 |

## 本章配套论文与书
| # | 文献 / 章节 |
|---|---|
| 1 | 《深入理解计算机系统（第 3 版）》Bryant & O'Hallaron（第 6 章：存储器层次结构中的 I/O 与 DMA 思想；第 8 章：异常控制流中的中断） |
| 2 | 《计算机组成与设计：硬件/软件接口》Patterson & Hennessy（第 6 章：I/O 系统、DMA、通道与中断控制器） |
| 3 | 《操作系统概念（恐龙书）》Silberschatz 等（第 13 章：I/O 系统、中断、设备驱动与缓冲） |
| 4 | 《计算机组成原理》唐朔飞（第 8 章：I/O 系统，408 计组标准参考教材） |
