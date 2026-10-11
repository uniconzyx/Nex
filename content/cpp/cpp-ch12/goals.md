# cpp-ch12 · 现代 C++ 特性：auto / 移动语义 / 范围 for / emplace

> **先修**：cpp-ch07（模板与泛型，理解 `auto` 推导与转发引用）、cpp-ch10（智能指针与 RAII，移动语义的工程动机）。
> **衔接**：cpp-ch13 文件 IO、cpp-ch17 元编程与 `concept`（`auto` 与类型萃取配合）、cpp-ch18 性能与底层（移动/拷贝的零开销取舍）。
> **面试权重**：★★★★★ —— 移动语义、`auto`、emplace 是现代 C++ 面试的绝对核心，几乎每场必问，且极易深挖。

## 学完你能做到

1. **说清 `auto` 的推导规则**：知道 `auto` 与模板实参推导一致；能区分 `auto`、`auto&`、`const auto&`、`decltype(auto)` 各自保留/丢弃了什么。
2. **讲透移动语义的本质**：右值引用、`std::move` 只是「无条件的类型转换（cast）」、移动构造/移动赋值的「窃取而非复制」语义，以及为什么移动构造通常要标 `noexcept`。
3. **分清三种值类别**：`lvalue` / `prvalue` / `xvalue`，理解「右值引用本身是左值」这一反直觉点。
4. **正确使用范围 for**：知道它等价于哪段迭代器循环，理解在循环中增删元素导致的迭代器失效。
5. **用对 `emplace_back`/`emplace`**：理解「原地构造少一次拷贝/移动」与转发引用参数的陷阱，能画出 `push_back` vs `emplace_back` 的构造次数对比。
6. **掌握现代便利设施**：结构化绑定、`std::optional`、`std::string_view` 的设计取舍与悬垂风险。

## 博士视角（要理解到什么程度）

- **`auto` 是语法层面的类型占位**：它的推导规则与函数模板的实参推导完全统一（C++11 起），因此理解模板推导就理解了 `auto`；`decltype(auto)` 进一步用 `decltype` 的规则保留引用与 cv 限定。
- **移动语义是「对资源所有权的转移」，不是「对象搬家」**：被移动后的源对象处于「有效但未指定状态」，标准允许它继续存在但值不确定，这是异常安全与性能之间权衡的结果（见 Howard Hinnant 关于「移动后状态」的论述）。
- **`noexcept` 是给标准库的「性能契约」**：`std::vector` 在扩容重分配时，只有元素的移动构造是 `noexcept` 才敢用移动（否则回退到拷贝以保证强异常安全），这是库作者与语言规则的协作点。

## 程序员视角（要能用出来）

- 用 `auto` 减少冗余类型名，但**返回函数接口、容器元素类型、涉及引用/const 的推导**要谨慎，避免意外拷贝。
- 写「管理资源」的类时，`= default` 或手写移动操作，并给移动构造/赋值标 `noexcept`。
- 在现代 C++ 里，**能用 `emplace_back` 就别 `push_back(临时)`**；遍历尽量用范围 for；读字符串切片用 `string_view` 避免分配。


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
