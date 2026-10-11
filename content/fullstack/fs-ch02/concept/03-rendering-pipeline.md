# 03 · 浏览器渲染管线：从字节到像素

## 一、理论根基：关键渲染路径（Critical Rendering Path）

"为什么页面会闪/卡/慢"的回答，必须落到**渲染管线**这一工程事实上。现代浏览器（Blink/WebKit/Gecko）把 HTML/CSS/JS 变成屏幕像素，主线是：

```
字节 → 字符 → Token → DOM        (HTML 解析)
CSS  → CSSOM                     (样式解析)
DOM + CSSOM → Render Tree        (样式计算)
Render Tree → Layout(Reflow)     (几何)
Layout → Paint(Raster)           (绘制)
Paint → Composite → 像素          (合成，常走 GPU)
```

> 博士视角：这是一条**流水线（pipeline）**，任一阶段重做都会让后续阶段重做。性能优化的核心就是"尽量少触发、尽量靠后触发"。

## 二、实现机制（按线程与阶段拆解）

1. **解析（Parse）**
   - HTML 解析器做 *tokenization* + *tree construction*，是**增量、容错、可中断**的；并带 **preload scanner**（预扫描器）提前发请求下载 `<img>/<link>/<script src>`。
   - 同步 `<script>`（`无 defer/async`）会**阻塞解析器**：下载+编译+执行期间 HTML 暂停，故脚本应放 `<body>` 底部或用 `defer`/`async`。
2. **样式计算（Style / Recalc）**
   - 把 CSS 规则与 DOM 节点匹配 → 每个元素的 **Computed Style**。涉及**层叠（cascade）、继承、特异性**计算。
3. **布局（Layout / Reflow）**
   - 计算每个盒子的几何信息（`x/y/width/height`）。Blink 中以 `LayoutObject`/`LayoutBox` 表示；**布局结果依赖视口尺寸**，故 resize 会触发整树重排。
4. **绘制（Paint）**
   - 把盒子拆成绘制指令（Paint ops）→ 光栅化（raster）到图块（tiles）。这一步可能很贵（大量文本/阴影/模糊）。
5. **合成（Composite）**
   - 浏览器把页面分成若干**图层（layer）**，独立的图层可交**合成器线程（Compositor Thread）+ GPU** 处理。触发提升的常见属性：`position:fixed`、`transform`、`opacity`、`will-change`、`video/canvas`、3D 变换。
   - **合成器线程独立于主线程**：即使主线程卡在 JS，滚动/动画（仅 transform/opacity）仍可流畅。

**主线程 vs 合成器线程**：JS、Style、Layout、Paint 在**主线程**串行；Composite 在**合成器线程**。这是 "JS 卡顿但 CSS 动画仍顺" 的根本原因。

## 三、Reflow / Repaint / Composite-only 的区别（面试高频）

| 触发操作 | 阶段 | 代价 |
|---|---|---|
| 改 `width/height/top/left/display` | Reflow（连带 Repaint+Composite） | 最贵 |
| 改 `color/background/visibility` | Repaint（连带 Composite） | 中 |
| 改 `transform` / `opacity`（在合成层上） | **仅 Composite** | 最便宜（走 GPU） |

## 四、工程实践：程序员怎么避免卡顿

- **避免强制同步布局（layout thrashing）**：连续「读布局属性（如 `offsetHeight`）再写样式」会让浏览器反复 Reflow。应**批量读、批量写**（见五·示例）。
- 动画只用 `transform`/`opacity`，并加 `will-change`（但别滥用——每个合成层都吃显存）。
- 用 `requestAnimationFrame` 把 DOM 写入对齐到帧，避免一帧内多次重排。
- `debounce`/`throttle` 处理 `resize`/`scroll`；大列表用虚拟滚动。
- `defer`/`async` 脚本、关键 CSS 内联、图片懒加载，缩短首屏 CRP。

## 五、边界与陷阱：layout thrashing 实例

```js
// 错误：循环里交替读 offsetHeight（强制 reflow）与写 width → 每轮都重排
for (const el of boxes) {
  const h = el.offsetHeight;   // 读：强制同步布局
  el.style.width = h + 10 + 'px'; // 写：下一轮读前又 reflow
}
// 修复：先批量读，再批量写
const hs = boxes.map(el => el.offsetHeight);
boxes.forEach((el, i) => { el.style.width = hs[i] + 10 + 'px'; });
```

> 关键结论：渲染管线分 5 步；性能优化 = 让变更尽量落在「合成层」、把读写批量、把重活移出主线程。DevTools 的 Performance 面板能直接看到每一帧的 Layout/Paint 耗时。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 只改 `transform` / `opacity` 可跳过 Layout 与 Paint，直接走 Composite（GPU 合成），这是动画流畅的关键。
- 避免 **layout thrashing**：读写分离、批量读后批量写，或把测量集中到 `requestAnimationFrame` 里。
- 慎用「无脑 `will-change`」：每多一个合成层就多一份显存，层爆炸反而更卡。

### 🎓 博士生视角
- **关键渲染路径（CRP）**：解析 HTML → DOM、解析 CSS → CSSOM、合并成渲染树 → 布局（Layout/Reflow）→ 绘制（Paint）→ 合成（Composite）。
- **Reflow 是 O(受影响子树) 的重计算**（几何变了要把后代全部重算），Repaint 只重绘像素，Composite-only 只重新合成位图——三者的代价量级不同。
- 把绘制下推到 GPU 是用**显存换主线程时间**；这与操作系统的「用缓存换 CPU」是同一权衡结构。
- JS 在主线程执行，长任务会阻塞渲染 → 掉帧，这正是「时间片/让出主线程」类方案（分片、Worker）的动机。

### 📚 考研者视角
- **408 操作系统交叉**：浏览器的多进程/多线程模型（主线程、合成线程、GPU 进程）、进程间通信、缓冲区与流水线——渲染管线本身就是一条流水线。
- 若考 Web 性能方向，常考「重排与重绘的区别」「如何减少重排」——按点作答。
- 记忆锚点：**Layout → Paint → Composite**；**`transform`/`opacity` 能跳过前两步**。
