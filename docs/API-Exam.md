# 考研题库 API 契约（v1）

> 适用范围：`server/app/api/v1/exam.py`、`server/app/services/exam_bank.py`
> 数据来源：`content/_exam/`（由 `python server/scripts/build_exam.py` 生成）
> 状态：已实现并通过 `server/tests/test_exam_api.py`（10 条契约测试）

这份文档是**先于实现写的契约**，不是实现完成后的说明。改接口先改这里，再改代码；
路由里出现业务判断、或者响应字段和本文不一致，都算 bug。

---

## 1. 全局约定

### 1.1 响应信封

所有接口（含错误）都返回同一层信封，定义见 `server/app/core/responses.py`：

```ts
interface Envelope<T> {
  code: number;      // 0 = 成功；非 0 见 §1.2
  message: string;   // 面向人的提示，可直接展示
  data: T | null;    // 业务数据；错误时用于放排障上下文
  traceId: string;   // 16 位，排查问题时让用户报这个值
}
```

FastAPI 默认的参数校验错误是 `{"detail": [...]}`，与本项目信封不一致。为此在
`app/main.py` 增加了 `RequestValidationError` 处理器，统一成
`code=1001`、`data.errors=[...]`。**这是全局行为变更**：此前依赖 `detail` 字段的代码
（仓库内没有）需要改为读 `message` / `data.errors`。

### 1.2 错误码与 HTTP 状态

| code | 含义 | HTTP | 典型场景 |
|---|---|---|---|
| 0 | 成功 | 200 | — |
| 1001 | 参数错误 | 400 | 未知专题/题型、选项下标越界、重复提交同一题、字段拼错 |
| 1002 | 未登录 | 401 | 本模块不涉及（全部公开只读） |
| 1004 | 资源不存在 | 404 | 考试/科目/题目/套卷/篇目不存在 |

**没有 5xx 的业务分支。** 题库缺失或损坏属于部署错误，启动即抛 `RuntimeError`，
不会以「接口 500」的形式暴露给用户。

`404` 时 `data.allowed` 给出合法取值，客户端可以直接渲染候选而不是猜：

```json
{
  "code": 1004,
  "message": "考试不存在：nope",
  "data": { "allowed": ["408", "math", "english", "politics", "discrete", "algorithm"] },
  "traceId": "…"
}
```

### 1.3 命名与单位

- **字段一律 `snake_case`**。设计规范里 REST 字段的默认建议是 camelCase，但本项目
  既有接口（`is_free`、`estimated_minutes`、`kind_label`）与前端类型全部是 snake_case。
  一个 API 里两种风格并存，比「选了哪个」糟糕得多，因此统一沿用既有风格。
- 数据文件里的 camelCase 字段（`questionIds`、`questionMap`、`seenIn`、`falseFriends`）
  在**服务层**翻译为 `question_ids`、`question_map`、`seen_in`、`false_friends`。
  客户端永远看不到原始命名。
- 时长单位分钟，分值单位分，`difficulty` 为 1–5 的整数（数据里叫 `diff`，对外统一为
  `difficulty`）。
- 分页参数是 `page`（从 1 开始）与 `size`（1–100），响应里原样回显。

### 1.4 枚举与未知值

`topic` / `type` 的取值范围随题库变化，**不在文档里写死**。传了不存在的值时返回
`1001`，`data.allowed` 是从题库实时算出来的合法列表：

```json
{ "code": 1001, "message": "未知专题：xxx", "data": { "allowed": ["algo-complexity", "..."] } }
```

前端应当容忍未来新增的 `type`（例如以后加 `coding`），渲染时给兜底文案，而不是白屏。

---

## 2. 资源模型

```
exam（408 / math / english / politics / discrete / algorithm）
└── subject（ds/co/os/cn；m1/m2；e1/e2；pol；dm；algo）
    ├── framework    专题 → 题型 → 固定步骤 + 陷阱（教你怎么想）
    ├── knowledge    知识点：名称 + 核心结论 + 提示（这题考什么）
    ├── summary      分类总结：认题信号 + 步骤 + 技巧 + 陷阱 + 题目清单
    ├── question     题目：四层讲解 + 答案 + 选项
    └── reading      精读篇目（仅英语）：段落主旨 / 词伙 / 长难句 / 复盘
exam
└── paper            套卷：分区 → 题目（整卷可覆盖多个科目）
```

**题目与套卷是两套并存的组织方式**：题库按专题练，套卷按考场结构练。套卷里的题
可能是题库引用、也可能是卷内独有的快照（408 整卷的 7 道设计题就只在卷子里）。

---

## 3. 端点清单

