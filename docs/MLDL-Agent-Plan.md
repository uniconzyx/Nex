# ML/DL 内容 → Agent 应用：完整方案（待敲定）

> 目标读者：主人（产品 + 技术一肩挑）。
> 本文回答两个问题：**① 现在 app 里 ML/DL 内容产生的「服务」到底体现在哪；② 要把它做成 agent 应用，完整方案是什么。**
> 状态：**方案待敲定，未执行**。敲定后按 §8 分期落地。

---

## 0. 结论先行（三句话）

1. **现状是「内容 + 聊天」，不是 agent。** ML 9 章 / AI 14 章共 23 章、137 道题，能读能练，但 AI 侧只有 6 个「聊天模式」（本质是 system prompt 分流），**没有一个能动手做事、能产出可验证产物、能自我纠错的服务**。
2. **差距不在模型，在「手脚」。** 后端 provider 的请求体只有 `{model, messages, stream}`——**没有 tools 字段**，模型永远只能说话。要变成 agent，必须补三样：工具表、执行循环、可验证产物。
3. **执行层不用新建。** `frontend/src/lib/pyodide/PyodideSandbox.ts` 已是一个带 worker 隔离 + 超时/内存限制的 Python 沙箱（`JudgeEngine` 的 `pyodide` 通道在用）。**把工具跑在浏览器里，服务端零改动、零安全风险**，这是本方案最重要的成本优势。

---

## 1. 现状体检：ML/DL 的「具体服务」体现在哪

分三层看，**只有第一层是真的，第二层是「沾边」，第三层基本空缺**。

### 1.1 第一层 · 内容层（真实存在，已可用）

| 学科 | 章数 | 题数 | 覆盖 |
|---|---|---|---|
| `ml` 机器学习 | 9 | 54 | 导论与梯度下降、线性/逻辑回归与正则、神经网络、评估与偏差方差、树与集成(XGBoost)、无监督、推荐系统、强化学习、SVM 与核方法 |
| `ai` 深度学习/大模型 | 14 | 83 | DL 基础与反向传播、CNN/RNN/注意力、Transformer 与 LLM、LoRA/RLHF/DPO、提示与上下文工程、RAG、**Agent 开发**、LLM 应用工程、服务化、SFT 数据工程、推理引擎与量化、多模态、生成模型、训练工程 |
| 合计 | **23** | **137** | 每章齐备 7 类内容（目标/概念三视角/陷阱/示例/习题/面经/项目）+ 工作场景 |

**这层的服务是**：能读（章节页）、能练（三关 + 掌握度）、能考（408 之外的独立学科）、能背（图鉴/八股）。

### 1.2 第二层 · 对话层（沾边，但服务很薄）

| 现有能力 | 实际是什么 | 问题 |
|---|---|---|
| `AiPage` 6 个模式：苏格拉底 / 编译诊断 / 代码审查 / 学习计划 / **DL 部署指导** / 模拟面试 | 6 段不同的 system prompt，走同一个 `/api/v1/ai/chat` | **模式 = 提示词，不是能力**。`dl` 模式只是「用 DL 专家的口吻回答」，它不能查你的进度、不能跑代码、不能出图 |
| `POST /ai/chat`（SSE 流式） | 单轮：检索 4 条 → 拼 prompt → 流式吐字 | 无循环、无工具、无状态 |
| `POST /ai/generate-quiz` | 按章节生成题目 | **ML/DL 用户不会主动去调它**，没接进任何流程 |
| `POST /ai/insight` / `/ai/plan` | 进度洞察 / 学习计划 | 只吃数字，不碰 ML/DL 内容 |
| `retrieval.KnowledgeIndex`（BM25） | 语料 = `content/**/*.md` + 题库 | **ML/DL 23 章的 markdown 确实在索引里**，所以问「LoRA 的秩怎么选」能命中 `ai-ch04`。这是目前最实在的一处服务 |
| `_ai_quota(plan)` | 按套餐限次数 | 已有计费雏形 |

**一句话**：ML/DL 现在能提供「**一个读过这些书的顾问**」，但提供不了「**一个陪你做实验、帮你定位问题、给你交报告的人**」。

### 1.3 第三层 · 执行层（空缺）

