# AI Agent 学科内容生产规范（agent-ch01 ~ agent-ch16 执行契约）

> 质量标杆：`content/agent/agent-ch01/`（本文件写完后由主代理产出）。
> 大纲与资源：`content/agent/_manifest.json`。**只读它，不要改它**。

## 0. 学科边界（写错方向会整章返工）

本学科 = **AI Agent 的交付链路**：怎么把模型能力做成能上线、能评估、能报价、能面试的项目。

- 技术纵深归 `content/ai`：Transformer 完整推导、LoRA 数学、RAG 内部实现、Agent 框架源码。
- 本学科对同一主题只保留：**够用即止的原理 + 工程判据 + 可运行产物**。
- 图片链路里偏产品/商业的节点（DAY 1/7/30/40/43/47/70/90），必须补上**技术承重**：
  每章 `manifest.chapters[].tech_load` 写了该章必须交付什么代码物，**不得只写读书笔记**。

## 1. 目录与文件（缺一不可，校验阈值见 `validate_content.py`）

```
content/agent/<chapter-id>/
├── goals.md                  # 目标 + 3 条关键认知 + GitHub 资源 + B 站清单
├── concept/01-xxx.md         # 恰好 3 个，每个覆盖 ≥2 个核心主题
├── concept/02-xxx.md
├── concept/03-xxx.md
├── pitfalls.md               # 6 条，格式：标题 / 现象 / 根因 / 正确做法
├── exercises.json            # 6 题：3 基础（choice/judge）+ 3 算法（coding）
├── examples/                 # 10 个，由构建器生成，**禁止手写**
├── interview.json            # 4 条，answer_md ≥500 字
└── project.json              # 1 个综合项目，≥5 个可验证任务
```

示例源码：`server/scripts/_agent_src/<chapter-id>/exNN_<slug>.py`，第一行 `# title: 中文标题`。

## 2. concept/*.md 硬性要求

- 每个文件 ≥2 个核心主题；每个主题先给中立陈述（定义/机制/公式/数据），再展开三视角。
- 三个标题必须**逐字**出现（emoji 含零宽连接符，复制粘贴，不要手敲）：

```
### 🧑‍💻 程序员视角
### 🎓 博士生视角
### 📚 考研者视角
```

- 程序员视角：真实取舍、线上故障、成本、性能、权限。
- 博士生视角：机制、推导、复杂度、与相邻概念的关系、历史演进。
- 考研者视角：标准定义、常考题型、计算口径、易混概念（对准自命题 AI 专业课与面试笔试）。
- 至少 2 处代码/公式围栏，至少 1 张表格或 ASCII 图。
- **禁止编造**：引用论文/教材必须真实存在；不确定的判断标「经验判断」。

## 3. examples 规则（本学科最容易写坏的部分）

10 个 `.py`，只允许 **Python 标准库 + numpy**，并且：

- **禁止联网、禁止 API Key、禁止读外部文件**。需要模型/工具的地方一律**本地模拟**
  （mock transport、规则打分、小型状态机），并在输出里说明「这是模拟，真实接入见第 X 章」。
- 固定随机种子，输出可复现；单个 < 10 秒；只打印文本（表格用字符画）。
- 每个示例必须以「结论 / 读法」行收尾，不能只有裸数字。
- 10 个示例要形成梯度：**概念验证 → 数值实验 → 失效边界 → 工程账本**。
- 不要求 10 个都是算法；允许 2-3 个是「工程计算器」（显存账本、成本模型、压测模拟）。

构建与验收（仓库根目录）：

```bash
PY=/c/Users/zyx/.workbuddy/binaries/python/envs/default/Scripts/python.exe
$PY server/scripts/build_examples.py --subject agent <chapter-id>
$PY server/scripts/verify_examples.py --subject agent --chapter <chapter-id>
```

`verify_examples.py` 必须显示「失败 0」。数值不稳就改参数，**不要手改 expected_output**。

