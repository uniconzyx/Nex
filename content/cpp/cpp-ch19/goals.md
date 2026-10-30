# cpp-ch19 · 工程化与测试：CMake、单元测试与 CI

本章把「能编译跑起来的 C++ 代码」推进到「能被别人接手、能被机器验收的代码」。
全章围绕三条主线：**现代 CMake 的 target-centric 建模**、**单元测试的设计与隔离**、
**静态分析与 CI 流水线把质量门禁自动化**。所有结论都能在本章 18 个示例里复现。

## 学习目标
完成本章后，你能：

1. 说出**现代 CMake（target-centric）**与旧式「目录级变量」写法的分水岭，并解释为什么
   `include_directories()` / `link_libraries()` / `set(CMAKE_CXX_FLAGS ...)` 会让配置泄漏到无关目标
   （对应 ex07、ex09 的 CM001–CM010 规则库）。
2. 正确使用 `PUBLIC` / `PRIVATE` / `INTERFACE` 三个关键字表达**使用要求（usage requirements）**，
   能手工推演某个目标「编译期可见的 include 集合」，并解释漏写 `PUBLIC` 会造成什么编译错误
   （对应 ex10 的传播求解器、ex15 的头文件可见性检查）。
3. 用 `target_compile_features` / `target_compile_options` / `install(EXPORT)` 表达语言级要求、
   开发期告警与可重定位安装；知道 `find_package` 与 `FetchContent` 的取舍（对应 ex07）。
4. 从零写出一个**极简单元测试框架**：用例注册宏、断言计数、失败定位（`__LINE__`）、
   汇总与**退出码语义**（0/1），并理解这就是 googletest/Catch2 的最小内核（对应 ex01、ex02）。
5. 用**边界值分析与等价类划分**设计用例，而不是随手凑几条；能用**参数化测试**（值参数化 +
   类型参数化）把 N 组输入输出压成一份用例体（对应 ex03、ex04）。
6. 用**夹具（fixture）SetUp/TearDown** 保证用例之间互相隔离，识别并修掉「静态状态跨用例泄漏」
   这类假失败（对应 ex05）。
7. 用**依赖注入**把时间、随机数、网络这类不可控依赖换成可控实现（`FakeClock`），
   做到被测逻辑零改动、无需 mock 框架（对应 ex06）。
8. 读懂并写出**行覆盖率**口径（可执行行 / 已覆盖行 / 门槛），知道覆盖率是「用例质量」的镜像
   而非目标本身（对应 ex14）。
9. 把**编译告警当作错误**：掌握 `-Wall -Wextra -Werror` 在 CI 上的拦截效果，理解为什么
   `-Werror` 应挂在目标上而非全局（对应 ex17、ex07 ⑤）。
10. 读懂 **GitHub Actions** 的完整结构：`on` 触发、`needs` 决定的 DAG、**矩阵构建**
    （`exclude`/`include` 语义与 256 上限）、缓存 key 设计、artifact 与 `if: always()`
    （对应 ex08、ex11、ex12、ex13）。
11. 用**静态检查器思维**审计自己的工程：CMakeLists 规则库、workflow 规则库、格式规则库、
    ODR 符号规则库，全部做到「正反两组用例可区分」（对应 ex09、ex13、ex16、ex18）。
12. 按**头文件/源文件组织约定**拆目标：公开头（PUBLIC）与实现头（PRIVATE）分离，
    理解 ODR 与强/弱/inline/static 链接属性，能判断同名符号是否违规（对应 ex15、ex16）。

## 前置
- **cpp-ch14**（预处理与宏）：`TEST` 宏、断言宏、`__FILE__`/`__LINE__` 是本章自研测试框架的实现基础。
- **cpp-ch15**（链接、存储期与 ODR）：本章 ex16 的 ODR 符号判定直接建立在该章的链接属性之上。

## 学习目标 ↔ 示例对应表