| 该有的 | 现在 | 影响 |
|---|---|---|
| 跑 Python（numpy/sklearn/matplotlib） | **有沙箱，但只服务判题**（`PyodideSandbox` 仅供 `JudgeEngine` 判题调用） | ML 内容完全没用到它 → 学员只能「读代码」，不能「改代码看结果」 |
| 出图（学习曲线/混淆矩阵） | 无 | ML 教学最需要的东西缺失 |
| 读用户进度喂给 AI | 无 | AI 不知道你哪章薄弱，只能泛泛而谈 |
| 产物（报告/notebook） | 无 | 聊完就没了，无法沉淀、无法导出到 E 盘 |
| 工具调用（function calling） | **provider 不支持** | 这是「agent」四个字的技术门槛 |

### 1.4 顺带查到的两个内容缺口

| 缺口 | 说明 |
|---|---|
| `ai-ch07`（Agent 开发）**题库为 0** | 全 23 章里唯二没题的章（另一处是新建的 `dm-ch*` 尚未进题库）→ 学完打不了关、mastery 永远到不了 100 → 本章总结永不解锁 |
| ML/DL 无「实验」定义 | 23 章的 `examples` 是**示例代码**，不是「可执行实验」（没有数据集、没有验收指标、没有 starter code） |

---

## 2. 硬缺口诊断（要做成 agent，必须补这 5 条）

| # | 缺口 | 为什么是硬门槛 | 补法 |
|---|---|---|---|
| G1 | **没有工具表** | agent 的定义就是「模型 + 工具」，没工具就只是聊天 | 新增 `frontend/src/lib/agent/tools.ts` 注册表 |
| G2 | **没有执行循环** | 单轮 prompt 无法「试→看结果→改」 | 新增 `agentLoop.ts`：plan → act → observe → 收敛，最多 8 步 |
| G3 | **没有可验证产物** | 聊完即焚，用户拿不到东西 | 新增 `agent_artifacts`：Markdown / .ipynb / PNG |
| G4 | **AI 不读用户状态** | 个性化是 agent 的核心价值 | `get_progress` 工具接 `progress.ts` 的 mastery/错题 |
| G5 | **数值靠模型算** | LLM 算显存/延迟必错（这是本仓一贯的教训：`audit_correctness` 抓出的错全在「人脑猜数值」） | **数值一律走纯函数**，模型只负责选参数和解释 |

---

## 3. 目标：什么叫「agent 应用」（可验收定义）

不满足这 5 条的不叫 agent，只叫聊天：

| # | 要素 | 本方案的验收口径 |
|---|---|---|
| A | **能动手** | 至少 6 个工具，其中 ≥1 个真的「执行代码并拿到真实输出」 |
| B | **能循环** | 一次任务内 ≥3 步（不是一问一答），且能因工具报错而改方案 |
| C | **有状态** | 读得到用户 mastery / 错题 / 已完成章节 |
| D | **有产物** | 会话结束产出可下载文件，且产物内每个数字都能追溯到某次工具调用的真实输出 |
| E | **能自证** | 有单测/审计脚本证明「产物里的数字不是编的」（`mock planner` 跑通全链路 + 真 stdout 比对） |

---

## 4. 架构

### 4.1 分层

