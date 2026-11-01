# fund-ch14 学习目标：指令系统

> 一句话引出：机器"听得懂"的命令到底是什么样子？

## 一、知识目标
1. 掌握指令的基本格式：操作码（做什么）+ 地址码（对谁做），理解定长操作码与变长（扩展）操作码的设计思想，能独立完成 15/15/15/16 这类三地址扩展编码方案。
2. 掌握零/一/二/三地址指令的取舍：在指令字长固定时，地址码个数与可寻址范围、寄存器数量的权衡关系。
3. 熟练掌握 10 种常见寻址方式（立即、直接、一次间接、寄存器、寄存器间接、基址、变址、相对、堆栈、隐含），能正确写出各自的有效地址 EA 与访存次数。
4. 理解指令的分类（数据传送、运算、程序控制、输入输出、特权）以及 CISC 与 RISC 的核心差异，并能结合 x86、MIPS、RISC-V 给出实例。
5. 理解指令周期的四段模型（取指、间址、执行、中断）与对齐/边界约束对访存性能的影响。

## 二、能力目标
- 能根据指令字长与地址码字段要求，反向推导操作码可编码的指令条数，或给定指令条数需求设计扩展操作码方案。
- 能针对一段汇编/机器码，手工计算有效地址 EA，并判断需要多少次访存。
- 能在阅读编译器（如 gcc -O2）生成的汇编时，识别出实际使用的寻址方式，并理解其性能含义。
- 能在真实工程中（如二进制插桩、模拟器、反汇编、漏洞利用）正确区分指令边界与操作数边界，避免踩坑。

## 三、三视角导航
| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | 写 C/汇编时，编译器如何选择寻址方式；缓冲区溢出与指令边界；用 objdump/Compiler Explorer 看真实机器指令。 |
| 🎓 博士生 | 从 ISA 形式化建模、操作码空间熵编码、CISC/RISC 历史演化与量化评价（CPI、代码密度）角度深入。 |
| 📚 考研者 | 408 高频考点：扩展操作码设计题、EA 计算题、寻址方式访存次数、CISC/RISC 对比、指令周期阶段。 |

## 四、前置
本章前置：fund-ch13（计算机系统概述）。

## 本章 GitHub 学习路线（按阅读顺序）
> ★ 为 GitHub 星数（2026-10-28 经 GitHub REST API 实取，非估算）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376373 | §指令即接口 | 看 API 设计那一章：指令集本质上就是「硬件对外暴露的 API」，格式规整、向后兼容的取舍和接口设计同构 |
| 2 | [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 363641 | §位运算与编码 | 看 Bitwise operations 一节：扩展操作码设计题全靠位域切分，先把「用几位表示几个状态」的手感练出来 |
| 3 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186408 | §CISC/RISC | 中文速记：计算机组成原理里的指令系统一节，重点背 CISC 与 RISC 的六条差异对照表 |
| 4 | [llvm/llvm-project](https://github.com/llvm/llvm-project) | 41282 | §指令选择 | 读 `llvm/lib/Target/RISCV/` 的 InstrInfo 与 ISel：看真实编译器如何把 IR 落到具体指令格式，以及寻址模式如何被匹配 |
| 5 | [chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip) | 3895 | §译码 | 读 `src/main/scala/rocket/Instructions.scala` 与 `IBuf.scala`：一条 32 位机器码怎么被拆成 opcode/rd/rs1/rs2，比看教材图直观得多 |
| 6 | [riscv/riscv-isa-manual](https://github.com/riscv/riscv-isa-manual) | 4872 | §指令格式原文 | 第 2 章 RV32I 的指令编码表就是本章「指令格式」的权威原文，对照教材的 R/I/S/B/U/J 六种格式逐位核对 |
| 7 | [riscv-collab/riscv-gnu-toolchain](https://github.com/riscv-collab/riscv-gnu-toolchain) | 4656 | §汇编与反汇编 | 装好后用 `riscv64-unknown-elf-as` 写几条带不同寻址方式的汇编，再 `objdump -d` 反汇编，亲眼看到 EA 是怎么算出来的 |

## 本章 B 站视频路线
| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 数据结构（考研） | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | 全章 | 体系总览 |
| 2 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | 全章 | 指令格式与寻址方式 |
| 3 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | 全章 | 特权指令与系统调用 |
| 4 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 协议命令类比 |

## 本章配套论文与书
| # | 文献 / 章节 |
|---|---|
| 1 | 《深入理解计算机系统（第 3 版）》Bryant & O'Hallaron |
| 2 | 《计算机组成与设计：硬件/软件接口》Patterson & Hennessy |
| 3 | 《计算机体系结构：量化研究方法》Hennessy & Patterson |
| 4 | 《计算机组成原理》唐朔飞（第 4 章 指令系统，408 经典教材） |
| 5 | 《计算机操作系统》汤子瀛（系统调用与特权级相关章节） |
