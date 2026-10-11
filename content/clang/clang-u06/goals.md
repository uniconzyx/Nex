# clang-u06 · 学习目标：Makefile 与构建

## 先修
- `clang-u05` 预处理与宏（翻译阶段、`#include` 的文本包含语义）

## 本单元要解决的问题
`gcc main.c util.c -o app` 敲一次可以，敲一百次就是灾难。更麻烦的是**你不知道该重编哪些文件**：

> 我改了 `util.h`，为什么 `make` 什么都没做，可程序行为确实是旧的？
> 为什么把 Makefile 里的一行缩进从 Tab 改成空格，就报 `missing separator`？
> `make -j8` 平时很快，偶尔却编出崩溃的二进制，重跑又好了——这算什么 bug？

这三个问题分别对应**增量构建的正确性**、**Makefile 的词法规则**、**并行构建的依赖完整性**。
它们都不是语法问题，而是「构建系统如何知道该做什么」这一机制问题。

## 学习目标
1. 说清**编译四阶段**（预处理 → 编译 → 汇编 → 链接）各自的输入输出，并能用 `-E / -S / -c` 单独触发。
2. 读懂**目标文件结构**：`.text / .data / .bss / .rodata` 各段、符号表与**重定位表**，会用 `objdump -h`、`nm`、`size` 观察。
3. 掌握 **Makefile 规则模型**：`target: prerequisites` + recipe、依赖图、**时间戳（mtime）比较**驱动的增量判定。
4. 区分变量赋值 **`=`（递归展开）/ `:=`（立即展开）/ `?=` / `+=`** 的语义差异与副作用。
5. 熟练使用**自动变量**（`$@ $< $^ $? $*`）与**模式规则**（`%.o: %.c`），理解隐式规则的作用与风险。
6. 理解 **`.PHONY`** 的必要性（同名文件导致的静默跳过），并知道 `mingw32-make` 这类命名差异的由来。
7. 掌握**头文件依赖**的正确处理：`-MMD -MP` 自动生成 `.d` 并 `-include`，避免「改了头文件不重编」。
8. 理解 **`make -j` 并行构建**与依赖声明完整性之间的关系，以及递归 make、现代构建系统（CMake/Ninja）的演进动因。

## 与 clang-u07 的分工
- **u06（本单元）**：构建**编排**——谁在什么时候被编译、依赖怎么声明、并行怎么调度。
- **u07**：符号**语义**——声明与定义的差别、链接属性、静态库/动态库、强符号弱符号。
两者互补：u06 让你「把工程编出来」，u07 让你「看懂链接器为什么报错」。

## 面试权重
★★★★★（C/C++ 岗位必考：编译四阶段、Makefile 依赖、增量构建、`make -j` 的坑）


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
