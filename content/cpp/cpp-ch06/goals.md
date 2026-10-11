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