```text
┌──────────────────────────── 浏览器（可信边界在这）────────────────────────────┐
│  AgentPage (#agent)                                                          │
│   ├── 会话视图：每步一张卡（思考 / 工具调用 / 工具结果 / 结论）                 │
│   ├── 产物面板：Markdown 预览 + 下载(.md/.ipynb) + 图片                        │
│   └── agentLoop.ts  ← 编排器（决定这一步调什么工具）                            │
│         ├── tools.ts        工具注册表（10 个，声明式 schema）                  │
│         ├── run_python ──► PyodideSandbox（已有，worker 隔离 + limits）        │
│         ├── get_progress ─► progress.ts（已有，mastery/错题）                  │
│         ├── read_chapter ─► data/chapterContent.ts（已有，全章正文切片）        │
│         ├── make_quiz ────► /api/v1/ai/generate-quiz（已有）                   │
│         └── estimate_dl_budget ─► lib/dlBudget.ts（纯函数，单测锁死）          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ SSE（复用现有 /api/v1/ai/chat 通道）
┌───────────────────────────────────┴─────────────────────────────────────────┐
│  服务端（FastAPI）                                                            │
│   ├── /ai/chat          单轮 LLM（现状，A 期不改 provider）                    │
│   ├── /ai/agent/session 会话落库（新增，可选）                                 │
│   └── KnowledgeIndex    BM25 检索 content/**/*.md + 题库（已有）               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**关键取舍：执行层放浏览器。** 理由：

| 方案 | 安全 | 成本 | 依赖 | 结论 |
|---|---|---|---|---|
| 服务端 subprocess（扩展 `judge_local.py`） | 需自建 cgroup/job 限制，风险高 | 需常驻进程 | 需装 numpy/sklearn（+torch 数百 MB） | ❌ A 期不做 |
| **浏览器 Pyodide（已有）** | worker 隔离，**碰不到服务器** | 0 | 首次加载 ~10MB CDN，已有进度回调 | ✅ 采用 |
| 接外部 Code Interpreter API | 安全 | 按次计费 | 多一个供应商 | ⏸ 备选 |

**必须诚实的一条限制**：Pyodide **官方包里有 numpy / scipy / scikit-learn / matplotlib / pandas，但没有 PyTorch**。所以：

- **ML 侧（sklearn）→ 可以真跑、真出图、真看指标**；
- **DL 侧（torch）→ 不能真训练**。DL 的服务定位改为「**估算 + 讲解 + 部署方案生成**」（这恰好是就业里最值钱的部分：显存/延迟/量化选型），而不是「陪你训模型」。

### 4.2 工具清单（10 个）

| # | 工具 | 执行位置 | 输入 | 输出 | 服务场景 |
|---|---|---|---|---|---|
| 1 | `search_content` | 服务端 BM25（复用 `KnowledgeIndex.retrieve`） | `{query, k}` | `[{chapter_id, title, snippet, score}]` | 全部 |
| 2 | `read_chapter` | 前端（`chapterContent.ts`） | `{chapter_id}` | 7 维正文切片 | 全部 |
| 3 | `get_progress` | 前端（`progress.ts`） | `{subject?}` | `[{chapter_id, mastery, done, wrong_count}]` | S1 |
| 4 | `run_python` | 前端 Pyodide | `{code, packages[], timeout_ms}` | `{stdout, stderr, elapsed_ms, vars}` | S2 |
| 5 | `plot` | 前端 Pyodide（matplotlib→PNG base64） | `{code}` | `{image_base64}` | S2 |
| 6 | `make_quiz` | 服务端（`/ai/generate-quiz`） | `{chapter_id, n, difficulty}` | `{items[]}` | S1/S4 |
| 7 | `grade_quiz` | 前端（`exerciseBank`） | `{item_id, answer}` | `{correct, explanation}` | S1/S4 |
| 8 | `estimate_dl_budget` | **前端纯函数** `lib/dlBudget.ts` | `{params_b, weight_bits, kv_tokens, gpu_vram_gb, target_tps}` | 方案表（显存/延迟/推荐量化/命令） | S3 |
| 9 | `write_report` | 前端 | `{title, sections[]}` | `{markdown, ipynb}` | 全部 |
| 10 | `ask_user` | 前端 | `{question, options[]}` | `{choice}` | S3（需要拍板时停） |

**设计铁律（承接本仓既有教训）**：

- **凡是数字，必须由工具算，不许模型算。** 显存、延迟、指标、寻道距离……模型只负责「选参数 + 解释为什么」。
- **产物里每个数字都要能溯源**到某次工具调用的真实输出（`write_report` 强制带 `evidence` 字段）。
- **工具失败要能被模型看见**（`stderr` 原样回填），这样它才会改代码重试——这是 agent 与「一次性生成」的本质区别。

### 4.3 执行循环：两个方案，A 期选「客户端编排」

| 方案 | 做法 | 改动 | 优点 | 缺点 |
|---|---|---|---|---|
| **① 客户端编排（A 期采用）** | 前端把工具 schema 塞进 system prompt，要求模型**只输出一个 JSON 动作**；前端执行后把结果作为新消息回填，循环 | **provider 零改动**，任何模型可用 | 立刻能跑；执行全在浏览器；可用 mock planner 离线单测 | 每步一次往返（token/延迟叠加 8 倍） |
| ② 服务端原生 tool-calling（A6 再做） | provider 请求体加 `tools`，SSE 事件加 `tool_call`/`tool_result` | 改 `ai_provider.py` + `ai.py` + 前端 SSE 解析 | 省往返、可异步长任务、可多用户 | 需要能正确支持 tools 的模型；服务端要承载执行 |

**①的协议（伪代码）**：

```ts
// agentLoop.ts
let msgs = [systemPlanner(tools), { role: 'user', content: task }];
for (let step = 0; step < MAX_STEPS; step++) {
  const action = await planner(msgs);          // 复用 streamChat，只要 JSON
  if (action.type === 'final') return writeReport(action);
  const result = await runTool(action.tool, action.args);
  msgs.push({ role: 'assistant', content: JSON.stringify(action) });
  msgs.push({ role: 'user', content: `OBSERVE ${truncate(result, 2048)}` });
}
```

**防爆措施**：`MAX_STEPS=8`、单个工具结果截断 2KB、token 预算上限、连续 2 次同一工具同一参数 → 强制收敛。

### 4.4 前端交互（不新开一个聊天框）

**新增页面 `#agent`「实验台」**，三个区：

