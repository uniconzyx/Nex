# py-ch04 · 标准库：os / sys / re / datetime / json · 学习目标

## 学习目标

学完本章你能：

1. 用 `pathlib.Path` 替代绝大多数 `os.path` 字符串拼接，写出**跨平台**的路径代码；
2. 说清 `sys.argv` / `sys.path` / 标准流这三件事，并写出能被 shell 与 CI 调用的命令行工具；
3. 正确处理「带时区的时间」与「不带时区的时间」，避开本地时间与夏令时的经典坑；
4. 掌握 `json` 的序列化边界——哪些类型能过、哪些会炸、如何自定义编码器；
5. 知道 `re` 在本章属于**速览层**，分组/替换/回溯的深挖见 `py-ch06`。

## 前置

- `py-ch01` Python 基础语法（变量、函数、模块导入）
- 会用终端执行 `python script.py`

## 面试权重

★★★★☆（后端 / 数据 / 运维岗位高频。`pathlib` 写法与 `datetime` 时区是筛人题）

## 真题依据（真实可查，仅存元数据）

| 来源 | 位置 | 主题 |
|---|---|---|
| 官方文档 | `docs.python.org/3/library/pathlib.html` | 路径对象 API |
| 官方文档 | `docs.python.org/3/library/datetime.html` | naive / aware 语义 |
| 《Python 编程：从入门到实践》 | 第 10 章 文件与异常 | 文件读写与异常 |
| 《流畅的 Python》(第 2 版) | 第 12 章 序列的修改、散列和切片 | 标准库设计风格 |

## 验收标准

- [ ] 能把一段 `os.path.join` 拼路径的代码改写为 `pathlib` 风格，并说明为什么更安全
- [ ] 能写出一个接收命令行参数、打印帮助、异常时返回非零退出码的脚本
- [ ] 能解释 `2026-10-07 14:30:00` 与 `2026-10-07T14:30:00+08:00` 的区别及各自风险
- [ ] 能说明为什么 `json.dumps({1: "a"})` 不报错但 `json.dumps({(1, 2): "a"})` 报错
- [ ] 能独立完成本章项目（日志清洗 CLI）
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,745 | §1.3 | 讲「os 与路径处理」时读仓库根目录的脚本组织方式：所有算法按目录归类、用 `if __name__ == "__main__"` 提供自测入口，这是「模块 vs 脚本」的现成范例 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,609 | §2.2 | 讲「datetime 与时区」时看 `Day16-20/` 的日期处理篇：`datetime` 是「无时区」的、`timezone` 要显式加，混用会导致跨时区差 8 小时 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,917 | §1.2 | 讲「json 读写」时看入门课的数据集加载：把配置与标签放在 JSON 里、用 `json.load` 读，比硬编码在脚本里更好维护 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | 全章 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（PurePath 语义）核对 |
| 2 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex02`（相对路径依赖 cwd）核对 |
| 3 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex03`（iterdir / glob / rgl）核对 |
| 4 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | 全章 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex04`（os.path 与 pathlib 的逐）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
