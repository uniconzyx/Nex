# 凯喵 Code 试炼录 · 交互微游戏

不是视频，是**可以点、可以拖、可以通关**的 React 组件。
每个模块都能单独嵌进任意 React 页面，自带全部样式，判定全在本地。

```bash
npm install
npm run dev        # http://localhost:5180
npm run build      # tsc --noEmit && vite build
```

打开后是**索引台**：16 学科 / 165 章，点任一章进入交互模块。

---

## 1. 目录结构

```
viz/interactive/
├─ lab/                      数据驱动层（不认学科，只认 interactive.json）
│  ├─ types.ts               数据契约（六种玩法）
│  ├─ expr.ts                沙盒公式求值器（不 eval、不 new Function）
│  └─ InteractiveLab.tsx     六种玩法的通用实现
├─ mw-ch04/                  手写精修样板（四个模块，物理拖拽 + 时序回放）
│  └─ CacheDesignLab.tsx     单文件，可直接拷走
├─ verify/                   真浏览器验收（Edge headless + playwright-core）
│  ├─ verify_lab.mjs         四玩法回归（索引 / 配对 / 打靶 / 挖空 / mw-ch04）
│  ├─ verify_handmade.mjs    sandbox 全组合扫描 + debug 拼装
│  └─ audit_labs.mjs         16 视口横向溢出审计
├─ src/
│  ├─ main.tsx               预览台（索引 / #/mw-ch04 / #/<subject>/<chapter>）
│  └─ data/
│     ├─ index.ts            生成物：165 章轻量索引（27KB，入库）
│     └─ labs/*.json         生成物：每章数据，按需 import()（884KB，gitignore）
└─ dist/                     静态产物（gitignore）
```

数据源在内容侧：`content/<subject>/<chapter>/interactive.json`（每章一份，入库）。

---

## 2. 六种玩法

| kind | 玩法 | 判定 | 数据来源 |
|---|---|---|---|
| `sequence` | **时序连线**：拖事件卡进时间轴槽，按序回放，走到尽头才判对错 | 槽位编号 === 步骤编号 | concept 里「步骤 / 流程 / 阶段 / 生命周期 / 握手」小节的有序列表 |
| `match` | **配对连线**：左「出事的写法」↔ 右「正确做法」，点左再点右，真画贝塞尔线 | 一对一 id 相等 | `pitfalls.md` 每条陷阱显式标出的正解（「正确做法 / 怎么改 / ✅」三套写法都认） |
| `boss` | **真题打靶**：答对削一层护甲，连答通关 | `answer.correct` 字母键 | `exercises.json` 的 choice 题（只读，文件不改） |
| `fill` | **代码挖空**：把缺失的标识符拖回代码空位 | token === 该空答案 | concept 代码块里的关键标识符（同块唯一、非内建、小写开头） |
| `sandbox` | **沙盒推演**：拖旋钮/点档位 → 指标实时重算 → 所有判据变绿才通关 | 判据表达式全部为真 | 手工精修：`content/_handmade/labs.json`（作者源 `scripts/_author_labs.py`） |
| `debug` | **代码拼装**：骨架留整行空位，把语句块拖进去，错块会说自己错在哪 | 块归属的槽位 === 落点 | 手工精修：同上 |

`boss` 与 `fill` 的选项/token 都会**确定性洗牌**（seed = 章节指纹），
同一题每次打开顺序一致、可复现，但答案位置不再固定（原章三题答案全 B 也不送分）。

---

## 3. 精修样板 · mw-ch04 缓存设计

`mw-ch04/CacheDesignLab.tsx`（单文件、四个模块）是「做到什么程度算好」的参照：

