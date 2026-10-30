# cpp-ch04 · 指针与内存管理：指针运算、new/delete 与悬垂 · 学习目标

- 掌握指针的取地址 `&`、解引用 `*`、空指针与指针类型匹配
- 理解指针算术与数组的底层关系，能安全地用指针遍历
- 掌握动态内存 `new` / `delete`、`new[]` / `delete[]` 及匹配规则
- 理解程序内存布局（栈/堆/全局/代码段）与栈对象生命周期
- 能识别并规避内存泄漏、悬垂指针、不匹配 delete 等常见陷阱
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [google/leveldb](https://github.com/google/leveldb) | 39,513 | 全章 | 本章讲「大块预分配 + bump 指针」看 `util/arena.h` 与 `util/arena.cc`：`Arena::Allocate` 只在当前 4KB 块里移动 `alloc_ptr_`，块用完才 `new char[]`；`AllocateAligned` 还会按 `align` 把指针向上取整——这就是本章说的「指针运算 + 手动对齐」 |
| 2 | [DaveGamble/cJSON](https://github.com/DaveGamble/cJSON) | 13,040 | 全章 | 「一 malloc 一 free 配对」的标准形态：`cJSON.c` 的 `cJSON_New_Item` 先 `malloc` 再 `memset` 清零，`cJSON_Delete` 递归释放 `child`/`next` 链表；重点看 `cJSON_Parse` 的失败路径——每个提前 return 前都先 `cJSON_Delete`，否则就是本书反复警告的那类泄漏 |
| 3 | [redis/redis](https://github.com/redis/redis) | 76,964 | 全章 | 「指针往前挪一格做记账」看 `src/zmalloc.c`：`zmalloc` 多申请 `PREFIX_SIZE` 字节，把长度写在返回指针之前，`zmalloc_size` 用 `(size_t*)ptr - 1` 取回；这是本章「指针算术 + 内存布局」最直接的工业用法，也解释了 `zmalloc_used_memory` 为什么准 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（取地址与解引用）核对 |
| 2 | 侯捷 · C++ 内存管理机制<br><sub>DetachmentSy</sub> | [BV1d3h5zFEjL](https://www.bilibili.com/video/BV1d3h5zFEjL/) | 全章 | new/delete 的真实调用链、allocator、内存池与 placement new；讲清「一次 new 到底发生了几件事」；看完回 `ex02`（指针算术）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex03`（指针遍历数组）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex04`（new / delete 单对象）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
