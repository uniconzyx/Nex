# CppMind · 阶段 6：AI 深化（CppCat 课程锚定）

> 版本：v0.1 · 日期：2026-09-21 · 依据：Phase1-PRD、Phase2-Architecture §8、Phase5-Client
> 状态：**待主人确认后进入阶段 7（内容生产）**

---

## 1. 阶段目标与定位

阶段 5 已搭好 AI 底座（6 模式 prompt、DeepSeek/OpenAI/Claude 多 provider、SSE 流式、会话存储、限额）。
但有一个**架构性缺口**——架构文档 §8.2 要求「当前章节(目标+知识点摘要)」上下文注入，阶段 5 实际只注入了
`chapter/code/wrong_questions/progress` 占位，**CppCat 完全不认识真实课程资料与题库**，回答是「凭空生成」的，
且 Flutter 端调用的 `/ai/chat` 后端根本没有实现（两端契约错位）。

阶段 6 把 AI 从「能聊」升级为「**懂课、能考、会诊断**」：

| 维度 | 阶段 5 | 阶段 6 |
|---|---|---|
| 知识来源 | 仅 prompt 模板 | 课程检索锚定（RAG-lite，BM25） |
| 测验 | 无 | 自适应测验（基于错题本弱项，每题带真题依据） |
| 诊断 | 无 | 薄弱点聚合 + 学习建议 |
| 计划 | `PlanGenerateIn` 未落地 | 注入进度+弱项流式生成 |
| 端契约 | Flutter 调 `/ai/chat` 后端无此路由 | 后端 `/ai/chat` 实装 SSE，契约对齐 |

---

## 2. 课程知识检索层（RAG-lite）

**文件**：`server/app/services/retrieval.py`

- `KnowledgeIndex`：纯内存 BM25 倒排索引（k1=1.5, b=0.75，idf 带平滑），**零外部向量库依赖、可单测、无网可跑**。
- 分词：英文/数字按词；中文按「单字 + 二元」切分（轻量、无需分词器）；标题参与检索（如「智能指针」贡献"指针"词）。
- 语料来源：
  - `build_corpus_from_content(content_dir)`：扫描 `content/*.md`，按路径推断 `subject` 与 `chapter_id`。
  - `build_corpus_from_exercises(rows)`：把题库行转为文档，每条带 `source_ref`（真题依据，合规：LeetCode/牛客仅存链接）。
- `retrieve(query, k, subject, chapter_id)`：支持 subject / 章节过滤（章节上下文优先），返回 `Hit(doc, score, snippet)`。

**为什么不上向量库**：MVP 语料规模小（20 章 Markdown + 数百题），BM25 已足够相关；避免引入 pgvector / 外部
embedding 服务的运维与成本，契合架构文档「成本控制」与「可离线」原则。后续若语料过万题，再平滑替换为向量检索。

---

## 3. 上下文注入升级

**文件**：`server/app/services/ai_provider.py` → `build_messages`

新增 `retrieved: list[Hit]` 参数；命中的课程片段以「【相关资料（优先参考）】」块注入系统 prompt，
含标题、章节、真题依据、摘要片段。所有 6 模式均受益——苏格拉底/诊断/审查的回答现在**锚定真实课程**，
不会编造与资料矛盾的结论。

```python
if retrieved:
    ref_lines = [f"· 《{h.doc.title}》（第 {h.doc.chapter_id} 章）〔真题依据：{ref}〕\n  {h.snippet}"
                for h in retrieved]
    ctx_parts.append("【相关资料（优先参考，回答须与之一致）】\n" + "\n".join(ref_lines))
```

---

## 4. 自适应测验

**文件**：`server/app/services/quiz.py` + 端点 `POST /ai/generate-quiz`

- `generate_quiz(exercises, weak_chapters, weak_types, n, rng_seed)`：**纯函数、确定性（seed 可复现）、可单测**。
- 候选池收敛优先级：弱章节 ∩ 弱题型 > 仅弱章节 > 仅弱题型 > 全库（无弱项时）。
- **关键约束**：候选池不足 n 时只返回池内全部，**不做跨学科/跨题型外溢**，保证练习有的放矢。
- 池内 easy/mid/hard 轮转均衡；输出 `QuizQuestion` 每条必带 `source_ref`（真题依据），**绝不凭空捏题**。
- 端点逻辑：读错题本聚合弱章节/弱题型 → 从题库抽题；无错题本用户退化为难度均衡抽样。

---

## 5. 薄弱点诊断

**文件**：`server/app/services/insight.py` + 端点 `GET /ai/insight`

- `analyze_weakness(error_book, progress, chapter_titles)`：聚合 `wrong_questions` + `progress`，
  按「错误次数 − 0.3×正确次数」加权排名弱章节，统计弱题型，给出结构化建议。纯函数、可单测。
- 端点返回 `InsightOut{weak_chapters, weak_types, recommendations, total_wrong}`，前端直接结构化渲染，
  也可喂给 `/ai/plan` 生成针对性计划。