| 区 | 内容 |
|---|---|
| 左 · 会话 | 每步一张卡：🧠 计划 / 🔧 工具（展开看 args+result）/ 📊 图 / ✅ 结论 |
| 中 · 产物 | Markdown 预览 + 「下载 .md」+「下载 .ipynb」+ 图片 |
| 右 · 上下文 | 当前章节、mastery、已调用工具数、token 用量、剩余配额 |

复用既有视觉体系（`.km-card` / `.km-btn` / `--km-glow`），按主人定的规矩走 `design-taste-frontend`。

---

## 5. 四个真实服务场景（「具体服务体现在哪」的正面回答）

每个场景都写清：**用户说什么 → agent 做什么 → 交出什么 → 怎么证明没瞎编**。

### S1 · 学习诊断 Agent（最刚需，最便宜）

> 用户：「我 ML 学到哪了？哪章其实没学会？」

| 步 | 动作 |
|---|---|
| 1 | `get_progress` → 拿到 9 章 mastery，筛出 `<60` 的章 |
| 2 | `read_chapter(薄弱章)` → 取该章 7 维（目标/概念/陷阱） |
| 3 | `make_quiz(薄弱章, 3)` → 现场出 3 题（不是复用做过的） |
| 4 | 用户作答 → `grade_quiz` 判分 |
| 5 | 错题 → 定位到**具体 concept**（不是笼统说「这章不行」） |
| 6 | `run_python` 跑一个**最小复现实验**（如梯度下降不收敛 → 3 行代码演示学习率影响） |
| 7 | `write_report` |

**产物**：`诊断报告.md`
```
## 结论（1 句）
ml-ch01 的真实卡点是「学习率与特征缩放的关系」，不是「梯度下降公式」。

## 证据
- mastery 42%，三关只过第一关（来源：get_progress）
- 3 题现场测：2 错，都错在「未归一化时 lr 要更小」（来源：grade_quiz）
- 复现实验：同一份数据 lr=0.1 不收敛、lr=0.01 收敛（来源：run_python 真实输出）

## 3 天补法
第 1 天 …（具体到做哪几道题、跑哪个实验）

## 复现实验（可直接改参数）
```python
...
```
```
**验证**：报告里每个论断后面必须挂 `来源：某工具`，缺一条即判失败。

### S2 · 实验陪跑 Agent（ML 侧真正「动手」）

> 用户：「用 iris 训个分类器，我准确率 100%，是不是有问题？」

| 步 | 动作 |
|---|---|
| 1 | `search_content("数据泄漏 交叉验证")` → 命中 `ml-ch04` |
| 2 | `run_python` 先**复现用户的错**（全量数据算 scaler → 泄漏） |
| 3 | 自主发现「100% 是泄漏」→ 改成 `Pipeline` + 交叉验证 → 再跑 |
| 4 | `plot` 出学习曲线（train/val 双线，肉眼可见过拟合） |
| 5 | `read_chapter(ml-ch04)` 对齐教材口径（偏差-方差） |
| 6 | `write_report` 生成 `.ipynb` |

**产物**：`实验报告.ipynb`（Markdown 单元 + 可运行代码单元 + **真实输出** + 图尾），完全对齐主人 E 盘笔记习惯。
**验证**：`ipynb` 里每个输出块必须能在 `run_python` 的 stdout 里逐字找到（复用 `scripts/check_md_outputs.py` 的思路）。

### S3 · 部署教练 Agent（DL 侧唯一的诚实定位）

> 用户：「7B 模型，24G 4090，要 30 tok/s，怎么部署？」

