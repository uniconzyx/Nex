# 概念图解工作台

把 `content/<学科>/<章>/concept/*.md` 里的小节结构，变成一张**可驱动的机制图**，
并让同一张图被三种现实场景照亮：考试真题 / 线上事故 / 面试追问。

```
python scripts/gen_concept_viz.py     # 生成 viz/data.js（约 3 MB）
open viz/index.html                   # 直接双击即可，无依赖、无构建、可离线
```

## 结构

| 层 | 文件 | 说明 |
|---|---|---|
| 数据 | `viz/data.js`（生成物，不入库） | 16 学科 / 165 章 / 717 概念 / 3478 小节 + 每章真题、工程坑、面经 |
| 引擎 | `viz/index.html` | SVG 四种图形 + 场景探照灯 + 步进器，纯原生 JS |
| 抽取 | `scripts/gen_concept_viz.py` | 只读 `concept/*.md`、`exercises.json`、`pitfalls.md`、`interview.json` |

## 四条原则

1. **节点不是段落，是作者自己分的节。** 每篇 concept 的 `##`（实战手记类退到 `###`）就是图上的一个节点，
   所以图与正文的小节号天然对齐，`§2.3` 可以直接指到图上第三节。
2. **真题只读。** 抽取器只解析 `exercises.json`，从不写回；答案在工作台里默认折叠。
   工程坑同理取自 `pitfalls.md`，面经取自 `interview.json`，三份数据都保持原样。
3. **场景是「照亮」，不是「另画一张」。** 切考试/事故/追问只改变节点配色与徽章，
   图形结构不动——这样「同一个机制被不同场景命中」才看得出来。
4. **命中要可解释。** 题目挂到哪一节用字符二元组重合度算（`affinity`），
   低于阈值就老实显示「这一节没被直接命中」，不硬塞一个不相关的问题。

## 图形怎么选

| 图形 | 触发 | 用在哪 |
|---|---|---|
| 机制链 `flow` | 默认 | 理论 → 机制 → 实践 → 陷阱 的推进 |
| 内存/层次 `stack` | 标题/前两节含 内存·栈·堆·布局·存储·对齐 | 对象模型、存储布局 |
| 时序 `timeline` | 含 时序·事件循环·调度·请求·重试·状态机 | 异步、握手、流水线 |
| 双列 `compare` | 含 对照·vs·区别·选型，且 ≤ 8 节 | 小节多时排成两列省纵向空间 |

超过 8 节、或实战手记/片段集，一律回落到机制链——对照图只有两列，塞不下十节。

## 已经接进 App：章节卡里的「机制图解」

工作台是「逛」用的，真正的阅读位置在 `frontend/src/pages/LearnPage.tsx` 的章节展开卡里：

```
LearnPage 章节卡
  摘要 → 旁白 → 前置 → 【ConceptViz】 → 三关 → 延伸仓库 → 本章题目 → 本章总结
```

- 组件：`frontend/src/components/ConceptViz.tsx`（样式 `ConceptViz.css`）
- 数据：生成器同时产出 `frontend/src/data/viz/<学科>.ts`，组件按学科 `dynamic import`，
  165 章全量 3MB 不会进主 chunk（构建后每学科 8–231KB 独立 chunk）
- 与工作台的三处差异（都是为了嵌进半宽主栏）：
  1. 三栏压成纵向：图 → 步进 → 这一节正文 → 命中的题/事故/面询；
  2. 窄屏（< 560px）把 `timeline` / `compare` 降级成纵向链，徽章退化成只显示数字；
  3. 图高超过 720px 才限高滚动，并给出「下面还有」的渐隐与文字提示。

重新生成（改了任何 concept / exercises / pitfalls / interview 之后）：

```bash
python scripts/gen_concept_viz.py          # 同时写 viz/data.js 与前端模块
python scripts/gen_concept_viz.py --skip-js  # 只更新工作台数据
```

验收脚本（需要 `vite --port 1420` 在跑）：

```bash
node .scratch/viz_embed.mjs   # 桌面 + 手机，含点击/切场景/展开答案断言与截图
node .scratch/viz_kinds.mjs   # 6 个学科 × 全部概念，检查四种图形是否溢出画布
node .scratch/viz_dark.mjs    # 暗色变量探针
```
