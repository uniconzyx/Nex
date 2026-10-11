# py-ch01 · 语法与数据类型：变量/流程控制/字符串/列表/字典/元组/集合/推导式 · 学习目标

- 理解 Python 动态类型与"变量即名字绑定"的语义，区分可变与不可变对象
- 掌握条件分支（if/elif/else）与循环（for/while、range、break/continue）流程控制
- 熟练使用不可变字符串及其切片、格式化（f-string）等基础操作
- 掌握四种内建容器：列表 list、字典 dict、元组 tuple、集合 set 的增删查改
- 能用列表推导式（及集合/字典推导式）写出简洁、可读的批量生成代码
- 能编写可独立运行的小程序，理解 `if __name__ == "__main__"` 的入口约定


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