| 方法 | 路径 | 用途 | 分页 |
|---|---|---|---|
| GET | `/api/v1/exams` | 考试目录 + 各科体量 | 否（固定 6 项） |
| GET | `/api/v1/exams/{exam}` | 单场考试详情 | 否 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/frameworks` | 解题框架 | 否 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/knowledge` | 知识点 | 否 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/summaries` | 分类总结 | 否 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/questions` | 题目列表（不含答案） | 是 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/questions/{question_id}` | 单题四层详解 | 否 |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/reading` | 精读索引 | 否（≤8 篇） |
| GET | `/api/v1/exams/{exam}/subjects/{subject}/reading/{passage_id}` | 精读详情 | 否 |
| GET | `/api/v1/exams/{exam}/papers` | 套卷列表 | 是 |
| GET | `/api/v1/exams/{exam}/papers/{paper_id}` | 套卷详情 | 否 |
| POST | `/api/v1/exams/{exam}/subjects/{subject}/grade` | 批量判分（无状态） | — |

**为什么目录、框架、知识点不分页**：它们是**枚举型资源**，上限由大纲决定（6 场考试、
每科 ≤8 个专题），永远不会有第 101 条。给固定 6 项加 `page/size` 只会让客户端多写
一层循环。题目与套卷会随题库增长，因此从第一天就分页。

---

## 4. 数据结构

### 4.1 目录

```ts
interface Catalog {
  content_version: number;   // 题库构建版本，可用于客户端缓存键
  items: ExamSummary[];
}

interface ExamSummary {
  key: string;               // "408"
  label: string;             // "408 计算机学科专业基础"
  short: string;             // "408"
  duration: number | null;   // 分钟
  total_score: number | null;
  subjects: SubjectSummary[];
  counts: { questions: number; topics: number; summaries: number; papers: number };
}

interface SubjectSummary {
  key: string;               // "ds"
  label: string;             // "数据结构"
  score: number;             // 该科在整卷中的分值
  counts: {
    questions: number; topics: number; patterns: number;
    knowledge: number; summaries: number;
    papers: number;          // 含整卷，见 §5.3
  };
}
```

### 4.2 解题框架

```ts
interface FrameworkDoc {
  exam: string; subject: string; label: string;
  score: number | null;
  pattern: string | null;    // 整卷题型结构的一句话描述
  intro: string | null;
  topics: FrameworkTopic[];
  totals: { topics: number; patterns: number };
}

interface FrameworkTopic {
  id: string;                // "algo-complexity"
  title: string;             // "复杂度与渐进分析"
  order: number | null;
  heat: number | null;       // 1–5，考频
  seen_in: number[];         // 考过的年份（归纳性标注）
  points: string[];          // 本专题必须记住的结论
  patterns: Pattern[];       // 题型：看到什么 → 怎么做
  question_count: number;
}

interface Pattern {
  id: string;                // "algo-complexity-p1"
  title: string;             // "主定理与递归式"
  freq: string | null;       // "high" / "mid" / "low"
  ask: string | null;        // 题目长什么样
  steps: string[];           // 固定步骤，按顺序执行
  traps: string[];           // 这一步最容易错在哪
}
```

### 4.3 知识点

```ts
interface KnowledgeDoc {
  exam: string; subject: string;
  book: string | null;       // 对应教材
  items: KnowledgeBlock[];
  total: number;
}

interface KnowledgeBlock {
  topic: string; topic_title: string;
  chapter: string | null;
  knowledge: KnowledgePoint[];
}

interface KnowledgePoint {
  id: string;                // "algo-complexity-k1"
  title: string;             // 知识点名称
  chapter: string | null;
  patterns: string[];        // 与哪些题型挂钩
  core: string;              // 核心结论（一句话能背下来）
  tip: string | null;        // 易错提示
}
```

### 4.4 分类总结

```ts
interface SummaryDoc {
  exam: string; subject: string;
  groups: SummaryGroup[];
  total: number;
}

interface SummaryGroup {
  topic: string;
  title: string;
  recognize: string;         // 认题信号：看到这种问法就归到本专题
  framework: string[];       // 固定步骤
  skills: { title: string; body: string }[];
  traps: string[];
  question_ids: string[];    // 本专题的题目清单，与题库严格一致
}
```

### 4.5 题目

**列表项（不含答案）**：

```ts
interface QuestionCard {
  order: number;             // 在本科目题库中的序号（从 1 开始，稳定）
  id: string;
  topic: string; topic_title: string;
  type: string;              // choice | multi | blank | calc | design | analysis
  difficulty: number | null; // 1–5
  stem: string;
  option_count: number;
  has_passage: boolean;      // 英语阅读题所依赖的原文
  knowledge_ids: string[];
}
```

**详情**：