## 4. exercises.json（照抄字段名）

```json
{
  "meta": {"chapter": "agent-chXX", "title": "…… —— 习题集", "count": 6,
           "note": "3 概念题 + 3 算法实践题，均为原创题干"},
  "items": [
    {"type": "choice", "category": "基础题", "platform": "self", "difficulty": 2,
     "title": "……", "content_md": "题干，A-D 各一行",
     "answer": {"correct": "A", "explain": "≥150 字，讲清对与错"},
     "explanation": "一句话考点", "tags": ["…"], "source": "self", "source_ref": "…"},
    {"type": "coding", "category": "算法题", "platform": "self", "difficulty": 4,
     "title": "……", "content_md": "编号任务",
     "answer": {"reference_code": "≤20 行关键代码", "explain": "≥150 字，含坑"},
     "explanation": "……", "tags": ["…"], "source": "self", "source_ref": "…"}
  ]
}
```

- 平台一律 `self`；3 道算法题必须彼此不同：一道手写核心逻辑、一道数值/边界验证、一道诊断/对比实验。
- 题干原创，**不得搬运 LeetCode/牛客题面**。

## 5. goals.md 结构

```
# <chapter-id> · <标题>
> 对应图片 DAY X · 先修：… · 面试权重：★★★★☆（一句说明）

## 本章目标（5 条，动词开头，可检验）
## 关键认知（本章最值钱的三句）
## 技术交付物（来自 manifest.tech_load，写清验收口径）
## 本章 GitHub 资源（star 由 GitHub API 实测，2026-10-21；≈ 表示千位近似）
## 本章 B 站学习清单（按 manifest.resources.bilibili_keywords，写「看什么 + 看完要能回答什么」）
## 与 ai 学科的分界（2-3 句）
```

GitHub 资源写法：`owner/repo — 12.3k★：看它的哪个目录/文件，解决本章哪个问题`。
star 取 `manifest.chapters[].resources.github_stars`，**不要自己写数字**；`github_approx[i]=true` 时加 `≈`。

B 站链接一律用 `manifest.resources.bilibili`（站内搜索），**禁止编造 BV 号**。

## 6. pitfalls.md：6 条，必须是 Agent 工程的真实故障

格式固定：

```
1. **一句话结论式标题**
   - 现象：……
   - 根因：……
   - 正确做法：……
```

反例（不要写）：「注意提示词要清晰」「要注意成本」。
正例：「流式响应里把 JSON 切断，解析成功率掉到 70%」——有现象、有根因、有修法。

## 7. interview.json：4 条

```json
{"meta": {"chapter": "agent-chXX", "title": "…… —— 面试深度追问", "count": 4},
 "items": [{"question": "……", "answer_md": "≥500 字，**要点** 分条，含数字或对比表",
            "follow_ups": ["…", "…", "…"], "difficulty": 3, "company_tags": ["字节跳动"]}]}
```

只收有区分度的题：不是「什么是 RAG」，而是「RAG 召回率 90% 但答案错，你先改哪一层」。

## 8. project.json：1 条

```json
{"meta": {"chapter": "agent-chXX", "title": "…… —— 综合项目", "count": 1},
 "items": [{"title": "……",
            "requirement_md": "编号 5-6 条要求，含验收口径与不做什么",
            "tasks": [{"title": "…", "verification": {"type": "output", "desc": "可核对判据"}}],
            "tags": ["…"]}]}
```

项目必须对应 `tech_load` 的交付物；`verification.type` 用 `output` 或 `accuracy`。

## 9. 禁止事项

- 不改 `content/agent/_manifest.json`、`_bagua.json`、其他章节、`content/ai/**`、前端。
- 不写第三方题面/正文；不编造 star、BV 号、论文标题。
- 不用「调用真实 API」当示例（无密钥、不可复现）。
- 不把 10 个示例写成同一个模板换参数。
