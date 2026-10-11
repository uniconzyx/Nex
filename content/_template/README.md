# CppMind 内容格式规范（7 类内容 + 八股模块）

> 阶段 7 内容生产模板。每个章节目录 `content/<subject>/<chapter-id>/` 必须包含以下 7 类文件；
> 每个学科目录 `content/<subject>/` 额外包含 `_manifest.json` 与 `_bagua.json`（八股模块）。
> 校验脚本：`server/scripts/validate_content.py`（CI 门禁，不满足则报错）。

## 目录结构

```
content/<subject>/
├── _manifest.json                # 学科课程大纲（章节 + 资源映射）
├── _bagua.json                   # ⑧ 八股模块（学科级，面试八股题库）
└── <chapter-id>/
    ├── goals.md                       # ① 学习目标
    ├── concept/                       # ② 核心概念讲解（≥3）
    ├── pitfalls.md                    # ③ 易错点（≥3 条）
    ├── exercises.json                 # ④ 练习题（≥5，须区分基础题/算法题）
    ├── examples/                      # ⑤ 可运行示例（≥10）
    ├── interview.json                 # ⑥ 面试题（≥3）
    └── project.json                   # ⑦ 项目任务（≥1）
```

---

## ② concept/*.md —— 三视角解析（硬性要求，2026-10-07 升级）

> **本节是全项目内容深度的最高标准。** 每个知识点解析**必须同时从三个视角展开**，
> 三者互补、缺一不可；不允许只写其中一个视角就交付。

### 三视角定义

| 视角 | 标记（必须逐字出现） | 回答的问题 | 典型内容 |
|---|---|---|---|
| **程序员视角** | `🧑‍💻 程序员视角` | 「**在工程里怎么用、会踩什么坑、性能如何**」 | 真实项目惯例、上线事故案例、性能数据、可维护性取舍、安全风险、替代方案对比 |
| **博士生视角** | `🎓 博士生视角` | 「**为什么是这样、底层到底发生了什么**」 | 第一性原理、形式化定义、数据结构/内存布局、硬件与 ABI 机制、设计动机与历史演进、复杂度分析证明、与相邻理论的关系 |
| **考研者视角** | `📚 考研者视角` | 「**408/统考怎么考、标准定义与易错点**」 | 统考纲内标准定义与术语、常考题型、公式与计算口径、命题角度、易混概念对比、真题风格问法 |

### 结构模板

每个核心主题下，先给**中立的事实陈述**（定义、机制），再分三个视角展开：

```markdown
## 二、inode：文件的真正本体

（中立陈述：inode 存什么、不存什么；用 ASCII 图给出目录项 → inode 的映射）

### 🧑‍💻 程序员视角
- `rm` 只是删目录项：误删后若进程仍持有 fd，可从 `/proc/<pid>/fd/` 抢救；
- `df` 满而 `du` 小 → 用 `lsof +L1` 排查「已删仍被占用」的文件；
- 工程惯例：日志清理用 logrotate（truncate）而非 `rm` + 重启。

### 🎓 博士生视角
- 抽象分层：路径名（dentry）→ inode → 数据块，三层解耦使硬链接成为自然产物；
- 为什么「12 直接块 + 三级间接」：在小文件命中率与超大文件上限之间取平衡；
- 现代演进：ext4 的 extent 用「起始块 + 长度」替代逐块指针，把元数据量降到 O(区段数)。

### 📚 考研者视角
- **408 统考点**：文件物理结构（连续/链接/索引）、索引节点（inode）的作用、
  目录项与 FCB 的关系、硬链接与符号链接在「文件共享」小节的标准对比表述；
- **常考口径**：给「12 直接 + 1 一级 + 1 二级间接」与块大小，计算**最大文件长度**（务必先算指针块能放多少指针）；
- **易混点**：`i_nlink` 与「打开计数」是两个不同字段，前者管删除、后者管释放。
```

### 要求细则

1. **三种标记必须逐字出现**（`🧑‍💻 程序员视角` / `🎓 博士生视角` / `📚 考研者视角`），
   以便 `validate_content.py` 的三视角覆盖度统计能识别（报告项，见下）。
2. **每个 concept 文件至少覆盖 2 个核心主题**，每个主题都要写全三视角；
   文件末尾可用「三视角小结」表格收束。
3. 三个视角**内容不得互相重复**：程序员视角写工程，博士生视角写机制，考研者视角写考点。
   若某主题确实无考研考点（如工具链操作），考研者视角应**显式说明**为什么不在考纲内、
   或指出与之相关的考纲概念（例：`find` 本身不考，但「文件目录结构」是考点）。
