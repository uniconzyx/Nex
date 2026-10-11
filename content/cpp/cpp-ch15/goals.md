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
