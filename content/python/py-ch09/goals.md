# py-ch09 · 面向对象：类、继承与魔术方法 · 学习目标

- 能讲清「类、实例与属性查找顺序」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「继承、MRO 与 super()」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「魔术方法：让对象接入语言协议」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 2 道编程题）与 4 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-28** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [python/cpython](https://github.com/python/cpython) | 77,791 | §1.4 属性查找 · §2.3 C3 | 解释器本体：Objects/ 下是 MRO、描述符协议、属性查找的真实实现，读 `Objects/typeobject.c` 的 `tp_getattro` 与 MRO 计算，直接对应本章 §1.4、§2.3 |
| 2 | [pallets/flask](https://github.com/pallets/flask) | 74,968 | §2.1 super | 工业级 metaclass 样例：Flask 用 `Scaffold` + `__init_subclass__` 收集视图，`App` 的继承与 `super()` 调用链正是 §2.1 讲的那套机制 |
| 3 | [python-attrs/attrs](https://github.com/python-attrs/attrs) | 5,863 | §3.2 property | 描述符与 `__getattr__` 的工业级应用：读 `attrs` 如何用描述符把类属性变成带校验的字段，对应 §3.2 三种方法修饰符 |
| 4 | [faif/python-patterns](https://github.com/faif/python-patterns) | 43,072 | §2.2 多继承 | GoF 设计模式合集，直接对应「继承 vs 组合」的取舍，§2.2 讲「什么时候真的该用多继承」时拿这里的 Strategy/Adapter 当反例 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 苑昊老师 · Python 面向对象<br><sub>苑昊老师</sub> | [BV1FXDVYkEQh](https://www.bilibili.com/video/BV1FXDVYkEQh/) | §1.1 类属性 · §3.1 规矩 | 主线课：类与对象、继承、魔术方法系统推导；看完回 `ex01`（类属性 vs 实例属性）核对 |
| 2 | 小渔学长 · 类与对象<br><sub>小渔学长</sub> | [BV1Vt411E7E3](https://www.bilibili.com/video/BV1Vt411E7E3/) | §1.2 创建对象 | 偏实战：实例化全流程、self 语义、`__init__` 与 `__new__` 的关系；看完回 `ex02`（MRO 手算）核对 |
| 3 | 码农高天 · 魔术方法大全<br><sub>码农高天</sub> | [BV1b84y1e7hG](https://www.bilibili.com/video/BV1b84y1e7hG/) | §3.1 规矩 · §3.3 查找 | 短而全：常用 dunder 方法一览与触发时机；看完回 `ex03`（描述符优先级）核对 |
| 4 | 水哥澎湃 · __new__ 与 __init__ 顺序<br><sub>水哥澎湃</sub> | [BV1mT43zhE8L](https://www.bilibili.com/video/BV1mT43zhE8L/) | §1.3 实验 | 专讲 `__new__` 先于 `__init__` 的实证实验，直接对应本章 §1.3 那一段可运行演示 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《流畅的 Python（第 2 版）》Ramalho — 第 9 章「类与协议」、第 20 章「属性描述符」 |
| 2 | 《Effective Python（第 2 版）》Slatkin — Item 42「用 super 初始化父类」、Item 43「理解 MRO」 |
| 3 | 《Python 编程：从入门到实践（第 3 版）》Matthes — 第 9 章「类」 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
