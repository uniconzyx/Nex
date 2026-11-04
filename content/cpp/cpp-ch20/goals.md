# cpp-ch20 · 综合项目与面试冲刺：系统设计、代码规范与复盘

> C++ 学习线收官章。前三阶段（基础语法 -> 面向对象与 STL -> 模板/并发/现代 C++）已搭好骨架，
> 本章把零散能力**收口成可交付的工程**：自己造一遍 STL 组件、写一个能用的线程池与 HTTP 服务器、
> 把代码规范与异常安全落到可执行的标准上，最后用高频八股与系统设计答法串讲面试。

## 一、学习目标

1. **造一遍 STL，把 RAII / 拷贝-移动语义 / 异常安全 / 迭代器失效学透**
   - 迷你 `vector`：容量倍增策略、`reserve` 语义、迭代器失效（对应 ex01 / ex02 / ex12）。
   - 迷你 `shared_ptr`：控制块与引用计数、`weak_ptr` 打破循环引用（对应 ex03 / ex04）。
   - RAII 守卫：把释放钉死在析构函数里，正常/异常/提交三条路径都不漏（对应 ex05）。
2. **实现一个真实并发组件：线程池 + 简易 HTTP 服务器**
   - 任务队列 + 条件变量 + 优雅关闭（对应 ex06）。
   - 请求行解析：纯字符串确定性解析（对应 ex07）。
3. **把异常安全等级与代码规范变成可判断的标准**
   - 基本保证 / 强保证 / 不抛（对应 ex08）。
   - 移动语义与 RVO、对象模型与虚表（对应 ex09 / ex10 / ex11）。
4. **面试冲刺**：用白板题（LRU Cache，对应 ex13）与高频八股，把知识收敛成能讲、能写、能比的状态。

## 二、与已验证示例的对应关系

| 示例 | 承载的能力点 | 本章落点 |
|---|---|---|
| ex01 迷你 vector 容量倍增与 reserve | 容量策略、引用/迭代器失效 | concept-01、pitfalls-1 |
| ex02 深拷贝、移动与 copy-and-swap | 移动语义、自赋值安全 | concept-01、pitfalls-2/3 |
| ex03 迷你 shared_ptr 控制块 | 引用计数、控制块布局 | concept-01、pitfalls-4 |
| ex04 循环引用与 weak_ptr | 内存泄漏根因、打破手段 | concept-01、pitfalls-5/6 |
| ex05 RAII 守卫三路径 | 资源释放钉死在析构 | concept-02/03、pitfalls-7/9 |
| ex06 线程池优雅关闭 | 并发组件工程化 | concept-02、pitfalls-15 |
| ex07 HTTP 请求行解析 | 确定性协议解析 | concept-02 |
| ex08 异常安全等级 | 基本/强/不抛 | concept-03、pitfalls-8 |
| ex09 移动 vs 拷贝计数 | 移动消除收益量化 | concept-04、pitfalls-10/11 |
| ex10 RVO / 移动消除 | NRVO、不要画蛇添足 move | concept-04、pitfalls-10/11 |
| ex11 虚函数表与对象模型 | vptr、动态绑定、切片 | concept-04、pitfalls-12/13 |
| ex12 STL 迭代器失效 | 容器复杂度与失效边界 | concept-04、pitfalls-14 |
| ex13 LRU Cache | 白板题参考实现 | concept-05、pitfalls-15 |

## 三、学完本章你将具备什么 / 进阶方向

- **能独立设计一个带所有权语义的 C++ 组件**：不再调 STL 就行，而是知道每个容器的失效边界、
  每个智能指针的代价，能在需要时拼出可用实现。
- **能写出异常安全、const 正确、RAII 彻底的代码**：这是区分会写和写得专业的分水岭。
- **能应对 C++ 高频面试**：虚表、移动语义、智能指针、迭代器失效、编译链接与内存布局都能讲清原理而非背结论。
- **进阶方向**：① 读源码（libstdc++ / folly / abseil）；② 参与开源（从修文档与单测起步）；
  ③ 跟进 C++23 新特性（`std::expected`、`std::mdspan`、`std::generator`、deducing this）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [isocpp/CppCoreGuidelines](https://github.com/isocpp/CppCoreGuidelines) | 45,390 | §3.1 一、异常安全等级（Basic / Strong / No-throw） | 读 `isocpp/CppCoreGuidelines` 的 `CppCoreGuidelines.md`：E.6（RAII 保证）与 C.vector 相关条款把「Basic / Strong / No-throw」写成了可引用规则；面试口述前先按编号找到原文，比背二手总结更抗追问——尤其是「为什么 `vector::push_back` 只给基本保证」这类题，原文会直接指到「重分配时移动构造若不是 noexcept 就退化为拷贝」 |
| 2 | [cpp-best-practices/cppbestpractices](https://github.com/cpp-best-practices/cppbestpractices) | 8,851 | §2.1 一、线程池：任务队列 + 条件变量 + 优雅关闭 | 读 `cpp-best-practices/cppbestpractices` 的 `README.md`：`chapters/` 目录按主题分章（工具、风格、CMake、测试、CI），每章末尾给可执行检查项；拿它给自己的项目做一次体检，能找出「能跑但不能交付」的具体项——这正是本章在 §3.2「RAII 与所有权」之外要补的工程面 |
| 3 | [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 286,133 | §5.2 二、系统设计题答法 | 读 `practical-tutorials/project-based-learning` 的 `README.md` 的 C++ 一节：它列了几十个「从零写一个 X」的项目（解释器、渲染器、数据库）；面试讲项目经历时，从这类项目里挑一个真正做完的，比堆功能列表更能撑住「你解决过什么真实约束」的追问——配合本章 §5.1「白板 coding 训练法」看，系统设计题的答法本质是把 §1「迷你 vector」与 §2「线程池」这类「你亲手写过的组件」复用成论据 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §4.1 虚函数表与对象模型 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（迷你 vector）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | §4.3 STL 容器复杂度与迭代器… | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（迷你 vector）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | §4.1 虚函数表与对象模型 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（迷你 shared_ptr）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | §4.1 虚函数表与对象模型 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（shared_ptr 循环引用泄漏与 w）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