| 模块 | 玩法 | 教学落点 | 数据锚点 |
|---|---|---|---|
| 01 `AvalancheSandbox` | 滑 `jitter 0→1200s`，31 档直方图实时重排 | **抖动是把峰值换成极差**，不是消除回源；**单飞对雪崩完全无效**（开关是「无效药」，故意做成没用） | `examples/ex08` 六档实测 |
| 02 `SingleflightDebug` | 3 空槽 + 5 块代码（2 块是坑） | 读缓存 / 单飞合并 / 回填 TTL，三件缺一不可 | `examples/ex04`、`ex05`（200 → 1，−99.5%） |
| 03 `DoubleDeleteSeq` | **时序连线**：7 张事件卡（含 1 张干扰）拖进 6 格时间轴 → 回放 → CACHE/DB 两格逐帧变化 | 延迟双删的六步因果，以及「延迟必须 ≥ 读库+回填耗时」 | `concept/03-consistency-update.md` |
| 04 `CacheBossRaid` | 三题连答，答对飞弹削护甲 | 穿透 / 击穿 / 雪崩的判别边界 | `exercises.json` |

`DoubleDeleteSeq` 的标准时序（最坏情形，回填落在写库之后）：

```
t01 A 删除缓存            cache=∅   db=v1
t02 B 缓存 miss，读库 v1   cache=∅   db=v1
t03 A 更新库为 v2          cache=∅   db=v2
t04 B 回填 v1（脏）        cache=v1  db=v2   ← 此刻已脏，且不会自愈
t05 延迟 ~500ms 再删一次    cache=∅   db=v2   ← 脏值被清掉
t06 下次读 miss 回填 v2     cache=v2  db=v2   ← 自愈
```

干扰卡是「A 直接把缓存更新成 v2（不删）」——文档明说「更新会引入并发覆盖」。
排错顺序时，`CACHE/DB` 会显示「状态」而非绿色的「一致」：**顺序没排对，那个"一致"不是这条时序挣来的**。

`ScenarioBar` 给每个模块套了两种进入方式，同一套交互、两套叙事：

- **工作现场**：从告警/工单进（「14:02 P99 从 80ms 冲到 12s」），关心先止血还是先查根因；
- **考场视角**：从题干进（「统一 TTL 的 2000 个 key 为何同时失效」），关心判别标准与选项陷阱。

---

## 4. 数据管线 · 一条命令铺到全科目

```bash
python scripts/gen_interactive.py            # 全量：165 份 interactive.json + 索引 + labs/
python scripts/gen_interactive.py --check    # 只统计不落盘
python scripts/gen_interactive.py --only middleware/mw-ch04 -v
```

**只读素材，绝不改写**：`exercises.json` / `pitfalls.md` / `concept/*.md` / `examples/*.json`
一律只读。生成物只有 `interactive.json`、`src/data/index.ts`、`src/data/labs/*.json`。

幂等：数据里只放素材指纹（sha1 前 10 位），不放时间戳 —— 重复跑 diff 为空。

### 当前覆盖率（2026-11-03）

| 指标 | 数值 |
|---|---|
| 章节 | **165 / 165**（16 学科，全部有可交互模块） |
| 模块总数 | **471**，平均 2.85 / 章 |
| boss | 165 章（每章 1~6 题，从 choice 真题抽） |
| match | **151 章**（595 对） |
| fill | 99 章 |
| sandbox | **31 章**（C/C++ 主线 9 + 408 主线 22） |
| debug | **12 章**（C/C++ 主线 11 + 408 主线 1） |
| sequence | 13 章 |

每章模块数分布：**1 个 → 0 章**，2 个 → 48 章，3 个 → 93 章，4 个 → 24 章。
**任何一章都至少「配对 + 打靶」两种玩法。**

### 为什么 sequence 只有 13 章（不是 165）

时序题的前提是「这几步**真的**有先后」。全文扫下来有编号列表的章节 154 章，但大部分是
并列要点（「三个真相」「上线治理四条」「缓存键的三条规则」）——拿来做排序题就是教错。

所以抽取条件收得很紧：小节标题必须命中 `步骤|流程|时序|顺序|阶段|链路|生命周期|执行流|流水线|握手|归因|诊断|推导|解析`，
且不命中 `真相|选型|治理|要点|清单|规范|技巧|误区|对比|区别|推荐|准则|陷阱|原则`；
剩下 17 章再人工复核，剔除 4 章（`SEQ_BLOCK`：标题像时序、内容是清单）。
**宁缺毋滥** —— 排序题错了比没有更糟。

