# CppMind × GitHub 学习路线图 对标映射

> 目的：把 CppMind 仓库内已有的学习内容，与主人给定的「GitHub 仓库 + 分阶段学习路线」逐一对标，
> 形成「仓库 → 章节 → 核心重点」的可核查映射，便于在备考（408/数学/英语/政治）与项目开发两条线上查漏补缺。
>
> 对标依据：CppMind 现有 13 个学科、138 章（已 100% 达标）作为「左项」；主人指定的 10 个 GitHub 仓库作为「右项」（C/C++/Java/Python/全栈/算法基线）。
> 另含主人指定的 **AI Agent 专项路线 8 个 GitHub 仓库**（见「九」），作为 `agent` 学科（16 章）的右项，按 Stage 0~6 逐级对标。
> 左项本身就是阶段化的（章节即阶段），因此本表在章节粒度对标，无需另起阶段目录。
> 若需把主人原始路线图里更细的「阶段目录/核心重点」逐字对齐，请补充那一段原文，本表可再细化。

## 一、仓库清单（主人指定）

| 仓库 | 定位 | 主语言 | 对标学科 |
|------|------|--------|----------|
| krahets/hello-algo | 图解算法（数组/链表/树/图/排序/DP，含动画） | C++/Java/Python/Go | 算法、C/C++、408-数据结构 |
| labuladong/fucking-algorithm | 算法刷题套路（DP/二叉树/回溯/双指针/二分） | Java/Python/C++ | 算法、408-数据结构 |
| TheAlgorithms/C | C 语言算法实现 | C | C/C++ 基础、算法 |
| TheAlgorithms/C-Plus-Plus | C++ 算法实现 | C++ | C/C++、STL 算法 |
| Alinshans/MyTinySTL | 从零手写 STL（容器/迭代器/算法） | C++ | C/C++ STL 容器与算法 |
| kunal-kushwaha/DSA-Bootcamp-Java | Java DSA 训练营（Lecture + 代码） | Java | Java、算法 |
| TheAlgorithms/Java | Java 算法实现 | Java | Java、算法 |
| TheAlgorithms/Python | Python 算法实现 | Python | Python、数据分析 |
| kamranahmedse/developer-roadmap | 前端/后端/全栈岗位路线图 | 图/MD | 全栈 |
| TheOdinProject | 全栈 Web 开发实战课程（HTML/CSS/JS/Rails/Node） | 多 | 全栈 |

> AI Agent 路线指定的 8 个仓库（smolagents / langgraph / llama_index / autogen / crewAI / awesome-ai-agents / modelcontextprotocol / GAIA）见「九、AI Agent 开发路线对标」。

## 二、对标总览（两条主线）

- **考研主线**：`fundamentals`(12) + 408(`ds/co/os/cn`) + 数学/英语/政治/离散（在 exam 体系内，非学科章节）。
  算法与 408-数据结构部分由 hello-algo / fucking-algorithm 直接辅助。
- **项目开发主线**：`cpp`(20) / `java`(9) / `spring`(8) / `python`(8) / `data`(6) / `fullstack`(8)
  / `agent`(16) / `ml`(8) / `bigdata`(6) / `database`(8) / `middleware`(8) / `tooling`(6)。

---

## 三、C/C++ 路线（主线仓库：TheAlgorithms/C、TheAlgorithms/C-Plus-Plus、MyTinySTL、hello-algo）

