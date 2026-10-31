# 可玩性 P0 / P1 交付记录

> 日期：2026-10-28
> 对应方案：`docs/Playability-Coherence-Plan.md`（§7 分期表）
> 本轮范围：**P0 数据打底 + P1 内环闭环**，并补齐过渡动画、素材与即时反馈
> 验收脚本：`scripts/verify_playability.mjs`（真 Edge，22/22 通过）

---

## 0. 一句话结论

这轮没有加"新内容"，只把**已经存在但没被记录**的东西接上了线：

| 之前 | 现在 |
|---|---|
| 判题结果只活在会话内，刷新即失 | 每次判定写入 `bestiary`，刷新不丢 |
| 图鉴页自述"所以图鉴是空的" | 图鉴按真实错题渲染：稀有度、HP、收服时间 |
| 260 条八股没有任何入口 | 图鉴「情报」按 tags 命中 + 「八股情报库」全量可读 |
| 金币只增不减、无来源 | 每笔进出都进 `coinLedger`，余额不可为负 |
| 首页「今日试炼」硬编码推荐 GoogleTest | 每天 3 道真题：错题 2 道 + 新题 1 道 |

---

## 1. P0 数据打底

### 1.1 进度模型 v2

`frontend/src/lib/progress.ts` 存储键从 `kaimao.progress.v1` 升到 `kaimao.progress.v2`，新增四张表：

```ts
interface ProgressState {
  // v1 保留：theme / outfit / doneProjects / doneChapters / checkins / coins
  coinLedger: CoinEntry[];                    // 最近 50 笔，最新在前
  bestiary: Record<string, Monster>;          // key = questionId
  chapterRuns: Record<string, ChapterRun>;    // 三关 + attempts（P2 用）
  daily: DailyRun | null;                     // 今日题单
  shards: number;                             // 装扮碎片占位（避免二次迁移）
}
```

**迁移（只做加法）**

- 首次读取时从 v1 迁移，并把原始字符串原样备份到 `kaimao.progress.v1.backup`；
- `doneChapters` 里已有的章节直接补成三关全通（mastery=100），一个不丢；
- 反过来，三关全通的章节也回到 `doneChapters`（`normalize()` 保证双向不变量）；
- 逐字段 sanitize：脏数组 / 脏 map / 负数币 / 坏 JSON 都回默认，不白屏。

### 1.2 单一事件流

```ts
type ProgressEvent =
  | { type: 'answer'; questionId; chapterId?; subject?; title?; diff?; qtype?; ok; mode? }
  | { type: 'stage'; chapterId; stage: 'concept'|'drill'|'boss'; ok }
  | { type: 'project'; slug; ok }
  | { type: 'checkin'; date }
  | { type: 'daily'; questionId; ok }
  | { type: 'dailyReset'; run }
  | { type: 'chapter'; chapterId; ok }
  | { type: 'coin'; delta; reason }
```

`dispatch(event)` 是**唯一写入口**：页面不再直接改字段，reducer 负责派生状态、记账、发反馈。
v1 的 `toggleChapter / toggleProject / checkinToday` 保留为薄封装，老页面零改动。

新增文件：`lib/gameTypes.ts`（纯类型 + 稀有度 + 掌握度）、`lib/feedback.ts`（toast/遭遇/金币脉冲）。

---

## 2. P1 内环闭环

### 2.1 S2 错题即怪物

| 规则 | 实现 |
|---|---|
| 答错 → 生成 `wild` 怪物，HP = 累计失败次数 | `applyAnswer` |
| 同题再错 → HP+1，失败 3 次起变「变异」（独立配色 + 旋转虚线环） | `rarityOf(diff, fails)` |
| 重做通过 → `tamed`，奖励 `稀有度基础币 + 失败次数×2` | 普通 6 / 精英 12 / 首领 24 / 变异 36 |
| 一次就答对 → 不产生怪物，给 4 结晶 | 避免图鉴被"没做错"的题污染 |
| 重复提交同一份答案 → 只重放判定，不再记一次失败 | `ExerciseBank` 的 `lastSig` |

双入口接入：

- `components/ExerciseBank.tsx`：选择题按集合比对、看码写输出按归一化比对，**提交时**记账；「标记已完成」= 自评通过（`mode: 'self'`）。
- `components/JudgePanel.tsx`：全部用例 AC 才记 ok；**只有存在内置用例时才记**——没有用例的「自由运行」无从判对错，不能凭空给图鉴塞怪物。

### 2.2 S3 每日试炼

`lib/daily.ts`：

1. `wild` 中 `fails` 最高的 2 道（错题优先复习）；
2. 当前学科一道没做过的新题（`dayIndex % pool.length`，同一天恒定、每天不同）；
3. 不足 3 题：剩余错题 → **未出现过的章节**优先 → 任意题。

