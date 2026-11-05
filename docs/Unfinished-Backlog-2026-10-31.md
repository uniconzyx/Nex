# CppMind 未完成事项清单（2026-10-31 快照）

> 数据来源：`server/scripts/validate_content.py`、`scripts/audit_sources.py`、`scripts/audit_depth.py` 三份守门脚本的**实跑输出**（非历史文档）。
> 结论先行：**结构与来源两条标准已 100% 达标**；剩余全部是「深度 / 路线颗粒度 / 新学科接线 / 工作区卫生」四类。

## 一、当前达标情况（实跑）

| 维度 | 结果 | 守门脚本 |
|---|---|---|
| 标准一 · 7 类内容齐备 | **165/165**（100%） | `validate_content.py` |
| 标准一 · 三视角齐全 | **165/165**（100%） | 同上 |
| 规划覆盖（manifest 分母） | 164/164（100%） | 同上 |
| 八股模块（学科级 `_bagua.json`） | **16/16**（本轮补齐 discrete-math） | 同上 |
| 标准二 · 来源完整 | **165/165**（本轮修复 fund-ch18 锚点） | `audit_sources.py` |
| 深度分级 A/B/C | **A8 / B71 / C86** | `audit_depth.py` |
| 路线颗粒度（章节专属 / 被复制） | **70 / 95** | `audit_sources.py` |

章节总数 165（16 学科）。其中 `discrete-math` 的 `dm-ch01` 已在磁盘但**尚未进入 manifest 与前端生成产物**（见 P2）。

---

## P0 · 工作区卫生：工作树远落后于 HEAD ✅ 已完成（2026-10-31）

- ✅ 分 6 个 commit 全部入库：`7b242f6` 脚本+文档（103）/ `7df42e4` 前端（112）/ `0e5de48` 后端（21）/ `d85e103` 内容（430）/ `db45043` Tauri+预览（68）/ `2526408` .gitignore。
- ✅ 工作区现 **0 未提交**；排除项（`_backup_*`、审计产物、scratch、`vite.config.ts.timestamp-*`、`src-tauri/gen`、`go-judge.exe`）已写入 `.gitignore`。
- ✅ 提交后复验：`validate_content` 规划 164/164、八股 16/16；`audit_sources` 来源 165/165；`tsc --noEmit` 0 error。

HEAD 仅跟踪 3707 个文件，但工作树里还有 **175 个已跟踪文件被改动**（`+16955 / −2516`）+ **355 个未跟踪文件**，合计约 530 处变更。未跟踪的不是零星文件，而是**整块核心目录**：

| 未跟踪 | 数量 | 性质 |
|---|---|---|
| `scripts/` | ~100 | 几乎所有审计/生成脚本（`audit_sources.py`、`audit_depth.py`、`gen_*.py`…）从未入库 |
| `frontend/src/` | 62 | 大量组件/页面未入库（仅 48 个被跟踪） |
| `content/` | ~98 | `ai-ch09/10`、`discrete-math/dm-ch01`、`_story/acts.json` 等新章与剧情源 |
| `src-tauri/` | ~20 | Tauri 壳层 |
| `docs/` | ~25 | 全部交付/审计文档 |
| `web-preview/` | 7 | 预览原型 |

**风险**：这批工作完全悬空——`git clean` 一次就没了，且换机/协作无法复现。这是当前第一优先。

**动作（分 4 个 commit，先 `git add` 明确路径）**：
1. `chore(repo): 纳入 scripts/ 审计与生成脚本 + docs/ 交付文档`
2. `feat(frontend): 纳入未入库的组件与页面`
3. `feat(content): ai-ch09/10 + discrete-math/dm-ch01 + _story + fundamentals 图示与习题更新`
4. `feat(tauri): 纳入 src-tauri 壳层`
- **不要提交**：`.scratch/`、`.taste-skill/`、`frontend/.scratch`、`server/.scratch`、`tmp/`、`content/_backup_*/`、`content/_depth_audit.*`、`content/_standards_audit.*`、`frontend/vite.config.ts.timestamp-*.mjs`、`*.log`、`dist*/`、`release/`（scratch/备份/可再生审计产物/构建产物）。
- 提交前跑：`validate_content.py` + `audit_sources.py` + `tsc --noEmit`。本清单已确认前两项通过、tsc **0 error**。

---

## P1 · 内容深度：52 章 C 级（最薄 7 章 + 仅缺代码块 27 章已补齐 ✅ 2026-10-31）

`audit_depth.py` 判为 C 级（讲解/推导/实现/陷阱密度不够）的章节，按学科分布（2026-10-31 复跑）：

