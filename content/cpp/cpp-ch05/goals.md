# cpp-ch05 · 类与对象：封装、构造/析构、拷贝与运算符重载

## 学习目标
完成本章后，你能：
1. 定义类与访问控制（`public` / `protected` / `private`），理解封装的意义。
2. 编写构造函数（含初始化列表）、析构函数，并理解其调用时机。
3. 实现拷贝构造函数与拷贝赋值运算符，掌握**三/五法则**（Rule of Three/Five）。
4. 编写 `const` 成员函数、静态成员、友元与运算符重载。
5. 用类封装资源，初步理解 RAII 思想（为 ch10 智能指针铺垫）。

## 前置
- cpp-ch02 函数与参数传递
- cpp-ch04 指针与内存管理

## 真题依据（真实可查）
- LeetCode 707 设计链表（`design-linked-list`）——用类封装节点与链表。
- 牛客 BM101 设计 LRU 缓存（`BM101`）——类封装哈希 + 双向链表。

## 验收标准
- 能独立写出一个满足 Rule of Three 的字符串包装类。
- 能解释 `const` 成员函数、`const` 对象、运算符重载的返回值类型选择。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [ssloy/tinyrenderer](https://github.com/ssloy/tinyrenderer) | 24,335 | §3.4 四、工程实践：返回类型与复合赋值的约定 | 读 `ssloy/tinyrenderer` 的 `geometry.h`：`Vec3` 的 `operator+`/`operator*` 全部返回值（不是引用），因为 `a+b` 的结果是个临时量；而 `operator+=` 返回 `Vec3&` 以支持链式。把这两个返回类型并排看，就是本章「复合赋值返回引用、二元运算返回值」的判据；配合 §3.3「成员函数 vs 非成员函数：对称性判据」，再看 `Vec3 operator*(float, const Vec3&)` 为什么必须写成非成员 |
| 2 | [nlohmann/json](https://github.com/nlohmann/json) | 50,829 | §2.4 四、工程实践：正确的拷贝赋值写法 | 读 `nlohmann/json` 的 `include/nlohmann/json.hpp` 里 `basic_json`：它显式写了拷贝构造、拷贝赋值、`swap`；读 `swap` 的实现会发现它交换的是内部 `json_value` union 与指针——这正是「拷贝赋值用 copy-and-swap 拿到强异常安全」的实例，对应本章 §2.3「实现机制：拷贝省略与 RVO」之外的另一半：RVO 省掉的是构造，copy-and-swap 保证的是「要么成功要么原样」 |
| 3 | [google/leveldb](https://github.com/google/leveldb) | 39,514 | §1.2 二、实现机制：对象在内存里到底是什么 | 读 `google/leveldb` 的 `include/leveldb/env.h` 与同目录的 `slice.h`：`Slice` 只有 `const char* data_` 与 `size_t size_` 两个成员，`sizeof(Slice)` 就是 16 字节且不拥有任何内存；它把「轻量值类型」做到了极致——按值传参也不亏，因为拷贝的只是这两个字段；本章 §1.3「工程实践：程序员视角的取舍」里的「值语义 vs 引用语义」判据，在这两行成员上就有了具体形态 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | §3.1 运算符本质上是"有语法糖的… | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（基本类定义与成员访问）核对 |
| 2 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex02`（构造函数与初始化列表）核对 |
| 3 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | §1.2 对象在内存里到底是什么 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex03`（const 成员函数与 const 对象）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（静态成员）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