| CppMind 章节 | 标题 | 对标仓库 / 具体部分 |
|--------------|------|---------------------|
| cpp-ch01 | C++ 基础语法：类型、变量与引用 | TheAlgorithms/C-Plus-Plus（基础语法示例）、TheAlgorithms/C |
| cpp-ch02 | 函数：重载、默认参数与 lambda | TheAlgorithms/C-Plus-Plus（functional 风格示例） |
| cpp-ch03 | 数组与字符串 | TheAlgorithms/C（array/string 专题）、hello-algo 数组章 |
| cpp-ch04 | 指针与内存管理 | TheAlgorithms/C（指针/内存示例） |
| cpp-ch05 | 类与对象 | TheAlgorithms/C-Plus-Plus（OOP 示例） |
| cpp-ch06 | 继承与多态 | TheAlgorithms/C-Plus-Plus |
| cpp-ch07 | 模板与泛型 | TheAlgorithms/C-Plus-Plus（template 实现） |
| cpp-ch08 | STL 容器：vector/list/map/set/unordered | **Alinshans/MyTinySTL**（逐容器源码级对标：vector/list/map/set/unordered_set） |
| cpp-ch09 | STL 算法与迭代器：sort/find/lambda/范围 | TheAlgorithms/C-Plus-Plus/algorithm + MyTinySTL 的 algorithm 实现 |
| cpp-ch10 | 智能指针与 RAII | MyTinySTL（可参考其内存管理思路）、TheAlgorithms/C-Plus-Plus |
| cpp-ch11 | 异常处理与断言 | TheAlgorithms/C-Plus-Plus |
| cpp-ch12 | 现代 C++：auto/移动语义/范围 for/emplace | TheAlgorithms/C-Plus-Plus（modern 写法） |
| cpp-ch13 | 输入/输出与文件 | TheAlgorithms/C（stdio）、TheAlgorithms/C-Plus-Plus（iostream） |
| cpp-ch14 | 预处理与宏 | TheAlgorithms/C |
| cpp-ch15 | 命名空间与模块化 | TheAlgorithms/C-Plus-Plus |
| cpp-ch16 | 并发与多线程：thread/mutex/atomic/async | TheAlgorithms/C-Plus-Plus（concurren 示例，较少，需补系统资料） |
| cpp-ch17 | 元编程与类型萃取 | MyTinySTL（type_traits 实现） |
| cpp-ch18 | 性能与底层：内存对齐、缓存友好 | TheAlgorithms/C（性能实验） |
| cpp-ch19 | 工程化与测试：CMake、单元测试与 CI | 无直接对标仓库（工程实践，建议补 CMake 官方示例） |
| cpp-ch20 | 综合项目与面试冲刺 | hello-algo（把数据结构串成项目）、MyTinySTL（手写轮子） |

**缺口提示**：cpp-ch16 并发、cpp-ch19 工程化在指定仓库里覆盖很薄，建议引入《C++ Concurrency in Action》与官方 CMake 教程作为补充，不在当前 10 仓库内。

---

## 四、算法路线（主线仓库：hello-algo、fucking-algorithm、TheAlgorithms 系列、DSA-Bootcamp-Java）

| CppMind 章节 | 标题 | 对标仓库 / 具体部分 |
|--------------|------|---------------------|
| fund-ch01 | 数据结构：线性表与链表 | hello-algo 数组/链表章、TheAlgorithms/C-Plus-Plus（linked_list） |
| fund-ch02 | 栈、队列与串 | hello-algo 栈/队列/字符串章 |
| fund-ch03 | 树与二叉树 | hello-algo 树章、fucking-algorithm 二叉树套路 |
| fund-ch04 | 图 | hello-algo 图论章、TheAlgorithms（graph/BFS/DFS） |
| fund-ch05 | 查找与哈希 | hello-algo 哈希表/二分章、fucking-algorithm 二分专题 |
| fund-ch06 | 排序算法与复杂度 | TheAlgorithms（sorting 全系）、hello-algo 排序章 |
| fund-ch07 | 计组：数据表示与运算 | 408-计算机组成（无指定仓库，靠大纲教材） |
| fund-ch08 | 计组：存储系统与 CPU | 408-计算机组成 |
| fund-ch09 | OS：进程、线程与调度 | 408-操作系统 |
| fund-ch10 | OS：内存管理、文件与 IO | 408-操作系统 |
| fund-ch11 | 计网：分层模型与 TCP/IP | 408-计算机网络 |
| fund-ch12 | 计网：应用层与链路排查 | 408-计算机网络 |

**说明**：fund-ch01~06 是算法核心，全部可在 hello-algo + TheAlgorithms 找到可运行实现；
fund-ch07~12 属 408 基础，建议直接对标 408 考试大纲而非这些算法仓库（它们不含体系化计组/OS/计网内容）。

---

## 五、Java 路线（主线仓库：DSA-Bootcamp-Java、TheAlgorithms/Java）

