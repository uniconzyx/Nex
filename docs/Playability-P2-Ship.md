# 可玩性 P2 交付记录 · 中环

> 日期：2026-10-28
> 对应方案：`docs/Playability-Coherence-Plan.md`（§7 分期表 / §7.1 实施状态）
> 本轮范围：**S1 章节三关 + 掌握度 + 项目 `requires` + C2 依赖图 + C3 NextAction**
> 验收脚本：`scripts/verify_p2.mjs`（真 Edge，29/29）、`scripts/audit_graph.py`（AUDIT_OK）、
> `scripts/check_contrast.mjs`（8/8）、`scripts/verify_playability.mjs`（22/22 回归）

---

## 0. 一句话结论

P1 解决了"做了有没有记录"，P2 解决"**接下来该做哪一件**"。

| 之前 | 现在 |
|---|---|
| 章节只有「已掌握 / 未掌握」两态，靠手点 | 三关（概念 30 / 演练 30 / BOSS 40）自动判定，掌握度 0~100 连续 |
| 掌握度只升不降，做错也没感觉 | BOSS 关答错 → 掌握度回落 + 「失守」提示 + 该题变成怪物 |
| 首页推什么看固定顺序 | 五档优先级：每日 → 错题 → 当前关卡 → 可开工项目 → 下一章 |
| 项目「前置要求」是自由文本 | 110 个项目共 320 条结构化 `requires`，可算门槛 |
| 项目列表看不出能不能开工 | 「只看前置达标」筛选 + 卡片 `n/m` + 详情逐章掌握度 |
| 260 条八股只是文字 | 259 条绑定到具体章节，图鉴能回答"这条属于哪一章" |

---

## 1. S1 章节三关

### 1.1 关卡定义（`frontend/src/lib/stages.ts`，纯函数，无 React 依赖）

| 关 | 权重 | 题型池 | 通关条件 |
|---|---|---|---|
| 概念关 concept | 30 | `choice` / `explain` | 答对 1 道概念题；本章无概念题时退化为「任意 1 题」 |
| 演练关 drill | 30 | `coding` / `output` / `fix_error` / `design` | 答对 `min(3, 本章动手题数)` 道 |
| BOSS 关 boss | 40 | 本章难度最高档的**最后一题** | 答对首领题，且本章 `wild` 怪数量为 0 |

`bossQuestionOf(ch)` 取题规则：`hard → medium → easy` 逐档回退，同档取最后一个。
这样"BOSS"永远是本章最难的那道，且题目稳定（不随排序抖动）。

`chapterStages(ch, st)` 返回三张 `StageView`：`{ key, weight, done, blockers[], hint, cta }`。
UI 不需要知道判定规则，只渲染这个结构 —— 规则要改只改一处。

### 1.2 掌握度是派生值，不是存储值

这是 P2 最重要的一条不变量：

```ts
// progress.ts
function deriveRuns(s) {
  // 对每条 answers[qid] = { chapterId, ok, at } 用 chapterStages 重算三关
  // → chapterRuns 永远等于「按作答事实重新数一遍」的结果
}
```

- `answers` 是**事实**（谁在什么时候答对/答错了哪题），`chapterRuns` 是**投影**。
- 每次 `normalize()` 先跑 `deriveRuns`，再据 `masteryOf == 100` 推出 `doneChapters`。
- 因此"BOSS 答错 → 掌握度从 100 回落到 60"**不需要任何撤销代码**：BOSS 关的那道题在
  `answers` 里变成 `ok: false`，重算后该关自然不通过。
- 同理，重做收服后掌握度自己回到 100，`doneChapters` 也自己加回来。

反例（不要这么写）：直接 `chapterRuns[id].boss = true` 而不写 `answers`。
下一次 `normalize()` 会把它抹掉 —— 这不是 bug，是设计。

### 1.3 与 P1 的衔接

`applyAnswer` 现在是三件事的合流点：

```
作答 → ① 写 answers（事实）
      → ② 重算三关，对比前后（passed / lost）
      → ③ 首次三关全通发 +60 金币，并 toast
```

