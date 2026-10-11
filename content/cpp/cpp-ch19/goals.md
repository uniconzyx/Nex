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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 286133 | 项目驱动的多语言实战教程合集（含 C/C++ 专题） |
| [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | 34742 | C++ 实现的经典算法与数据结构合集，可直接编译运行 |
| [ssloy/tinyrenderer](https://github.com/ssloy/tinyrenderer) | 24335 | 从零手写软件渲染器，C++ 底层与内存布局的极佳教材 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 侯捷 · C++ 面向对象高级开发 | [视频](https://www.bilibili.com/video/BV14s411E772/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++11/14 新标准 | [视频](https://www.bilibili.com/video/BV1p4411v7Dh/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++ 内存管理机制 | [视频](https://www.bilibili.com/video/BV1Kb411B7N8/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 侯捷 · C++ STL 标准库与泛型编程 | [视频](https://www.bilibili.com/video/BV1db411q7B8/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 黑马程序员 · C++ 入门到精通 | [视频](https://www.bilibili.com/video/BV1Tb411j7uM/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 郑莉 · C++ 语言程序设计（清华大学） | [视频](https://www.bilibili.com/video/BV1PA411b75a/) | 本学科配套视频，建议结合本章示例与习题观看 |
