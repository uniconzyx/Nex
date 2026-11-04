# cpp-ch06 · 继承与多态：虚函数、抽象类与 RTTI

## 学习目标
完成本章后，你能：
1. 区分公有/保护/私有继承的语义，理解 `protected`/`private` 成员在继承体系中的可见性边界。
2. 讲清楚**派生类对象的构造/析构顺序**，并指出「基类构造/析构中调用虚函数不触发多态」这一底层事实。
3. 解释**虚函数表（vtable）与 vptr** 的内存布局，理解动态绑定的机器级实现（间接调用 + this 指针调整）。
4. 使用 `override`/`final` 显式标注覆盖关系，避免「签名写错导致默默新重载」的隐蔽 bug。
5. 定义**纯虚函数与抽象类**，用接口隔离变化，并理解抽象类不能实例化的原因。
6. 使用 `dynamic_cast` 与 `typeid` 做运行时类型判别（RTTI），理解其**运行时查表**成本与适用边界。
7. 辨析**多重继承**下的 this 指针修正（thunk/偏移）、二义性，以及**虚继承（菱形）**如何消除重复基类子对象。

## 前置
- cpp-ch05 类与对象（封装、构造/析构、拷贝控制、`this` 指针）——本章所有机制都建立在「对象内存模型」之上。

## 与后续章节的衔接
- **ch07 模板与泛型**：多态有两种范式——运行期多态（本章虚函数）与编译期多态（模板），二者在性能/灵活性/二进制体积上取舍不同，第 7 章展开对比。
- **ch10 智能指针与 RAII**：`shared_ptr<Base>` 持有派生对象是多态的天然载体；基类析构是否 `virtual` 直接决定 `delete` 派生对象时是否 UB。
- **ch18 性能与底层**：虚调用会阻断内联（devirtualization 是优化重头戏）、增大可执行体积（每多态类一张 vtable）、影响指令缓存命中。

## 真题/考点依据（真实可查）
- LeetCode 208 实现 Trie（前缀树，`implement-trie-prefix-tree`）——常用多态节点或接口封装。
- 牛客 BM65 最长公共子序列（多态封装状态机）——可借接口隔离比较策略。

## 面试权重
> **高**。继承与多态是 C++ 面向对象面试的「第一道分水岭」：几乎必问「虚函数表在哪、多继承如何布局、为什么基类析构要 virtual、虚函数有性能开销吗」。本章 concept 与 interview 直接对标这些追问。

## 验收标准
- 能画出「单继承下基类子对象 + vptr 在对象首部」的内存布局 ASCII 图。
- 能写出一个基类析构非 virtual 导致派生部分泄漏的最小复现，并解释修复方式。
- 能解释 `dynamic_cast` 在无多态基类时编译失败/返回 null 的两种情形。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [google/googletest](https://github.com/google/googletest) | 39,687 | §2.2 二、实现机制：vtable 与 vptr（核心） | 读 `google/googletest` 的 `googletest/src/gtest.cc`：`Test::Run()` 是虚函数，`UnitTestImpl::RunAllTests` 只持有 `TestInfo*`，通过基类指针调用 `Run()`——派生类 `TestBody()` 的具体实现到运行时才被选中，这就是 vptr 指到派生类 vtable 的结果；本章 §2.1「理论根基：为什么需要运行期多态」给的是动机，这里给的是「为什么恰好快」 |
| 2 | [llvm/llvm-project](https://github.com/llvm/llvm-project) | 41,282 | §3.2 二、RTTI：dynamic_cast 与 typeid 的运行时查表 | 读 `llvm/llvm-project` 的 `llvm/include/llvm/Support/Casting.h`：`classof` + `dyn_cast` 自己实现类型判别，不依赖 `dynamic_cast`（LLVM 默认关闭 RTTI）。读 `isa`/`cast`/`dyn_cast` 三件套，就明白「RTTI 只是手段，类型判别可以有更便宜的实现」——`classof` 基于一个静态的类 ID 字段做整数比较，代价是一次比较而非查表 |
| 3 | [google/leveldb](https://github.com/google/leveldb) | 39,514 | §3.1 一、纯虚函数与抽象类：接口隔离的契约 | 读 `google/leveldb` 的 `include/leveldb/env.h`：`class Env` 几乎全是纯虚函数（文件、锁、线程全抽象掉），实现放在 `util/env_posix.cc` 的 `PosixEnv : public Env`；整份 leveldb 只通过 `Env*` 访问系统调用——这是「面向接口编程」在 C++ 里的完整闭环，也是本章 §2.4「override / final：把错误交给编译器」为什么必须开 `override` 的理由：接口一改，所有实现立刻编译不过 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（公有/保护/私有继承下的成员可见性）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | §1.1 继承不是「代码复用」那么简单 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex02`（派生类构造顺序（由内向外））核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（虚函数动态绑定（基类引用调派生版本））核对 |
| 4 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | §1.2 派生类对象的真实内存布局 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex04`（override 覆盖与 final 禁）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
