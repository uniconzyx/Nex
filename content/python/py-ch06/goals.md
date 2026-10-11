# py-ch06 · 正则与文本处理：re / 分组 / 替换 · 学习目标

## 学习目标

学完本章，你应当能够：

1. **说清 `re` 模块的四个入口**（`match` / `search` / `fullmatch` / `finditer`）各自的匹配起点与返回值语义，并能在一句话内判断"该用哪个"。
2. **熟练使用分组**：捕获组、非捕获组 `(?:...)`、命名组 `(?P<name>...)`，以及 `m.groups()` / `m.groupdict()` / `m.group(n)` 的取值口径。
3. **区分贪婪、非贪婪与占有量词**，并能解释 `.*` 与 `.*?` 在 `<a><b>` 上为何得到不同结果。
4. **识别回溯爆炸（catastrophic backtracking）**，会用原子组 `(?>...)` 或占有量词 `*+` 剪枝，也能用「改写成无歧义模式」根治。
5. **掌握零宽断言** `(?=...)` / `(?!...)` / `(?<=...)` / `(?<!...)`，并知道 Python 的 `lookbehind` **必须是定宽**这一限制。
6. **用好 `re.sub` 的三种替换形态**（字符串、函数、带反向引用的模板），并知道 `\1` 与 `\g<1>` 的取舍。
7. **能判断"该用正则还是该用 `str` 方法 / `csv` 模块"**，避免用正则解析 JSON、CSV、HTML 这类有正式语法的格式。

## 前置

- `py-ch04`（标准库：pathlib / datetime / json）—— 需要能读写文件、理解 `str` 与 `bytes` 的边界。
- 基本的字符串操作：切片、`split`、`join`、f-string。

## 面试权重

| 主题 | 出现频率 | 常见问法 |
|---|---|---|
| `re` 四大入口的区别 | 高 | "`match` 和 `search` 有什么区别？" |
| 贪婪 vs 非贪婪 | 高 | "`.*` 和 `.*?` 什么时候结果不同？" |
| 分组与反向引用 | 高 | "怎么把 `2026-10-08` 改写成 `10/08/2026`？" |
| 回溯爆炸 | 中 | "为什么这个正则会把服务打挂？" |
| 零宽断言 | 中 | "怎么匹配『后面跟着 X 的 Y』？" |
| 正则 vs 解析库 | 中 | "为什么不该用正则解析 HTML？" |

## 真题依据（真实可查，仅存元数据）

- LeetCode 题库中的**正则匹配类**题目（如「正则表达式匹配」），仅提供题号与链接，不搬运题面。
- 《Python 编程：从入门到实践》第 10 章「文件和异常」、附录「正则表达式速查」。
- 《流畅的 Python》第 3 章「字典和集合」中关于 `re` 与 `str` 方法取舍的讨论。

## 验收标准

- [ ] 能写出并解释至少 3 个含分组的正则，并说明每个分组的用途。
- [ ] 能对一段给定的「慢正则」说出它的回溯路径，并给出至少两种优化（占有量词 / 原子组 / 改模式）。
- [ ] 能完成 `examples/` 中 12 个示例的复现，且输出与 `expected_output` 一致。
- [ ] 能独立完成 `project.json` 中的日志解析项目。


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
