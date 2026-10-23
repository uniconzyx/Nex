# Phase 15 · 题库打通判题台

> 日期：2026-10-21
> 范围：`content/*/*/exercises.json` → 前端题库 → 判题台
> 关键结论：**818 道题第一次真正进了安装包**，从「坐在 content 里没人能看见」变成「学习页能看到章内题、题库能筛能做、能判的能一键送进判题台」。

---

## 1. 断点在哪

上一阶段的判题台是好的（桌面 go-judge、移动 Pyodide 全链路实测通过），但它是个**孤立入口**：

| 环节 | 状态 |
| --- | --- |
| `content/` 里有 818 道题 | 有 |
| 后端 `/api/v1/exercises` 能读 | 有，但需要 PostgreSQL |
| exe / apk 里能读到题 | **没有** —— `bundle.ts` 只打包 projects / chapters / guides |
| 前端有做题界面 | **没有** —— `PracticePage` 只有一个空白判题台 |
| 学习页能进入本章题 | **没有** |

exe 和 apk 是离线单机，不能指望数据库。所以题库必须像 bundle 一样**编进前端产物**。

---

## 2. 生成链路

```
content/<subject>/<chapter>/exercises.json   818 题 / 13 学科
        │
        │  server/scripts/gen_exercise_bundle.py
        ▼
frontend/src/data/exercises.ts               898 KB（EXERCISES）
frontend/src/data/clangUnits.ts              7 个 C 语言单元（CLANG_CHAPTERS）
```

重新生成：

```bash
python server/scripts/gen_exercise_bundle.py          # 写文件
python server/scripts/gen_exercise_bundle.py --check   # 只统计
python server/scripts/gen_exercise_bundle.py --json    # 机器可读
```

> `bundle.ts` 头部注释写的 `scripts/gen_bundle_data.py` **已不存在**，那条链路是断的。
> 这个脚本只负责题库与 C 语言单元，不重建 bundle.ts。

### 2.1 为什么必须归一化 `answer`

818 道题的 `answer` 有 **20 多种键组合**：

```
choice    → correct: ["B"] / correct: "A" / choice: "C" / value: "C" / index: 0
output    → output / expected_output / stdout / value / correct
coding    → reference_code / code / correct(文本) / text / reference
fix_error → reference_code / code / correct / explain / explanation / fix_explanation_md
```

如果让 UI 自己判断，每加一种形态就要改一次前端，必然出漏。生成时一次性收敛成 7 个字段：

| 产物字段 | 来源（按优先级） |
| --- | --- |
| `correct` | `answer.correct` → `answer.choice` → `answer.value`（单字母）→ `answer.index`（转字母） |
| `expect` | `answer.output` → `answer.expected_output` → `answer.stdout` → `answer.value`（长文本） |
| `code` | `answer.reference_code` → `answer.code` |
| `note` | `answer.reference` → `reference_text` → `text` → `tests_md` → `external_note` |
| `explain` | 顶层 `explanation` → `answer.explanation` → `explain` → `explanation_md` → `fix_explanation_md` |
| `external` | `external_url` |
| — | 原文件不动，归一化只发生在产物里 |

### 2.2 语言推断

不能只看学科：`bigdata` 混 Python 与 SQL，`fullstack` 混 JS 与 Python，`middleware` 混 SQL 与 Python。

所以按 **hint → 代码语法特征 → 学科兜底** 三级判定，且强特征优先：

```
public class / System.out.print / import java.   → java
#include <iostream|vector|string|bits/...>       → cpp
std:: / cout << / using namespace std           → cpp
#include <stdio.h> 且无 std::                      → c
SELECT|INSERT|CREATE TABLE|EXPLAIN              → sql
def f() / import x / from x import              → python
function / => / const x = / console.log          → js
docker|git|kubectl|systemctl|make               → shell
```

判定结果（全库）：

| 语言 | 题数 | 能否本地运行 |
| --- | --- | --- |
| python | 253 | 两端可（桌面 go-judge / 移动 Pyodide） |
| c | 130 | 仅桌面 |
| cpp | 130 | 仅桌面 |
| java | 116 | 仅桌面 |
| sql | 104 | **都不能**（没有 SQL 引擎） |
| js | 55 | **都不能**（见 §6.2） |
| shell | 30 | **都不能** |

