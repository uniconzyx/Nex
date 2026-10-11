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