| 步 | 动作 |
|---|---|
| 1 | `ask_user`（要保精度还是要速度？并发多少？） |
| 2 | `estimate_dl_budget` **纯函数**算：FP16 权重 14GB + KV cache(4k×batch) → 24G 够不够；INT8/AWQ 后各需要多少；预估吞吐 |
| 3 | `read_chapter(ai-ch13)` 取「KV Cache 分页 / continuous batching / GPTQ-AWQ-GGUF」口径 |
| 4 | 生成**可复制的命令**（vLLM / llama.cpp / TensorRT-LLM 三选一 + 参数） |
| 5 | `write_report` |

**产物**：`部署方案.md`（估算表 + 命令 + 风险项 + 回退方案）
**验证**：估算表由 `lib/dlBudget.ts` 生成，**单测锁死公式**（如 7B×2B = 14GB；KV cache = 2×layers×heads×d×tokens×bytes）。模型不给数字，只解释。

### S4 · 模拟面试 Agent（接就业链路，复用已有资产）

> 用户：「面 ML 算法岗，练一轮」

| 步 | 动作 |
|---|---|
| 1 | `make_quiz` / 复用 `reexam.json` 面试结构 → 出第 1 题 |
| 2 | 多轮追问（5 轮，每轮基于用户上一答） |
| 3 | 按固定 4 维打分：准确性 / 深度 / 工程感 / 表达（1-5） |
| 4 | 弱项回链章节 → `read_chapter` 生成补课清单 |
| 5 | `write_report` |

**产物**：`面试评估.md`（逐题得分 + 追问链 + **引用用户原话作为打分证据** + 补课章节）
**验证**：每个分数必须附一句用户原话引用，禁止空口打分。

---

## 6. 内容侧配套（不做这步，agent 只能空谈）

现有 23 章的 `examples` 是**示例代码**，不是**实验**。要支撑 S2，需要给每章加 `labs`：

```json
// content/ml/ml-ch04/labs.json（新增，每章 1-2 个）
{
  "chapter": "ml-ch04",
  "labs": [{
    "id": "leakage-demo",
    "title": "数据泄漏现场复现：为什么你的准确率是 100%",
    "dataset": "sklearn.datasets.load_breast_cancer",
    "packages": ["numpy", "scikit-learn", "matplotlib"],
    "starter_code": "# 有 bug 的版本，先让学员跑出 100% 再修\n...",
    "checkpoints": [
      {"ask": "cv 分数是多少", "expect_regex": "^0\\.9[0-9]"},
      {"ask": "训练/验证曲线差距", "expect": "train 高 val 低"}
    ],
    "pitfalls": ["全量 scaler 泄漏", "只看 accuracy 不看 AUC"],
    "linked_concepts": ["04-cross-validation", "04-bias-variance"]
  }]
}
```

**配套改动**：

| 项 | 说明 | 量 |
|---|---|---|
| 补 `ai-ch07` 题库 | Agent 开发章当前 0 题 → 学完打不了关 | 8 题 |
| 给 23 章加 `labs.json` | S2 的素材 | 23 文件 / 30 个实验 |
| `ml`/`ai` 进 `validate_content.py` 实验守门 | labs 必须能真跑（`packages` 全在 Pyodide 官方包内） | 1 条规则 |

---

## 7. 数据模型（新增 3 张表，A 期可先用 localStorage）

```sql
agent_sessions(id, user_id, scenario, chapter_id, title, state_json, created_at, updated_at)
agent_steps(id, session_id, idx, think, tool, args_json, result_json, ok, tokens, latency_ms)
agent_artifacts(id, session_id, kind /* md | ipynb | png */, name, content_sha256, bytes)
```

A 期走 localStorage（与 `progress.ts` 同款 `persistQuietly` 策略），A6 再落库——理由：先跑通体验，避免过早引入迁移。

---

## 8. 分期与验收

| 期 | 交付 | 验收（可复跑） |
|---|---|---|
| **A0** | `lib/agent/{tools,agentLoop}.ts` + mock planner + 纯函数单测 | `node scripts/verify_agent.mjs --check-loop`：**不接 LLM**，用 mock planner 跑通「3 步 + 1 次工具失败重试 + 收敛」，产物 Markdown 逐字断言 |
| **A1** | 接真 LLM（复用 `/ai/chat`）+ `MAX_STEPS`/token 上限 + 失败降级 | 有 key 时真跑一条 S1；无 key 时降级到「规则 planner」（固定工具序列），仍能出报告 |
| **A2** | **S1 诊断 Agent** + `#agent` 页面（会话卡 + 产物面板） | 报告的每个论断都有 `来源：tool`；抽 3 个用户状态（全 0 / 有薄弱 / 全通）各跑一遍 |
| **A3** | **S2 实验 Agent** + `.ipynb` 导出 | `ipynb` 内每个输出块都能在真实 stdout 中逐字找到（复用 `check_md_outputs.py` 思路） |
| **A4** | **S3 部署教练** + `lib/dlBudget.ts` | 纯函数单测：7B/13B/70B × FP16/INT8/AWQ × 24G/48G/80G 全组合断言显存与吞吐 |
| **A5** | **S4 面试 Agent** + 补 `ai-ch07` 题库 8 题 | 分数必带原话引用；题库回归 `--check-summary` 不破 |
| **A6**（可选） | 服务端原生 tool-calling（`ai_provider` 加 `tools`）+ 会话落库 + 异步长任务 | SSE `tool_call` 事件契约测试；断线重连可续 |

