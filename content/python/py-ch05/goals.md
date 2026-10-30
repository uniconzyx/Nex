# py-ch05 · 文件与 IO：读写 / 上下文管理器 / 序列化 · 学习目标

## 学习目标

学完本章，你应当能够：

1. **文本与二进制文件**——分清 `open(mode="r")` 与 `"rb"` 的语义差异；理解 `encoding`
   与 `newline` 参数为什么必须显式写；能识别 BOM（`utf-8-sig`）与换行符差异带来的 bug。
2. **上下文管理器**——理解 `with` 的展开过程（`__enter__` / `__exit__` / 异常传播），
   能自己写一个可复用的资源管理器，并知道 `contextlib.contextmanager` / `ExitStack` 的适用场景。
3. **缓冲与落盘语义**——分清 **Python 缓冲区**（`flush`）与 **OS 页缓存**（`fsync`）两层；
   会写「原子写入」（临时文件 + `os.replace`），知道为什么 `f.write` 成功不等于数据安全。
4. **序列化**——`csv` 与 `json` 的读写；大文件流式处理（逐行迭代 vs `read()`）；
   `json.dump(ensure_ascii=False)` 与编码的关系；`csv` 的 `newline=""` 为什么是必须的。

## 前置

- `py-ch01`（基础语法）、`py-ch04`（pathlib / json 边界）为**软前置**：
  本线**独立自足**，若你已能用 Python 写函数与循环、知道 `pathlib.Path` 的基本用法，
  可直接从本章开始；不熟则先花 1~2 小时过一遍这两个主题，本章不依赖其进阶内容。

## 面试权重

| 考点 | 出现频率 | 常见问法 |
|---|---|---|
| `with` 的原理与自定义上下文管理器 | 高 | 「`with` 帮我们做了哪三件事？」「异常时 `__exit__` 的返回值有什么作用？」 |
| 文本 vs 二进制模式、编码坑 | 高 | 「为什么读文件要显式指定 encoding？」「`UnicodeDecodeError` 怎么排查？」 |
| `flush` / `fsync` / 原子写入 | 中高 | 「`f.write()` 返回了，数据一定在磁盘上吗？」 |
| 大文件处理 | 中高 | 「一个 10 GB 的日志文件，你如何统计某个字段？」 |
| csv / json 的边界 | 中 | 「`csv` 为什么必须 `newline=""`？」「中文写入 json 为什么成了 `\u4e2d`？」 |

## 真题依据（真实可查，仅存元数据）

- 教材：《Python 编程：从入门到实践》第 10 章「文件和异常」；《流畅的 Python》第 12 章
  「文本和字节序列」。
- 官方文档：`open()` / `io` / `contextlib` / `csv` / `json` 模块（题面以官方链接为准）。
- 平台题：LeetCode 按 `pathlib`、`file io` 标签检索（本章题集仅存元数据与链接，不搬运题面正文）。

## 验收标准

- [ ] 能不看文档写出一个「自动关闭 + 异常时回滚」的上下文管理器
- [ ] 能解释 `flush` 与 `fsync` 的区别，并写出一个原子文件替换函数
- [ ] 能说出至少 3 种「读文件读出乱码」的原因与对应排查手段
- [ ] 能用恒定内存处理一个大于可用内存的文本文件
- [ ] 完成 `exercises.json` 中全部基础题，并至少独立完成 1 道算法题
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225,569 | 全章 | Python 实现的全部经典算法，含详细注释；本章先读与「两种模式，两套世界」「`encoding` 必须…」相关的部分 |
| 2 | [jackfrued/Python-100-Days](https://github.com/jackfrued/Python-100-Days) | 187,492 | 全章 | Python 100 天从新手到大师（中文系统教程）；本章先读与「两种模式，两套世界」「`encoding` 必须…」相关的部分 |
| 3 | [microsoft/ML-For-Beginners](https://github.com/microsoft/ML-For-Beginners) | 91,785 | 全章 | 微软官方 12 周机器学习入门课程，含 26 课与测验；本章先读与「两种模式，两套世界」「`encoding` 必须…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 零基础（8 天）<br><sub>黑马程序员</sub> | [BV1qW4y1a7fU](https://www.bilibili.com/video/BV1qW4y1a7fU/) | §3.6 大文件处理的内存红线 | 主线课：语法、函数与作用域、面向对象、文件与异常，节奏紧凑且每节都有练习；看完回 `ex01`（文本模式 vs 二进制模式）核对 |
| 2 | 黑马程序员 · Python 数据分析<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | numpy 的 ndarray 与广播、pandas 的 Series/DataFrame 与分组聚合，配真实 CSV 案例；看完回 `ex02`（解码失败的四种 errors 策略）核对 |
| 3 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | 最短路径：每集 5 分钟讲一个 API，适合当「动手前的速查手册」而不是系统课；看完回 `ex03`（换行符翻译）核对 |
| 4 | 黑马程序员 · Python 600 集全<br><sub>黑马程序员</sub> | [BV1ex411x7Em](https://www.bilibili.com/video/BV1ex411x7Em/) | 全章 | 查漏用：讲得慢而全，容器底层、深浅拷贝、装饰器这些容易含糊的点在这里有完整推导；看完回 `ex04`（BOM 是 3 个真实字节）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《Python 编程：从入门到实践（第 3 版）》Matthes |
| 2 | 《流畅的 Python（第 2 版）》Ramalho |
| 3 | 《利用 Python 进行数据分析（第 3 版）》McKinney |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
