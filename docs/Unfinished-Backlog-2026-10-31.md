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

## P0 · 工作区卫生：工作树远落后于 HEAD（必须先处理）

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

## P1 · 内容深度：86 章 C 级偏薄

`audit_depth.py --min-grade C` 判为 C 级（讲解/推导/实现/陷阱密度不够）的 86 章，按学科分布：

| 学科 | C 级章数 | 学科 | C 级章数 |
|---|---|---|---|
| cpp | 13 | ml | 6 |
| agent | 12 | spring | 6 |
| ai | 9 | middleware | 6 |
| fullstack | 8 | fundamentals | 5 |
| bigdata | 4 | java | 4 |
| clang | 3 | database | 3 |
| tooling | 3 | python | 2 |
| data | 1 | discrete-math | 1 |

**最薄的 7 章**（字数 < 1700，先补这批性价比最高）：
`java-ch01`、`py-ch01`、`cpp-ch03`、`db-ch01`、`cpp-ch01`、`cpp-ch04`、`cpp-ch02`。短板集中在 `concept_chars / code_blocks / h3 / pitfalls`。

**修法**：给 concept 补可运行代码块 + 拆 H3 小节 + 补陷阱；补完必须过 `audit_correctness.py`（重编译重跑示例）与 `check_md_outputs.py`（正文输出必须对得上真实 stdout）。

---

## P1 · 路线颗粒度：95 章是「学科级复制」

判据：同科目内多章 `github_notes` 读法文本完全相同 → 不算章节级路线。健康的那批（agent / clang / cpp / ml / discrete-math）已是章节专属。

**待改 95 章分布**：

| 学科 | 被复制 | 学科 | 被复制 |
|---|---|---|---|
| fullstack | 13 | java | 9 |
| fundamentals | 12 | middleware | 8 |
| ai | 11 | python | 8 |
| database | 8 | spring | 8 |
| bigdata | 6 | tooling | 6 |
| data | 6 | | |

**修法（模板已在 clang 验证 7/7）**：
- 在 `scripts/attach_all_sources.py` 的 `NOTES_OVERRIDE`（或 `_cpp_sources.py` 的 `CPP_NOTES`）里按 `"章id|owner/repo"` 写「`§x.y` + 入口文件 + 函数名 + 它在本章证明什么」。
- `§` 编号规则：篇号=concept 文件序号，节号=文件内 `##` 序号。
- 无明确知识点的章（如 cpp-ch01/03/04）如实标「全章」，不假装精确。
- 改完跑 `audit_sources.py`，看「章节专属章」数上涨、被复制数下降。

---

## P2 · discrete-math 学科收尾（当前只有 1 章，未接线）

现状：`content/discrete-math/dm-ch01` 已完整（且本轮补了 `_bagua.json`），但：
- 缺 `content/discrete-math/_manifest.json` → 未进规划分母、未进前端。
- `dm-ch01` 正文预告的 `dm-ch02`（集合/关系/函数）、`dm-ch03`（图论）**尚未创建**。
- 前端 `graph.ts / exercises.ts / story.ts` 里搜不到 `dm-ch01` → 用户看不到。

**动作**：
1. 建 `dm-ch02`、`dm-ch03`（按标准一七类内容 + 标准二来源）。
2. 写 `content/discrete-math/_manifest.json`（照 `data/_manifest.json` 结构）。
3. 跑注册链路：`sync_bundle_chapters.py --write` → `gen_chapter_content.py` → `gen_tracks.py` → `gen_graph.py` → `gen_exercise_bundle.py`。
4. 复跑 `validate_content.py`（规划分母应变 166+）与 `tsc`。

---

## P3 · 双后端收尾（非阻断）

- `server/scripts/verify_nex_parity_pg.py`（真 PG 5 项验收）**尚未接入 CI**，目前靠手动跑。
- 前端 dev server 长驻验证（`vite dev` + 真登录网关）未做常驻冒烟。
- 说明：`nex` 与 `auth-server` 两套令牌互不通用，切后端先清令牌已实现，属于已知设计而非缺陷。

---

## 本轮已闭环（2026-10-31）

- ✅ `fund-ch18` 来源锚点：`§连通性` 等自由文本 → 规则要求的 `§1.2 / §2.2 / §3.2` 小节号。来源完整 164→**165/165**。
- ✅ `discrete-math/_bagua.json` 新建（4 领域 / 16 条目：命题逻辑、谓词逻辑、集合与关系、图论）。八股模块 15→**16/16**。

---

## 建议推进顺序

1. **P0 提交**（按上面的 4 个 commit 分批把未入库目录纳入版本控制，先消除丢失风险）。
2. **P1 深度**：先补最薄的 7 章（<1700 字），一批一批过 `audit_correctness`。
3. **P1 路线**：按学科逐个把 95 章改成章节级路线（fullstack 13 + fundamentals 12 + ai 11 最大块）。
4. **P2 discrete-math**：补 dm-ch02/03 并接线（决定这个学科是否正式上线）。