### match 的右栏是怎么认出来的（151 章）

配对题的右栏必须是**真正的解**，不能是现象描述。第一版用「破折号后面的内容」当右栏，
结果 `**标题**` 换行后接 `- 现象：…` 的块格式被 `\s*` 吃掉换行，把「现象」当成了「正解」，
覆盖率一度跌到 89 章。现在按条目切块，只认三套**显式标记**：

| 写法 | 出现范围 | 处理 |
|---|---|---|
| `正确写法` / `正确做法` / `正确口径是` / `正解：` / `改为` | 全站 | 取关键词后到第一个句号 |
| `*怎么改*：` / `怎么避免：` | fullstack 系列 | 同上，等价标记 |
| `✅ …` | cpp 全家、fs-ch05/07/08 | 取勾号后整行 |

都没有的条目直接丢弃。剩下 10 章（`ai-ch04`、`fund-ch07/08/20/22/23`、`py-ch06/08`、
`data-ch04`、`db-ch06`）一条标记都没写，用 `scripts/patch_pitfalls_fixline.py`
在各条目末尾补一行 `**正确做法**：…`（内容取自该条自己的结论，不新增知识点），
覆盖率 89 → **151 章 / 595 对**，逐条扫过，没有一对是现象冒充的。

两个必须记住的坑：

- **`_` 是标识符的一部分**。原来那句 `re.sub(r"[*_]{1,2}", "", s)` 会把 `lora_B` 变成 `loraB`、
  `node_modules` 变成 `nodemodules`、`std::erase_if` 变成 `std::eraseif` —— 数据看着齐全，
  只有读内容才发现标识符被悄悄改写。现在代码段与 `$…$` 先占位、再清洗，孤立 `_` 不碰。
- **右栏要按句号截断**。否则「正确做法是 X。**正确做法**：Y」会把后一句一起吞掉，
  前端显示成一整段带 `正确做法：` 前缀的怪句子；括号不平衡的残片（`8000×8 = 64kbps）。`）直接丢弃。

### fill 的挖空规则

只挖「同块唯一 + 非语言内建 + 小写开头 + 长度 ≥ 4 + 落在含 `if/return/for/= →` 的逻辑行」的标识符。
首字母大写的（`Alice` / `Beijing` / `Adopt`）多是数据值和枚举，挖了没教学价值。
干扰项只从**同语言、跨章节出现 ≥ 3 次**的池里取（`status` / `stdout` / `sorted` 这种真 API），
所以 `abar` / `abc123` / `A1001` 这类一次性变量不会混进来。

---

## 5. 视觉与物理规范落地

| 规范 | 实现位置 |
|---|---|
| 极浅冰蓝底 `#EBF4FA` | `C.bg`，`.kmlab` 根节点渐变 |
| 液态玻璃 `bg-white/60 + blur + border-white/80 + shadow` | `glass()`，`backdrop-filter: blur(12px)` |
| 统一圆角 14 | `glass()` 的 `borderRadius: 14` |
| 等宽字体 | `MONO`（JetBrains Mono → Consolas 回退） |
| 点击回弹 `scale: 0.95` | `TAP`，所有 button 的 `whileTap` |
| 拖拽边缘拉伸 `dragElastic: 0.2` | `DRAG_ELASTIC` + `dragSnapToOrigin` |
| 回弹 `stiffness 300 / damping 20` | `SPRING` |
| 放置成功：缩放 + 边框爆闪 + 粒子飞溅 | `Burst` + `boxShadow` 关键帧 |
| 出错：红框 + 抖动 | `x: [0,-9,9,-6,0]` + `border: C.coral` |
| 音效占位 | 源码里 17 处 `// TODO: play xxx.mp3` |
| 凯喵常驻右下、按状态换脸换词 | `KaimaoBubble` + `useKaimao`（同一槽第 3 次卡壳自动切知识点台词） |
| 六边形母题 | `Node`（时间轴节点 / 护甲 / 成败标记）全部用 `clip-path` 六边形 |