4. **考研者视角优先服务 408**（数据结构 / 计算机组成原理 / 操作系统 / 计算机网络）；
   非 408 学科（Java/Spring/大数据/AI 等）的考研视角改写为**「面试笔试考点」**，
   仍然使用 `📚 考研者视角` 标记，但内容对准该方向的笔试/面试标准化问法与易错口径。
5. 语气：严谨、有依据。能引用标准条款/经典著作/官方文档就引用；**不臆造、不含糊其辞**。

### 存量说明

2026-10-07 之前产出的章节（约 40 章）按「博士 + 程序员」双视角写成，
需按本节标准**补写 🧑‍💻 / 🎓 / 📚 三视角小节**（回归升级，不重写内容）。
`validate_content.py` 会输出 `tri_view` 覆盖度报告，**不阻塞**章节达标判定，
但新产内容必须一次到位。

---

## ④ exercises.json —— 习题分类（硬性要求）

每道题**必须**标注 `category` 与 `platform`，用于在学习端区分「基础题」与「算法题」并溯源：

| 字段 | 取值 | 含义 |
|---|---|---|
| `category` | `基础题` \| `算法题` | **基础题**：考察语言/知识点本身的语法、语义、输出、Debug<br>**算法题**：考察数据结构与算法设计，通常来自刷题平台 |
| `platform` | `self` \| `github` \| `leetcode` \| `nowcoder` \| `book` | 题目来源平台 |

**规则**：
- `platform` 为 `leetcode`/`nowcoder`/`github` 时，`category` **通常**为 `算法题`（来自刷题平台），
  且必须含 `external_url`（真实链接）+ `source_ref`（题号/仓库）。
- `category` 为 `基础题` 时，`platform` 一般为 `self`/`book`，`source_ref` 注明教材章节。
- 每章**建议混合**：基础题 ≥2、算法题 ≥1，避免全章只有一种类型。
- **合规红线**：来自 `leetcode`/`nowcoder` 的题只存**元数据与链接**，**绝不搬运题面正文**。

```json
{
  "meta": { "chapter": "<chapter-id>", "note": "..." },
  "items": [
    {
      "type": "choice | fix_error | output | coding",
      "category": "基础题 | 算法题",
      "platform": "self | github | leetcode | nowcoder | book",
      "difficulty": "easy | mid | hard",
      "title": "题目标题",
      "content_md": "题干（Markdown，可含代码块）",
      "options": [ { "key": "A", "text": "..." } ],
      "answer": { "correct": ["B"], "output": "...", "reference_code": "..." },
      "explanation": "解析",
      "tags": ["reference"],
      "source": "self | leetcode | nowcoder",
      "source_ref": "《C++ Primer》第6章 / LeetCode 20（valid-parentheses）",
      "external_url": "https://leetcode.cn/problems/valid-parentheses/",
      "time_limit_ms": 2000,
      "memory_limit_mb": 256,
      "test_cases": [ { "input": "...", "expected_output": "...", "is_sample": true } ]
    }
  ]
}
```

---

## ⑧ _bagua.json —— 八股模块（学科级）

"八股"指面试高频、需要**背记 + 理解**的标准问答。与章节 `interview.json`（偏追问、偏深度）互补：
八股模块追求**覆盖面广、答案标准化、便于速记**。

```json
{
  "subject": "cpp",
  "title": "C++ 八股模块",
  "note": "面试高频八股题库，按领域分类；答案标准化便于速记，与章节 interview.json 互补。",
  "categories": [
    {
      "id": "lang",
      "title": "语言基础",
      "items": [
        {
          "q": "问题（八股题干）",
          "a": "标准答案（Markdown，要点化）",
          "tags": ["指针"],
          "difficulty": "easy | mid | hard",
          "hot": 5,
          "source_ref": "《C++ Primer》第2章"
        }
      ]
    }
  ]
}
```

**要求**：
- `categories` ≥3 个领域（如：语言基础 / 数据结构与算法 / 操作系统 / 计算机网络 / 数据库 / 框架与工程）。
- 每个学科 `items` 总数 **≥12** 条（校验门槛）。
- 答案要点化、可速记；能注明出处就写 `source_ref`。

---

## 其余各类格式（不变）

### ① goals.md
普通 Markdown，列出本章学习目标。

### ③ pitfalls.md
Markdown 编号列表，每条：`N. **陷阱标题** —— 说明 + 正确写法`。

> ⚠️ **编号必须出现在行首**（`1.` `2.` `- `）。若写成 `## 1. 标题` 这类 Markdown 标题形式，
> `validate_content.py` 的 `_count_pitfalls` 按**行首**判定，会静默读成 0 条并判定本章不达标。