---

## 6. 端点清单（新增 / 实装）

| 方法 | 路径 | 说明 | 流式 |
|---|---|---|---|
| POST | `/api/v1/ai/chat` | 统一对话入口，自动建/续会话，**检索锚定**，契约对齐 Flutter | SSE ✅ |
| POST | `/api/v1/ai/generate-quiz` | 自适应测验（Body: `n/chapter_ids/types`） | — |
| GET | `/api/v1/ai/insight` | 薄弱点诊断 | — |
| POST | `/api/v1/ai/plan` | 学习计划（注入进度+弱项，复用 `PlanGenerateIn`） | SSE ✅ |
| POST | `/api/v1/ai/conversations` 等 | 阶段 5 既有会话端点 | — |

SSE 事件：`meta{model,mode,conversation_id}` → 多个 `delta{text}` → `done{quota_left,conversation_id}` / `error{message}`。
`/ai/chat` 与阶段 5 的 `/ai/conversations/{id}/messages` 并存：前者适合前端自维护 history 的轻量调用，后者适合多会话管理。

---

## 7. 客户端（Flutter）

- `features/ai/ai_page.dart`：**实装 SSE 流式**（`dio` `ResponseType.stream` 逐 token 渲染），模式切换用 `ChoiceChip`，
  顶栏新增「生成测验」「学习诊断」入口；后端未连通时降级为引导式兜底，骨架始终可用。
- 新增 `features/ai/ai_quiz_page.dart`、`ai_insight_page.dart`：分别调 `/ai/generate-quiz`、`/ai/insight`，
  结构化展示题目（含高亮「真题依据」条）/ 弱章节与建议。
- `core/router/app_router.dart`：注册 `/ai/quiz`、`/ai/insight`。

> 注：Flutter 端为演示骨架，需后端 + DeepSeek Key 方可跑通真实流式；当前以契约对齐 + 降级兜底保证可编译。

---

## 8. Web 演示（`web-preview/index.html`）

- AI 对话卡片新增「📚 相关资料（已锚定真实课程）」真题依据条，呼应阶段 6 锚定能力。
- 顶栏新增「生成自适应测验」「学习诊断」两个演示按钮，分别注入带真题依据的练习卡与薄弱点诊断卡
  （模拟 `POST /ai/generate-quiz` 与 `GET /ai/insight`，无后端亦可体验）。

---

## 9. 测试

新增 `tests/test_retrieval.py`（6）、`test_quiz.py`（5）、`test_insight.py`（5），共 **16 例**，全部通过。
全量回归 `pytest tests/` = **31 passed**（阶段 4/5 的 15 例无回归）。

---

## 10. 与阶段 5 的衔接

- 复用：`ai_provider` 多 provider 与 `pick_model` 分级、`AIMode` 枚举、会话/限额模型、`WrongQuestion`/`Progress` 表。
- 落地：阶段 5 定义但未实现的 `PlanGenerateIn` 在 `/ai/plan` 中实装；Flutter 错位调用的 `/ai/chat` 现有后端承接。
- 合规：所有题目 `source_ref` 延续「LeetCode/牛客仅存元数据+链接，不存题面正文」红线。

---

## 11. 逻辑自查（主人规则 · 必填）

逐项核查阶段 6 交付是否存在逻辑漏洞：

1. **检索相关性**：BM25 仅对 `text` 相关词打分，标题参与索引但摘要取自 `text`；若某文档标题命中但正文无词，
   摘要可能为空 → 已用 `_snippet` 兜底取首段，`build_corpus_from_exercises` 也把标题并入正文，风险可控。
2. **测验外溢**：初版 `generate_quiz` 会为凑满 n 从全库外溢，导致「弱章节测验」混入无关章节——
   **已修复**：候选池收敛且不足 n 时只返回池内全部，测试 `test_quiz_grounded_in_weak_chapters` 锁死。
3. **端点事务**：流式 `finally` 中 `db.add + await db.commit()` 替代 `async with db.begin()`，
   避免与请求级会话已有的事务嵌套冲突（与阶段 5 既有写法一致）。
4. **契约对齐**：`/ai/chat` 的 SSE `event/delta` 字段与 Flutter `ai_page._parseDelta` 解析完全对应；
   元事件含 `conversation_id` 供续聊。
5. **降级不空屏**：后端无 Key（503）/ 前端无网时均有兜底文案，不出现空白对话。
6. **真题依据真实性**：检索锚定与测验 `source_ref` 均来自真实题库字段，未引入任何虚构题面（合规红线保持）。
7. **可测性**：检索/测验/诊断均为纯函数，不依赖 DB/网络，单测可稳定复现（seed 固定）。
8. **回归**：全量 31 测试通过，未破坏阶段 4/5 既有能力。

**结论**：阶段 6 逻辑闭环，无未决漏洞。建议进入阶段 7（内容生产：20 章 × 7 类内容填充，为检索层提供足量语料）。