`lab/` 层不复制色板，直接 `import { C, glass, SPRING, ... } from '../mw-ch04/CacheDesignLab'` ——
**单一色源**，改主题只改一处。

---

## 6. 集成到 CppMind（三种方式）

**A. 直接当 React 组件引**（现有 Tauri/React 前端）

```tsx
// 手写精修版
import CacheDesignLab from '@/viz/interactive/mw-ch04/CacheDesignLab';
// 通用数据驱动版（任意章节）
import { InteractiveLab } from '@/viz/interactive/lab/InteractiveLab';
import data from '@/content/database/db-ch02/interactive.json';

<CacheDesignLab />
<InteractiveLab data={data} />            // 全部模块
<InteractiveLab data={data} only="boss" /> // 只要打靶
```

记得装 `framer-motion`：`npm i framer-motion`。组件自带样式，不依赖 Tailwind 配置。

**B. WebView 加载静态页**（Flutter / 原生外壳）

```bash
npm run build     # 首页 361KB（gzip 120KB）+ 每章 2.7~4.9KB 独立 chunk
```

`dist/` 塞进 assets，WebView 指向 `index.html#/database/db-ch02`。
首页只加载 27KB 索引，章节数据按需 `import()`，不会一进门就下 884KB。

**C. 挂到章节卡里**：位置在「概念图解」之后、「三关」之前——
先看图解建立框架，再动手，最后才是三关判定。

---

## 7. 验收（真浏览器，不是读代码）

```bash
cd viz/interactive && npm run build
cd ../.. && npx vite preview --port 5190   # vite preview 只监听 [::1]，必须用 localhost

# 脚本已入库，路径相对仓库根；依赖 playwright-core + 系统 Edge（可用 EDGE_PATH 覆盖）
node viz/interactive/verify/verify_lab.mjs http://localhost:5190   # 全量：索引 + 三玩法 + 时序
node viz/interactive/verify/audit_labs.mjs                          # 8 章 × 2 视口逐个 tab 量溢出
node .scratch/verify_all.mjs                                        # mw-ch04 精修版回归
```

最近一次结果（Edge headless，1280×900 / 420×900）：

```json
{ "indexCards": 165, "matchDone": true, "matchLines": 4, "bossArmor": "1->0",
  "fillProgress": "2 / 2", "fillDone": true,
  "ddSlots": 6, "ddCards": 7, "ddFilled": 6, "ddOk": true, "ddHealed": true,
  "ddFinalCache": "v2", "ddWrongDetected": true, "ddWrongNotPass": true,
  "sandboxAlive": true, "debugAlive": true, "bossAlive": true,
  "narrowOverflow": 0, "errors": [], "pass": true }
```

覆盖：索引 165 卡 → 配对连线 4 对（含 SVG 连线数）→ 真题打靶削甲 → 代码挖空 2/2 →
时序模块拖 6 卡回放至「时序正确 + 自愈」→ 故意错序必须判脏（**不是怎么排都过**）→
其余三模块存活 → 420px 无横向溢出 → 控制台零报错。

---

## 8. 这一轮修掉的真 bug（都是"看着能跑，其实不工作"）

1. **挂载即崩**：`CODE_LINES` 的 `render(placed)` 少传 `zr`，`Dropzone` 里 `zr.current` 直接 `TypeError`。
2. **落点永远判不中**：一个 `width:0;height:0` 的隐藏测量层把 `zoneRefs` 覆盖成 0×0，`getBoundingClientRect()` 恒等于原点。
3. **槽位填满后无法替换**：落点只挂在"空槽虚线框"上，填满后落点消失。重构为 `SlotBody`——空/满都保持同一落点。
4. **切 Tab 白屏**：`<AnimatePresence mode="wait">` 包住含 `drag` 子节点的模块时，被拖走并卸载的代码块留下未完成的 presence 子节点，exit 永不结束。
   改成按 `key` 重挂的 `motion.div`，不需要 exit 动画。（凯喵气泡同一个陷阱，同样改法。）
