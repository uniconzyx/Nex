# cpp-ch11 · 异常处理与断言：try/catch、noexcept 与契约

## 学习目标
完成本章后，你能：
1. 使用 `throw` / `try` / `catch` 结构化地处理错误，理解**栈展开（stack unwinding）**与对象析构的确定性。
2. 解释 C++ 异常的**零开销原则**（zero-overhead principle）：正常路径不付代价，但异常路径与代码体积有成本。
3. 掌握**异常安全三保证**（基本 / 强 / 不抛），并用 RAII 把"保证"落实到代码。
4. 正确使用 `noexcept`：理解它对 `std::vector` 扩容时"移动 vs 拷贝"的决定性影响，以及对 `std::terminate` 的约束。
5. 使用标准异常体系（`std::exception` 派生类）、`assert` 与编译期 `static_assert`，并理解断言/契约的定位（调试 vs 契约）。
6. 对比 **错误码 / C++ 异常 / Rust `Result`** 三种错误处理范式的取舍。

## 前置
- cpp-ch05 类与对象（构造/析构、RAII 雏形、三/五法则）
- （建议）cpp-ch10 智能指针与 RAII（本章大量依赖 RAII 保证异常安全）

## 真题依据（真实可查）
- 《C++ Primer（第5版）》第 18 章 用于大型程序的工具（异常处理、命名空间、多重继承）。
- C++ Core Guidelines：E 系列（Error handling，见 `isocpp/CppCoreGuidelines`）。
- google/sanitizers：ASan/UBSan 运行期检查实践。

## 验收标准
- 能解释"为什么析构函数不能抛异常"。
- 能写出一个**带强异常安全保证**的容器/操作（如 `push_back` 失败则状态回滚）。
- 能判断一段 `vector` 扩容代码会走"移动"还是"拷贝"，并说明 `noexcept` 的决定作用。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,897 | §1.2 栈展开到底发生了什么 | §1.2 栈展开前的最后一站：`include/fmt/base.h` 的 `FMT_THROW` 可被配置成抛异常或直接 abort，`FMT_ASSERT` 在 debug 下抛 `format_error`；读这两个宏的分支，就看清「库要不要让异常穿过自己」是一个可配置的契约，而不是语言强制 |
| 2 | [google/googletest](https://github.com/google/googletest) | 39,670 | §3.4 断言 | §3.4 断言分级：`googletest/include/gtest/gtest.h` 里 `EXPECT_*` 失败继续跑、`ASSERT_*` 失败立刻 return，`EXPECT_THROW`/`EXPECT_NO_THROW` 把「抛不抛」变成可断言的性质，`ASSERT_DEATH` 连崩溃都能测；这套 API 是本章「断言与异常各管一段」的现实版 |
| 3 | [nlohmann/json](https://github.com/nlohmann/json) | 50,813 | §2.1 异常安全的"契约" | §2.1 异常安全契约的开关：`include/nlohmann/json.hpp` 的 `JSON_THROW` 由 `JSON_NOEXCEPTION` 决定展开成`throw` 还是 `std::abort`，`parse(..., allow_exceptions=false)` 则让调用方自己查 `is_discarded()`；同一个库给出三条错误处理路径，正好对本章的「异常 vs 错误码 vs 终止」取舍 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §1.1 异常不是"错误返回"，而是… | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（try/catch 多重捕获与匹配顺序（）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §3.2 noexcept 如何改变… | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（栈展开演示）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | §3.2 noexcept 如何改变… | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（异常安全 RAII）核对 |
| 4 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex04`（noexcept 函数声明与调用（契约）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
