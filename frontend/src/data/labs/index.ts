/* 自动生成 · 请勿手改 —— python scripts/gen_interactive.py */
/**
 * 应用内交互实验的数据入口。
 * 正文按**学科**懒加载，索引常驻：实验台列表与章节卡都读这一份，不重复打包。
 */
import type { LabData } from './types';

export type * from './types';

export interface LabIndexItem {
  /** 完整键：<subject>/<chapter>，与 interactive.json 里的 chapter 对应 */
  key: string;
  subject: string;
  chapter: string;
  title: string;
  kinds: string[];
  fingerprint: string;
}

export const LAB_INDEX: LabIndexItem[] = [
  { key: "agent/agent-ch01", subject: "agent", chapter: "agent-ch01", title: "AI 行业认知与岗位地图：从「会用」到「知道为什么值钱」", kinds: ["boss", "fill", "match"], fingerprint: "80565f213b" },
  { key: "agent/agent-ch02", subject: "agent", chapter: "agent-ch02", title: "Prompt 工程与结构化输出：把自然语言当接口设计", kinds: ["boss", "fill", "match"], fingerprint: "4f4176e999" },
  { key: "agent/agent-ch03", subject: "agent", chapter: "agent-ch03", title: "模型接入与 DeepSeek 实操：第一次让程序真的说话", kinds: ["boss", "fill", "match"], fingerprint: "63589a3b0b" },
  { key: "agent/agent-ch04", subject: "agent", chapter: "agent-ch04", title: "需求洞察：用户故事与 AI 产品画布", kinds: ["boss", "fill", "match"], fingerprint: "ed1e992ee6" },
  { key: "agent/agent-ch05", subject: "agent", chapter: "agent-ch05", title: "RAG 技术精讲：检索质量决定回答上限", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "666c0ef3d2" },
  { key: "agent/agent-ch06", subject: "agent", chapter: "agent-ch06", title: "私有化部署与推理服务：把模型放进自己的机房", kinds: ["boss", "match"], fingerprint: "e1310dc8c4" },
  { key: "agent/agent-ch07", subject: "agent", chapter: "agent-ch07", title: "轻量化微调：LoRA / QLoRA 与数据工程", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "81d2e75fd3" },
  { key: "agent/agent-ch08", subject: "agent", chapter: "agent-ch08", title: "Transformer 核心机理：能白板推一遍才算懂", kinds: ["boss", "fill", "match"], fingerprint: "b9be0c19ff" },
  { key: "agent/agent-ch09", subject: "agent", chapter: "agent-ch09", title: "多模态应用开发：图像、文档与语音的工程接口", kinds: ["boss", "fill", "match"], fingerprint: "e7647c3a14" },
  { key: "agent/agent-ch10", subject: "agent", chapter: "agent-ch10", title: "AI 产品设计与评估方法论：把「感觉不错」变成分数", kinds: ["boss", "fill", "match"], fingerprint: "55c9a6218d" },
  { key: "agent/agent-ch11", subject: "agent", chapter: "agent-ch11", title: "Agent 系统开发：工具、记忆、规划与多智能体", kinds: ["boss", "fill", "match"], fingerprint: "0523c6f099" },
  { key: "agent/agent-ch12", subject: "agent", chapter: "agent-ch12", title: "商业化与行业解决方案：从 demo 到能签单", kinds: ["boss", "fill", "match"], fingerprint: "5e0978053d" },
  { key: "agent/agent-ch13", subject: "agent", chapter: "agent-ch13", title: "前沿技术追踪：建立自己的信息过滤系统", kinds: ["boss", "fill", "match"], fingerprint: "d22d4987c8" },
  { key: "agent/agent-ch14", subject: "agent", chapter: "agent-ch14", title: "职业发展框架：把能力翻译成岗位语言", kinds: ["boss", "match"], fingerprint: "9f6c3f4479" },
  { key: "agent/agent-ch15", subject: "agent", chapter: "agent-ch15", title: "项目实操：端到端交付一个可演示的 Agent 产品", kinds: ["boss", "fill", "match"], fingerprint: "37ce31553e" },
  { key: "agent/agent-ch16", subject: "agent", chapter: "agent-ch16", title: "简历、模拟面试与入职答辩：把项目讲成录用理由", kinds: ["boss", "fill", "match"], fingerprint: "7175528c17" },
  { key: "ai/ai-ch01", subject: "ai", chapter: "ai-ch01", title: "深度学习基础：张量、前向与反向传播", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "8acb5fa2c4" },
  { key: "ai/ai-ch02", subject: "ai", chapter: "ai-ch02", title: "视觉与序列建模：CNN、RNN 到注意力机制", kinds: ["boss", "match", "sandbox"], fingerprint: "6f21249a33" },
  { key: "ai/ai-ch03", subject: "ai", chapter: "ai-ch03", title: "Transformer 与大语言模型原理", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "2e1bfe6bee" },
  { key: "ai/ai-ch04", subject: "ai", chapter: "ai-ch04", title: "高效微调与对齐：LoRA、RLHF 与 DPO", kinds: ["boss", "match", "sandbox"], fingerprint: "fa43c0383c" },
  { key: "ai/ai-ch05", subject: "ai", chapter: "ai-ch05", title: "提示工程与上下文工程", kinds: ["boss", "fill", "match"], fingerprint: "3ae24217f7" },
  { key: "ai/ai-ch06", subject: "ai", chapter: "ai-ch06", title: "RAG：向量检索与知识增强", kinds: ["boss", "fill", "match"], fingerprint: "c38be31d68" },
  { key: "ai/ai-ch07", subject: "ai", chapter: "ai-ch07", title: "Agent 开发：工具调用、记忆与多智能体", kinds: ["boss", "fill", "match"], fingerprint: "6cd688b3bf" },
  { key: "ai/ai-ch08", subject: "ai", chapter: "ai-ch08", title: "LLM 应用工程：推理优化、评测、可观测性与安全", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "884e59f8dc" },
  { key: "ai/ai-ch09", subject: "ai", chapter: "ai-ch09", title: "生成模型：从自编码器到扩散", kinds: ["boss", "fill", "match"], fingerprint: "eef3aac70e" },
  { key: "ai/ai-ch10", subject: "ai", chapter: "ai-ch10", title: "训练工程与规模化：从「能跑通」到「能训起来」", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "f675ddd1ca" },
  { key: "ai/ai-ch11", subject: "ai", chapter: "ai-ch11", title: "模型服务化落地：从 `train()` 跑到线上不崩", kinds: ["boss", "fill", "match"], fingerprint: "1d1383f08e" },
  { key: "ai/ai-ch12", subject: "ai", chapter: "ai-ch12", title: "SFT 数据工程：任务 schema、合成数据过滤、去重与污染、难例挖掘、标注一致性 Kappa", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "1d6f4a1aaf" },
  { key: "ai/ai-ch13", subject: "ai", chapter: "ai-ch13", title: "推理引擎与量化部署：KV Cache 分页、continuous batching、GPTQ/AWQ/GGUF", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "34e8cd10ff" },
  { key: "ai/ai-ch14", subject: "ai", chapter: "ai-ch14", title: "多模态落地：图文对齐、OCR→VLM 流水线、多模态 RAG、成本与延迟", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "0286ace003" },
  { key: "bigdata/bd-ch01", subject: "bigdata", chapter: "bd-ch01", title: "Hadoop 生态与 HDFS 架构（bd-ch01）", kinds: ["boss", "match"], fingerprint: "2a8f24eda6" },
  { key: "bigdata/bd-ch02", subject: "bigdata", chapter: "bd-ch02", title: "MapReduce 原理与 YARN 调度（bd-ch02）", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "6005f6f4f5" },
  { key: "bigdata/bd-ch03", subject: "bigdata", chapter: "bd-ch03", title: "Hive 数据仓库与 HQL（bd-ch03）", kinds: ["boss", "fill", "match"], fingerprint: "b4e694dff2" },
  { key: "bigdata/bd-ch04", subject: "bigdata", chapter: "bd-ch04", title: "Spark 核心：RDD 与惰性求值（bd-ch04）", kinds: ["boss", "match", "sandbox"], fingerprint: "fc9fc1ed00" },
  { key: "bigdata/bd-ch05", subject: "bigdata", chapter: "bd-ch05", title: "Spark SQL、DataFrame 与 Catalyst（bd-ch05）", kinds: ["boss", "fill", "match"], fingerprint: "44249cdc0d" },
  { key: "bigdata/bd-ch06", subject: "bigdata", chapter: "bd-ch06", title: "离线数仓实战：分层建模与调度（bd-ch06）", kinds: ["boss", "fill", "match"], fingerprint: "ba0cafbc25" },
  { key: "clang/clang-u01", subject: "clang", chapter: "clang-u01", title: "指针与地址运算", kinds: ["boss", "match"], fingerprint: "17379a5043" },
  { key: "clang/clang-u02", subject: "clang", chapter: "clang-u02", title: "内存与动态分配（malloc/free）", kinds: ["boss", "fill", "match"], fingerprint: "85a3defe98" },
  { key: "clang/clang-u03", subject: "clang", chapter: "clang-u03", title: "结构体与联合体", kinds: ["boss", "match"], fingerprint: "c6079ed7cf" },
  { key: "clang/clang-u04", subject: "clang", chapter: "clang-u04", title: "文件 IO 与二进制", kinds: ["boss", "fill", "match"], fingerprint: "574363b0e8" },
  { key: "clang/clang-u05", subject: "clang", chapter: "clang-u05", title: "预处理与宏", kinds: ["boss", "match"], fingerprint: "cf44b6f54d" },
  { key: "clang/clang-u06", subject: "clang", chapter: "clang-u06", title: "Makefile 与构建", kinds: ["boss", "match"], fingerprint: "5d3ef17b93" },
  { key: "clang/clang-u07", subject: "clang", chapter: "clang-u07", title: "多文件编译与链接", kinds: ["boss", "match", "sequence"], fingerprint: "89011e0e1a" },
  { key: "cpp/cpp-ch01", subject: "cpp", chapter: "cpp-ch01", title: "C++ 基础语法", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "62ee75eb10" },
  { key: "cpp/cpp-ch02", subject: "cpp", chapter: "cpp-ch02", title: "函数：声明/定义、重载、默认参数与 lambda", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "98b8273aca" },
  { key: "cpp/cpp-ch03", subject: "cpp", chapter: "cpp-ch03", title: "数组与字符串：C 数组、std::string 与字符串视图", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "80c734e71c" },
  { key: "cpp/cpp-ch04", subject: "cpp", chapter: "cpp-ch04", title: "指针与内存管理：指针运算、new/delete 与悬垂", kinds: ["boss", "debug", "fill", "sandbox"], fingerprint: "4860fff3bf" },
  { key: "cpp/cpp-ch05", subject: "cpp", chapter: "cpp-ch05", title: "类与对象：封装、构造/析构、拷贝与运算符重载", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "8c97077ab4" },
  { key: "cpp/cpp-ch06", subject: "cpp", chapter: "cpp-ch06", title: "继承与多态：虚函数、抽象类与 RTTI", kinds: ["boss", "match", "sandbox"], fingerprint: "686029f237" },
  { key: "cpp/cpp-ch07", subject: "cpp", chapter: "cpp-ch07", title: "模板与泛型：函数模板、类模板与特化", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "c16df05a44" },
  { key: "cpp/cpp-ch08", subject: "cpp", chapter: "cpp-ch08", title: "STL 容器：vector/list/map/set/unordered", kinds: ["boss", "match", "sandbox"], fingerprint: "071095edf4" },
  { key: "cpp/cpp-ch09", subject: "cpp", chapter: "cpp-ch09", title: "STL 算法与迭代器：sort/find/lambda/范围", kinds: ["boss", "debug", "match", "sandbox"], fingerprint: "98bf4ef908" },
  { key: "cpp/cpp-ch10", subject: "cpp", chapter: "cpp-ch10", title: "智能指针与 RAII：unique_ptr / shared_ptr / weak_ptr", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "83d3e14be8" },
  { key: "cpp/cpp-ch11", subject: "cpp", chapter: "cpp-ch11", title: "异常处理与断言：try/catch、noexcept 与契约", kinds: ["boss", "debug", "match", "sandbox"], fingerprint: "088d08184f" },
  { key: "cpp/cpp-ch12", subject: "cpp", chapter: "cpp-ch12", title: "现代 C++ 特性：auto / 移动语义 / 范围 for / emplace", kinds: ["boss", "debug", "match", "sandbox"], fingerprint: "6462146a0b" },
  { key: "cpp/cpp-ch13", subject: "cpp", chapter: "cpp-ch13", title: "输入/输出与文件：iostream、fstream 与格式化", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "eceb025a2c" },
  { key: "cpp/cpp-ch14", subject: "cpp", chapter: "cpp-ch14", title: "预处理与宏：include/define/条件编译/头文件守卫", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "1ab47e7960" },
  { key: "cpp/cpp-ch15", subject: "cpp", chapter: "cpp-ch15", title: "命名空间与模块化：namespace / inline namespace / C++20 模块", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "b2427a93b9" },
  { key: "cpp/cpp-ch16", subject: "cpp", chapter: "cpp-ch16", title: "并发与多线程：thread / mutex / atomic / async", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "bbc4096ecb" },
  { key: "cpp/cpp-ch17", subject: "cpp", chapter: "cpp-ch17", title: "元编程与类型萃取：type_traits / constexpr / SFINAE / concept", kinds: ["boss", "debug", "fill", "match", "sandbox"], fingerprint: "a967d1de21" },
  { key: "cpp/cpp-ch18", subject: "cpp", chapter: "cpp-ch18", title: "性能与底层：内存对齐、缓存友好与内联", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "7a38bfea36" },
  { key: "cpp/cpp-ch19", subject: "cpp", chapter: "cpp-ch19", title: "工程化与测试：CMake、单元测试与 CI", kinds: ["boss", "debug", "match", "sandbox"], fingerprint: "6e2a420696" },
  { key: "cpp/cpp-ch20", subject: "cpp", chapter: "cpp-ch20", title: "综合项目与面试冲刺：系统设计、代码规范与复盘", kinds: ["boss", "fill", "sandbox"], fingerprint: "d084e73ae1" },
  { key: "data/data-ch01", subject: "data", chapter: "data-ch01", title: "NumPy 基础：ndarray 与向量化", kinds: ["boss", "match", "sandbox"], fingerprint: "84c1bd5ff8" },
  { key: "data/data-ch02", subject: "data", chapter: "data-ch02", title: "NumPy 进阶：广播、随机与性能", kinds: ["boss", "match", "sandbox"], fingerprint: "bbf8441a27" },
  { key: "data/data-ch03", subject: "data", chapter: "data-ch03", title: "Pandas 基础：Series 与 DataFrame", kinds: ["boss", "fill", "match"], fingerprint: "df3ac2d2da" },
  { key: "data/data-ch04", subject: "data", chapter: "data-ch04", title: "Pandas 进阶：分组聚合、合并与时间序列", kinds: ["boss", "match"], fingerprint: "e426f2163c" },
  { key: "data/data-ch05", subject: "data", chapter: "data-ch05", title: "数据采集：requests 与解析（含合规边界）", kinds: ["boss", "fill"], fingerprint: "513cf3568b" },
  { key: "data/data-ch06", subject: "data", chapter: "data-ch06", title: "数据分析与数学建模实战", kinds: ["boss", "fill"], fingerprint: "0195d26d0f" },
  { key: "database/db-ch01", subject: "database", chapter: "db-ch01", title: "关系模型与 SQL 基础（DDL/DML/SELECT/JOIN/聚合/分组）", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "1438f1c41e" },
  { key: "database/db-ch02", subject: "database", chapter: "db-ch02", title: "表连接与子查询：JOIN、子查询、集合操作", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "596fad2642" },
  { key: "database/db-ch03", subject: "database", chapter: "db-ch03", title: "索引与事务：B+树索引、ACID、隔离级别", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "54f22d289f" },
  { key: "database/db-ch04", subject: "database", chapter: "db-ch04", title: "查询优化与执行计划（EXPLAIN）", kinds: ["boss", "match", "sandbox"], fingerprint: "efd6b46733" },
  { key: "database/db-ch05", subject: "database", chapter: "db-ch05", title: "存储过程 / 触发器 / 自定义函数", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "592838a631" },
  { key: "database/db-ch06", subject: "database", chapter: "db-ch06", title: "范式与数据库建模", kinds: ["boss", "match", "sandbox"], fingerprint: "72f9532862" },
  { key: "database/db-ch07", subject: "database", chapter: "db-ch07", title: "备份恢复与权限安全", kinds: ["boss", "fill", "sandbox", "sequence"], fingerprint: "1b84f65a78" },
  { key: "database/db-ch08", subject: "database", chapter: "db-ch08", title: "高可用 / 主从复制 / 分库分表", kinds: ["boss", "match", "sandbox"], fingerprint: "191809f3b7" },
  { key: "discrete-math/dm-ch01", subject: "discrete-math", chapter: "dm-ch01", title: "命题逻辑与谓词逻辑（知识表示与自动推理）", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "0523ec35a2" },
  { key: "discrete-math/dm-ch02", subject: "discrete-math", chapter: "dm-ch02", title: "集合、关系与函数（离散世界的\"名词\"与\"动词\"）", kinds: ["boss", "sandbox"], fingerprint: "f8f0489962" },
  { key: "discrete-math/dm-ch03", subject: "discrete-math", chapter: "dm-ch03", title: "图论（离散世界的\"关系网络\"）", kinds: ["boss", "sandbox"], fingerprint: "f8eba2c384" },
  { key: "fullstack/fs-ch01", subject: "fullstack", chapter: "fs-ch01", title: "Web 工作原理：HTTP 与浏览器-服务器交互", kinds: ["boss", "fill", "match"], fingerprint: "2329247b1c" },
  { key: "fullstack/fs-ch02", subject: "fullstack", chapter: "fs-ch02", title: "前端基础：HTML 语义化与 CSS 盒模型/布局", kinds: ["boss", "fill", "match", "sequence"], fingerprint: "d06d64439b" },
  { key: "fullstack/fs-ch03", subject: "fullstack", chapter: "fs-ch03", title: "JavaScript 核心：类型、原型链、DOM 与事件、异步(Promise/async)", kinds: ["boss", "fill", "match"], fingerprint: "d08c31594d" },
  { key: "fullstack/fs-ch04", subject: "fullstack", chapter: "fs-ch04", title: "Node.js 与后端 API", kinds: ["boss", "fill", "match"], fingerprint: "3722f0502e" },
  { key: "fullstack/fs-ch05", subject: "fullstack", chapter: "fs-ch05", title: "数据库与 REST API 设计", kinds: ["boss", "match"], fingerprint: "75852c7512" },
  { key: "fullstack/fs-ch06", subject: "fullstack", chapter: "fs-ch06", title: "用户认证 / JWT / 鉴权", kinds: ["boss", "fill", "match"], fingerprint: "0951560d3a" },
  { key: "fullstack/fs-ch07", subject: "fullstack", chapter: "fs-ch07", title: "全栈项目实战（GitHub 资源驱动）", kinds: ["boss", "match"], fingerprint: "98dbf3c5de" },
  { key: "fullstack/fs-ch08", subject: "fullstack", chapter: "fs-ch08", title: "部署 / CI-CD / Docker", kinds: ["boss", "match"], fingerprint: "4537d066a8" },
  { key: "fullstack/fs-ch09", subject: "fullstack", chapter: "fs-ch09", title: "TypeScript：结构化类型、泛型与类型收窄", kinds: ["boss", "fill", "match"], fingerprint: "508eb340b4" },
  { key: "fullstack/fs-ch10", subject: "fullstack", chapter: "fs-ch10", title: "Vue 3 + TypeScript + Pinia：响应式原理与 ref/reactive 边界", kinds: ["boss", "fill", "match"], fingerprint: "4dc4bc63f5" },
  { key: "fullstack/fs-ch11", subject: "fullstack", chapter: "fs-ch11", title: "Spring Boot 3 工程骨架：分层边界、异常与校验收口", kinds: ["boss", "fill", "match"], fingerprint: "99cf6be6ff" },
  { key: "fullstack/fs-ch12", subject: "fullstack", chapter: "fs-ch12", title: "服务拆分与网关：拆分判断、网关职责、配置中心", kinds: ["boss", "match"], fingerprint: "32c0517817" },
  { key: "fullstack/fs-ch13", subject: "fullstack", chapter: "fs-ch13", title: "前端测试与质量门禁：测试金字塔、E2E、契约测试", kinds: ["boss", "match"], fingerprint: "3fa7fc71cb" },
  { key: "fullstack/fs-ch14", subject: "fullstack", chapter: "fs-ch14", title: "Agent × 全栈工程接缝：流式、长任务、幂等与成本", kinds: ["boss", "fill", "match"], fingerprint: "35a1ae8632" },
  { key: "fullstack/fs-ch15", subject: "fullstack", chapter: "fs-ch15", title: "Go + Gin 后端：并发模型、接口契约与 Java 路线对照", kinds: ["boss", "match"], fingerprint: "5e1365ac81" },
  { key: "fundamentals/fund-ch01", subject: "fundamentals", chapter: "fund-ch01", title: "数据结构 · 线性表与链表", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "ef937af3c6" },
  { key: "fundamentals/fund-ch02", subject: "fundamentals", chapter: "fund-ch02", title: "栈、队列与串", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "916197c4a5" },
  { key: "fundamentals/fund-ch03", subject: "fundamentals", chapter: "fund-ch03", title: "树与二叉树", kinds: ["boss", "match", "sandbox"], fingerprint: "4de01a472d" },
  { key: "fundamentals/fund-ch04", subject: "fundamentals", chapter: "fund-ch04", title: "fund-ch04", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "c02a4c9797" },
  { key: "fundamentals/fund-ch05", subject: "fundamentals", chapter: "fund-ch05", title: "查找与哈希", kinds: ["boss", "match", "sandbox"], fingerprint: "3b42dfaebc" },
  { key: "fundamentals/fund-ch06", subject: "fundamentals", chapter: "fund-ch06", title: "排序算法与复杂度分析", kinds: ["boss", "match", "sandbox"], fingerprint: "1e26345a14" },
  { key: "fundamentals/fund-ch07", subject: "fundamentals", chapter: "fund-ch07", title: "计算机组成原理：数据表示与运算", kinds: ["boss", "match", "sandbox"], fingerprint: "b3c27b0d4e" },
  { key: "fundamentals/fund-ch08", subject: "fundamentals", chapter: "fund-ch08", title: "计组：存储系统与 CPU", kinds: ["boss", "match", "sandbox"], fingerprint: "b645a136f8" },
  { key: "fundamentals/fund-ch09", subject: "fundamentals", chapter: "fund-ch09", title: "操作系统：进程、线程与调度", kinds: ["boss", "match", "sandbox"], fingerprint: "81bb6f982e" },
  { key: "fundamentals/fund-ch10", subject: "fundamentals", chapter: "fund-ch10", title: "操作系统：内存管理、文件与 IO", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "1c34c1bdba" },
  { key: "fundamentals/fund-ch11", subject: "fundamentals", chapter: "fund-ch11", title: "计算机网络：分层模型与 TCP/IP", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "a022b96d21" },
  { key: "fundamentals/fund-ch12", subject: "fundamentals", chapter: "fund-ch12", title: "计算机网络：应用层与链路排查", kinds: ["boss", "debug", "match"], fingerprint: "0745d6ad32" },
  { key: "fundamentals/fund-ch13", subject: "fundamentals", chapter: "fund-ch13", title: "计算机系统概述", kinds: ["boss", "match", "sandbox"], fingerprint: "12b059588c" },
  { key: "fundamentals/fund-ch14", subject: "fundamentals", chapter: "fund-ch14", title: "指令系统", kinds: ["boss", "match", "sandbox"], fingerprint: "6db16159e0" },
  { key: "fundamentals/fund-ch15", subject: "fundamentals", chapter: "fund-ch15", title: "中央处理器（CPU）", kinds: ["boss", "match", "sandbox"], fingerprint: "45db84f476" },
  { key: "fundamentals/fund-ch16", subject: "fundamentals", chapter: "fund-ch16", title: "总线", kinds: ["boss", "match", "sandbox"], fingerprint: "4764b2fab6" },
  { key: "fundamentals/fund-ch17", subject: "fundamentals", chapter: "fund-ch17", title: "I/O 系统", kinds: ["boss", "fill", "sandbox"], fingerprint: "c25bd75382" },
  { key: "fundamentals/fund-ch18", subject: "fundamentals", chapter: "fund-ch18", title: "并查集与字符串高级", kinds: ["boss", "match", "sandbox"], fingerprint: "5422c7caa3" },
  { key: "fundamentals/fund-ch19", subject: "fundamentals", chapter: "fund-ch19", title: "操作系统概述与运行机制", kinds: ["boss", "fill", "sandbox"], fingerprint: "cdd915c4d4" },
  { key: "fundamentals/fund-ch20", subject: "fundamentals", chapter: "fund-ch20", title: "文件管理", kinds: ["boss", "match", "sandbox"], fingerprint: "b847fdef0e" },
  { key: "fundamentals/fund-ch21", subject: "fundamentals", chapter: "fund-ch21", title: "I/O 管理与磁盘", kinds: ["boss", "fill", "sandbox"], fingerprint: "df65bf7119" },
  { key: "fundamentals/fund-ch22", subject: "fundamentals", chapter: "fund-ch22", title: "物理层", kinds: ["boss", "match", "sandbox"], fingerprint: "337379bbbc" },
  { key: "fundamentals/fund-ch23", subject: "fundamentals", chapter: "fund-ch23", title: "数据链路层", kinds: ["boss", "match", "sandbox"], fingerprint: "b21566f8f0" },
  { key: "java/java-ch01", subject: "java", chapter: "java-ch01", title: "环境与基础语法", kinds: ["boss", "fill"], fingerprint: "e174db3e6a" },
  { key: "java/java-ch02", subject: "java", chapter: "java-ch02", title: "类与对象：封装、构造器、this", kinds: ["boss", "match", "sequence"], fingerprint: "1c7aa377a5" },
  { key: "java/java-ch03", subject: "java", chapter: "java-ch03", title: "继承与多态：extends、方法重写、抽象类与接口", kinds: ["boss", "fill", "match"], fingerprint: "f063875e1d" },
  { key: "java/java-ch04", subject: "java", chapter: "java-ch04", title: "集合框架：List、Set、Map、Queue 与泛型集合", kinds: ["boss", "fill", "match"], fingerprint: "aee1bc9aed" },
  { key: "java/java-ch05", subject: "java", chapter: "java-ch05", title: "异常体系与泛型进阶", kinds: ["boss", "match"], fingerprint: "34fca93362" },
  { key: "java/java-ch06", subject: "java", chapter: "java-ch06", title: "IO 与 NIO", kinds: ["boss", "fill", "match"], fingerprint: "f64c617a8d" },
  { key: "java/java-ch07", subject: "java", chapter: "java-ch07", title: "并发：Thread、线程池与 JUC 并发容器", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "6392ef0789" },
  { key: "java/java-ch08", subject: "java", chapter: "java-ch08", title: "JVM 与内存模型、GC、类加载", kinds: ["boss", "fill", "sandbox", "sequence"], fingerprint: "45dfbf3e88" },
  { key: "java/java-ch09", subject: "java", chapter: "java-ch09", title: "工程与框架：Maven 与 Spring Boot 入门", kinds: ["boss", "match"], fingerprint: "f8e72843bc" },
  { key: "middleware/mw-ch01", subject: "middleware", chapter: "mw-ch01", title: "Redis 数据结构与底层编码（mw-ch01）", kinds: ["boss", "fill", "match"], fingerprint: "df3b743ccc" },
  { key: "middleware/mw-ch02", subject: "middleware", chapter: "mw-ch02", title: "Redis 持久化与内存管理（mw-ch02）", kinds: ["boss", "match"], fingerprint: "ca6746ee07" },
  { key: "middleware/mw-ch03", subject: "middleware", chapter: "mw-ch03", title: "Redis 高可用：主从、哨兵与 Cluster（mw-ch03）", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "29e60be822" },
  { key: "middleware/mw-ch04", subject: "middleware", chapter: "mw-ch04", title: "缓存设计与三大经典问题（mw-ch04）", kinds: ["boss", "fill", "match"], fingerprint: "02ef55dee8" },
  { key: "middleware/mw-ch05", subject: "middleware", chapter: "mw-ch05", title: "Kafka 架构：Topic、Partition 与 Replica（mw-ch05）", kinds: ["boss", "match", "sandbox"], fingerprint: "57df7cc76b" },
  { key: "middleware/mw-ch06", subject: "middleware", chapter: "mw-ch06", title: "Kafka 生产者与消费者机制（mw-ch06）", kinds: ["boss", "fill", "match"], fingerprint: "d57efc4a24" },
  { key: "middleware/mw-ch07", subject: "middleware", chapter: "mw-ch07", title: "消息可靠性：不丢、不重、有序（mw-ch07）", kinds: ["boss", "fill"], fingerprint: "f3791bca46" },
  { key: "middleware/mw-ch08", subject: "middleware", chapter: "mw-ch08", title: "消息队列选型与工程实践（mw-ch08）", kinds: ["boss", "fill", "match"], fingerprint: "1709fa8d08" },
  { key: "ml/ml-ch01", subject: "ml", chapter: "ml-ch01", title: "学习范式与数学基础：从「拟合」到「泛化」", kinds: ["boss", "match", "sandbox", "sequence"], fingerprint: "3813b6b187" },
  { key: "ml/ml-ch02", subject: "ml", chapter: "ml-ch02", title: "线性模型：最小二乘、正则化与逻辑回归", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "8d51d6aaf5" },
  { key: "ml/ml-ch03", subject: "ml", chapter: "ml-ch03", title: "神经网络：推理、训练与多分类", kinds: ["boss", "match", "sandbox"], fingerprint: "5123563bed" },
  { key: "ml/ml-ch04", subject: "ml", chapter: "ml-ch04", title: "应用机器学习：评估、偏差方差与误差分析", kinds: ["boss", "match", "sandbox"], fingerprint: "c91c1724af" },
  { key: "ml/ml-ch05", subject: "ml", chapter: "ml-ch05", title: "决策树与集成学习：从信息增益到 XGBoost", kinds: ["boss", "match", "sandbox"], fingerprint: "a2e05f0d49" },
  { key: "ml/ml-ch06", subject: "ml", chapter: "ml-ch06", title: "无监督学习与降维：聚类、谱方法与 PCA", kinds: ["boss", "match", "sandbox"], fingerprint: "2da60f0511" },
  { key: "ml/ml-ch07", subject: "ml", chapter: "ml-ch07", title: "推荐系统：协同过滤与矩阵分解", kinds: ["boss", "match"], fingerprint: "f90f4e680d" },
  { key: "ml/ml-ch08", subject: "ml", chapter: "ml-ch08", title: "强化学习：马尔可夫决策过程与 Q-learning", kinds: ["boss", "fill", "sandbox"], fingerprint: "2a08d956cf" },
  { key: "ml/ml-ch09", subject: "ml", chapter: "ml-ch09", title: "支持向量机与核方法", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "0a964191ab" },
  { key: "python/py-ch01", subject: "python", chapter: "py-ch01", title: "语法与数据类型：变量/流程控制/字符串/列表/字典/元组/集合/推导式", kinds: ["boss", "fill", "sandbox"], fingerprint: "91802b8b21" },
  { key: "python/py-ch02", subject: "python", chapter: "py-ch02", title: "函数与作用域：def、参数解包、lambda、闭包、命名空间", kinds: ["boss", "match", "sandbox"], fingerprint: "480809db64" },
  { key: "python/py-ch03", subject: "python", chapter: "py-ch03", title: "内置数据结构：list / tuple / dict / set 与推导式、深浅拷贝", kinds: ["boss", "match", "sandbox"], fingerprint: "1deaded3c7" },
  { key: "python/py-ch04", subject: "python", chapter: "py-ch04", title: "标准库：os / sys / re / datetime / json", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "c978d9a49c" },
  { key: "python/py-ch05", subject: "python", chapter: "py-ch05", title: "文件与 IO：读写 / 上下文管理器 / 序列化", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "97a1b9febf" },
  { key: "python/py-ch06", subject: "python", chapter: "py-ch06", title: "正则与文本处理：re / 分组 / 替换", kinds: ["boss", "match", "sandbox"], fingerprint: "c861e57bf5" },
  { key: "python/py-ch07", subject: "python", chapter: "py-ch07", title: "并发：threading / asyncio", kinds: ["boss", "fill", "sandbox"], fingerprint: "e1ae4e2fab" },
  { key: "python/py-ch08", subject: "python", chapter: "py-ch08", title: "数据分析：numpy/pandas 入门", kinds: ["boss", "match", "sandbox"], fingerprint: "37e9da84ff" },
  { key: "python/py-ch09", subject: "python", chapter: "py-ch09", title: "面向对象：类、继承与魔术方法", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "2adfc72db6" },
  { key: "spring/spring-ch01", subject: "spring", chapter: "spring-ch01", title: "Spring 核心：IoC 容器与依赖注入", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "4f765b9d5d" },
  { key: "spring/spring-ch02", subject: "spring", chapter: "spring-ch02", title: "Bean 生命周期与作用域", kinds: ["boss", "fill", "match", "sandbox", "sequence"], fingerprint: "57a05c1636" },
  { key: "spring/spring-ch03", subject: "spring", chapter: "spring-ch03", title: "AOP 与代理机制", kinds: ["boss", "match", "sandbox"], fingerprint: "c3990afa51" },
  { key: "spring/spring-ch04", subject: "spring", chapter: "spring-ch04", title: "SpringBoot 自动配置与起步依赖", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "28bac3ce47" },
  { key: "spring/spring-ch05", subject: "spring", chapter: "spring-ch05", title: "Web 层：REST 控制器与参数校验", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "2387cc454e" },
  { key: "spring/spring-ch06", subject: "spring", chapter: "spring-ch06", title: "MyBatis 基础：映射与 CRUD", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "cb4a0a1529" },
  { key: "spring/spring-ch07", subject: "spring", chapter: "spring-ch07", title: "MyBatis 进阶：动态 SQL、缓存与插件", kinds: ["boss", "fill", "match", "sandbox"], fingerprint: "3aefd4f47f" },
  { key: "spring/spring-ch08", subject: "spring", chapter: "spring-ch08", title: "事务管理与工程实践", kinds: ["boss", "match", "sandbox"], fingerprint: "893f3c19e5" },
  { key: "tooling/tool-ch01", subject: "tooling", chapter: "tool-ch01", title: "Linux 基础：文件系统与权限", kinds: ["boss", "match"], fingerprint: "7ae3252852" },
  { key: "tooling/tool-ch02", subject: "tooling", chapter: "tool-ch02", title: "Linux 进程、管道与 Shell 脚本", kinds: ["boss", "match"], fingerprint: "db7328c5cf" },
  { key: "tooling/tool-ch03", subject: "tooling", chapter: "tool-ch03", title: "Git 核心：对象模型与分支", kinds: ["boss", "fill", "match"], fingerprint: "667c40d116" },
  { key: "tooling/tool-ch04", subject: "tooling", chapter: "tool-ch04", title: "Git 协作：分支策略与冲突处理", kinds: ["boss", "match", "sequence"], fingerprint: "95cbed9ed8" },
  { key: "tooling/tool-ch05", subject: "tooling", chapter: "tool-ch05", title: "Docker 基础：镜像、容器与 Dockerfile", kinds: ["boss", "match"], fingerprint: "2633d67e94" },
  { key: "tooling/tool-ch06", subject: "tooling", chapter: "tool-ch06", title: "Docker Compose 与部署实践", kinds: ["boss", "match", "sandbox"], fingerprint: "2ffe00dac0" },
];

