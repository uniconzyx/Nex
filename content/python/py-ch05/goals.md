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