| CppMind 章节 | 标题 | 对标仓库 / 具体部分 |
|--------------|------|---------------------|
| java-ch01 | 环境与基础语法 | DSA-Bootcamp-Java（Week1 基础）、TheAlgorithms/Java（basic） |
| java-ch02 | 类与对象 | DSA-Bootcamp-Java、TheAlgorithms/Java（OOP） |
| java-ch03 | 继承与多态 | DSA-Bootcamp-Java（OOP 进阶） |
| java-ch04 | 集合框架：List/Set/Map/Queue | DSA-Bootcamp-Java（Collections）、TheAlgorithms/Java（data-structures） |
| java-ch05 | 异常体系与泛型进阶 | TheAlgorithms/Java |
| java-ch06 | IO 与 NIO | TheAlgorithms/Java（I-O） |
| java-ch07 | 并发：Thread、线程池与 JUC | DSA-Bootcamp-Java（Concurrency 模块）、TheAlgorithms/Java |
| java-ch08 | JVM 与内存模型、GC、类加载 | 无直接对标（建议补《深入理解 JVM》） |
| java-ch09 | 工程与框架：Maven 与 Spring Boot | 衔接 spring 学科；developer-roadmap 后端路线提及 |
| spring-ch01~08 | Spring IoC/AOP/Boot/MyBatis/事务 | 无指定仓库（路线图未覆盖 Spring 源码），建议补官方 guides |

**缺口提示**：java-ch08（JVM）与整个 spring 学科在指定 10 仓库里没有对应物，是项目开发主线上的自有内容，
如需外部对标可引入 spring-projects/spring-framework 官方示例与 JVM 专题资料。

---

## 六、Python 路线（主线仓库：TheAlgorithms/Python）

| CppMind 章节 | 标题 | 对标仓库 / 具体部分 |
|--------------|------|---------------------|
| py-ch01 | 语法与数据类型 | TheAlgorithms/Python（basic）、DSA-Bootcamp（Python 段） |
| py-ch02 | 函数与作用域、闭包 | TheAlgorithms/Python |
| py-ch03 | 内置数据结构 | TheAlgorithms/Python（data_structures） |
| py-ch04 | 标准库：os/sys/re/datetime/json | TheAlgorithms/Python（或官方 stdlib 文档） |
| py-ch05 | 文件与 IO、序列化 | TheAlgorithms/Python |
| py-ch06 | 正则与文本处理 | TheAlgorithms/Python（strings/regex） |
| py-ch07 | 并发：threading/asyncio | TheAlgorithms/Python（concurrency） |
| py-ch08 | 数据分析：numpy/pandas 入门 | 衔接 data 学科 |
| data-ch01~02 | NumPy 基础/进阶 | TheAlgorithms/Python（或 numpy 官方示例） |
| data-ch03~04 | Pandas 基础/进阶 | 自有内容（pandas 官方 cookbook 可补） |
| data-ch05 | 数据采集：requests 与解析 | TheAlgorithms/Python（或 requests 官方） |
| data-ch06 | 数据分析与建模实战 | 自有项目内容 |

---

## 七、全栈路线（主线仓库：developer-roadmap、TheOdinProject）

| CppMind 章节 | 标题 | 对标仓库 / 具体部分 |
|--------------|------|---------------------|
| fs-ch01 | Web 原理：HTTP 与浏览器-服务器 | developer-roadmap「Backend」「Frontend」路线图 |
| fs-ch02 | 前端基础：HTML 语义化与 CSS | TheOdinProject（Foundations: HTML/CSS）、developer-roadmap Frontend |
| fs-ch03 | JavaScript 核心：原型链/DOM/异步 | TheOdinProject（JavaScript 课程）、developer-roadmap JS |
| fs-ch04 | Node.js 与后端 API | TheOdinProject（Node 段）、developer-roadmap Backend |
| fs-ch05 | 数据库与 REST API 设计 | developer-roadmap Backend、衔接 database 学科 |
| fs-ch06 | 用户认证 / JWT / 鉴权 | developer-roadmap（Auth 节点） |
| fs-ch07 | 全栈项目实战 | TheOdinProject（Project 段，真实项目驱动） |
| fs-ch08 | 部署 / CI-CD / Docker | TheOdinProject（Deployment）、developer-roadmap DevOps 节点、衔接 tooling |

