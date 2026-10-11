# CppMind · 阶段7 内容生产任务清单

> 生成时间：2026-10-08（最后更新：同日 18:1x）
> 状态口径：**已完成 68 / 规划 114 单元（59.6%）**；三视角 251/251 = 100%（规范标记 251/251，漂移 0）；八股题库 13/13；全库示例真实回放 **672/672 通过**。
> 学习线独立完整性与三元服务（考研/学习/就业）审计见 **`docs/Phase7-LearningLines-Audit.md`**；
> 复跑审计：`python server/scripts/audit_learning_lines.py --json`。
> 本清单是**执行清单**——每项都可直接派发或亲产，完成一项勾选一项。

## 近三轮已完成（可直接核对）

| 单元 | 内容 | 状态 |
|---|---|---|
| `data-ch04` | Pandas 进阶：分组聚合 / 合并 / 时间序列 / 透视与性能（4 concept + 10 pitfalls + 8 题 + **12 个 pandas 实测示例** + 6 面经 + 1 项目） | 门禁 OK · 回放 12/12 |
| `data-ch03` | Pandas 基础：Series 与 DataFrame（补齐 12 示例 + 6 题 + 6 面经 + 1 项目） | 门禁 OK · 回放 12/12 |
| `fund-ch12` | 计算机网络：应用层与链路排查（**408 线 12/12 收官**） | 门禁 OK · 回放 10/10 |
| `fund-ch07` | 计算机组成原理：数据表示与运算 | 门禁 OK · 回放 10/10 |
| `fund-ch08` | 计组：存储系统与 CPU | 门禁 OK · 回放 10/10 |
| `fund-ch10` | 操作系统：内存管理、文件与 IO | 门禁 OK · 回放 10/10 |
| `fund-ch11` | 计算机网络：分层模型与 TCP/IP | 门禁 OK · 回放 10/10 |
| `java-ch07` | 并发：Thread、线程池与 JUC 并发容器 | 门禁 OK · 回放 10/10 |
| `java-ch08` | JVM 与内存模型、GC、类加载 | 门禁 OK · 回放 10/10 |
| `docs/Phase7-LearningLines-Audit.md` | 学习线独立完整性 + 三元服务审计报告 | 13/13 无风险项 |

---

## 一、总览

| 指标 | 数值 | 说明 |
|---|---|---|
| 规划单元总数 | 114 | 13 学科章节 + clang 7 单元 |
| 已达标（磁盘 7 类齐全 + 门禁 OK） | **68** | 覆盖率 59.6% |
| 剩余待产 | **46** | 见下表 |
| 三视角覆盖 | 251 / 251 = 100% | 规范标记 251/251，漂移 0 |
| 八股题库 | 13 / 13 学科 | `content/<subj>/_bagua.json`（fundamentals 含数据结构/算法/计组/OS/网络五类） |
| 示例真实回放 | 672 / 672 | `verify_examples.py` 全量通过 |
| 学习线独立性 | 13 / 13 达标 | `audit_learning_lines.py` 零风险项 |
| 状态漂移 | 0 | `sync_manifest_status.py` |

**注意两个分母**：`coverage_pct`（分母=磁盘已开工章节，衡量已产出质量）与
`planning.coverage_pct`（分母=大纲全部 114 单元，衡量整体进度）。只看前者会得出虚假的 100%。

---

## 二、剩余 46 个单元（按优先级）

### P1 · 高优先级（面经权重最高，建议先做）

| # | 单元 | 标题 | 建议实测栈 |
|---|---|---|---|
| 1 | `java-ch06` | IO 与 NIO（BIO/NIO/AIO、Channel、Selector、零拷贝） | javac 23（输出 ASCII） |
| 2 | `java-ch09` | 工程与框架：Maven 与 Spring Boot 入门 | javac 23 |
| 3 | `spring-ch05` | Web 层：REST 控制器与参数校验 | javac 23（手写路由/校验器） |
| 4 | `spring-ch06` | MyBatis 基础：映射与 CRUD | javac 23（手写映射器） |
| 5 | `spring-ch07` | MyBatis 进阶：动态 SQL、缓存与插件 | javac 23 |
| 6 | `spring-ch08` | 事务管理与工程实践 | javac 23（手写事务管理器） |
| 7 | `db-ch04` | 查询优化与执行计划（EXPLAIN） | Python 模拟代价估算 + B+ 树 I/O |
| 8 | `mw-ch05` | Kafka 架构：Topic、Partition 与 Replica | Python 模拟（ISR/水位/leader 选举） |

### P2 · 中优先级（学科主线，承接已完章节）