`lost` 的判定必须比较**重算前后**，不能只看"这题错了"——概念关答错但 BOSS 已过时，
掌握度只掉 30，不算"失守"。只有从 100 掉下来才发「BOSS 关失守」提示。

### 1.4 学习页重构（`pages/LearnPage.tsx`）

- **移除**「标记为已掌握」按钮。手点通关和三关判定不能并存，否则掌握度失去意义。
- 节点上三枚 pip 显示三关状态（空心 / 半亮 / 满亮），不展开也能看出卡在哪关。
- 展开后三张关卡卡：权重条、条件说明、阻塞原因（`blockers`）、CTA。
  - BOSS 卡 CTA 直接跳首领题（带 `chapterId`，题库自动定位）。
  - 概念 / 演练卡 CTA 进本章题库。
- 前置章节列出名字 + 当前掌握度百分比，未达 60 标红。
- 「重置本章」清该章 `answers` / `bestiary` / `runs` 并移出 `doneChapters` —— 用于自测和"我想重打一遍"。

---

## 2. C2 依赖图

### 2.1 生成（`scripts/gen_graph.py` → `frontend/src/data/graph.ts`）

产物四个表，共 17.5KB：

```
chapterDeps     141 章 / 149 条前置边
projectRequires 110 项目 / 320 条 requires 边
chapterSubject  章节 → 学科（agent / ml 归一到 ai）
chapterTitle    章节 → 标题（避免为了显示名字去遍历 BUNDLE）
```

**章节前置边**直接来自 manifest 的 `prerequisites`，不做推断 —— 作者写的就是事实。

**项目 requires 是推断的**，口径写在脚本头注释里：

1. 同科目内，项目标题 + summary 与章节标题做 **2-gram 词重合**；
2. 按 **IDF 加权**（"系统""设计"这类高频词权重自动降低）；
3. 标题命中的词 ×2（标题比摘要更能代表考点）；
4. 按 tier 限制数量与章号上限：t1 `2 章 / ≤8`、t2 `3 / ≤14`、t3 `3 / ≤20`、t4 `4 / ≤99`
   —— 入门项目不该要求第 18 章，硬核项目不该只要求第 2 章；
5. 无任何词重合时退化为「同科前 N 章」，保证每个项目都有前置（audit 强制 ≥1）。

抽样合理性（人工核对过）：

| 项目 | requires | 判断 |
|---|---|---|
| `cpp-googletest` | cpp-ch01, cpp-ch02 | 基础语法 + 函数，合理 |
| `cpp-muduo` | cpp-ch12, cpp-ch16, cpp-ch20 | 现代 C++ + 并发 + 综合，合理 |
| `mw-etcd` | mw-ch02, mw-ch03 | 持久化 + 高可用，合理 |
| `ai-vllm` | ml-ch05, agent-ch06, ai-ch08 | 推理部署 + 推理优化，合理 |

### 2.2 门槛取值

```ts
export const UNLOCK_MASTERY = 60;  // 概念 + 演练都过 = 60
```

**取 60 而不是 100 的理由**：60 = 概念关 + 演练关，代表"读懂了也会动手了"，
但还没打 BOSS。要求 100 等于逼用户把每个前置章节的 BOSS 都打掉才能开项目 ——
而 BOSS 是本章最难的一题，且一个项目平均要 2.91 章（最短 1、最长 4），
任一章卡在 BOSS 就整条锁死。

实测对比（按 `graph.ts` 真实数据算，前置章节掌握度都设成 60）：

| 场景 | 门槛 60 | 门槛 100 |
|---|---|---|
| cpp 前 8 章各 60 | 2 个项目可开 | 0 |
| 全 141 章各 60 | **110 / 110 全部可开** | **0** |

也就是说：门槛取 100 时，"概念 + 演练都过了但没打 BOSS"的用户连一个项目都开不了，
而这时他其实已经具备做项目的知识了。60 是"能力门槛"，100 是"完美门槛"——
推荐系统要用能力门槛。

**软门槛而非硬锁**：前置未满足仍可标记项目通关，但卡片显示 `n/m`，详情列出缺哪几章并可点击跳学。
理由见方案文档 §7.1 的两条取舍。

