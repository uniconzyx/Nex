# 04 · 现代布局：Flexbox 与 Grid

## 一、理论根基：一维 vs 二维

- **Flexbox**：为一维布局设计（沿一条主轴排布，main axis + cross axis），擅长"把一组元素排成一行/一列并分配剩余空间"。
- **Grid**：为二维布局设计（同时控制行与列），擅长"整体页面骨架 / 圣杯布局 / 卡片墙"。

二者不是替代关系，而是**互补**：大骨架用 Grid，组件内排列用 Flex。

## 二、实现机制：Flexbox

容器 `display:flex` 后，子项成为 **flex item**，布局由以下属性驱动：

- **主轴方向** `flex-direction: row|column|row-reverse|column-reverse`。
- **主轴对齐（分配剩余空间）** `justify-content: flex-start|center|space-between|space-around|space-evenly`。
- **交叉轴对齐** `align-items: stretch|center|flex-start|baseline`。
- **伸缩三件套** `flex: <grow> <shrink> <basis>`：
  - `flex-grow`：有剩余空间时放大的比例。
  - `flex-shrink`：空间不足时缩小的比例（默认 1，可设 0 禁止收缩）。
  - `flex-basis`：分配前的初始主轴尺寸（优先于 `width`）。
- **隐式最小尺寸**：flex item 默认 `min-width:auto`，可能"撑不缩"导致溢出——需要时可显式 `min-width:0`。

## 三、实现机制：Grid

- **显式轨道** `grid-template-columns: 200px 1fr 1fr;` `grid-template-rows: auto 1fr;`
- **`fr` 单位**：剩余空间的比例分配（类似 flex-grow，但在二维同时成立）。
- **隐式轨道** `grid-auto-rows/columns`：内容超出显式定义时自动生成。
- **区域命名** `grid-template-areas: "header header" "side main" "footer footer";`——可读性强。
- **对齐** `justify-items/align-items`（单格）、`justify-content/align-content`（整个网格在容器内的对齐）。
- **自动放置**：子项默认按行/列自动流入；可用 `grid-column: 1 / 3` 跨轨。

## 四、工程实践

- 居中最简解：`display:flex; justify-content:center; align-items:center;`（见 ex07）。
- 圣杯布局：`grid-template-areas` 一行声明（见 ex08）。
- 响应式断点切换 `grid-template-columns` 数量（`repeat(auto-fit, minmax(200px,1fr))` 实现自适应卡片墙）。
- 优先 `gap` 而非 `margin` 控制间距（不会外溢、不参与 margin 折叠）。

## 五、边界与陷阱

- Flex 的 `min-width:auto` 导致文本过长时子项不收缩、撑破容器 → 设 `min-width:0`/`overflow:hidden`。
- `flex:1` 是 `1 1 0%`（`basis:0`），与 `flex:auto`（`1 1 auto`）行为不同：前者无视内容初始宽，后者保留。
- Grid 的 `1fr` 含 `min-content` 下限，长内容仍可能撑开 → 配 `minmax(0, 1fr)`。
- `float`/`clear`/`vertical-align` 在 Flex/Grid 容器中**失效**（item 脱离普通流）。

## 六、可运行示例（浏览器渲染，见 examples/ex07-flexbox-center.json、ex08-grid-layout.json）

---

## 三视角解析

### 🧑‍💻 程序员视角
- **一维用 Flex、二维用 Grid**；间距统一用 `gap`（不再用 margin 凑，避免首尾多余留白）。
- 响应式卡片网格的标准写法：`grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))`——不用写媒体查询就能自适应。
- 居中的现代答案：容器 `display:flex; justify-content:center; align-items:center`，比 `absolute + transform` 更少副作用。

### 🎓 博士生视角
- Flexbox 是**主轴-交叉轴的一维约束求解**：`flex-grow/shrink/basis` 共同决定剩余空间的分配（等价于带弹性的线性分配）。
- Grid 是**显式二维网格 + 隐式轨道**：`grid-template-areas` 让布局与源码顺序解耦，这是它相对 float 布局的根本优势。
- **`1fr` 是弹性单位而非百分比**：它表示「剩余可用空间的一份」，在内容溢出时行为与 `%` 完全不同——这是最常见的概念混淆点。
- 二者都是「声明式约束」而非「命令式定位」，与约束求解/布局引擎的学术传统一脉相承。

### 📚 考研者视角
- 408 无直接考点；可类比**资源分配的约束满足问题**（把可用空间按权重分配）。
- 若考前端方向，「Flex 与 Grid 的适用场景」「`1fr` 的含义」是高频面试题。
- 记忆锚点：**Flex 一维、Grid 二维、`1fr` 是份数不是百分比、`gap` 优于 margin**。