| # | 单元 | 标题 | 建议实测栈 |
|---|---|---|---|
| 9 | `db-ch05` | 存储过程 / 触发器 / 自定义函数 | SQL（`_verified: false`）+ Python 模拟 |
| 10 | `db-ch06` | 范式与数据库建模 | Python 模拟 / SQL 文本 |
| 11 | `db-ch07` | 备份恢复与权限安全 | Python 模拟 |
| 12 | `db-ch08` | 高可用 / 主从复制 / 分库分表 | Python 模拟 |
| 13 | `mw-ch06` | Kafka 生产者与消费者机制 | Python 模拟 |
| 14 | `mw-ch07` | 消息可靠性：不丢、不重、有序 | Python 模拟 |
| 15 | `mw-ch08` | 消息队列选型与工程实践 | Python 模拟 |
| 16 | `bd-ch04` | Spark 核心：RDD 与惰性求值 | Python 模拟（compute 计数器证明惰性） |
| 17 | `bd-ch05` | Spark SQL、DataFrame 与 Catalyst | Python 模拟 |
| 18 | `bd-ch06` | 离线数仓实战：分层建模与调度 | Python 模拟 |
| 19 | `cpp-ch18` | 性能与底层：内存对齐、缓存友好与内联 | g++（c++17） |
| 20 | `cpp-ch19` | 工程化与测试：CMake、单元测试与 CI | g++ / CMake |
| 21 | `cpp-ch20` | 综合项目与面试冲刺 | g++ |

### P3 · 补齐型（学科完整度）

| # | 单元 | 标题 | 建议实测栈 |
|---|---|---|---|
| 22 | `data-ch05` | 数据采集：requests 与解析（含合规边界） | venv（requests/lxml/bs4） |
| 23 | `data-ch06` | 数据分析与数学建模实战 | venv numpy/pandas |
| 24 | `ai-ch02` | 视觉与序列建模：CNN、RNN 到注意力机制 | Python（numpy 手搓） |
| 25 | `ai-ch03` | Transformer 与大语言模型原理 | Python（numpy 手搓自注意力） |
| 26 | `ai-ch04` | 高效微调与对齐：LoRA、RLHF 与 DPO | Python 模拟 |
| 27 | `ai-ch05` | 提示工程与上下文工程 | Python 模拟 |
| 28 | `ai-ch06` | RAG：向量检索与知识增强 | Python（numpy 手写向量检索） |
| 29 | `ai-ch07` | Agent 开发：工具调用、记忆与多智能体 | Python 模拟 |
| 30 | `ai-ch08` | LLM 应用工程：推理优化、评测、可观测性与安全 | Python 模拟 |
| 31 | `fs-ch03` | JavaScript 核心：类型、原型链、DOM、异步 | node 22 |
| 32 | `fs-ch04` | Node.js 与后端 API | node 22 |
| 33 | `fs-ch05` | 数据库与 REST API 设计 | node 22 / SQL 文本 |
| 34 | `fs-ch06` | 用户认证 / JWT / 鉴权 | node 22（手写 JWT 签名） |
| 35 | `fs-ch07` | 全栈项目实战（GitHub 资源驱动） | node 22 |
| 36 | `fs-ch08` | 部署 / CI-CD / Docker | node 22 / shell 文本 |
| 37 | `py-ch04` | 标准库：os/sys/re/datetime/json | venv python |
| 38 | `py-ch05` | 文件与 IO：读写/上下文管理器/序列化 | venv python |
| 39 | `py-ch06` | 正则与文本处理：re/分组/替换 | venv python |
| 40 | `py-ch07` | 并发：threading/asyncio | venv python（确定性判据） |
| 41 | `py-ch08` | 数据分析：numpy/pandas 入门 | venv |
| 42 | `tool-ch02` | Linux 进程、管道与 Shell 脚本 | bash 实测 / 文本 |
| 43 | `tool-ch03` | Git 核心：对象模型与分支 | git 命令实测 |
| 44 | `tool-ch04` | Git 协作：分支策略与冲突处理 | git 命令实测 |
| 45 | `tool-ch05` | Docker 基础：镜像、容器与 Dockerfile | 文本 + `_verified: false` |
| 46 | `tool-ch06` | Docker Compose 与部署实践 | 文本 + `_verified: false` |

---

## 三、单章生产标准流程（每章必须走完）

### 产出 7 类文件 → `content/<subject>/<chapter_id>/`

1. `goals.md` — 学习目标
2. `concept/*.md` — **≥3 个**，每个必须内嵌三视角：
   `### 🧑‍💻 程序员视角` / `### 🎓 博士生视角` / `### 📚 考研者视角`
   （emoji 需含**零宽连接符**，生成脚本里用显式码点拼，勿手打）
3. `pitfalls.md` — **≥3 条**，**行首必须有编号**（`1.` / `- `；写成 `## 1.` 会被门禁静默读成 0 条）
4. `exercises.json` — **≥5 题**，每题顶层 `category`(基础题/算法题) + `platform` + `source` + `source_ref`；
   基础题≥2、算法题≥1；leetcode/nowcoder 必须带 `external_url` 且**只存元数据+链接**
5. `examples/*.json` — **≥10 个**，字段 `title/code_lang/code_std/stdin/expected_output/code`
6. `interview.json` — **≥3 条**
7. `project.json` — **≥1 条**

### 三步校验（缺一不可）