### 2.3 消费方

- `lib/graph.ts`：`projectGate` / `unlockedProjects` / `nextChapter` / `currentChapter` /
  `subjectMastery` / `masterySummary`（全项目平均掌握度）。
- **学习页**：前置百分比、未达标标色。
- **项目页**：`只看前置达标` 筛选、`cp-ready-tag` / `cp-lock-tag(n/m)`、详情「前置章节」段。
- **首页**：`todayProject` 优先取已解锁项目；Ring 显示 `masterySummary.avg`。
- **右栏 / 抽屉**：显示「平均 X%」，让"进度"从章数变成可感知的百分比。

---

## 3. C3 NextAction

`lib/nextAction.ts` 重写为**五档优先级**，任何时刻只返回 1 件事：

| 优先级 | 条件 | CTA |
|---|---|---|
| 1 | 今日试炼未清 | 「做今日 3 题」 |
| 2 | 有 `wild` 怪（错题未收服） | 「收服错题」 |
| 3 | **当前章有未过的关**（掌握度 1~99） | boss → 「打这一关的首领」；否则 → 「继续这一关」 |
| 4 | **有前置达标且未通关的项目** | 「开始项目」 |
| 5 | 有前置满足的下一章 | 「学下一章」 |
| 6 | 今日未签到 | 「签到」 |
| 7 | 兜底 | 「换个学科看看」 |

第 3 档是本轮新增的关键：它让首页第一次能说出"你卡在 BOSS 关"，
而不是笼统地推"下一章"。这也是验收标准「首页只推 1 件事且随状态变化」的核心。

`NextAction` 结构扩了 `questionId` / `chapterId`，首页大卡据此直接跳题或跳章。

---

## 4. 图鉴绑章（`frontend/scripts/gen_bagua_data.py`）

`BaguaItem` 新增 `chapterIds: string[]`（≤3 章），绑定规则：

1. 标签 → 章节标题/摘要的词面命中（`TAG_ALIAS` 处理 js→javascript 等别名）；
2. 题面 + 答案与章节标题/摘要做词重合加权；
3. 取分数最高的 ≤3 章。

结果 **259 / 260（99.6%）**。唯一未绑定：`database/sql/02`（CHAR vs VARCHAR，纯概念对比题，
本章语料里没有词面锚点）。**不硬凑**：UI 显示「暂无对应章节」，audit 允许 ≤5% 未绑定。

同时修了两个数据管道 bug：

- clang 单元被 `load_chapters()` 误归到 `ai` 学科，导致 20 条 clang 八股全部无锚点 → 路由到 `clang`；
- clang 单元无 `summary` 字段 → 从 `goals.md` 取首段（`_first_paragraph`）。

---

## 5. 内容可达性修复

审计时发现真实缺口：`ml-ch09`（SVM 与核方法）在 `content/` 和题库里都存在，
但**不在 `frontend/src/data/bundle.ts`** —— 用户点不到这一章，题也做不了。

新增 `scripts/sync_bundle_chapters.py`（幂等）：manifest 有、bundle 缺的章节补进对应合并后学科包，
`order` 取该包最大 +1，分组用 `GROUP_LABEL_OVERRIDE`（`('ai','C4') → '机器学习 · 核方法与收口'`）。
**只做加法，不动已有字段。**

结果：bundle 133 → **134 章** + clangUnits 7 单元 = **141 章**，与题库 141 章一一对齐（audit 强制）。

---

## 6. 视觉与无障碍

新增 P2 样式（`game.css`）：`.km-pip` / `.km-stages` / `.km-stage*` / `.km-mastery-*` /
`.km-dep-*` / `.cp-open-only` / `.cp-ready-tag` / `.cp-lock-tag` / `.cp-requires` / `.cp-mastery`，
全部带 `prefers-reduced-motion` 兜底。

对比度是这轮真正花时间的地方。新增的小字号文字（关卡提示、前置百分比、pip、`n/m` 角标）
在深浅两套主题下逐一测，首轮多项不达标：