**每期固定动作**：`tsc --noEmit` 0 error + `vite build` ✓ + 四条既有 verify 不回归 + `git commit`（只提交本期文件）。

---

## 9. 风险与取舍（提前说清，避免过度承诺）

| 风险 | 影响 | 应对 |
|---|---|---|
| **Pyodide 无 PyTorch** | DL 侧不能真训练 | 明确定位为「估算 + 讲解 + 部署方案」，**不承诺**训模型；torch 相关交给 `ai-ch10/13` 的**命令与公式**，不跑 |
| Pyodide 首载 ~10MB | 首次打开慢 | 懒加载（进 `#agent` 才 load）+ 复用已有 `SandboxProgress` 进度条 |
| 每步一次 LLM 往返 | 8 步 → 8 倍 token | 动作只出 JSON（~80 token）+ 结果截断 2KB + 步数上限 + 连续重复即收敛 |
| 模型不按 JSON 输出 | 循环崩 | 解析失败重试 1 次 → 仍失败则降级「规则 planner」 |
| 产物数字编造 | 学术诚信 | `write_report` 强制 `evidence`；`verify_agent.mjs` 逐条校验数字来源 |
| 无 API key（离线/未配置） | 演示不了 | 「规则 planner」兜底：S1/S3 本来就能纯工具跑完（LLM 只负责措辞） |
| 配额被工具调用放大 | 成本 | `_ai_quota` 改为「按步计费」，A1 起在 UI 显示剩余步数 |

---

## 10. 需要主人敲定的 3 个决策点

### 决策 1 · 首期做到哪
- **① 最小闭环（A0+A1）**：证明「能循环、能调工具」，1 轮可完，风险最低。
- **② 两个真服务（A0→A3）**：S1 诊断 + S2 实验，**能演示、能交付产物**，推荐。
- **③ 全铺（A0→A5）**：四个场景 + 面试，工期最长。

### 决策 2 · DL 侧定位
- **① 诚实版（推荐）**：只做「估算 + 讲解 + 部署方案」，可验收、不吹。
- **② 硬要真训**：需服务端 GPU 或接外部 Code Interpreter，成本与风险另算。

### 决策 3 · 实验产物格式
- **① `.ipynb`（推荐）**：对齐主人 E 盘笔记习惯，可回放、可复用。
- **② 纯 Markdown**：轻，但不能回放。
- **③ 两者都给**：默认 `.md`，一键转 `.ipynb`。

---

## 附：本方案复用到的既有资产（不重复造轮子）

| 资产 | 位置 | 用途 |
|---|---|---|
| Python 沙箱 | `frontend/src/lib/pyodide/PyodideSandbox.ts` | `run_python` / `plot` 的执行底座（含 worker 隔离 + limits + 进度） |
| 判题通道选择 | `frontend/src/lib/JudgeEngine.ts` | `pyodide` 通道已验证可用，可直接借鉴调用方式 |
| BM25 检索 | `server/app/services/retrieval.py` | `search_content` |
| 章节正文切片 | `frontend/src/data/chapterContent.ts`（`gen_chapter_content.py` 生成） | `read_chapter` 的 7 维数据 |
| 进度模型 | `frontend/src/lib/progress.ts` | `get_progress`（mastery / doneChapters / answers） |
| 7 维总结 | `frontend/src/lib/chapterSummary.ts` | 报告里的「本章总结」表直接复用 |
| 出题 | `POST /api/v1/ai/generate-quiz` | `make_quiz` |
| 面试结构 | `content/_tracks/reexam.json` | S4 的题型/评分维度 |
| 正文输出溯源 | `scripts/check_md_outputs.py` | 产物数字防编造的校验思路 |