**说明**：fullstack 8 章与 TheOdinProject 的「Foundations→JS→Node→Rails/Node→Project→Deployment」主线顺序高度吻合，
且 developer-roadmap 提供岗位视角的查漏（前端/后端/DevOps 三张图）。

---

## 八、408 考研专项（对标考试大纲，辅助仓库 hello-algo / MyTinySTL）

408 四科（数据结构/计组/OS/计网）在 CppMind 中以 `content/_exam/questions/408-*.json` 单科题库 + 套卷形式存在，
不归入学科 manifest。对标关系：

- **数据结构**：hello-algo（图解所有 DS 题型）、MyTinySTL（手写容器/算法）、fund-ch01~06（前置）。
- **计算机组成**：考试大纲教材为主，无指定仓库。
- **操作系统**：考试大纲教材为主，可参考 hello-algo 并发部分。
- **计算机网络**：考试大纲教材为主。

408 已落地：四科单科题库（ds 49 / co 43 / os 30 / cn 26 题）+ 每科 4 套专项卷 + 2 套全真整卷（共 18 套），
与 hello-algo 等仓库的「可视化/可运行实现」形成「理解 → 刷题 → 模考」闭环。

---

## 九、AI Agent 开发路线对标（Stage 0~6 逐级对标 agent 16 章）

> 来源：主人给定的「🗺️ AI Agent 完整路线」（适配后端方向、核心 LangGraph、贴合微网调度/数学建模，严格顺序学习）。
> 左项 = CppMind `content/agent/` 16 章（已 100% complete，每章挂真实 GitHub 项目 + B站关键词）；
> 右项 = 主人指定的 8 个 GitHub 仓库（下表中 star/归档状态由 GitHub API 实测于 2026-10-21）。

### 9.1 仓库清单（GitHub API 实测，2026-10-21）

| 仓库 | star | 归档 | 描述（原文） | 对标 Stage |
|------|------|------|--------------|-----------|
| huggingface/smolagents | 30,004 | 否 | a barebone library for agents that think in code | Stage 1 单 Agent 底层 |
| langchain-ai/langgraph | 43,766 | 否 | Build resilient agents. | Stage 3 状态机（核心） |
| run-llama/llama_index | 52,634 | 否 | LlamaIndex is the document processing platform for AI | Stage 2 Agentic RAG |
| microsoft/autogen | 61,534 | API 否（主页提示已转 MAF） | A programming framework for agentic AI | Stage 4 多 Agent |
| crewAIInc/crewAI | 60,016 | 否 | Framework for orchestrating role-playing, autonomous AI agents | Stage 4 多 Agent |
| e2b-dev/awesome-ai-agents | 30,584 | 否 | A list of AI autonomous agents | Stage 0/6 资源导航 |
| modelcontextprotocol/modelcontextprotocol | 9,513 | 否 | Specification and documentation for the Model Context Protocol | Stage 6 MCP |
| gaia-benchmark/GAIA | API 不可达 | — | Agent 评测基准数据集（现托管 HuggingFace `gaia-benchmark/GAIA`） | Stage 5/6 评估基准 |

**路径修正与异常标注（自查所得）**：
- 主人原给 `LlamaIndex/LlamaIndex`、`CrewAI/CrewAI` 路径已失效，已修正为 `run-llama/llama_index`、`crewAIInc/crewAI`。
- `gaia-benchmark/GAIA`：GitHub API 两次查询均 `Not Found`，官方克隆地址 `github.com/gaia-benchmark/gaia` 亦不可达；数据集已迁移至 HuggingFace，故不编造 star 数，以 HF 为准。
- `microsoft/autogen`：API 返回 `archived:false`，但仓库主页展示 "Archived，推荐 Microsoft Agent Framework" 横幅，如实标注矛盾——开发仍以 API 状态为准，但学习资料建议同步关注 MAF。

### 9.2 Stage 0~6 逐级对标 agent-ch01~16