| 目标 | 对应示例 | 关键结论 |
|---|---|---|
| 1 现代 CMake 建模 | ex07、ex09 | 目录级命令 → target_* 命令；规则库 CM001–CM010 正反可判 |
| 2 usage requirements | ex10、ex15 | PUBLIC/INTERFACE 传播、PRIVATE 不传播；跨目标包含 PRIVATE 头即 HS001 违规 |
| 3 语言级要求与依赖获取 | ex07 | `cxx_std_17` 挂在 target；`find_package` vs `FetchContent` |
| 4 自研测试框架内核 | ex01、ex02 | 注册宏 + 断言计数 + 失败定位 + 退出码语义（0/1） |
| 5 等价类/边界值/参数化 | ex03、ex04 | 12 个边界点覆盖 6 个等价类；参数化展开 50 个用例 |
| 6 夹具与用例隔离 | ex05 | `TEST_F` 每用例独立实例；静态状态必然泄漏 |
| 7 依赖注入替代 mock | ex06 | `IClock`/`FakeClock`/`SystemClock`，`RateLimiter` 可测 |
| 8 覆盖率口径 | ex14 | 37.5% → 62.5%，覆盖率是「用例质量」的镜像 |
| 9 告警即错误 | ex17 | `-Werror` 前后返回码 0 → 1 |
| 10 CI 流水线 | ex08、ex11、ex12、ex13 | DAG/并行层/关键路径/环检测；矩阵 12 组合；WF001–WF007 |
| 11 静态检查器思维 | ex09、ex13、ex16、ex18 | 四套规则库全部正反两组可区分 |
| 12 头文件组织与 ODR | ex15、ex16 | 公开头/实现头分离；strong/weak/inline/static 判定 |

## 验收标准
- 能把一份「目录级命令 + 全局变量」的 CMakeLists 改写成 target-centric 写法，并说清每个关键字为什么这么选。
- 能不靠框架、用 60 行写出可统计失败数并返回非零退出码的测试框架，并把它接进 CI。
- 能为一个依赖系统时间的模块引入可注入接口，使 100 个用例在毫秒级跑完且结果稳定。
- 能读出一个 workflow 的拓扑序、并行层与关键路径，并指出矩阵展开后的真实组合数。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [google/googletest](https://github.com/google/googletest) | 39,670 | §2.1 测试框架的最小内核与退出码… | §2.1 测试框架的最小内核：`googletest/src/gtest.cc` 的 `RUN_ALL_TESTS` → `UnitTest::Run` → 逐个 `TestInfo::Run`，最后把失败数折成进程退出码；看清「退出码即结论」这条链，CI 里的 `ctest` 才知道该不该红 |
| 2 | [catchorg/Catch2](https://github.com/catchorg/Catch2) | 21,538 | §2.1 测试框架的最小内核与退出码… | §2.1 的另一种内核与 §1.2 的 CMake 用法：`src/catch2/catch_session.cpp` 的 `Session::run` 返回失败用例数，`CMakeLists.txt` 里 `catch_discover_tests` 把用例注册成独立测试；对照 googletest 的「一次跑完」与 Catch2 的「逐用例发现」，能看出两种框架对 CI 并行粒度的不同假设 |
| 3 | [cpp-best-practices/gui_starter_template](https://github.com/cpp-best-practices/gui_starter_template) | — | §1.2 `PUBLIC` / `P… | §1.2、§1.3 与 §4.1 的整体样板：根 `CMakeLists.txt` 用 target-based 写法，`cmake/` 放自写模块，`.github/workflows/` 里是完整的矩阵构建 + 缓存 + artifact；把它当作本章的参考实现逐条对照——这是少数把「现代 CMake + 测试 + CI」串成一条线的小型仓库 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（自研极简单元测试框架）核对 |
| 2 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex02`（同一测试框架抓出两个真实 bug（边界/）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（边界值分析与等价类划分）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | §4.2 矩阵构建、缓存与 arti… | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（参数化测试）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
