# cpp-ch03 · 数组与字符串：C 数组、std::string 与字符串视图 · 学习目标

- 理解 C 风格数组的本质、与指针的关系及"数组退化"陷阱
- 掌握 `std::string` 常用接口（拼接/查找/子串/遍历）
- 理解 C 字符串（以 `\0` 结尾的字符数组）与 `std::string` 的区别与互转
- 掌握 `std::string_view` 零拷贝视图的适用场景与生命周期陷阱
- 能处理常见字符串算法（反转、分割、匹配）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [nlohmann/json](https://github.com/nlohmann/json) | 50,829 | §三 它不保证什么 | 本章讲「string_view 式零拷贝」看 `include/nlohmann/json.hpp` 的 `get_ref<const string_t&>()`：它不复制字符串，直接把内部 `std::string` 以 const 引用交出去；再读 `get<std::string>()` 的返回类型，对比「视图」和「拥有」在这一个 API 上的分野 |
| 2 | [fmtlib/fmt](https://github.com/fmtlib/fmt) | 25,899 | §一 它到底是什么：两个字段 | `include/fmt/core.h`（v11 起并入 `base.h`）里的 `basic_string_view` 是 fmt 自带实现：只存 `const Char* data_` 与 `size_t size_`，`substr` 返回新视图而非新字符串；把它和 `std::string` 的 `substr` 并排看，就明白本章「视图不拥有内存」的代价与收益 |
| 3 | [Tencent/rapidjson](https://github.com/Tencent/rapidjson) | 15,150 | §二 生命周期：唯一的、也是致命的风险 | 「视图 vs 拥有」的极端案例：`include/rapidjson/document.h` 的 `kParseInsituFlag` 直接在你的缓冲区上把 token 切开（原地写 `\\0`），解析完字符串指针指向原缓冲——省掉全部拷贝，代价是原数据不能再用 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · C++ 从 0 到 1 入门<br><sub>黑马程序员</sub> | [BV1et411b73Z](https://www.bilibili.com/video/BV1et411b73Z/) | 全章 | 按目录定位到本章语法点所在集，跟敲一遍再回来做 exercise；这套的强项是「每个特性都配一个能跑的小例子」；看完回 `ex01`（C 数组遍历求和）核对 |
| 2 | 侯捷 · STL 标准库与泛型编程<br><sub>DetachmentSy</sub> | [BV1kBh5zrEYh](https://www.bilibili.com/video/BV1kBh5zrEYh/) | 全章 | 六大部件（容器/分配器/算法/迭代器/适配器/仿函数）的协作关系，以及 traits 如何让算法适配不同迭代器；看完回 `ex02`（数组与指针关系）核对 |
| 3 | 侯捷 · C++ 面向对象高级开发（上）<br><sub>DetachmentSy</sub> | [BV1r6h5zgE2i](https://www.bilibili.com/video/BV1r6h5zgE2i/) | 全章 | 讲「类到底怎么长出来的」：构造/析构顺序、拷贝构造与赋值、深拷贝、static、类模板。看完应能画出对象内存布局；看完回 `ex03`（std）核对 |
| 4 | 侯捷 · C++ 面向对象高级开发（下）<br><sub>DetachmentSy</sub> | [BV1kBh5zrEWL](https://www.bilibili.com/video/BV1kBh5zrEWL/) | 全章 | 继承、虚函数与多态的实现机制：vptr/vtable、虚析构、委托与继承的组合取舍。对应「为什么基类析构要 virtual」；看完回 `ex04`（std）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《C++ Primer（第 5 版）》Lippman 等 |
| 2 | 《Effective C++（第 3 版）》Meyers |
| 3 | 《深度探索 C++ 对象模型》Lippman |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。