5. **`dropTo` 里嵌套 `setState`**：在 `setPlaced` 更新函数里调 `setTray`，StrictMode 下执行两次，同一块能进托盘两份。
6. **配对题右栏被抓成"现象"**：`**标题**\s*(?:——|-{1,2}\s)` 里的 `\s*` 吃了换行，`- 现象：` 被当成破折号，
   于是「现象」成了「正解」。这是本模块最隐蔽的一个——数据看上去完全合理，只有读内容才发现答非所问。
7. **时序题把清单当时序**：标题含「生命周期」但内容是并列要点，做出来是错题。加了 `SEQ_BAD` 标题黑名单 + `SEQ_BLOCK` 人工排除。
8. **`splitMarker` 自造正则转义**：把 `‹n›` 占位符用 `new RegExp` 拼转义字符，`(` 与 `\` 的处理互相干扰；
   改成 `indexOf` 找开闭符号，稳定得多。
9. **420px 下横向溢出 14px**：时序槽 `flex:1` 没给 `minWidth: 0`，一个 `$k+(n-1)$` 长 token 就把整行撑出视口。
10. **`ScenarioBar` 在 420px 把整页撑宽 14px**：场景标题里有 `header/nav/main/article/aside/footer`
    这种**不含空格的长 token**，flex 子项按 min-content 取宽（226px > 卡片 166px）。
    修法：文案列 `flex: '1 1 240px'` + 长 token 的 span 加 `overflowWrap: 'anywhere'`，
    外层 `flexWrap: 'wrap'` 让它在窄屏整列换行；换行后那条竖分隔线会孤零零留在第一行末尾，
    用 `@media (max-width:560px){.km-sb-div{display:none}}` 收掉（`GlobalStyle` 与 `LabStyle` 两处都要写，
    因为 `lab/` 视图不渲染 `GlobalStyle`）。
11. **审计脚本会「错位认账」**：`_audit_labs.mjs` 是按章循环里取 `scrollWidth-clientWidth`，
    出现非零时先单独复现那**一章**——我第一次照着输出追到了下一章（`db-ch05`），
    真正溢出的是上一章（`fs-ch02`）。定位用 `document.querySelectorAll('body *')` 找 `getBoundingClientRect().right` 最大者，比猜快。

---

12. **`log` 只在校验器里实现了**：`expr.ts` 一开始只写了 `log2/log10`，而数据里用 `log(n)/log(f)`，
    前端整章指标显示 `—`（求值抛错被 catch 成 NaN），Python 守门却报"不认识函数 log"——
    两边报的错不一样，恰恰说明两套实现都要跑。
13. **校验器自己短路了**：Python 版把 `&&` 写成 `v and cmp()`，`or`/`and` 短路导致右边根本没解析，
    解析器卡在下一个 token 上，报"期望 )"——看着像数据写错，其实是校验器的 bug。
14. **只改 hash 不会重新加载**：验收脚本逐章 `goto('#/xx')` 时不 reload，等到的仍是上一章的 DOM，
    断言于是拿 A 章的旋钮去评 B 章（第一版就这么"全绿"了一次）。改成 `goto + reload` 并等
    `[data-chapter="<key>"]` 出现才对。

## 9. 手工精修 · sandbox / debug 是怎么写出来的

这两种玩法没法自动抽 —— 「该拖哪个旋钮」「缺的是哪条语句」都是作者判断，正则猜不出来。
所以数据单独存一份，走三段式：

```
scripts/_author_labs.py         作者源（Python 三引号装代码片段，写 JSON 手打 
 太容易错）
        ↓
content/_handmade/labs.json     生成物：43 章 × 1 个模块（sandbox 31 / debug 12）
        ↓  python scripts/gen_interactive.py
