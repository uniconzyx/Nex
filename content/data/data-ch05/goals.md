# data-ch05 · 数据采集：requests 与解析（含合规边界）

## 一、为什么"采集"是数据分析的第一道真门槛

数据分析课上拿到的永远是干净的 CSV。真实世界里，**数据要自己找、自己拿、自己洗**：
- 找：站点结构、列表页→详情页的分页规律、有没有公开 API；
- 拿：HTTP 请求怎么发才稳（超时、重试、会话、限速），返回的是不是你要的那份数据；
- 洗：HTML 是**不合法**的结构化文本，解析器选择直接决定提取率。

而"能不能拿"永远是**先于"怎么拿"**的问题。本章把合规红线放在和其他技术点**同等**的位置：
`robots.txt`、频率控制、版权与个人信息边界、**不绕过技术措施**——这些不是"附加注意事项"，而是工程约束的一部分。

## 二、学完之后你应该能做到

1. 读一份 HTTP 响应，说清状态码、重定向链、编码来源，并判断"这份响应能不能用"。
2. 用 `requests` 写出带**超时 + 重试 + 会话复用**的请求；解释每一步在防什么。
3. 面对一个页面，按 **JSON 接口 → 静态 HTML → 浏览器内核** 的顺序选方案，并说明理由。
4. 用 `lxml`/`bs4` 稳健提取列表、属性、表格；知道正则提取的边界在哪。
5. 写出一个**守规矩**的采集器：先读 `robots.txt`，带 Crawl-delay，能识别并跳过敏感字段。
6. 排查乱码：区分"服务器声明编码错误"与"解码方式错误"，并用 `charset_normalizer` 兜底。

## 三、本章结构

| # | 概念文件 | 核心内容 |
|---|---|---|
| 1 | `01-http-in-scraping.md` | HTTP 在采集场景的落地：方法、状态码、重定向、Cookie/Session、常见反爬信号 |
| 2 | `02-requests-in-depth.md` | `requests` 实战：参数、头、超时（连接/读取）、重试与退避、会话与连接池、流式下载 |
| 3 | `03-parsing-and-encoding.md` | 解析三件套（lxml/bs4/正则）的取舍、编码与乱码排查、结构化抽取 |
| 4 | `04-dynamic-pages-and-compliance.md` | 动态渲染的应对顺序、工程化（去重/限速/断点续抓）、**合规红线** |

## 四、动手实践（建议顺序）

1. 先跑 `examples/ex01`~`ex03`：把 HTTP 报文、`Response` 对象、编码三者关系打通。
2. 再跑 `ex04`~`ex07`：URL 规范化 → XPath → bs4 容错 → 三方案对比。
3. 最后跑 `ex08`~`ex12`：`robots.txt` 判定 → 限速 → 去重调度 → 表格入库 → **合规自检清单**。

> 全部示例均为**离线可实测**：响应对象手工构造、HTML 用内联字符串，不依赖网络。
> 这不是"简化"，而是把采集拆成"网络"与"解析"两层后，**只测可确定的那一层**——解析层才是 bug 高发区。

## 五、自检清单

- [ ] 能说出 `timeout=(连接, 读取)` 两段各自的含义，以及只设一个数的后果
- [ ] 能解释 4xx/5xx 里**哪些该重试、哪些重试也没用**
- [ ] 能区分 `resp.text` 与 `resp.content`，并说出 `apparent_encoding` 的适用场合
- [ ] 能说出 `lxml` 与 `bs4` 在**容错性**上的差别，以及为什么抓网页常用 `lxml` + `bs4` 组合
- [ ] 能用最长匹配解释 `robots.txt` 的 `Disallow` / `Allow` 覆盖关系
- [ ] 能列出至少 4 条合规红线，并说明"不绕过技术措施"的具体含义


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67487 | 经典机器学习库官方仓库：算法实现与最佳实践 |
| [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50114 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib） |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49928 | Pandas 官方仓库：API 与内部机制权威来源 |
| [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37525 | 微软官方 10 周数据科学课程 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |
