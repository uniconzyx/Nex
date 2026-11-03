# 交互模块 · mw-ch04 缓存设计与三大经典问题

不是视频，是可以点、可以拖、可以通关的 React 组件。三个模块共用一套液态玻璃视觉与凯喵气泡，
每个模块都能单独嵌进任意 React 页面。

- 源码：`mw-ch04/CacheDesignLab.tsx`（单文件，可直接拷走）
- 默认导出：`CacheDesignLab`（三个 Tab 的外壳）
- 具名导出：`AvalancheSandbox` / `SingleflightDebug` / `CacheBossRaid` / `ScenarioBar` / `Burst` /
  `KaimaoBubble` / `useKaimao` / `glass` / `C` / `SPRING` / `DRAG_ELASTIC`

```bash
npm install
npm run dev        # http://localhost:5180
npm run build      # tsc --noEmit && vite build
```

## 1. 三个模块分别教什么

| 模块 | 玩法 | 教学落点 | 数据来源 |
|---|---|---|---|
| 01 `AvalancheSandbox` | 沙盒推演：滑 `jitter 0→1200s`，31 档直方图实时重排 | **抖动是把峰值换成极差**，不是消除回源；**单飞对雪崩完全无效** | `examples/ex08-ttl-jitter-benchmark.json` 六档实测 |
| 02 `SingleflightDebug` | 物理拖拽拼装：3 个空槽 + 5 块代码（2 块是坑） | 读缓存 / 单飞合并 / 回填 TTL，三件缺一不可 | `examples/ex04`、`ex05`（已勘误：200 → 1，−99.5%） |
| 03 `CacheBossRaid` | 打靶：三题连答，答对削一层护甲 | 穿透 / 击穿 / 雪崩的判别与解法边界 | `exercises.json` 三道真题（**只读引用，文件未改**） |

`ScenarioBar` 给每个模块套了两种进入方式，同一套交互、两套叙事：

- **工作现场**：从告警/工单进（「14:02 P99 从 80ms 冲到 12s」），关心先止血还是先查根因；
- **考场视角**：从题干进（「统一 TTL 的 2000 个 key 为何同时失效」），关心判别标准与选项陷阱。

## 2. 视觉与物理规范落地

| 规范 | 实现位置 |
|---|---|
| 极浅冰蓝底 `#EBF4FA` | `C.bg`，`.kmlab` 根节点渐变 |
| 液态玻璃 `bg-white/60 + blur + border-white/80 + shadow` | `glass()`，`backdrop-filter: blur(12px)` |
| 统一圆角 14 | `glass()` 的 `borderRadius: 14` |
| 等宽字体 | `MONO`（JetBrains Mono → Consolas 回退） |
| 点击回弹 `scale: 0.95` | `TAP`，所有 button 的 `whileTap` |
| 拖拽边缘拉伸 `dragElastic: 0.2` | `DRAG_ELASTIC` |
| 回弹 `stiffness 300 / damping 20` | `SPRING` |
| 放置成功：缩放 + 边框爆闪 + 粒子飞溅 | `BlockInline` 的 `boxShadow` 关键帧 + `<Burst>` |
| 出错：红框 + 抖动 | 选项卡 `border: C.coral` + `x: [0,-10,10,-10,0]` |
| 音效占位 | 源码里 8 处 `// TODO: play xxx.mp3` |
| 凯喵常驻右下、按状态换脸换词 | `KaimaoBubble` + `useKaimao`（第 3 次卡壳自动切知识点台词） |

## 3. 集成到 CppMind（三种方式，从轻到重）

**A. 直接当 React 组件引**（现有 Tauri/React 前端）

```tsx
import CacheDesignLab from '@/viz/interactive/mw-ch04/CacheDesignLab';
// 记得装 framer-motion：npm i framer-motion
<CacheDesignLab />
```

只要一个模块：`import { CacheBossRaid } from '...';`，组件自带全部样式，不依赖 Tailwind 配置。

**B. WebView 加载静态页**（Flutter / 原生外壳）