content/<subj>/<chapter>/interactive.json   精修模块排在最前（页签默认落它上面）
```

覆盖率：**C/C++ 主线 20 章 + 408 主线 23 章，章章都有一个**。
类型按「这一章的知识点有没有可算的量」分：

| 走 sandbox 的（有连续量可推） | 走 debug 的（是个逐句判断） |
|---|---|
| 整型宽度与溢出、vector 扩容因子、虚表与对象大小、Amdahl、连接池容量、SSO 阈值、字段顺序对齐 | 默认参数写两遍、`delete` 忘配对、`erase` 迭代器失效、`return std::move(v)`、`while(!eof())`、宏不加括号、头文件里的全局变量、缺 `typename`、CMake 链接方向、`Cache-Control` 用错 |
| 顺序表 vs 链表、循环队列容量、完全二叉树高度、邻接矩阵 vs 表、装填因子与 ASL、稳定排序、IEEE754 位宽、AMAT、RR 时间片、多级页表、BDP、CPI/MIPS、指令格式、流水线、总线带宽、轮询/中断/DMA、并查集优化、缓冲区大小、索引结点、磁盘访问时间、香农、停等利用率 | （408 只有这 1 个） |

### sandbox 的公式为什么用表达式而不是写死的数字

`metrics[].expr` 是一段表达式（`ceil(log(n) / log(factor))`），参数和前面算出的指标都能引用。
理由：一张表要同时服务「32 位 4KB 页」和「48 位 64KB 页」，写死数字就只能演示一种参数组合；
而**学生自己拖出来的反例才是真反例**，作者编的数字说服不了人。

求值器 `lab/expr.ts` 是手写递归下降，**不用 `eval` / `new Function`**：这份 JSON 将来会被别的宿主
（App 内嵌、分享页）复用，一旦有人能改数据就等于能执行任意脚本。只放行数字、标识符、
四则/幂/比较/逻辑/三元 + 13 个纯函数（`min/max/abs/ceil/floor/round/sqrt/pow/log/log2/log10/exp/clamp/if`）。

### 守门：`scripts/audit_handmade_labs.py`

它回答两个只有作者才会犯、玩家一定会踩的问题：

1. **这一关能不能通关**：把参数区间按 step 穷举（组合超过 2 万组就按"点最多的轴减半"抽样），
   确认至少有一组参数让所有 `checks` 为真。一个括号写错，前端就是一排 ✗ 且永远不变 ✓ ——
   玩家拖到手抽筋也不知道是数据错了。
2. **开局是不是已经通关**：默认参数就全绿，等于模块一进来就"通过"，白给。

浏览器侧 `verify_handmade.mjs` 用**另一套独立实现**（TS 求值器）把同一件事再做一遍，
两边结论一致才说明没有语义漂移 —— 只跑 Python 会漏掉"TS 里 `log` 没实现"这类事故（真发生过）。

### debug 的错块必须带 `why`

「错了」不是反馈，「这块是修内存泄漏的，不是修并发」才是。所以每个干扰块都写自己的
`why`，落错时凯喵气泡说的是那句话；正确块用 `for` 指向槽位，干扰块 `for` 留空。

## 10. 已知边界

- **`sandbox` / `debug` 覆盖 C/C++ 与 408 两条主线（43 章）**，其余 122 章还是四种自动玩法。
  要铺到别的章不用改组件：往 `scripts/_author_labs.py` 加一段数据，跑 `_author_labs.py` +
  `audit_handmade_labs.py` + `gen_interactive.py` 三条命令即可（见第 9 节）。
- **「只有打靶」的章节已清零**（2026-11-03）。原来有 29 章只挂了一个 boss 模块，
  因为这些章既没有可用的 pitfall 正解结构、也没有合格代码块。补齐分两步：
  先让抽取器认 `✅` 与 `*怎么改*：` 两套等价标记（自动补回 19 章，不用改内容），
  再给剩下 10 章在各条目末尾补一行 `**正确做法**：`（`scripts/patch_pitfalls_fixline.py`，
  幂等，重复跑不会叠加）。现在 **165 章全部 ≥ 2 个模块**。
- **`sequence` 的步骤可能不是完整流程**：例如「类加载五阶段」小节只列了 3 项，
  模块顶部如实写「3 步」，不会假装是全部。
