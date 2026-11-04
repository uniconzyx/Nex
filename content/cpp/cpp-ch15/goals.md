# cpp-ch15 · 命名空间与模块化：namespace / inline namespace / C++20 模块

## 学习目标
完成本章后，你能：
1. 用 `namespace` 组织大型代码的名字作用域，理解**限定查找**与**未限定查找**的差异。
2. 解释 ADL（参数依赖查找）的动机、机制与「意外选中他处重载」的坑。
3. 区分**匿名命名空间**（内部链接）与全局作用域，理解它与 `static` 的等价语义。
4. 用 `inline namespace` 实现**库版本化与 ABI 兼容**；用命名空间别名简化长前缀。
5. 分清 `using` 声明与 `using` 指令（污染风险），并遵守「头文件里禁用 `using namespace`」的铁律。
6. 理解 C++20 **模块（`import`/`export`）** 解决了头文件文本包含的三类顽疾（编译时间、宏泄漏、ODR），并掌握与旧头文件的混用边界。

## 前置
- cpp-ch14 预处理与宏（理解 `#include` 文本包含、翻译单元、ODR 背景）

## 真题依据（真实可查）
- LeetCode 无对应专门题；但命名空间污染 / ADL 是编译期高频 debug 现场（见 pitfalls）。
- 工程级阅读：llvm/llvm-project（模块化与分层命名空间实践）。

## 验收标准
- 能解释「为什么头文件里写 `using namespace std;` 是反模式」。
- 能写一个用 `inline namespace` 做版本切换、并用 `using` 声明选择性暴露符号的小库。
- 能说清模块相比头文件解决的三件事，以及哪些场景仍需保留头文件（如纯 C 接口、`#include` 宏）。

## 面试权重
- 中高：ADL、匿名命名空间的内部链接、`inline namespace` 版本化、模块动机是高频追问；
  与「ODR」「链接模型」「编译期模型」强相关，是区分「会用」与「懂编译/链接」的分水岭。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,899 | §3.2 二、实现机制：透明性从何而来 | 读 `include/fmt/base.h`：`FMT_BEGIN_NAMESPACE` 展开成 `namespace fmt { inline namespace v11 {`，于是 `fmt::format` 与 `fmt::v11::format` 是同一个实体；库靠它做到「ABI 版本可以换、用户代码不用改」——本章 §3.1「为什么需要 inline namespace」的答案是：普通嵌套命名空间做不到「同名别名」，而 inline 让内层名字自动进入外层作用域 |
| 2 | [abseil/abseil-cpp](https://github.com/abseil/abseil-cpp) | 18,177 | §3.1 一、理论根基：为什么需要「inline namespace」 | 读 `abseil/abseil-cpp` 的 `absl/base/config.h`：`ABSL_NAMESPACE_BEGIN` 展开成 `namespace absl { ABSL_INTERNAL_NAMESPACE {`，具体名字由 `absl/base/options.h` 的 LTS 宏决定；对照 fmt 与 abseil 两种版本化命名空间，能看清「透明 vs 显式」的取舍——fmt 用 inline 让用户无感，abseil 让用户可以显式写 `absl::lts_20240116::` 锁死版本 |
| 3 | [apache/brpc](https://github.com/apache/brpc) | 17,638 | §1.2 二、实现机制：名字查找到底怎么走 | 读 `apache/brpc` 的 `src/brpc/server.h`：`namespace brpc` 下再分 `policy`、`detail` 等子命名空间，对外只暴露少数类型；读它的 include 顺序与 `using` 声明，能看到「哪些名字允许被 ADL 找到、哪些必须写全限定名」是被刻意设计的——这正是本章 §1.5「五、可运行示例：眼见为实」里 ADL 那一例的现实约束：ADL 只查实参类型所在命名空间，所以把重载放进 `detail` 就同时切断了 ADL |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §4.1 头文件到底有什么病 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（命名空间嵌套与 using 声明）核对 |
| 2 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex02`（ADL（参数依赖查找）演示）核对 |
| 3 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex03`（匿名命名空间（内部链接））核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（inline namespace 版本切）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