```bash
npm run build          # 产出 dist/，单页 290KB（gzip 97KB）
```

把 `dist/` 塞进 assets，WebView 指向 `index.html`；`index.html` 已设 `viewport`，
窄屏下直方图与代码区会自动换行（`grid-template-columns` 用 `minmax(0,1fr)`）。

**C. 挂到章节卡里**：位置建议在「概念图解」之后、「三关」之前——
先看图解建立框架，再动手，最后才是三关判定。

## 4. 这一轮修掉的真 bug（都是"看着能跑，其实不工作"）

1. **挂载即崩**：`CODE_LINES` 的 `render(placed)` 少传了 `zr`，`Dropzone` 里 `zr.current`
   直接 `TypeError`。改成 `render({ placed, zr, rm })`。
2. **落点永远判不中**：另有一个 `width:0;height:0` 的隐藏测量层把 `zoneRefs` 覆盖成 0×0 的 span，
   `getBoundingClientRect()` 恒等于原点。删掉隐藏层，落点直接挂真实元素。
3. **槽位填满后无法替换**：落点只挂在"空槽虚线框"上，填满后落点消失，只能先点回旧块。
   重构为 `SlotBody`——空/满都保持同一落点。
4. **切 Tab 白屏**：`<AnimatePresence mode="wait">` 在外层包住三个模块时，模块 02 里被拖走并卸载的
   代码块会留下未完成的 presence 子节点，导致 exit 永不结束：按钮高亮变了，内容却不换。
   改成按 `key` 重挂的 `motion.div`，不需要 exit 动画。
5. **凯喵空气泡**：同一个 `mode="wait"` 陷阱，气泡文字换台时出现空框。同样改为 keyed 重挂。
6. **`dropTo` 里嵌套 `setState`**：在 `setPlaced` 的更新函数里调 `setTray`，StrictMode 下会执行两次，
   同一块能进托盘两份。改成闭包取值 + 原子换位。

## 5. 验收（真浏览器，不是读代码）

```bash
# 先 npm run build && npx vite preview --port 5190
node ../../.scratch/verify_all.mjs http://localhost:5190
```

最近一次结果（Edge headless，1280×900，DPR 2）：

```json
{ "peak0": "2000", "peak300": "80", "peak300_afterSf": "80", "sfDidNotChangePeak": true,
  "peak1200": "27", "examMode": true, "pass": true, "hits1": true, "cleared": true, "errors": [] }
```

覆盖：滑块六档数值 → 单飞开关**不改变**峰值（教学点）→ 拖三块进槽 → `[PASS]` 回源 1 次 →
拖干扰块替换 → `[FAIL] TTL=0` → 点回托盘 → 三题连答到「本章通关」→ 控制台零报错。

## 6. 把这一套铺到 9 学科 165 章

每章产出一个 `content/<subject>/<chapter>/interactive.json`，组件层只认这份数据：

```jsonc
{
  "chapter": "mw-ch04",
  "modules": [
    { "kind": "sandbox",  "scenario": { "work": {...}, "exam": {...} }, "params": [...], "truth": [...] },
    { "kind": "debug",    "scenario": {...}, "code": [...], "blocks": [...], "slots": [...], "verdicts": [...] },
    { "kind": "boss",     "scenario": {...}, "questions": [...] }
  ]
}
```

选型规则（按知识点形态，不按学科）：

| 知识点形态 | 用哪个 | 例子 |
|---|---|---|
| 有连续可调参数、结果能画出来 | `sandbox` | TTL 抖动、扩容比、索引选择性、学习率 |
| 有固定骨架、只缺几块 | `debug` | 单飞补全、TCP 握手补全、SQL 注入修补、RAII 补全 |
| 有明确对错、适合短回合 | `boss` | 真题选择题、口头禅式判断题 |

落地顺序建议：先做各学科的**头部章节**（学员最先撞上、也最值得打磨），
`mw-ch04` 这套已经把「场景条 + 玩法 + 凯喵 + 验收脚本」跑通，后面是填数据而不是重写组件。
