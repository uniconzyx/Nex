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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67,957 | 全章 | 经典机器学习库官方仓库：算法实现与最佳实践；本章先读与「请求方法、状态码与"这份响…」「重定向链、Cookie 与…」相关的部分 |
| 2 | [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50,277 | 全章 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib）；本章先读与「请求方法、状态码与"这份响…」「重定向链、Cookie 与…」相关的部分 |
| 3 | [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 50,278 | 全章 | Pandas 官方仓库：API 与内部机制权威来源；本章先读与「请求方法、状态码与"这份响…」「重定向链、Cookie 与…」相关的部分 |
| 4 | [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37,860 | 全章 | 微软官方 10 周数据科学课程；本章先读与「请求方法、状态码与"这份响…」「重定向链、Cookie 与…」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 黑马程序员 · Python 数据分析全套<br><sub>黑马程序员</sub> | [BV1ReshzoEgG](https://www.bilibili.com/video/BV1ReshzoEgG/) | 全章 | 从 numpy/pandas 到清洗、可视化、案例的完整链路，配真实的电商与招聘数据集；看完回 `ex01`（HTTP 状态码分类与重试判定）核对 |
| 2 | 莫烦 Python · NumPy & Pandas<br><sub>莫烦Python</sub> | [BV1Ex411L7oT](https://www.bilibili.com/video/BV1Ex411L7oT/) | 全章 | API 速查：广播、索引、合并、透视各一集，10 分钟能补齐一个操作；看完回 `ex02`（离线手工构造 Response）核对 |
| 3 | Pandas 数据分析从入门到实战<br><sub>蚂蚁学Python</sub> | [BV1UJ411A7Fs](https://www.bilibili.com/video/BV1UJ411A7Fs/) | 全章 | 偏实战：时间序列、缺失值、多表关联这几节比教科书细；看完回 `ex03`（编码与乱码三步定位法）核对 |
| 4 | 黑马程序员 · MySQL 入门到精通<br><sub>黑马程序员</sub> | [BV1Kr4y1i7ru](https://www.bilibili.com/video/BV1Kr4y1i7ru/) | 全章 | 数据分析绕不开 SQL：查询、聚合、窗口函数与索引，看前 1/3 足够支撑取数；看完回 `ex04`（URL 规范化与去重）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《利用 Python 进行数据分析（第 3 版）》McKinney |
| 2 | 《Python 数据科学手册》VanderPlas |
| 3 | 《统计学（第 8 版）》贾俊平 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