跨日自动重建；3/3 清空 +50，全对再 +20，`claimed` 防重复领。

### 2.3 S5 金币流水

| 收入 | 数额 | 说明 |
|---|---|---|
| 收服怪物 | 6~36 + 失败次数×2 | 与难度挂钩 |
| 首次答对 | +4 | 即时正反馈 |
| 每日清空 | +50（全对 +70） | |
| 章节掌握 | +20 | |
| 项目通关 | +30 | |
| 签到 | 20 + min(连击,6)×5 | 文案已同步 |

支出通道位已留（`spendCoins`，余额不足直接拒绝并提示差额），P3 抽装扮/买提示直接复用。

### 2.4 图鉴页与 260 条八股

- `frontend/scripts/gen_bagua_data.py` → `frontend/src/data/bagua.ts`（15 文件 / **260 条**）。
  `agent`、`ml` 两科按 `merge_agent_ml_into_ai.py` 的口径归一到 `ai`（61 条），原科名存 `rawSubject` 可溯源。
- `<学科>/_bagua.json` 字段 → `BaguaItem`（id / subject / category / q / a / tags / difficulty / hot / src）。
- 图鉴「情报」匹配规则可解释：同学科优先 → tags 双向包含 +2 → 热度排序；
  **匹配不到不硬凑**：退回同学科最热 2 条并标注「本题无直接命中」。
- 「八股情报库」Tab：按学科分组、分类折叠，260 条全部可读。

---

## 3. 动画、素材与即时反馈

原则：**只给"状态真的变了"的动作做动效**，不做无意义背景动效。

| 状态变化 | 反馈 |
|---|---|
| 首次答错（新怪物） | 全屏遭遇卡：怪物抖动着出现 + 金色粒子 + 「去收服 / 稍后再说」；Esc 可关 |
| 再错 | toast「怪物强化 ×N」，第 3 次变「变异了」 |
| 收服 | 紫色 toast「收服 · 稀有度」+ 金币飘字；图鉴卡片 0.9s 金色爆发 + 精灵变眯眼笑脸 |
| 金币变动 | 顶栏数字上方 `+N / −N` 上浮，全局任何入口都生效 |
| 切页 | `.km-page` 淡入 + 卡片错峰入场（40~220ms 递进） |
| 展开图鉴 | 卡片 3px 上浮 + 阴影；详情面板 0.24s 滑入 |

**素材**：`components/MonsterSprite.tsx` 用 `questionId` 哈希生成参数（体型、眼距、角数、倾斜角），
每道题有稳定且互不相同的形象；稀有度直接映射角数与配色。
不引入图片资源——避免"同一张图配不同题"的错位感，也不给安装包加体积。

**无障碍**：`prefers-reduced-motion: reduce` 下关闭全部动画与过渡。

---

## 4. 验收

### 4.1 自动化（真 Edge / Playwright）

```
node scripts/verify_playability.mjs      # 22/22 PASS
```

覆盖：清空进度 → 答错 → 遭遇弹窗 → 图鉴出现 → 详情八股 → 去收服带题 → 重做答对 →
收服 toast → 已收服列表 → 背包流水 → **刷新不丢** → 八股情报库可读 → 无 JS 运行时报错。

迁移专项：v1（2 章 / 999 币 / 1 项目 / cape）→ v2，章节不丢、掌握度补 100、备份存在、流水不伪造。

### 4.2 构建与类型

```
npx tsc --noEmit -p frontend/tsconfig.json   # 0 error
npx vite build                               # OK（CSS 93.6KB / JS 1.46MB gzip 763KB）
```

### 4.3 内容侧回归（确认没被玩法层碰到）

```
server/scripts/validate_content.py
  章节 141/141 · 三视角 519/519 = 100% · 八股 15/15 学科达标
```

---

## 5. 未做 / 下一步

- **P2 中环**：章节三关判定（`chapterRuns` 结构已就位，`dispatch({type:'stage'})` 已可用）、
  项目 `requires` + 图鉴 `chapterIds`、`audit_graph.py`。
- **P3 外环**：周 Boss、141 幕旁白、装扮碎片消费。
- **离线判题**：判题链路仍需后端（8000）+ judge_local（2358）+ arq worker；本轮把结果落库改成
  纯本地，后端只做同步，所以离线时玩法闭环仍然成立。
- **首屏体积**：`bagua.ts` 366KB 进了主 chunk。后续可按路由懒加载（图鉴页才需要）。

---

## 6. 如何复跑

```bash
# 1) 起前端（后端未起也可验，离线模式）
cd frontend && npx vite --host 127.0.0.1 --port 1420
# 2) 玩法验收
node ../scripts/verify_playability.mjs
# 3) 重新生成图鉴数据（content 改动后）
python frontend/scripts/gen_bagua_data.py
```