```ts
interface QuestionDetail {
  id: string; exam: string; subject: string;
  topic: string; topic_title: string;
  type: string; difficulty: number | null;
  stem: string;
  options: string[];         // 无选项题为 []
  passage: string | null;
  ask: string[];             // 主观题的分问
  answer: { correct?: number | number[]; text?: string };
  explain: { right?: string; wrong?: string; link?: string };
  walkthrough: Walkthrough;
}

interface Walkthrough {
  framework: { title: string; pattern: string; steps: string[]; trap: string };
  approach: string;          // 解决思路：这题从哪下手
  points: {                 // 知识点：这题具体考哪一条
    id: string; title: string; core: string;
    note?: string; pitfall?: string;
  }[];
  solution: string;          // 详细解法
}
```

`walkthrough` 的**键顺序固定**为 `framework → approach → points → solution`。
JSON 保留插入顺序，客户端按 `Object.keys` 渲染即可得到正确的教学顺序；数据层由
`server/scripts/validate_exam.py` 校验，API 测试再从出口验一次。

### 4.6 套卷

```ts
interface PaperCard {
  id: string;
  exam: string;
  subject: string | null;    // null = 整卷
  scope: "subject" | "full";
  title: string;
  kind: string;              // "mock"
  duration: number | null;
  total_score: number | null;
  section_count: number;
  question_count: number;
  subjects: string[];        // 卷面覆盖的科目
}

interface PaperDetail extends PaperCard {
  disclaimer: string;
  blueprint: { subject: string; name: string; score: number }[];
  sections: PaperSection[];
  counts: { sections: number; questions: number };
}

interface PaperSection {
  no: number; name: string; type: string;
  range: string | null;      // "1~3 题"
  score: number; per_score: number | null;
  note: string | null;
  items: PaperItem[];
}

interface PaperItem {
  id: string;
  order: number;             // 分区内序号，从 1 开始
  type: string;
  topic: string | null; topic_title: string | null;
  difficulty: number | null;
  stem: string;
  options: string[];
  ask: string[];
  answer: { correct?: number | number[]; text?: string } | null;
  explain: object | null;
  walkthrough: Walkthrough | null;
  score: number | null;
  in_bank: boolean;          // false = 只存在于卷子里（无题库条目）
}
```

### 4.7 精读

```ts
interface ReadingIndex {
  exam: string; subject: string;
  items: {
    id: string; title: string;
    word_count: number; paragraph_count: number;
    vocab_count: number; sentence_count: number;
    question_ids: string[];
  }[];
  total: number;
}

interface Passage {
  id: string; exam: string; subject: string;
  title: string; text: string; word_count: number;
  paragraphs: { no: number; zh: string }[];                 // 段落主旨
  vocab: { word: string; pos: string; cn: string; note: string }[];
  sentences: { en: string; main: string; mods: string; zh: string; point: string }[];
  question_map: { qid: string; type: string; locate: string }[];
  takeaway: string[];         // 读后复盘
  false_friends: { word: string; usual: string; here: string; note: string }[];
  synonyms: { from: string; to: string }[];
}
```

### 4.8 判分

```ts
interface GradeRequest {
  answers: {
    question_id: string;
    choice?: number;    // 单选：选项下标，从 0 开始
    choices?: number[]; // 多选：下标集合，顺序无关
    text?: string;      // 填空：作答原文
  }[];
}

interface GradeResult {
  exam: string; subject: string;
  items: {
    question_id: string;
    type: string;
    verdict: "CORRECT" | "INCORRECT" | "UNGRADED";
    your_answer: number | number[] | string | null;
    expected: object;     // 参考答案原样回声
    explain: object;
    walkthrough: Walkthrough;
  }[];
  summary: {
    total: number; correct: number; incorrect: number; ungraded: number;
    accuracy: number | null;   // correct / (correct + incorrect)，全主观题时为 null
  };
}
```

---

## 5. 必须遵守的行为规则

### 5.1 题目列表不下发答案

`GET .../questions` 只返回 `QuestionCard`。答案、解析、四层讲解一律在详情接口。
理由很直接：列表里带上 `answer`，刷题就退化成看答案，而客户端没有任何办法「忽略」
已经到手的字段。契约测试 `test_question_list_does_not_leak_answers` 钉住这一点。

### 5.2 判分是整批原子的

一次请求里的答案要么全部通过校验、要么整批 400，**不做部分判分**。三种拒绝情形：

- 同一题重复出现 → `data.duplicate_ids`
- 题目不属于该 `{exam}/{subject}` → `data.unknown_ids`
- 题型与作答字段不匹配 / 下标越界 → `data.question_id` + 期望字段或 `option_count`

这样客户端不会出现「交 10 题、判了 7 题、剩下 3 题悄悄丢了」的状态。

### 5.3 套卷的 subject 过滤按「卷面覆盖」判定

