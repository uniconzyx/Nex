# fs-ch02 易错点（Pitfalls）

1. **忘记 `viewport` 标签** —— 移动端页面按默认约 980px 视口缩放，字体极小需双指放大。务必在 `<head>` 加 `<meta name="viewport" content="width=device-width, initial-scale=1">`。

2. **盒模型尺寸算错（content-box 陷阱）** —— 默认 `content-box` 下 `width` 不含 `padding/border`：设 `width:200px` 又加 `padding:16px; border:2px` 实际占 236px（见 ex10 Node 实测），导致换行/溢出。✅ 全局 `* { box-sizing: border-box; }`，让 `width` 即总宽。

3. **用一堆 `<div>` 拼结构忽略语义** —— 损害 SEO 与读屏体验，`<div class="nav">` 对辅助技术只是无名方块。✅ 用 `header/nav/main/article/section/aside/footer` 等地标标签。

4. **外边距塌陷（margin collapse）** —— 相邻兄弟或「父 margin-top 与首子 margin-top」会取较大值合并为一个，不是简单相加。✅ 用 `padding`/`border`/`overflow:hidden`/`display:flow-root` 阻断（计算见 ex11）。

5. **浮动导致父容器高度塌陷** —— 子元素 `float` 后脱离普通流，父容器高度为 0，背景/边框不包住。✅ 父容器建立 BFC：`display:flow-root` 或 `overflow:hidden`（注意裁切副作用）。

6. **选择器优先级误判** —— 写了 `.btn{color:red}` 却被 `button{color:blue}` 覆盖，因标签选择器特异性低。✅ 用类选择器、提高特异性，别急着 `!important`；优先级 `(a=ID,b=类/属性/伪类,c=标签)` 逐位比较。

7. **强制同步布局（layout thrashing）** —— 循环里交替读 `offsetHeight` 等布局属性与写样式，每轮都触发重排，页面巨卡。✅ 批量读、批量写，或用 `requestAnimationFrame` 对齐帧（见 concept/03）。

8. **滥用 `will-change` 制造过多合成层** —— `will-change:transform` 会给元素开独立 GPU 图层，乱用耗尽显存、反而更卡。✅ 仅对真正持续动画的元素使用，动画结束移除。

9. **用 div 堆页面，丢掉语义结构** —— 错在：`<div class="header">`、`<div class="nav">` 视觉上没问题，就没再管标签选择。

   *为什么*：语义标签自带 role，读屏软件据此生成大纲、支持「跳到主导航」等快捷键。全 div 的页面只对视觉用户友好，无障碍审计必然飘红，SEO 的结构化理解也拿不到分。

   *怎么改*：先写 HTML 再写 CSS。检验方法：把 HTML 单独打印出来，大纲是否清楚。`header/nav/main/article/section/aside/footer` 各司其职，配合 `aria-label` 补充说明。

10. **一个页面多个 h1、标题层级跳级** —— 错在：为了字号更大，把 `h3` 换成 `h1`；或者从 `h1` 直接跳到 `h3`。

   *为什么*：标题层级是文档大纲，不是字号工具。多个 `h1` 会让大纲失去唯一主题，跳级会让读屏用户困惑「中间少了一层」。

   *怎么改*：一个页面一个 `h1`，其余按 `h2 → h3` 递进不跳级。需要更大字号就用 CSS 调 `font-size`，视觉层级与语义层级可以分离。

11. **踩了 margin 折叠，以为样式没生效** —— 错在：两个块元素上下 margin 设了 20px 和 30px，实际间距只有 30px，于是反复加 `!important`。

   *为什么*：相邻块级元素的外边距会折叠，取两者中较大的（负值时取最负的再相加）。这是规范行为不是 bug，加权重没有任何作用。

   *怎么改*：现代布局优先用 `gap` 控制间距（只作用于容器内部子元素之间，不折叠）；需要阻止父子折叠时给父元素 `display: flow-root`。

12. **用 overflow:hidden 顺手当 BFC** —— 错在：为了解决高度塌陷，给父元素加 `overflow: hidden`。

   *为什么*：`overflow: hidden` 确实建立了 BFC，但它同时会**裁剪溢出内容**——下拉菜单、tooltip、阴影全部被切掉，还可能改变滚动行为。副作用往往在几周后才被发现。

   *怎么改*：需要 BFC 就写 `display: flow-root`——这是专为此设计的值，没有裁剪副作用。团队规范里可以直接禁掉「用 overflow 建 BFC」。

13. **Flex 子元素加省略号不生效** —— 错在：给卡片里的文字加了 `text-overflow: ellipsis; white-space: nowrap; overflow: hidden`，省略号就是不出现。

   *为什么*：Flex 子元素的 `min-width` 默认是 `auto`，意思是「不能小于内容最小宽度」。长单词或长 URL 会强行撑开，元素根本没被压缩，省略号自然无从谈起。

   *怎么改*：给该子元素加 `min-width: 0`（列方向用 `min-height: 0`）。口诀：「Flex 里要省略号，先给 min-width: 0」。

14. **Grid 的 1fr 在长内容下撑破容器** —— 错在：写 `grid-template-columns: repeat(3, 1fr)`，以为就是三等分。

   *为什么*：`fr` 的默认最小值是 `auto`（内容最小尺寸），不是 0。某一列内容很宽时，该列会超过 1fr 的名义宽度，总宽超出容器，出现横向滚动条。

   *怎么改*：统一写 `repeat(3, minmax(0, 1fr))`。这一行应该形成肌肉记忆，几乎所有「Grid 三列崩掉」的案例答案都是它。

15. **漏写 viewport meta，移动端整页缩小** —— 错在：模板里忘了 `<meta name="viewport" content="width=device-width, initial-scale=1">`，桌面模拟器看着正常，真机上字特别小。

   *为什么*：缺这行时移动端按 980px 虚拟宽度渲染再整体缩放；部分桌面调试工具的模拟器会自动补上，所以本地看不出来，只有真机暴露。

   *怎么改*：模板里必须有这行。同时**不要**加 `user-scalable=no`——它禁用了缩放，视力不好的用户无法放大文字，是明确的无障碍反模式。
