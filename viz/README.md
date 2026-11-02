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
| 对照 `compare` | 含 对照·vs·区别·选型，且 ≤ 8 节 | A/B 两条实现路线 |

超过 8 节、或实战手记/片段集，一律回落到机制链——对照图只有两列，塞不下十节。

## 接进 App 的路径

`data.js` 是 `window.VIZ = {...}` 一段 JSON，`index.html` 里的渲染函数是纯函数
（`drawFlow / drawStack / drawTimeline / drawCompare` + `svgEl`），不依赖 DOM 之外的东西。
把它搬进 `frontend/src` 时只需要：

1. 把 `data.js` 改成 `viz.json`，随内容构建一起产出（`gen_concept_viz.py --json` 即可扩展）；
2. `svgEl` 换成 React 的 `<svg>` 组件，四个 `draw*` 各自变成一个 `<ConceptDiagram kind=… />`；
3. `S` 状态换成页面级 store，场景面板复用现有 `km-*` 卡片样式。