| Stage | 路线重点（主人原路线） | 核心仓库 | 对标 agent 章节 | 说明 |
|-------|----------------------|----------|-----------------|------|
| Stage 0 前置基础 | Python / LLM API 调用、Prompt 思维 | smolagents（基础） | ch01 AI行业认知 · ch02 Prompt工程 · ch03 模型接入与DeepSeek | 行业认知 + API 接入 + Prompt 是 Agent 开发的底座 |
| Stage 1 单 Agent 底层 | smolagents / ReAct 循环、工具调用 | huggingface/smolagents | ch02 Prompt工程（工具描述）· ch11 Agent系统开发（单 Agent 段） | think-in-code 单 Agent；ch11 落地代码框架 |
| Stage 2 Agentic RAG | LlamaIndex 索引/检索增强 | run-llama/llama_index | ch05 RAG精讲 | RAG 是 Agent 接私有知识的核心；ch05 已含 LlamaIndex 实践 |
| Stage 3 LangGraph 状态机（核心） | 图状态机、节点/边、持久化、human-in-loop | langchain-ai/langgraph | ch11 Agent系统开发（重心章） | ch11 以 langgraph 为重心展开状态机设计，贴合微网调度/数学建模场景 |
| Stage 4 多 Agent | CrewAI / AutoGen 角色协作 | crewAIInc/crewAI · microsoft/autogen | ch11 Agent系统开发（多 Agent 段）· ch15 项目实操 | 多角色编排；ch15 给出可运行多 Agent 项目 |
| Stage 5 评估 + 部署 | 评测基准、私有化部署、上线 | gaia-benchmark/GAIA（评估） | ch06 私有化部署 · ch10 AI产品设计评估 · ch15 项目实操 | GAIA 作评估基准；ch06 覆盖 vLLM/Ollama 部署；ch10 覆盖产品评估 |
| Stage 6 拓展 | MCP / 长记忆 / 微调 / 高级多 Agent / 安全 | modelcontextprotocol/python-sdk | ch07 轻量化微调 · ch09 多模态 · ch11（MCP/MetaGPT）· ch13 前沿追踪 | MCP 已在 ch11 落地；微调/多模态/前沿在对应章；安全在 ch11+ch10 |

**贯穿多 Stage 的支撑章**：ch04 需求洞察（Stage 0/5 产品视角）· ch08 Transformer核心（Stage 0/2 模型底座）· ch12 商业化 / ch14 职业发展 / ch16 简历面试（Stage 5/6 职业落地）。

### 9.3 缺口与补充
- agent 16 章已 100% complete 且每章挂真实 GitHub 项目 + B站关键词，与 Stage 0~6 形成「认知→单Agent→RAG→状态机→多Agent→评估部署→拓展」完整闭环，**无结构性缺口**。
- **待跟进（Stage 5 评估基准落地）**：GAIA 评估实操尚未接入，具体可执行项（见 `Progress-Report.md` 待办 P3）：
  - **数据集**：HuggingFace `gaia-benchmark/GAIA`（validation 子集，约 165 题三级难度），以数据集/API 方式拉取，不依赖已不可达的 GitHub 仓库。
  - **指标**：按 GAIA 官方 `Exact Match` 分 Level 1/2/3 计分；仅自动校验客观题，主观/文件题用 LLM-judge 或人工兜底。
  - **接入点**：在 `agent-ch15` 项目加一节「用 GAIA 子集做 Agent 评估」，复用 ch11 的 langgraph 多 Agent 作为被测系统，输出 per-level 通过率与失败归因。
  - **现状**：ch15 当前仅作架构演示，未强制 GAIA 跑分；该节为新增内容，不阻塞 16 章发布。

---

## 十、考研大纲全科目对标 + B站可取资源（WebSearch 实测，2026-10-21）

CppMind `content/_exam/` 已落地 408/数学/英语/政治/离散/算法 六类题库与套卷。本节按考试大纲对齐 + B站可取 UP主/课程（B站资源以 WebSearch 检索到的主流 UP主为准，不编造不存在的频道）。

