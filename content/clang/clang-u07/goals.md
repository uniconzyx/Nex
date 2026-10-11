# clang-u07 · 学习目标：多文件编译与链接

## 先修
- `clang-u05` 预处理与宏（翻译阶段、头文件包含语义）
- `clang-u06` Makefile 与构建（四阶段产物、构建自动化）

## 本单元要解决的问题
单个 `.c` 文件里写完全部代码只能做练习。真实工程必然是多文件、多模块，甚至多语言混编。
一旦拆成多个文件，新问题立刻出现：

> 函数写在 `a.c`，在 `b.c` 里调用，为什么编译器说「未定义引用（undefined reference）」而不是「未声明」？
> 为什么同一个 `int x;` 写在头文件里被两个 `.c` 包含，链接就报「multiple definition」？
> `static` 加在函数上和不加，差别到底在哪一层？

这些问题的答案都不在语法层面，而在**链接（linking）**这一环：它把多个独立的编译单元
缝合成一个可执行文件。不掌握链接，就只能靠试错写 `extern`。

## 学习目标
1. 说清**翻译单元（translation unit）**的边界，区分**声明**与**定义**在链接阶段的后果。
2. 掌握 **链接属性（linkage）**：外部链接 / 内部链接 / 无链接，以及 `extern`、`static` 如何改变它。
3. 读懂**符号表**：用 `nm` 区分 `T`（已定义文本段）/ `U`（未定义，待链接）/ `D`/`B`（数据）等符号类型。
4. 会用 **静态库（`.a`）** 与理解**动态库（`.dll`/`.so`）**的链接差异与取舍。
5. 掌握**链接顺序敏感性**的根因，并能用 `--start-group` 解决静态库循环依赖。
6. 理解**强符号 / 弱符号**、多重定义的判定规则，以及 C++ 名称修饰（name mangling）与 `extern "C"`。
7. 能用 `nm` / `objdump` / `size` 做链接期排障。

## 与后续衔接
- 衔接 `cpp-ch15`（命名空间与模块化）：C++ 的 ODR 与模块正是为了解决这里的痛点。
- 衔接 `tool-ch01`（Linux）：动态库加载、`ldd`、`LD_LIBRARY_PATH` 是同一套机制的运维视角。

## 面试权重
★★★★☆ —— 「为什么头文件里不能放定义」「`static` 函数和普通函数的区别」「静态库和动态库怎么选」
「`undefined reference` 和 `未声明` 的区别」是 C/C++ 岗位高频起点题，且能一路追问到 ODR、ABI。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 286133 | 项目驱动的实战教程合集（含 C 专题） |
| [TheAlgorithms/C](https://github.com/TheAlgorithms/C) | 22507 | C 语言实现的算法与数据结构合集 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 小甲鱼 · 带你学透 C 语言 | [视频](https://www.bilibili.com/video/BV1ti4y1K7rA/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 郝斌 · C 语言自学完整版 | [视频](https://www.bilibili.com/video/BV1vh411S7LV/) | 本学科配套视频，建议结合本章示例与习题观看 |