`GET /exams/408/papers?subject=ds` 返回 **9 份**：8 份数据结构专项卷 + 1 份 408 整卷。
整卷的 `subject` 是 `null`、`scope` 是 `"full"`，它同时出现在 ds/co/os/cn 四个科目下。

副作用：四个科目的 `counts.papers` 相加（36）大于考试总数（33）。这是刻意的——
科目视角要看到「我能刷的卷子」，而不是「只属于我的卷子」。客户端做总计时用
`exam.counts.papers`，不要对科目求和。

### 5.4 精读「空集合」不是 404

政治/数学没有精读材料，`GET .../reading` 返回 `items: [], total: 0`。
集合存在但为空，与「资源不存在」是两件事：后者会让前端弹错误提示，前者只是没内容。

### 5.5 判分规则

| 题型 | 判定方式 |
|---|---|
| `choice` | `choice` 与 `answer.correct` 相等 |
| `multi` | `choices` 去重排序后与 `answer.correct` 完全相等（多选少选都算错，不给部分分） |
| `blank` | 归一化后字符串比较：去掉所有空白（含全角空格）、忽略大小写、去掉尾部标点 |
| `calc` / `design` / `analysis` | 一律 `UNGRADED`，回声参考解法 |

主观题**不做**字符串比对。把「证明题」当成文本匹配，会训练出背答案而不是写推导的
习惯；接口明确告诉你「这题自己对着解法看」。

### 5.6 四层顺序是契约的一部分

`framework → approach → points → solution`。不允许在同一响应里重排、也不允许把
`points` 合并进 `solution`。前端按 JSON 键序渲染即可，不需要额外的排序表。

---

## 6. 版本、兼容与缓存

### 6.1 兼容策略

- **只增不改**：新增字段必须可选；已有字段不改类型、不改语义、不删除。
- 新增考试/科目/题型属于**枚举扩展**，不算破坏性变更；客户端必须容忍未知枚举值。
- 路径版本（`/v1`）只在无法向后兼容时才升；本项目优先「加字段」而不是 `/v2`。
- `paper_id`、`question_id`、`topic` 是**持久标识**，不得因重新生成而改名。

### 6.2 缓存

题库是构建产物，进程首次访问时整库载入内存并常驻：

- `GET` 接口无副作用，可安全缓存；客户端可用 `content_version` 作为缓存键。
- **重新跑 `build_exam.py` 后必须重启服务**，否则进程内还是旧数据。这是刻意的取舍：
  每次请求 stat 上百个文件换来的「热更新」，对一年更新几次的题库不值得。

### 6.3 重试与幂等

| 接口 | 重试安全性 |
|---|---|
| 全部 `GET` | 天然幂等，可任意重试 |
| `POST .../grade` | **无状态**：不写库、不记进度，重试不会产生重复数据 |

因此本模块**不使用** `Idempotency-Key`。将来引入「保存答题记录 / 交卷」这类
有副作用的接口时，必须按下面的方式做，而不是加一个被忽略的请求头：

1. 键来自**意图**而非尝试：`attempt:{userId}:{paperId}`，不是 `randomUUID()`；
2. 用唯一约束**原子占位**（`INSERT` 抢锁），禁止 `SELECT` 后再 `INSERT`；
3. 同键不同 body → `422`，不返回上一次的结果；
4. 首次请求仍在途时，重复请求返回 `409`（或 `202` + 查询地址），不放行；
5. 键的保留期必须长于最长重试链路（含死信队列重放窗口）。

---

## 7. 非目标（明确不做）

- 不做用户作答记录与错题本持久化（需要新表 + 迁移，另行设计）。
- 不做套卷计时、交卷、成绩单。
- 不做题目搜索的全文检索（当前只按题干子串过滤）。
- 不做多语言题干（题库本身是中文，英语科目是英文材料 + 中文解析）。

---

## 8. 验收清单

- [x] 每个端点都有明确的输入/输出类型（本文 §4）
- [x] 所有响应（含错误）同一信封，校验错误也已统一
- [x] 校验发生在边界：Pydantic 管形状、服务层管业务、内部不再重复校验
- [x] 列表端点支持分页（枚举型资源已在 §3 说明例外）
- [x] 新字段只增不改，枚举扩展不影响旧客户端
- [x] 命名全链路一致（snake_case，含数据层 camelCase 的翻译）
- [x] 契约文档与实现同仓提交
- [x] 有状态变更的接口才需要幂等键；当前 `grade` 无状态，已在 §6.3 说明
- [x] 契约测试覆盖信封、分页、答案不外泄、套卷形状统一、判分各分支

```bash
# 契约测试
cd server && pytest tests/test_exam_api.py -q
# 数据层校验（四层顺序、答案、总结一致性、卷面分值）
python server/scripts/build_exam.py
```