| 学科 | C 级章数 | 学科 | C 级章数 |
|---|---|---|---|
| agent | 12 | ml | 6 |
| cpp | 9 | spring | 6 |
| ai | 9 | fundamentals | 5 |
| fullstack | 8 | bigdata | 4 |
| middleware | 6 | clang | 3 |
| java | 3 | tooling | 3 |
| database | 2 | python | 1 |
| data | 1 | discrete-math | 1 |

**已完成**：最薄的 7 章（`cpp-ch01~04`、`java-ch01`、`py-ch01`、`db-ch01`）已全量重写 concept 三篇 + 补齐 pitfalls，全部 C→B。实测指标：

| 章节 | chars | 代码块 | H3 | 陷阱 | 等级 |
|---|---|---|---|---|---|
| cpp-ch01 | 1616→5130 | 3→15 | 9→15 | 4→11 | C→B |
| cpp-ch02 | 1679→4955 | 4→16 | 9→11 | 5→12 | C→B |
| cpp-ch03 | 1545→4321 | 3→13 | 9→10 | 4→12 | C→B |
| cpp-ch04 | 1661→4519 | 3→20 | 9→11 | 5→12 | C→B |
| java-ch01 | 1414→4654 | 5→20 | 9→16 | 5→15 | C→B |
| py-ch01 | 1419→4557 | 3→27 | 9→14 | 6→17 | C→B |
| db-ch01 | 1548→5018 | 6→21 | 9→22 | 6→16 | C→B |

总盘：A 8 / B 71 / C 86 → **A 8 / B 78 / C 79** →（第二批）**A 8 / B 105 / C 52**。

**第二批已完成（27 章「仅缺 code_blocks」，C→B）**：

| 类别 | 章节 | 补法 |
|---|---|---|
| 各需 +4 | `cpp-ch18`、`data-ch06`、`tool-ch05` | 补齐到 5 个块（布局探针 / pandas 体检 / overlayfs 挂载等） |
| 各需 +2 | `fs-ch14`、`mw-ch06`、`py-ch02`、`spring-ch03` | 状态机、事务型生产者、闭包 cell、JDK 代理手写 |
| 各需 +1 | `ai-ch02/03/05/06/09/10`、`bd-ch03`、`cpp-ch20`、`fs-ch03/04`、`fund-ch07/08/09`、`ml-ch09`、`mw-ch07/08`、`spring-ch05/06`、`tool-ch04/06` | 统一补在各章第 2 篇 concept（原文里代码全挤在第 1 篇） |

补的代码都带可验证的**定量结论**（如流水线加速比 5 级 4.81、停顿 20% 掉到 2.72；GAN 饱和损失在 logit=-8 时梯度仅 -0.000335；RoPE 旋转保范），不写「运行后你会看到」这类空话。

**同批清理：26 个 project.json 的 `requirement_md` 缺 `###` 小节**（audit 硬性 FAIL）。做法是**原文一字不改**，只按语义重排为 `### 背景 / ### 功能要求 / ### 约束与边界 / ### 验收标准`。另把 `mw-ch07`、`mw-ch08` 的 `exercises.json` 从旧 schema（`stem_md`/`explanation_md`）统一到 `content_md`/`explanation`。

**下一批优先级（按性价比排序，非按字数）**——剩余 52 章的短板已高度集中：

| 短板类型 | 章数 | 修法 | 成本 |
|---|---|---|---|
| 仅 `h3`<10 | 23 | 拆 `###` 小节标题 | 极低 |
| `code_blocks`+`pitfalls` | 9 | 加代码块 + 补陷阱 | 中 |
| 仅 `pitfalls`<8 | 7 | 补陷阱条目 | 低 |
| `code_blocks`+`h3` | 6 | 两者都加 | 低 |
| 其余组合 | 7 | 逐项 | 中 |

> 注意：`ai-ch09`（14912 字）、`ai-ch10`（13808 字）、`tool-ch06`（12782 字）这些"厚章"也在 C 级——**它们的正文已经足够，只缺代码块数量**。按字数排序会严重误判优先级。

