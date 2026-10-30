# cpp-ch13 · 输入/输出与文件：iostream、fstream 与格式化

## 学习目标
完成本章后，你能：
1. 理解 iostream 体系的分层结构（`istream`/`ostream`/`iostream` 与 `streambuf` 的分工），并用状态位 `good/eof/fail/bad` 判断与恢复流的错误。
2. 解释 `cin` 与 C 标准库 `scanf` 的同步开销，掌握 `std::ios::sync_with_stdio(false)` 与 `cin.tie(nullptr)` 的加速原理与代价。
3. 用操纵符（`setw`/`setprecision`/`fixed`/`setfill`/`left`/`right`）做可控的格式化输出，理解浮点默认精度丢失的成因。
4. 用 `fstream` 以文本/二进制模式读写文件，掌握打开模式（`in/out/app/trunc/binary`）、文件位置（`seekg`/`seekp`/`tellg`）与 `is_open()` 检查。
5. 用 `stringstream` 做字符串解析与格式化，并理解它与 `std::format`（C++20）各自的取舍。

## 前置
- cpp-ch03 数组与字符串（`std::string`/`string_view` 基础）

## 真题依据（真实可查）
- 牛客/LeetCode 大量题目依赖快速 IO（如 `sync_with_stdio(false)` 提速），属工程基本功。
- 文件 IO 与格式化是「读入数据 + 输出报表」类项目的核心（如 nlohmann/json 流式解析）。

## 验收标准
- 能写出一个健壮的输入循环：读失败后用 `clear()` 恢复、用 `getline` 与 `>>` 混用时不残留换行。
- 能正确用 `setprecision`/`fixed` 控制浮点位数，区分文本与二进制模式。
- 能解释 iostream 的性能来源（虚函数 + 本地化 facet）以及何时该改用 `std::format` 或 `printf`。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,897 | §4.3 std | §4.3 `std::format` 的设计动机：`include/fmt/format.h` 的 `format_to` 把结果直接写进输出迭代器，`include/fmt/ostream.h` 则给「只有 `operator<<` 的老类型」搭桥；两处合看就知道 `std::format` 为什么比 `stringstream` 快——它不建流对象、不碰 locale |
| 2 | [Tencent/rapidjson](https://github.com/Tencent/rapidjson) | 15,147 | §1.3 性能本质 | §1.3 与 §3.2 的缓冲策略：`include/rapidjson/filereadstream.h` 的 `FileReadStream` 要你自己给一块`buffer`（默认 64KB），`FileWriteStream` 同理；这解释了本章「stdio 缓冲 vs 流对象」的层次——库不替你藏缓冲，性能就变得可预测 |
| 3 | [nlohmann/json](https://github.com/nlohmann/json) | 50,813 | §4.4 CSV 行解析 | §4.4 结构化文本解析：`include/nlohmann/json.hpp` 的 `operator>>` 与 `dump()` 是「流式接口 + 一次性序列化」的组合；对比它和 `std::stringstream` 解析同一份 CSV 的代码量，能直观看出本章说的「手写分隔符解析为什么容易漏边界」 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §3.2 文件位置指针与文本/二进制… | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（cin 读取多类型并检查流状态位）核对 |
| 2 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | §4.1 内存中的「流」 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex02`（getline 与 >> 混用的换行修复）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | §3.1 fstream 是「流 +… | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex03`（浮点格式化）核对 |
| 4 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex04`（setw/setfill 对齐表格输出）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