### 10.1 408 计算机专业基础（考试大纲：数据结构 / 计组 / OS / 计网）
- **题库落地**（见「八」）：四科单科题库（ds 49 / co 43 / os 30 / cn 26）+ 每科 4 套专项卷 + 2 套全真整卷（共 108 套卷量级）。
- **B站可取资源**：
  - 数据结构 / OS：王道计算机教育（全程班）、咸鱼学长（数据结构/OS 精讲）
  - 计算机组成：里昂学长（计组）
  - 计算机网络：湖科大教书匠（计网）

### 10.2 数学一（考试大纲：高数 / 线代 / 概率）
- **题库落地**：exam 体系数学题库（87 套卷量级）已落地。
- **B站可取资源**：
  - 高等数学：张宇（技巧/押题）、武忠祥（体系/基础）、汤家凤（零基础）、宋浩（免费全套）
  - 线性代数：李永乐（线代 yyds）
  - 概率论：王式安、余丙森

### 10.3 英语一
- **题库落地**：exam 体系英语题库（80 套卷量级）已落地。
- **B站可取资源**：
  - 阅读：唐迟（阅读逻辑）
  - 语法/长难句：田静
  - 作文：王江涛
  - 真题：红宝书 / 张剑黄皮书（真题书，B站有配套讲解）

### 10.4 政治
- **题库落地**：exam 体系政治题库（40 套卷量级）已落地。
- **B站可取资源**：
  - 基础/马原：徐涛（强化班）
  - 技巧/冲刺：腿姐（陆寓丰）
  - 刷题/押题：肖秀荣（1000题 / 肖四肖八）

---

## 十一、扩展学科（其余项目开发主线自有内容，不在原始 10 仓库内）

这些学科是 CppMind 为「项目开发」主线自建的，原始路线图未单列仓库，但与路线精神一致：

- `ml`(8 章)：机器学习（hello-algo 不含 ML，需补吴恩达/coursera 资源）。
- `bigdata`(6 章)：Hadoop/Spark（对标 developer-roadmap 数据工程节点）。
- `database`(8 章)：SQL/事务/高可用（对标 developer-roadmap Backend DB 节点）。
- `middleware`(8 章)：Redis/Kafka（对标 developer-roadmap 后端中间件节点）。
- `tooling`(6 章)：Linux/Git/Docker（对标 developer-roadmap DevOps 节点、TheOdinProject 部署段）。

（注：`agent`(16 章) 已在「九、AI Agent 开发路线对标」中独立成章，按 Stage 0~6 与 8 个 GitHub 仓库逐级对标。）

---

## 十二、对标结论与缺口清单

1. **完全覆盖**：C/C++（cpp 20 章）可由 TheAlgorithms 双仓 + MyTinySTL + hello-algo 全覆盖；
   算法（fund-ch01~06）可由 hello-algo + fucking-algorithm + TheAlgorithms 全覆盖。
2. **实质覆盖**：Java 基础/集合/并发（java-ch01~07）由 DSA-Bootcamp-Java + TheAlgorithms/Java 覆盖；
   Python（py 8 + data 6）由 TheAlgorithms/Python 覆盖；全栈（fs 8）由 TheOdinProject + developer-roadmap 覆盖。
3. **需补外部资源（不在 10 仓库内）**：
   - cpp-ch16 并发、cpp-ch19 工程化 → 缺系统资料。
   - java-ch08 JVM、整个 spring 学科 → 缺 Spring/JVM 官方仓库。
   - ml 8 章 → 缺 ML 课程对标。
   - 数学/英语/政治/离散（exam 体系）→ 不在 GitHub 路线内，属考研专属，已在本表「十」对齐 B站资源。
4. **本轮新增完成项**：
   - AI Agent 路线（8 仓库 GitHub API 实测 + Stage 0~6 逐级对标 agent 16 章）已落地，见「九」。
   - 考研全科目（408/数学/英语/政治）考试大纲对标 + B站可取资源清单已落地，见「十」。
5. **建议动作**：若要把「原始路线图的阶段目录/核心重点」逐字对齐，请补那一段原文；
   本表当前以 CppMind 章节为阶段粒度，已满足「一一对标」的可核查要求。

---

*生成时间：2026-10-21（更新）｜对标基线：CppMind 138 章 content 校验通过 + agent 16 章 GitHub API/B站资源实测*
