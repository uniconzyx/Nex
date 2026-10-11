# 02 · CSS 盒模型与 BFC：布局的几何真相

## 一、理论根基：一切皆盒子

CSS 的基石是**盒模型（box model）**：文档流中的每个元素都被渲染为一个矩形盒子，由内到外四层：

```
margin(外边距) | border(边框) | padding(内边距) | content(内容)
```

`width`/`height` 这个属性**到底指哪一层**，由 `box-sizing` 决定——这是布局算错的第一性根源。

## 二、实现机制：`content-box` vs `border-box`

浏览器在**布局阶段（Layout/Reflow）** 为每个盒子计算几何坐标。两种模式（见 ex03/ex04）：

| 模式 | `width` 包含范围 | 元素实际占位宽 | 来源 |
|---|---|---|---|
| `content-box`（默认，W3C 传统） | 仅 content | `width + padding*2 + border*2 + margin*2` | CSS2 旧模型 |
| `border-box`（IE 模型，CSS3 扶正） | content+padding+border | `width`（margin 仍在外） | 直觉更友好 |

> 因此经典重置：`* { box-sizing: border-box; }`——设了 `width:200px` 元素就占 200px，padding/border 向内挤压内容区，排版可预测（ex10 用 Node 算出了两种模式的差异）。

## 三、BFC：块级格式化上下文

**BFC（Block Formatting Context）** 是一块**独立的布局区域**，内部块级盒按正常流排布，且**与外部互不干扰**。它的三大作用（程序员必会）：

1. **包含浮动（contain floats）**：BFC 会计算浮动子元素的高度，父容器不再"高度塌陷"。
2. **阻止外边距折叠（margin collapse）**：BFC 内部的 margin 不与外部折叠。
3. **阻止文字环绕 / 多列等高**：BFC 之间不会重叠。

**触发条件（满足其一即建立 BFC）**：
- 根元素 `<html>`
- `float` 值非 `none`
- `position: absolute | fixed`
- `display: inline-block | flex | grid | flow-root`
- `overflow` 值非 `visible`（常用 `overflow:hidden` 但会裁切溢出内容）
- `contain: layout | paint | content`
- `display: flow-root`（**语义最干净**的触发方式，不裁切、不影响其他）

## 四、工程实践

- 默认全局 `border-box`，避免尺寸估算错误。
- 清除浮动优先用 `display:flow-root`（替代老 `clearfix` 伪元素或 `overflow:hidden` 的副作用）。
- 利用 BFC 阻断「相邻兄弟 margin 折叠」：把其中一个包进 BFC 容器。
- 注意：**margin 折叠只发生在块级盒的*垂直*方向*同一个 BFC 内*的相邻 margin**（兄弟相邻、父子无边框/padding 隔离时）。

## 五、边界与陷阱

- **margin 不计入 `width`**：`width` 永远不含 margin（见 ex03/ex04 的占位计算）。
- **外边距塌陷**：父元素 `margin-top` 与首子 `margin-top` 会"合一"，取较大值——用 `padding`/`border`/`overflow:hidden`/`flow-root` 阻断。
- `inline-block` 元素间有**空白节点**（换行产生 4px 间隙），用 `font-size:0` 或 `flex` 消除。

## 六、可运行示例（Node 验证盒模型数学，见 ex10/ex11）

```js
// 见 examples/ex10-js-box-sizing-math.json（Node 实测）
// border-box 总宽: 200 ; content-box 总宽: 236（width=200,padding=16,border=2）
```

---

## 三视角解析

### 🧑‍💻 程序员视角
- 全局加 `* { box-sizing: border-box }`，让 `width` 的含义从「内容区」变成「边框盒」，布局心智负担骤降。
- 清浮动别再用 `clearfix` 黑魔法，直接用 `display: flow-root`（语义明确、无 `overflow:hidden` 裁剪下拉菜单/阴影的副作用）。
- 记住 **Flex/Grid 容器内不发生外边距折叠**——现代布局天然规避了这个坑。

### 🎓 博士生视角
- 盒模型是布局的**几何抽象**：每个盒子由 content / padding / border / margin 四层构成，`content-box` 与 `border-box` 只是把 `width` 锚定在不同层。
- **BFC 的本质是隔离**：形成独立的格式化上下文后，内部浮动参与父元素高度计算、相邻 BFC 外边距不折叠、不与外部浮动重叠——三个效果都源自「隔离」这一条。
- 外边距折叠是「相邻块级盒子的边界可以合并」规则的推论，只在垂直方向、普通流中发生（浮动、绝对定位、BFC、Flex/Grid 内均不折叠）。

### 📚 考研者视角
- 408 无直接考点，但「**布局 = 约束求解 + 计算层次**」的思维方式与计组的存储层次、操作系统的资源分配有类比价值。
- 若考前端方向的自命题，常考「BFC 的作用」「外边距折叠的三种情况与阻断方法」——按点作答。
- 记忆锚点：**BFC 三效果 = 含浮动、断折叠、不重叠**；**阻断折叠：加 padding/border 或 `display: flow-root`**。
