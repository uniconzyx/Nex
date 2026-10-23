# 机器学习学科内容生产规范（ml-ch02 ~ ml-ch08 执行契约）

> 参考实现（**必须先读**）：`content/ml/ml-ch01/` 全部文件 + `server/scripts/_ml_src/ml-ch01/` 的 10 个 .py。
> 质量标杆就是那一章。你产出的章节要和它**同深度、同结构、同语气**。

## 0. 学科边界（写错方向会返工）

- 本学科 = **经典机器学习**：统计学习、凸优化、树与集成、核方法、概率模型、无监督、评估与工程。
- **不要写深度学习**：不写反向传播、不写 Transformer/CNN/LLM——那是 `content/ai` 的职责。
- 可以用一句话衔接（「这类非线性可由 ai 学科的神经网络进一步表达」），但不得展开。

## 1. 目录与文件（缺一不可）

```
content/ml/<chapter-id>/
├── goals.md                       # 学习目标 + 3 条关键认知 + 本章 GitHub 资源
├── concept/01-xxx.md              # ≥3 个，每个文件覆盖 ≥2 个核心主题
├── concept/02-xxx.md
├── concept/03-xxx.md
├── pitfalls.md                    # 6 条编号条目，每条含 现象 / 根因 / 正确做法
├── exercises.json                 # 6 题：3 基础题 + 3 算法题
├── examples/                      # 10 个，由构建器生成，**不要手写**
├── interview.json                 # 4 个追问，answer_md 每个 ≥ 500 字
└── project.json                   # 1 个综合项目，≥5 个可验证任务
```

示例源码放 `server/scripts/_ml_src/<chapter-id>/exNN_<slug>.py`，
第一行必须是 `# title: 中文标题`。

## 2. concept/*.md 的硬性要求

- 每个文件 **≥2 个核心主题**，每个主题先给中立陈述（定义/机制/公式），再展开三个视角。
- 三个视角标记必须**逐字**出现（emoji 含零宽连接符，直接从本文件复制，不要自己敲）：

```
### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角
```

- 程序员视角写**工程**：真实取舍、常见 bug、性能、上线事故。
- 博士生视角写**机制**：第一性原理、推导、复杂度、与相邻理论的关系、历史演进。
- 考研者视角写**考点**：标准定义、常考题型、计算口径、易混概念（机器学习非 408 科目，
  这里对准**自命题 AI 专业课与面试笔试**，用词要标准化）。
- 至少出现 2 处公式/伪代码块（``` 围栏），至少 1 张 ASCII 图或表格。
- **禁止编造**：引用教材要写真实书名与章节；不确定的结论要标明是经验判断。

## 3. exercises.json 结构（照抄字段名）

```json
{
  "meta": {"chapter": "ml-chXX", "title": "…… —— 习题集", "count": 6, "note": "3 概念题 + 3 算法实践题，均为原创题干"},
  "items": [
    {"type": "choice", "category": "基础题", "platform": "self", "difficulty": 2,
     "title": "……", "content_md": "题干，选项 A-D 各占一行",
     "answer": {"correct": "A", "explain": "≥150 字，讲清为什么对、其他选项错在哪"},
     "explanation": "一句话说明这道题考什么",
     "tags": ["…"], "source": "self", "source_ref": "《机器学习》第X章"},
    {"type": "coding", "category": "算法题", "platform": "self", "difficulty": 4,
     "title": "……", "content_md": "任务要求，编号列出",
     "answer": {"reference_code": "≤20 行关键代码（不是完整答案）", "explain": "≥150 字，含坑"},
     "explanation": "……", "tags": ["…"], "source": "self", "source_ref": "……"}
  ]
}
```

- 基础题类型可用 `choice` / `judge`；算法题用 `coding`。
- **平台一律 `self`**（不要写 leetcode/nowcoder，避免合规问题）。
- 3 道算法题必须**彼此不同**：一道手写核心算法、一道做数值验证、一道做诊断/对比实验。

## 4. examples 生产方式（关键）

写 10 个 .py 到 `server/scripts/_ml_src/<chapter-id>/`，命名 `ex01_xxx.py` … `ex10_xxx.py`。

**硬约束**：
- 只允许 `numpy` + 标准库（**没有** pandas / sklearn / matplotlib / scipy）。
- 固定随机种子（`np.random.default_rng(固定数)`），输出必须**可复现**。
- 每个示例运行 < 10 秒，只打印文本（表格/曲线用字符画），不画图、不读外部文件。
- 输出要有**结论行**（「读法/结论/机理」），不是裸数字。
- 示例要覆盖该章的核心公式：例如手写算法、数值验证、失效边界。

生成并自检（在仓库根目录执行）：

```bash
PY=/c/Users/zyx/.workbuddy/binaries/python/envs/default/Scripts/python.exe
$PY server/scripts/build_ml_examples.py ml-chXX      # 执行 .py，把真实 stdout 写进 examples/*.json
$PY server/scripts/verify_examples.py --subject ml --chapter ml-chXX   # 重新执行并比对
```

`verify_examples.py` 必须显示通过。若某示例数值不稳定（误差爆炸到 1e10 以上），
调整噪声/样本量或改用中位数+对数展示，**不要**手改 expected_output。

## 5. pitfalls.md：6 条，格式固定

```
1. **一句话结论式标题**
   - 现象：……
   - 根因：……
   - 正确做法：……
```

必须是**真实会犯的错**，不要写「注意过拟合」这种空话。参考 ml-ch01 的 6 条。

## 6. interview.json：4 条

```json
{"meta": {"chapter": "ml-chXX", "title": "…… —— 面试深度追问", "count": 4},
 "items": [{"question": "……", "answer_md": "≥500 字，**要点** 分条，含公式/对比表",
            "follow_ups": ["…", "…", "…"], "difficulty": 3, "company_tags": ["字节跳动"]}]}
```

题目要选**真正区分度**的：不是「什么是 X」，而是「为什么 X 在 Y 情况下失效」。

## 7. project.json：1 条

```json
{"meta": {"chapter": "ml-chXX", "title": "…… —— 综合项目", "count": 1},
 "items": [{"title": "……", "requirement_md": "编号列出 5-6 条要求，含验收口径",
            "tasks": [{"title": "…", "verification": {"type": "output", "desc": "可核对的判据"}}],
            "tags": ["…"]}]}
```

`verification.type` 用 `output`（打印判据）或 `accuracy`（指标阈值）。

## 8. goals.md 结构

```
# <chapter-id> · <标题>
> 先修：… 后续：… 面试权重：★★★★☆（一句说明）
## 本章目标      （5 条，动词开头，可检验）
## 关键认知（本章最值钱的三句）
## 本章 GitHub 资源（star 数由 GitHub API 实测，2026-10-21）
## 与「深度学习」的分界   （2-3 句，说明本章不碰神经网络）
```

GitHub 资源从 `content/ml/_manifest.json` 中该章的 `resources.github` 取，
写全 `仓库名 — star★：一句话说明看它什么`。

## 9. 禁止事项

- 不要修改 `content/ml/_manifest.json`、`_bagua.json`、其他章节、`content/ai/**`、前端。
- 不要写第三方题面/正文（合规红线）。
- 不要用 `sklearn` 的现成实现替代「手写」，示例的价值在于把算法拆开。