| 元素 | 浅色 | 深色 | 修法 |
|---|---|---|---|
| pip | 2.74 | 1.80 | `--km-ink-faint` → `--km-ink-soft` |
| mastery-chip | 3.49 | 2.68 | `--km-accent-ink` → `--km-ink` |
| dep-bad | 3.46 | — | `--km-warn` → `--km-warn-ink`（新增文字版令牌） |
| cp-mastery | 2.94 | — | 同上 |

深色主题的 `--km-ink-soft` 逐档抬到 `#bcd0e2`。最终 8/8 全过，最差一处是深色 `.km-tag-gray` **4.83**（深色 pip 4.89）。

**令牌分层原则**：`--km-warn` 是给边框/底色用的（可以浅），`--km-warn-ink` 是给文字用的（必须深）。
混用是这类对比度问题最常见的来源。

---

## 7. 验收

### 7.1 自动化（真 Edge / Playwright）

```
node scripts/verify_p2.mjs            # 29/29 PASS
node scripts/verify_playability.mjs   # 22/22 PASS（P0/P1 回归）
node scripts/audit_graph.py           # AUDIT_OK（1 项提醒）
node scripts/check_contrast.mjs       # 8/8 PASS
```

`verify_p2.mjs` 覆盖的状态迁移：

| 预置进度 | 期望 | 验证点 |
|---|---|---|
| 空 | 首页推「推开新章」 | 无关卡残留、无误报 |
| 概念 + 演练已过 | 推「打这一关的首领」 | 掌握度 60、CTA 带首领 `questionId` |
| 三关全通 | 掌握度 100、三 pip 全亮 | 进 `doneChapters`、`chapterRuns` 写满 |
| 三关全通后 BOSS 答错 | 掌握度回 60 | 「失守」toast、移出 `doneChapters`、该题变 wild |
| 项目前置达标 / 未达标 | ready / lock(n/m) | 筛选生效、详情列出缺失章节 |
| 全程 | 无 JS 运行时错误 | 控制台零 error |

`audit_graph.py` 六项：无环（拓扑序覆盖 141/141）、无悬空边、每项目 ≥1 requires、
requires 全在本学科、项目覆盖 110/110、图鉴绑章 ≥95%、题库 141 章全有学习页入口。

### 7.2 构建与类型

```
npx tsc --noEmit -p frontend/tsconfig.json   # 0 error
npx vite build                               # OK
```

### 7.3 内容侧回归（确认玩法层没碰内容）

```
python server/scripts/validate_content.py
  章节总数 141 · 完成 141 · 覆盖率 100.0%
  三视角 519/519 = 100% · 八股 15/15 学科达标
```

141 章体系、三视角、来源、260 条八股**全部未受影响** —— P2 只读内容，不写内容。

---

## 8. 未做 / 下一步

- **P3 外环**：S4 周 Boss（门槛检查 + 称号）、C4 141 幕旁白、装扮碎片消费。
  旁白工作量最大（141 条 × 与 `goals.md` 一致的认知点），建议先做 20 条样板再批量。
- **`bagua.ts` 366KB 仍在主 chunk**：建议按路由懒加载（P1 就记录过，仍未做）。
- **`database/sql/02` 未绑章**：可接受（纯概念题无词面锚点），如要修需人工指定 `chapterIds`。
- **项目 requires 是推断值**：目前合理但未经用户验证。若用户反馈"这个前置不对"，
  在 `gen_graph.py` 加 `REQUIRES_OVERRIDE` 表，而不是手改 `graph.ts`（会被重新生成覆盖）。

---

## 9. 如何复跑

```bash
# 1) 起前端
cd frontend && npx vite --host 127.0.0.1 --port 1420
# 2) P2 验收
node ../scripts/verify_p2.mjs
# 3) 离线审计（不需要前端）
python ../scripts/audit_graph.py
python ../scripts/check_contrast.mjs      # 需要 1420 端口在跑
# 4) content 改动后重新生成
python ../scripts/gen_graph.py
python ../scripts/sync_bundle_chapters.py
python ../frontend/scripts/gen_bagua_data.py
```