---

## 3. 判题链路

### 3.1 三层能力判定，职责分开

| 层 | 函数 | 回答的问题 |
| --- | --- | --- |
| 设备 | `capabilityOf(lang, RUNTIME)` | 这台机器能不能跑这个语言 |
| 题目 | `isJudgeable(e)` | 这道题够不够判（有没有 cases + 语言有没有运行时） |
| 入口 | `toJudgeProblem(e)` | 转成 JudgePanel 认的 `JudgeProblem` |

**不能合并的理由**：桌面端能跑 Java，但一道没有用例的 Java 题仍然判不了。
如果只问设备能力，用户会点「去判题台」，落地后才发现按钮是灰的。

### 3.2 页面结构

`PracticePage` 改成两个 Tab：

```
题库 ── 筛选（学科 / 题型 / 难度 / 关键词 / 仅可判 / 未完成）
     ├─ 列表 → 点开详情
     └─ 详情
         ├─ 选择题     → 多选 → 对照答案（按集合比对）
         ├─ 输出/改错  → 文本框 → 归一化比对（复用 OJ 的 normalizeOutput）
         ├─ 编程题     → 有 cases：去判题台｜无 cases：自由运行｜无运行时：说明
         └─ 显示参考答案（correct / expect / code / note / explain / external）
判题台 ── 原 JudgePanel（problem 由题库带入）
```

### 3.3 跨页跳转

模块级 store，不走 props：

```ts
sendToJudge(problem)     // 题库 → 判题台，PracticePage 切 Tab 并带题面
focusChapter(chapterId)  // 学习页 → 题库，锁定某一章
usePendingJudgeProblem() // PracticePage 订阅
useFocusedChapter()      // ExerciseBank 订阅
```

`PracticePage` 用 `key={id-judgeKey}` 强制重建 JudgePanel —— 同一道题重复点也要重置，
否则 React 认为 props 没变，上一次的判题结果会留在屏幕上。

---

## 4. 本阶段修掉的真实缺陷

| # | 缺陷 | 根因 | 修法 |
| --- | --- | --- | --- |
| 1 | C 语言题被 g++ 编译 | Rust `judge_client.rs` 的 `"cpp" \| "c++" \| "c"` 共用一个分支，源文件名写死 `main.cpp` | 新增独立 `"c"` 分支：`gcc` + `main.c` |
| 2 | `environment.rs` 不检测 gcc | 只 probe 了 g++ / python / java | 补 `gcc --version` |
| 3 | **C 语言学科在学习页是空页** | `clang` 的 7 个单元挂在 `cpp/_manifest.json` 的 `clang_module.units` 里，从来没进过 `BUNDLE.chapters`；而 `SUBJECTS` 里却有「C 语言」这一项 | 生成 `clangUnits.ts`，`LearnPage` 在 `subject === 'clang'` 时用它 |
| 4 | 浏览器预览说「移动端暂不支持」 | `capabilityOf` 对 `web` 和 `android` 共用一条文案 | 新增 `WEB_UNSUPPORTED_REASON`，按 runtime 分文案 |
| 5 | 选择题下方冒出「自由运行」 | 只判了 `isJudgeable`，没判题型；选择题也带 `reference_code` | 加 `codeLike` 闸（仅 coding / fix_error 且有 code） |
| 6 | 判题台题面标题重复两行 | `composeProblemMarkdown` 自己加了 `## title`，JudgePanel 又渲染一次 `problem.title` | 去掉 markdown 里的标题 |
| 7 | Pyodide 4 处类型错误挡住构建 | ① `DedicatedWorkerGlobalScope` 不在 `lib` 里；② `activeId` 写了不用；③④ `Omit<联合类型,'id'>` 把联合塌缩了 | ① 改结构化声明；② 删除；③④ 用 `DistributiveOmit` |

> 第 3 条最值得记：`SUBJECTS` 有 13 个学科、`BUNDLE.chapters` 只有 12 个键，
> 差的那一个正好是 C 语言。这种「列表和字典对不上」的空洞，页面不报错、不空白加载，
> 只显示一句「这个学科还没有章节清单」，非常容易被当成「内容还没写」。

