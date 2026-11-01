# fund-ch15 学习目标：中央处理器（CPU）

> 一句话引出：一条指令从"取"到"执行"到底走了什么路？为什么多核、流水线和分支预测能让同一颗芯片跑得更快？

## 一、知识目标
1. 说清 CPU 四大组成（运算器、控制器、寄存器、内部总线）及其在"取指—译码—执行"中的分工，能画出单总线/多总线/专用通路三种数据通路草图并比较其冲突与带宽。
2. 区分硬布线控制器与微程序控制器的本质差异：微命令/微指令/微程序的概念层次，水平型与垂直型微指令的编码方式、并行度与译码速度权衡，微地址的形成（增量、下址字段、多路转移）。
3. 掌握四级时序概念：指令周期 / 机器周期（CPU 周期）/ 节拍（时钟周期）/ 节拍电位，能解释为什么一条指令要拆成多个机器周期、一个机器周期拆成多个节拍。
4. 吃透五段式流水线的时空图，能计算吞吐率、加速比、效率，并识别三类冒险（结构/数据/控制）及其对策（转发旁路、阻塞 stall、分支预测、乱序执行与 Tomasulo 思想）。
5. 用 CPU 性能公式（CPU 时间 = 指令数 × CPI × 时钟周期）解释超标量、多发射、超线程对实际性能的影响，而不是只背公式。

## 二、能力目标
- 给定一个指令序列，能手算单周期 / 多周期 / 流水线的总时钟周期数，并指出数据冒险位置、插入正确数量的 stall，或用旁路消除 stall。
- 能根据流水线时空图画法，推演任意指令混排下的吞吐率与效率，判断"加段数是否一定加速"。
- 能把"微程序 vs 硬布线""结构/数据/控制冒险"等概念映射到真实后端（GCC 调度、CPU 分支预测误判、超线程争用）上，用 `perf` 等指标定位性能瓶颈。

## 三、三视角导航
| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | 用 perf 看 IPC / 分支预测命中率 / Cache 缺失来优化热点；理解超线程对吞吐与延迟的相反影响；写对"无数据依赖"友好的代码让 CPU 多发射真正生效。 |
| 🎓 博士生 | 数据通路作为有限状态机的形式化建模；Tomasulo 算法如何用保留站+CDB 实现乱序发射与写回；冒险本质是"资源/数据/控制依赖"在时空上的冲突，旁路是空间换时间。 |
| 📚 考研者 | 408 高频：五段式流水线时空图、加速比/吞吐率/效率计算、数据冒险与旁路转发、控制冒险与分支预测、微程序 vs 硬布线、CPI 计算。几乎每年必考大题。 |

## 四、前置
本章前置：fund-ch14（指令系统）。只有先理解"指令格式、操作码/地址码、寻址方式、RISC/CISC 差异"，才能理解 CPU 如何取指、译码、取操作数、执行并写回。

## 本章 GitHub 学习路线（按阅读顺序）
> ★ 为 GitHub 星数（2026-10-28 经 GitHub REST API 实取，非估算）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376373 | §吞吐与延迟 | 读 Latency numbers 与「吞吐 vs 延迟」：流水线的本质就是用延迟（单条指令变慢）换吞吐（单位时间完成更多），这个 trade-off 在这里讲得最清楚 |
| 2 | [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 363641 | §CPU 缓存与流水 | 看 CPU caches 与「Instruction pipelining」条目：把 cache 与流水线当成同一套「让 CPI 下降」的手段来理解 |
| 3 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186408 | §CPU 高频考点 | 中文速记：CPU 结构与流水线一节，考前背「五段流水时空图 + 加速比公式 + 三类冒险」三件套 |
| 4 | [llvm/llvm-project](https://github.com/llvm/llvm-project) | 41282 | §消除冒险 | 读 `MachineScheduler` 与 `llvm-mca`：`llvm-mca` 能直接对一段汇编出「周期表 + 停顿原因」，是本章模型最实用的工业级对照 |
| 5 | [chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip) | 3895 | §数据通路 | 读 `src/main/scala/rocket/RocketCore.scala`：五级流水、旁路网络、stall 信号是怎么用几百行硬件描述写出来的 |
| 6 | [riscv/riscv-isa-manual](https://github.com/riscv/riscv-isa-manual) | 4869 | §流水线相关 | 看 RISC-V 对 load-use 与分支延迟槽（无延迟槽）的规定：规范层面就把「哪些冒险必须由硬件处理」定死了 |
| 7 | [qemu/qemu](https://github.com/qemu/qemu) | 13951 | §多发射建模 | 读 `accel/tcg/`：TCG 动态翻译如何把目标指令拆成微操作并重排——这是「多发射 + 乱序」在软件层的等价实现 |

## 本章 B 站视频路线
| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 数据结构（考研） | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | 全章 | 体系总览与学习方法 |
| 2 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | 全章 | CPU 数据通路与流水线（本章主线课） |
| 3 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | 全章 | 进程调度类比（吞吐/冒险 ↔ 调度/饥饿） |
| 4 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 流水线思想类比（分组交换与流水传输） |

## 本章配套论文与书
| # | 文献 / 章节 |
|---|---|
| 1 | 《深入理解计算机系统（第 3 版）》Bryant & O'Hallaron —— 第 4 章 处理器体系结构（Y86-64 流水线与冒险） |
| 2 | 《计算机组成与设计：硬件/软件接口》Patterson & Hennessy —— 第 4 章 处理器、第 5 章 流水化实现 |
| 3 | 《计算机体系结构：量化研究方法》Hennessy & Patterson —— 第 3 章 指令级并行（Tomasulo、分支预测、多发射） |
| 4 | Tomasulo, R. M. (1967). *An Efficient Algorithm for Exploiting Multiple Arithmetic Units* —— 乱序执行思想的原始论文 |