```bash
PY="C:/Users/zyx/.workbuddy/binaries/python/versions/3.13.12/python.exe"
cd C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/CppMind

# 1) 门禁：7 类门槛 + 习题分类 + 平台题链接 + 三视角报告
"$PY" server/scripts/validate_content.py        # 必须看到 [OK ] <chapter-id>

# 2) 真实回放：把示例代码重新编译运行，与 expected_output 逐行比对
"$PY" server/scripts/verify_examples.py --chapter <chapter-id>   # 必须 0 失败

# 3) 状态同步：磁盘达标 -> manifest status=complete
"$PY" server/scripts/sync_manifest_status.py
```

### 交付后清理

删除临时生成脚本 `server/scripts/_gen_*.py`、`_fix_*.py`、`_patch_*.py`，
`server/scripts/` 只保留 **9 个常驻工具**（validate_content / verify_examples / sync_manifest_status /
sync_github_resources / sync_dart_manifest / audit_learning_lines / classify_exercises / import_bank / init_db）。

---

## 四、实测环境对照表

| 栈 | 解释器 / 编译器 | 备注 |
|---|---|---|
| C | `D:/mingw64/bin/gcc.exe -std=c11 -O2` | **必须 Windows 路径**，`/d/...` 会 WinError 2 |
| C++ | `D:/mingw64/bin/g++.exe -std=c++17`（或 c++20） | 多线程加 `-pthread` |
| Java | `javac 23.0.2` / `java -Dstdout.encoding=UTF-8 -cp .` | **输出一律 ASCII**（Windows 控制台按 GBK 转码） |
| JavaScript | `node 22` | |
| Python（生成用） | `C:/Users/zyx/.workbuddy/binaries/python/versions/3.13.12/python.exe` | |
| Python（数据栈实测） | `C:/Users/zyx/WorkBuddy/2026-09-19-21-42-03/.workbuddy/pyenv-cppmind/Scripts/python.exe` | numpy 2.5.3 / pandas 3.0.6 / matplotlib / requests / lxml / bs4 |

---

## 五、质量红线（血的教训，违反必返工）

1. **禁止把墙钟时间、纳秒耗时、内存地址写进 `expected_output`** —— 换机器必失败。
   性能类示例改用**确定性判据**：操作计数 / 比较次数 / 指针跳转次数 / 布尔判据（如 `加速比>100: True`）。
2. **禁止使用 `hash(str)`** —— PYTHONHASHSEED 随机化导致输出不可复现。改用 `zlib.crc32`。
3. **定量结论必须先核对实测数字** —— 文案说「衰减到 1e-6」而实测 1e-2、说「Adam 最优」而实测 Momentum 更好，这类事故已发生过。
4. **演示「模型学到东西」的示例，标签必须真由特征决定** —— 随机标签根本学不动。
5. **C/C++ 禁止把「有副作用的调用」与「它写入的变量」放进同一个 printf / `<<` 链**（求值顺序未定义）。先算后打印。
6. **生成脚本内嵌代码避免裸 ASCII 双引号** —— 用 `r'''...'''`（三单引号）包裹源码，内部可自由用双引号。
7. **Java 示例输出一律 ASCII**；subprocess 调 javac 加 `errors="replace"`。
8. **同一文件的多处修改禁止并行 Edit** —— 改用 Python 脚本「一次性原子替换 + 每处断言恰好命中 1 次」。
9. **子代理被 429 截断可能留下静默半成品** —— 每批后必须跑门禁复核 + 检查幽灵/重复目录，不能只信汇报。
10. **pandas 示例的版本红线**：`M` / `Q` / `Y` / `H` 频率别名在 pandas 3.x **已移除**（写就抛
    `ValueError: Invalid frequency`），必须用 `ME` / `QE` / `YE` / `h`；`DataFrame.join` 默认按**索引**合并，
    两边索引相同时会**静默错位对齐**（不报错、不出 NaN）；`round(np.float64(x), 2)` 的 repr 依赖 numpy 版本，
    一律 `round(float(x), 2)`。
11. **跑完生成脚本必须人眼核对关键输出数字**，不能只看 `rc=0`。本轮又抓到 7 处「rc=0 但内容错」。

---

## 六、推进节奏建议

- **批次大小**：每批 4 章并行派发（子代理）；子代理 429 限流期间改为主代理串行亲产。
- **排序原则**：先 P1（Java IO/工程、Spring Web/MyBatis/事务、MySQL 优化、Kafka），
  再 P2（学科主线），最后 P3（学科完整度补齐）。
- **每批收尾**：`validate_content.py` → `verify_examples.py`（本批章节）→ `sync_manifest_status.py` → 清理临时脚本。
- **里程碑**：
  - 60 → **68 ✅（已完成）**
  - 68 → 84（P1 全部 + P2 主体）
  - 84 → 114（全量完成，进入阶段8）

---

## 七、当前已知缺口（非内容生产，单独排期）

- **App 侧八股入口**：`content/fundamentals/_bagua.json` 已含数据结构/算法/计组/OS/网络五类，
  但 **App 还没有独立入口**（前端排期）。
- **SQL 类示例**：本机 mysql client 在但无凭证，相关示例只能标 `_verified: false`。
- **AI 学科**：本机无 torch，深度学习示例需用 numpy 从零手搓（可行，但耗时更长）。