---

## 5. 验收

### 5.1 内容侧

```bash
python server/scripts/verify_examples.py --json
# {"total": 1303, "ok": 1303, "failed": 0, "failures": []}
```

1303 个 `examples/*.json` 全部真编译真运行、输出与 `expected_output` 一致 ——
这是「示例可以当判题用例」的前提。

### 5.2 前端侧

`frontend/shot.mjs`（系统 Edge headless + playwright-core，无需下载 Chromium）：

```bash
npm run build
npx vite preview --port 4175 --strictPort --host 127.0.0.1 &
node shot.mjs http://127.0.0.1:4175 .shots
```

实测输出（零控制台错误）：

```json
{
  "learnBank": "本章题目 5 题 · 可直接判 2 题 选择 1 编程 2 输出 1 改错 1 做本章这 5 题",
  "focusBar": "已锁定章节：C++ 基础语法：类型、变量与引用 看全学科",
  "chapterRows": 5,
  "allRows": 130,
  "allChip": "全部 130",
  "judgeableRows": 2,
  "detailCtas": 1,
  "judgeTitle": "读取 n 个数求和",
  "hasProblem": 1,
  "caseRows": 3,
  "choiceCtas": 0,
  "choiceOpts": 4,
  "errors": []
}
```

逐条对应：

| 断言 | 期望 | 实测 |
| --- | --- | --- |
| 学习页本章题数 | cpp-ch01 = 5 题 | 5 ✓ |
| 章内可判数 | cpp-ch01 有 cases 的 2 题 | 2 ✓ |
| 「做本章这 N 题」→ 锁定章节 | 列表只剩该章 | 5 行 ✓ |
| 清锁 → 全学科 | 130 行 | 130 ✓ |
| 勾「仅可判」 | 只剩 2 行 | 2 ✓ |
| 去判题台带题面 | 标题 + 题面 + 用例 | 读取 n 个数求和 / 3 个用例 ✓ |
| 选择题不出现判题入口 | 0 | 0 ✓ |

截图：`frontend/.shots/{03-learn-open,04-bank-chapter,05-bank-judgeable,06-bank-detail,07-judge,08-choice,09-mobile}.png`

### 5.3 构建

```
tsc --noEmit                通过
vite build                  1.25s
dist/assets/index-*.js      1,018 KB │ gzip 495 KB
dist/assets/index-*.css      66.8 KB │ gzip 12.8 KB
```

---

## 6. 自查：已知的漏洞与边界

### 6.1 可判率只有 39 / 272（14%）

全库 272 道编程题里，**只有 39 道带 `test_cases`**：

| 学科 | 有 cases | 无 cases |
| --- | --- | --- |
| database | 18 | 7 |
| java | 10 | 10 |
| bigdata | 5 | 10 |
| tooling | 3 | 18 |
| cpp | **2** | 25 |
| spring | 1 | 12 |
| python | **0** | 23 |
| clang | **0** | 15 |
| ai / fullstack / fundamentals / middleware / data | 0 | 93 |

题库里 **160 道**编程题的参考代码只有函数体、没有 `main`（另有 57 道连参考代码都没有，
只有 55 道是完整的可运行程序）。函数形态的题**不可能自动生成判据**：不知道要喂什么参数，
就不知道期望输出是什么。

已评估过的自动补全方案与其结论：

| 方案 | 结论 |
| --- | --- |
| 用 `answer.output` 当期望输出，空 stdin 跑参考代码 | 全库只有 **17 道**同时具备 `reference_code` 与 `output`，收益上限 17 题，需要逐题真跑验证才敢写入 |
| 从 `examples/*.json` 借用用例 | 示例属于**单元**而非具体题目，输入输出对不上，不能硬借 |
| 从题面描述反推 stdin | 题面是自然语言，不可靠，会写出「编造的判据」 |

**结论：剩下的 233 道必须人工补 `test_cases`，这是内容生产工作，不是工程工作。** 本阶段不做，
UI 已经用「没有内置用例 → 自由运行」承接，不会假装能判。

### 6.2 JS / SQL / Shell 共 189 题两端都判不了

