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