**修法（通用）**：补完必须过 `audit_correctness.py` + `check_md_outputs.py`（正文 ```text 块若上文 3 行含"输出/打印/终端"字样，会被要求对得上真实 stdout）。

---

## P1 · 审计可信度：已修复 ✅（2026-10-31）

原状态：`audit_correctness` 在 AI/ML/data 学科**根本跑不动**，门禁是半瞎的。对 27 章跑出 119 条问题，逐类查清后**没有一条是内容真错**，全是环境与数据形态问题。已全部闭环：

| 原问题 | 数量 | 根因 | 处置 |
|---|---|---|---|
| `运行失败(rc=1)` | 72 | `server/.venv` 没装 numpy，而 ai/ml/data 的 examples 全是 numpy 实现 | 装 numpy 2.5.4 / pandas 3.1.0 / bs4 / requests；固化为 `server/requirements-audit.txt` |
| `输出不一致` | 13 | 全在 `cpp-ch20`。**不是内容错**：`expected_output` 末尾是孤立 `\r`（CRLF 截断），与 stdout 的 `\n` 字节不等；逐行 diff 时 `\r` 不可见，看上去"两行一模一样" | 84 个 examples、890 处 `\r` 规整为 LF（仅改 `expected_output` 值内转义，文件行尾不动）→ 13 条全降为 warn，`AUDIT_OK` |
| 习题缺 `content_md` 等 | 8 条 × 4 类字段 | `data-ch06/exercises.json` 只有 `title` + `answer_md`，**没有题面、没有 answer**：前端题干空白、选择题无法判分 | 真写 8 条题面 + answer + explanation；3 段参考代码用 400 组随机用例对照暴力解验证 |
| 可疑字样 `error:`/`Error:` | 2 | `tool-ch04/ex08`（stash pop 被拒）、`tool-ch06/ex13`（端口占用）——**故意的反例教学**，报错文本来自 code 里的样例数据 | 改审计判据：若可疑串同时出现在 `code` 中，降级 warn 而非 FAIL |

**另外修掉的静默缺陷**：
- `data-ch06/ex05` 打印 `最大误差 = 2.04e-14`，换 numpy 版本变成 `7.11e-15`（语义相同、字节不等）→ 改成布尔判据 `能精确还原 = True`，输出跨版本确定。
- 审计脚本三处加固：① `ModuleNotFoundError` 不再伪装成"运行失败"，直接点名缺哪个包并指向 `requirements-audit.txt`；② `expected` 侧归一化补上孤立 `\r`，避免 CRLF 残留造成"看着一样却判不等"的假 FAIL；③ 反例教学白名单（见上表末行）。

**原遗留项已全部闭环（2026-11-01）**：

| 原遗留 | 规模 | 处置 | 结果 |
|---|---|---|---|
| `concept/*.md` 缺 ```` ```text ```` 图示块 | 403 / 605 文件 | ① 184 个本有无标识围栏（ASCII 图/公式/输出）只补 `text` 标签，正文零改动；② 219 个确无围栏，按章主题原创 ASCII 概念图并插入标题/引言后 | **605 / 605，0 缺失** |
| 旧 schema 习题（`stem_md`/`explanation_md`；`explanation` 误塞进 `answer` 内部；缺 `answer` 对象） | 全库 12+ 文件 | 一次性确定式迁移到 canonical 八字段；`choices` 只认 `{key,text}` 对象数组，`answer.correct` 为字母键 | 1165 题 **0 问题** |
| `interview.json` 字段 outlier（`q`/`level`，缺 `follow_ups`） | `ai-ch11` 5 条（全库唯一） | 对齐全库 canonical：`question`/`difficulty`/`company_tags`/`follow_ups` | 全库 786 条统一 |
| `answer.code` 非 Python（C/C++/Java）被当 Python 跑 → 假 FAIL | 4 条 | 审计改为按语言**真编译**：C/C++ 有 main 就跑到完、无 main 走 `-c`；Java 走 `javac`；仅无法识别的语言才告警 | FAIL 清零，且 4 段参考实现首次获得真实编译验证 |

**审计能力同时升级**（可信度不只是"少报错"，而是"多验证"）：
- 新增 **Java / JavaScript 实跑分支**（javac + `-Dstdout.encoding=UTF-8`；托管 node）→ 320 个原本「未支持语言，跳过实跑」的示例进入真实校验。
- 「仅末尾换行不同」（已按通过处理）与「未支持语言」从逐条 warn 改为 `[info]` 聚合计数，避免数百条噪声淹没真 FAIL。
- 新增 `--warn-out`：完整 warn 清单落盘。此前控制台只打印前 20 条，导致把 `798 条 warn` 误读成 `20 条`，进而误判"已清零"。

> 最终基线：`--all --skip-net` → **158 章 / 2016 检查项 / FAIL 0 / WARN 0**。

> 教训：**门禁报错先怀疑门禁自己。** 72 条"运行失败"里 0 条是内容问题，13 条"输出不一致"里 0 条是内容问题——如果不去查根因，就会花几天去"修"本来正确的示例。

---

## P1 · 路线颗粒度：95 章是「学科级复制」 ✅ 已结清（2026-11-04）

判据：同科目内多章 `github_notes` 读法文本完全相同 → 不算章节级路线。健康的那批（agent / clang / cpp / ml / discrete-math）已是章节专属。

**最终结果**：`audit_source_anchor.py` 锚点 604 条 **全部真实命中**（起点 370 命中 / 233 漂移 / 72 问题章），
`audit_sources.py` 章节 165 / 来源完整 165，`audit_depth.py` A165 / B0 / C0。

**已修的 95 章分布**（按批次提交，每批 2~3 学科验一次）：

| 学科 | 章数 | 提交 | 病因 |
|---|---|---|---|
| fundamentals | 11 | `d44920b` `b5d4790` | 学科级复制，且 82 个占位小节标题（`## 1. 背景/动机`）先改成真实标题 |
| cpp | 17 | `7b3d4de` | 内容成立，纯「编号—标题错位」+ 少量仓库错配 |
| fullstack | 14 | `3629768` | 有编号意识但关键词凭记忆；ch12~15 引用不存在小节 |
| data | 6 | `3daa22a` | 与 fundamentals 同构，6 章共用一套 4 仓库 + 同一模板 |
| bigdata | 6 | `696fa80` | 同 data，另需按仓库整列归位（`sql/` 路径曾挂在 hadoop 行） |
| agent / ml | 6 | `1cf35c5` | 零散锚点措辞漂移（引用该章不存在的小节） |

**锚点判据的两个隐藏性质**（写锚点前必读，否则会反复返工）：
- `overlap()` 的分母是**锚点自身**的二元组数 → 锚点写得越描述性，重合率**越低**。
- 唯一稳妥的写法是**尽量短地忠实复制小节标题原文**（如 `§4.2 二、实现机制`，而非改写成「CORS 预检的报文往来」）。

**守卫**：`audit_source_anchor.py` 已并入 CONTRIBUTING 第 8 节提交前校验，非零退出即阻断。

**修法（模板已在 clang 验证 7/7）**：
- 在 `scripts/attach_all_sources.py` 的 `NOTES_OVERRIDE`（或 `_cpp_sources.py` 的 `CPP_NOTES`）里按 `"章id|owner/repo"` 写「`§x.y` + 入口文件 + 函数名 + 它在本章证明什么」。
- `§` 编号规则：篇号=concept 文件序号，节号=文件内 `##` 序号。
- 无明确知识点的章（如 cpp-ch01/03/04）如实标「全章」，不假装精确。
- 改完跑 `audit_sources.py`，看「章节专属章」数上涨、被复制数下降。

**完成（2026-11-05）**：仓库-笔记错位检查已提升为 `scripts/audit_repo_align.py` 并写入 CONTRIBUTING 第 8 节门禁清单（接在 `audit_source_anchor.py` 之后）。判据为「github_notes 代码路径须命中本章已登记仓库前缀」，宁松勿严：只认真实代码路径（带扩展名或 ≥2 级目录且含小写）、逐位配对、未登记仓库不判、正文点名仓库即视为对齐、不强制 github 与 github_notes 等长。全仓跑通 0 条错位，且正向测试能拦出 `sql/catalyst`（spark 路径）误挂 hadoop 行。旧 `.scratch/check_repo_align.py` 已删除。

---

## P2 · discrete-math 学科收尾（dm-ch01/dm-ch02/dm-ch03 全部接入，学科正式上线 ✅）

进度：
- `dm-ch01`（命题逻辑）：已于 `bf99831` 建 `_manifest.json` 正式接入，`validate_content` 165→166、锚点 609/609、tsc 0 全绿。
- `dm-ch02`（集合/关系/函数）：已于 `3802fbb` 从零建齐七类内容并接入。覆盖 166/166、锚点 10/10、tsc 0；深度审计 `code=12/pit=15/h3=29` 均 A，仅 `concept_chars=3529` 为 B（该章 3 个 concept 文件，A 线 6000 按典型 5 文件章校准，结构使然，非缺陷）。
- `dm-ch03`（图论）：已于本轮从零建齐七类内容并接入（commit 见下方）。覆盖 167/167、锚点 15/15（含本组 5 条）、tsc 0；深度审计 `code=9/pit=15/h3=27/examples=100%/types=4` 均 A，仅 `concept_chars=3774` 为 B（同 dm-ch02 的结构性原因，3 个 concept 文件）。

**P2 已结清**：discrete-math 三章全部进入 manifest + 前端生成产物，守门全绿。`audit_depth` 现状 **A165 / B2（dm-ch02、dm-ch03）/ C0**，无 C 级章节，所有硬门禁通过。

复盘要点：dm-ch03 的 example 生成脚本最初 `ROOT` 多算一层 `dirname`（把文件误写到 CppMind 的父目录），导致 `validate_content` 报 `examples:0`；修正为 `dirname×2` 并重跑后落盘正确。此坑已记工作记忆，后续 `gen_*_examples.py` 的 ROOT 一律用 `dirname(dirname(abspath(__file__)))`。

---

## P3 · 双后端收尾（非阻断）✅ 已收尾（2026-11-05）

- `server/scripts/verify_nex_parity_pg.py`（真 PG 5 项验收）**已接入 CI**：新增 `.github/workflows/ci.yml` 的 `backend-parity` job，在 `postgres:18` service container 上跑真 PG 端到端验收（迁移 ADD jsonb / 昵称校验 / 整份快照往返 / 非对象 400 / legacy 5 字段回退）。
- 脚本已改造为 **CI 友好**：`PGDATA` 可用 `EMBEDDED_PG_PGDATA` 覆盖（默认仍为本机 Windows 路径），且若外部注入 `DATABASE_URL` 则跳过 embedded-postgres、直接用注入的真 PG（CI 不装 embedded 也能跑）；`embedded_postgres` 改为按需导入，`server.cleanup()` 也加了存在性保护。本地 embedded 路径已复跑验证：5 项全过、`PG_PARITY_OK`。
- 前端**构建 + dev server 冒烟**已接入同一 workflow 的 `frontend-smoke` job：`npm ci` → `npm run build`（tsc --noEmit + vite build）→ 起 `vite dev`（:1420）轮询 HTTP 200 并校验入口挂载点，跑完 kill。**说明**：workflow 只在 GitHub 上执行，本沙箱无法实跑，已按仓库真实工具链（`requirements.txt`、`package-lock.json`、vite 端口 1420）对齐；push 后需以首次 CI 结果为准。
- 说明：`nex` 与 `auth-server` 两套令牌互不通用，切后端先清令牌已实现，属于已知设计而非缺陷。前端"真登录网关"的全栈集成冒烟需活的后端 + 凭据，未纳入自动 job（避免不稳定），留作后续可选（Playwright + 双服务）。

---

## 本轮已闭环（2026-10-31）

- ✅ `fund-ch18` 来源锚点：`§连通性` 等自由文本 → 规则要求的 `§1.2 / §2.2 / §3.2` 小节号。来源完整 164→**165/165**。
- ✅ `discrete-math/_bagua.json` 新建（4 领域 / 16 条目：命题逻辑、谓词逻辑、集合与关系、图论）。八股模块 15→**16/16**。

---

## 建议推进顺序

1. ~~**P0 提交**~~ ✅ 已完成（7 个 commit，工作区清零）。
2. ~~**P1 深度·最薄 7 章**~~ ✅ 已完成（全部 C→B，`audit_correctness` 对新改章节 `AUDIT_OK`）。
3. ~~**P1 深度·仅缺 `code_blocks` 的 27 章**~~ ✅ 已完成（C 86→52；同批把 26 个 project.json 的 `requirement_md` 补成 `###` 四小节）。
4. ~~**P1 审计可信度**~~ ✅ 已完成（装 numpy/pandas 让 ai/ml/data 真跑；84 个 examples 的 CRLF 污染清零；`data-ch06` 8 条题面真写；审计脚本三处加固）。**这一步做完，「内容正确性通过」才第一次有意义。**
5. **P1 深度·仅缺 `h3` 的 23 章**：拆 `###` 小节标题即可，成本最低。
6. **P1 路线** ✅ 已结清：95 章全部改成章节级路线（604 条锚点 100% 命中，`audit_source_anchor.py` 已入守门）。
7. **P2 discrete-math**：补 dm-ch02/03 并接线（决定这个学科是否正式上线）。
8. ~~**P1 残余 schema**~~ ✅ 已完成（2026-10-31）：`data-ch05`、`py-ch04~py-ch08`、`mw-ch02`、`mw-ch03`、`cpp-ch12` 全部迁到 canonical 八字段；顺带全库扫描修掉 14 处嵌套 `explanation`，1165 题 0 问题。
9. ~~**图示例题库**~~ ✅ 已完成（2026-11-01）：605 个 concept 文件 ```` ```text ```` 覆盖 100%；14 个跨章仓库 star 归一化 + 77 个刷新为 GitHub API 实时值。
10. **下一步候选**：P1 深度·仅缺 `h3` 的 23 章 / P1 路线颗粒度 95 章 / P2 discrete-math 接线。