`judge_client.rs` 只有 python / c / cpp / java 四个分支。全栈 26 道编程题里 21 道是 JS/TS，
**桌面端也无法运行**。UI 显示「JavaScript 暂无本地运行时」，不给假入口。

补法有三条路，都要单独评估：

1. go-judge 加 Node 运行时（桌面端，需随包分发 node，约 +50MB）
2. 移动端 QuickJS-WASM（体积小，但 ES2020 之后的新语法支持不全）
3. 只判「纯函数 + JSON 输入输出」的子集，用现有 Python 沙箱跑一个 JS 解释器（不现实）

### 6.3 打包体积从 ~250KB 涨到 1MB

`exercises.ts` 898KB 静态 import，gzip 后 +495KB。对整个 APK（16MB）不是问题，
但 Vite 报了 chunk > 500KB 警告。

**没有做代码分割的理由**：`LearnPage` 也需要 `chapterBankStats()`，而学习页是首屏之一。
真要做只能把 `ExerciseBank` 和 `LearnPage` 都改成 `React.lazy`，把题库推迟到点开时加载 ——
收益是首屏少解析 700KB（本地资源，约 60–80ms），代价是多一层 loading 态。
离线应用不吃网络，暂时不值得。**若以后 APK 首屏启动时间成为问题，这是第一个该动的地方。**

### 6.4 进度仍是 localStorage

题库完成度写 `nex.bank.done.v1`，**没有**并进 `kaimao.progress.v1`，也没有 SQLite。
刻意分开的两个理由：

- 818 个 id 塞进 `progress` 会让每次 `setProgress` 都序列化一个大数组；
- 题库是新增域，将来要单独同步到云端时，混在一起很难拆。

代价：清缓存即丢。与当前 `progress.ts` 的整体策略一致（都是 localStorage），不是本阶段新引入的问题。

### 6.5 客观题比对是「宽松相等」，不是「判题」

- 选择题：按**集合**比对，`["B","C"]` 与 `["C","B"]` 等价，多选少选都算错。
- 输出题：复用 OJ 的 `normalizeOutput()`（去行尾空白 + 末尾空行），不做语义等价。
- 判断题的 `correct` 有时是长句结论，此时不做比对，只给「显示参考答案」自评。
  `见解析` / `见链接` 这类占位值被显式排除，否则用户会看到「一致」的假通过。

### 6.6 `fullstack` 的 GitHub 项目数据结论

10 个项目全部真实可访问、`lang` 与 `stars` 齐全，**数据没有缺口**：

| 项目 | 语言 | stars | license |
| --- | --- | --- | --- |
| vercel/next.js | JavaScript | 143,078 | MIT |
| shadcn-ui/ui | TypeScript | 125,897 | MIT |
| supabase/supabase | TypeScript | 111,748 | Apache-2.0 |
| realworld-apps/realworld | TypeScript | 84,302 | **NOASSERTION** |
| appwrite/appwrite | TypeScript | 57,724 | BSD-3-Clause |
| calcom/cal.diy | TypeScript | 49,143 | MIT |
| vercel/next-learn | TypeScript | 4,797 | MIT |
| valarchie/AgileBoot-Back-End | Java | 2,315 | MIT |
| liyupi/yu-ai-code-mother | Java | 1,982 | **None** |
| wsydxiangwang/Mood | Vue | 783 | **None** |

三个没有许可证的是**仓库本身没声明**（实时 API 核对：`Mood` 与 `yu-ai-code-mother` 返回
`license: null`，`realworld` 返回 `NOASSERTION`），不是抓取失败。`ProjectsPage` 已渲染为
「无许可证」。法律含义要写清：**无许可证 = 保留所有权利，不能直接拿代码商用**，
只能参考架构与思路。

---

## 7. 下一步（按收益排序）

1. **给 python / cpp / clang 的 63 道编程题补 `test_cases`** —— 这三个学科是主线，可判率从 14% 提到 40% 以上
2. **JS 判题**（`fullstack` 26 题 + 其他学科 js）—— 桌面端 go-judge 加 Node 分支优先
3. SQL 判题需要嵌入式引擎（sql.js / DuckDB-WASM），移动端比桌面端更容易落地
4. 首屏分包（见 §6.3），等启动时间真的成为问题时再做
