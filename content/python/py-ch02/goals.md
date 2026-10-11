# py-ch02 · 函数与作用域：def、参数解包、lambda、闭包、命名空间 · 学习目标

完成本章后，你能：

1. 理解 Python 对象模型：一切皆对象、名字绑定（而非"盒子"）、引用语义与可变/不可变对象（CPython 引用计数、GIL 背景）。
2. 掌握 `def` 定义函数，区分位置/默认/`*args`/`**kwargs` 参数，并会用 `*seq` / `**dict` 解包传入调用。
3. 理解 LEGB 作用域链与命名空间（局部/闭包/全局/内建），会用 `global` / `nonlocal` 改写外层变量。
4. 掌握 lambda 表达式与"一等公民函数"：函数可赋值、传参、返回、存容器（字典分发、回调、高阶函数）。
5. 理解闭包：自由变量绑定、延迟绑定陷阱（循环 lambda）与修复，能写出有状态工厂函数。
6. 规避可变默认参数陷阱，掌握 `None` 哨兵惰性初始化惯用法。
7. 理解装饰器基于闭包的原理（含 `functools.wraps` 与叠放顺序），并能读懂/写出基础装饰器。


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225266 | Python 实现的全部经典算法，含详细注释 |
| [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187118 | Python 100 天从新手到大师（中文系统教程） |
| [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91310 | 微软官方 12 周机器学习入门课程，含 26 课与测验 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 600 集零基础 | [视频](https://www.bilibili.com/video/BV1ex411x7Em/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 千锋教育 · Python 700 集零基础 | [视频](https://www.bilibili.com/video/BV1R7411F7JV/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 鱼C工作室（小甲鱼）· 零基础入门学习 Python | [视频](https://www.bilibili.com/video/av52080698/) | 本学科配套视频，建议结合本章示例与习题观看 |