### ⑤ examples/*.json（可运行示例）
```json
{
  "title": "示例标题",
  "code_lang": "cpp | c | java | python | sql | javascript | html",
  "code_std": "cpp17 | c11 | java17 | python3 | mysql | node18",
  "stdin": "",
  "expected_output": "a=2 b=1",
  "code": "..."
}
```

**`expected_output` 的硬约束**（`validate_content.py` 会阻塞校验）：

- 必须来自**真实执行**，不得手写猜测；每批产出后用 `verify_examples.py` 回放复核。
- **禁止机器相关量**：墙钟耗时（`ms`/`ns`）、内存地址（`0x...`）、对象身份哈希（`@1a2b3c`）、
  随机哈希（Python `hash(str)`，受 `PYTHONHASHSEED` 影响）。性能类示例改用**确定性判据**——
  操作计数、指针跳转次数、或布尔判据（如 `加速比>100: True`）。
- **教学性乱码需显式豁免**：若示例刻意演示乱码/编码损坏（如字符编码、乱码排查章节），
  必须在示例里声明 `"_intentional_corrupt": "<原因>"`——**原因必填**，用于防止拿它掩盖真脏数据。
  该豁免只作用于脏数据特征匹配，返回码一致性检查照常执行。

### ⑥ interview.json
```json
{
  "meta": { "chapter": "<chapter-id>" },
  "items": [
    {
      "question": "面试题",
      "answer_md": "解析（Markdown）",
      "follow_ups": ["追问1", "追问2"],
      "difficulty": "easy | mid | hard",
      "company_tags": ["通用", "字节"]
    }
  ]
}
```

### ⑦ project.json
```json
{
  "meta": { "chapter": "<chapter-id>", "category": "basic | system | dl" },
  "items": [
    {
      "title": "项目名",
      "requirement_md": "需求说明（Markdown）",
      "tasks": [ { "title": "步骤", "verification": { "type": "manual | test", "desc": "验证口径" } } ]
    }
  ]
}
```

---

## 学习线独立性与三元服务（2026-10-08 新增，硬性要求）

> **每条学习线必须「独立且完整」，同时服务考研、学习、就业。** 审计工具：`server/scripts/audit_learning_lines.py`。

### 独立性（可从零起步）

1. **首章无前置**：每条线的第一章 `prerequisites` 必须为空数组。
2. **跨学科先修只允许写进 `soft_prerequisites`**（属「建议」，可跳过）：

```json
{
  "id": "data-ch05",
  "prerequisites": [],
  "soft_prerequisites": [
    { "id": "py-ch01", "note": "Python 语法基础（若已掌握可跳过）" }
  ]
}
```

> ⚠️ 把跨学科章节写进 `prerequisites` 会让该线**无法独立起步**，审计会判为风险项。
> `prerequisites` 只允许引用**本线**章节；软前置还需要在 `goals.md` 里加一段
> 「## 软前置（可选，不阻断学习）」说明。

3. **自带资源与八股**：每条线都要有 `_manifest.json` 里的 GitHub 资源与学科级 `_bagua.json`，不依赖其他线。

### 三元服务（每条线都要能交付这三件事）

| 服务 | 交付物 | 判定口径 |
|---|---|---|
| **考研** | 每个 concept 内嵌 `📚 考研者视角`；fundamentals 对准 408 四门 | 三视角齐备 + 八股 ≥10 题 |
| **学习** | `goals.md` + `concept/` + `pitfalls.md` + `examples/`（真实实测） | 7 类门槛全达标 |
| **就业** | `_bagua.json` + 每章 `interview.json`(≥3) + `project.json`(≥1) + GitHub 资源 | 同上 |

---

## ⚠️ 三视角标记的字节规范（2026-10-08 血的教训）

标记必须**逐字**为：

```
### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角
```

**坑**：「🧑‍💻」是**带零宽连接符（ZWJ, U+200D）**的复合 emoji，即
`U+1F9D1 + U+200D + U+1F4BB`。早期脚本产出过**不带 ZWJ** 的版本（`U+1F9D1 + U+1F4BB`），
两者渲染出来几乎一样、**字节却不同**，肉眼无法分辨。

- 旧版门禁只按中文关键词（`程序员视角`）检测，于是这类「标记漂移」长期被判为合格，
  还掩盖了 `clang-u06` 三个 concept **完全没有三视角章节**的事实（关键词在正文里出现过）。
- 现在 `validate_content.py` 会**同时报告「标记规范性」**并在输出里单列 `标记漂移` 清单。
- **生成三视角小节时不要手打 emoji**：用 Python 显式码点构造，例如
  `"\U0001F9D1\u200D\U0001F4BB"`，或直接从已合规文件里复制整行标题。

**同理适用于生成脚本**：往 Markdown 里写三视角标题时，优先从常量拼接，避免不同编辑器/模型
产出 ZWJ 变体。