type Loader = () => Promise<LabData[]>;

const LOADERS: Record<string, Loader> = {
  agent: () => import('./agent').then((m) => m.default),
  ai: () => import('./ai').then((m) => m.default),
  bigdata: () => import('./bigdata').then((m) => m.default),
  clang: () => import('./clang').then((m) => m.default),
  cpp: () => import('./cpp').then((m) => m.default),
  data: () => import('./data').then((m) => m.default),
  database: () => import('./database').then((m) => m.default),
  "discrete-math": () => import('./discrete-math').then((m) => m.default),
  fullstack: () => import('./fullstack').then((m) => m.default),
  fundamentals: () => import('./fundamentals').then((m) => m.default),
  java: () => import('./java').then((m) => m.default),
  middleware: () => import('./middleware').then((m) => m.default),
  ml: () => import('./ml').then((m) => m.default),
  python: () => import('./python').then((m) => m.default),
  spring: () => import('./spring').then((m) => m.default),
  tooling: () => import('./tooling').then((m) => m.default),
};

const CACHE = new Map<string, LabData[]>();

/** 按学科加载；同一学科只下载一次，之后走内存 */
export function loadLabSubject(subject: string): Promise<LabData[]> {
  const hit = CACHE.get(subject);
  if (hit) return Promise.resolve(hit);
  const load = LOADERS[subject];
  if (!load) return Promise.resolve([]);
  return load().then((list) => {
    CACHE.set(subject, list);
    return list;
  });
}

/** 已经加载过就直接给（避免首帧闪「加载中」） */
export function peekLabSubject(subject: string): LabData[] | undefined {
  return CACHE.get(subject);
}

/** 实验台用：某学科的章节清单（来自常驻索引，不需要等数据包） */
export function labIndexBySubject(subject: string): LabIndexItem[] {
  return LAB_INDEX.filter((x) => x.subject === subject);
}

/** 全部学科（按索引里出现的顺序去重），实验台的学科胶囊用 */
export const LAB_SUBJECTS: string[] = LAB_INDEX.reduce<string[]>((acc, x) => {
  if (!acc.includes(x.subject)) acc.push(x.subject);
  return acc;
}, []);
