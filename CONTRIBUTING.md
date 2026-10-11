# 贡献指南（Nex）

感谢参与 Nex 多学科学习内容的建设。本仓库内容由**脚本化门禁**保障质量，提交前请确保通过
`server/scripts/` 下的校验工具。以下规则为**硬性约束**，违反会被 CI / 门禁拦截。

## 1. 学科与章节结构

- 13 个学科目录：`content/<subject>/`，其中 `subject ∈`
  `cpp, clang, java, python, database, fullstack, spring, middleware, bigdata,
  fundamentals, tooling, data, ai`。
- 章节目录：`content/<subject>/<id>/`，其中 C/C++/clang 用 `cpp-chNN` / `clang-uNN`，
  其余用 `<subject>-chNN`。
- `clang` 的元数据挂在 `content/cpp/_manifest.json` 的 `clang_module.units[]`，**无独立 manifest**。
- 母清单：`content/cpp/_manifest.json`（含 `clang_module.units`）。其余学科各有
  `<subject>_manifest.json`。门禁以 manifest 的 `chapters[]` 作为"规划单元"分母。

## 2. 每章 7 类文件（缺一不可）

```
content/<subject>/<id>/
├── goals.md            # 学习目标 + 软前置 + 【GitHub 资源】+【B 站教程】双来源段
├── concept/*.md        # ≥3 个概念文件，每个内嵌三视角
├── pitfalls.md         # ≥3 条（行首必须是编号 1. / - ）
├── exercises.json      # ≥5 道（choice / fix_error / output / coding 混合）
├── examples/*.json     # ≥10 条，字段见下
├── interview.json      # ≥3 条面试题
└── project.json        # ≥1 个项目任务
```

规范详见 `content/_template/README.md`。

### examples/*.json 字段
`code_lang` / `code_std` / `stdin` / `expected_output` / `code` 必填；`expected_output`
必须是**真实编译器/解释器实测产物，禁止编造**。

### exercises.json 真题字段
```json
{
  "source": "self | leetcode | nowcoder",
  "source_ref": "LC-1 / NC-101",
  "external_url": "https://leetcode.cn/problems/two-sum/"
}
```
`source_ref` 与 `external_url` **必须写在题项顶层**（写在 `answer` 里会被门禁判缺失）。

## 3. 三视角（每个 concept/*.md 必含）

每个概念文件必须内嵌三段，三者**互补不重复**：

- `### 🧑‍💻 程序员视角`：工程决策树与排查顺序。
- `### 🎓 博士生视角`：第一性原理与形式化依据。
- `### 📚 考研者视角`：408 考点记忆锚点。

> **标记码点必须带零宽连接符（ZWJ）**：程序员 `🧑‍💻` = `\U0001F9D1\u200D\U0001F4BB`，
> 博士生 `🎓`、考研者 `📚` 同理。脚本里一律用**显式码点构造**，不要手打 emoji
> （不带 ZWJ 的变体渲染几乎一样但字节不同，会长期掩盖"三视角缺失"）。
> 新章节一次写到位，勿事后 retrofit。

## 4. 学习来源：GitHub（star 最高）+ B 站 双来源（强制）

**每章 `goals.md` 必须同时包含 GitHub 真实代码源与 B 站真实教程源两段。**

- **GitHub 资源**：所有 `resources` 必须指向 GitHub **star 最高**仓库，star 用 API 实时抓取，
  刷新用 `server/scripts/sync_github_resources.py`（幂等）。**勿手写 star、勿凭记忆填 repo**。
- **B 站教程**：每条必须是真实 UP 主 + 真实 BV 号 / 视频链接（不要用占位链接）。
- `goals.md` 注入锚点：优先插在 `## 软前置` / `## 学习路径建议` / `## 学习路径` 之前，否则追加文件尾。

门禁会扫描每章 `goals.md` 是否含「GitHub 资源」与「bilibili / B站」两段。

## 5. 学习线独立性与三元服务

- 每学科「独立且完整」，同时服务**考研 / 学习 / 就业**三类用户。
- 首章 `prerequisites` **必须为空**；跨学科先修只写 `soft_prerequisites`
  （如 `[{"id":"py-ch01","note":"若已掌握可跳过"}]`），并在 `goals.md` 加
  「## 软前置（可选，不阻断学习）」。`prerequisites` 只引用本线章节。
- 考研 = 三视角 + 八股 ≥10；学习 = goals/concept/pitfalls/examples 齐全；
  就业 = 八股 + interview ≥3 + project ≥1 + GitHub 资源。

## 6. 合规红线

- **LeetCode / 牛客：只存元数据 + 链接，不存题面正文**（`source` / `source_ref` / `external_url`）。
- 示例禁止机器相关量进 `expected_output`：墙钟时间、纳秒耗时、内存地址。性能类改用操作计数 /
  指针跳转次数 / 布尔判据（如 `加速比>100: True`）。
- Python 示例禁用 `hash(str)`（PYTHONHASHSEED 随机化）→ 用 `zlib.crc32`。
- C 示例禁止把「有副作用的调用」与「它写入的变量」放进同一 `printf` 参数列表
  （求值顺序未定义 → 假通过）。先算后打印。
- 含 `timeit` 的示例只输出布尔判据，绝不写具体毫秒。

## 7. 密钥与本地环境安全

- `server/.env` 含 `DEEPSEEK_API_KEY` 等敏感信息，**已被 `.gitignore` 排除，绝不提交**。
- 贡献者请复制 `server/.env.example` 为 `server/.env` 并填入自己的密钥。
- CI / 发布构建通过 GitHub Secrets 注入，不在仓库内留明文密钥。
- `scratch/`、`build/`、`dist/`、发布二进制（`*.exe` / `*.apk`）均在 `.gitignore` 中。

## 8. 提交流程

```bash
# 1) 校验（必须全绿）
python server/scripts/validate_content.py      # 门禁
python server/scripts/verify_examples.py       # 示例真实回放
python server/scripts/verify_exercises.py      # 题集健康度
python server/scripts/audit_learning_lines.py  # 学习线审计（可选）

# 2) 刷新 GitHub star（如改动 resources）
python server/scripts/sync_github_resources.py

# 3) 更新 manifest 状态
python server/scripts/sync_manifest_status.py
python server/scripts/sync_dart_manifest.py    # 同步前端 content_manifest.dart

# 4) 提交（不要提交 .env / 大二进制）
git add content/<subject>/<id> ...
git commit -m "content(<subject>): 新增 <id> 三视角 + 双来源"
```

> 凡要经 Bash 执行的生成脚本，请先 `Write` 落 `.py` 再执行（避免反引号命令替换吞掉内容）。
> 跑完务必人眼核对关键数字，不能只看退出码 0。
