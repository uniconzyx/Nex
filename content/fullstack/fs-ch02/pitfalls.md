# fs-ch02 易错点（Pitfalls）

1. **忘记 `viewport` 标签** —— 移动端页面按默认约 980px 视口缩放，字体极小需双指放大。务必在 `<head>` 加 `<meta name="viewport" content="width=device-width, initial-scale=1">`。

2. **盒模型尺寸算错（content-box 陷阱）** —— 默认 `content-box` 下 `width` 不含 `padding/border`：设 `width:200px` 又加 `padding:16px; border:2px` 实际占 236px（见 ex10 Node 实测），导致换行/溢出。✅ 全局 `* { box-sizing: border-box; }`，让 `width` 即总宽。

3. **用一堆 `<div>` 拼结构忽略语义** —— 损害 SEO 与读屏体验，`<div class="nav">` 对辅助技术只是无名方块。✅ 用 `header/nav/main/article/section/aside/footer` 等地标标签。

4. **外边距塌陷（margin collapse）** —— 相邻兄弟或「父 margin-top 与首子 margin-top」会取较大值合并为一个，不是简单相加。✅ 用 `padding`/`border`/`overflow:hidden`/`display:flow-root` 阻断（计算见 ex11）。

5. **浮动导致父容器高度塌陷** —— 子元素 `float` 后脱离普通流，父容器高度为 0，背景/边框不包住。✅ 父容器建立 BFC：`display:flow-root` 或 `overflow:hidden`（注意裁切副作用）。

6. **选择器优先级误判** —— 写了 `.btn{color:red}` 却被 `button{color:blue}` 覆盖，因标签选择器特异性低。✅ 用类选择器、提高特异性，别急着 `!important`；优先级 `(a=ID,b=类/属性/伪类,c=标签)` 逐位比较。

7. **强制同步布局（layout thrashing）** —— 循环里交替读 `offsetHeight` 等布局属性与写样式，每轮都触发重排，页面巨卡。✅ 批量读、批量写，或用 `requestAnimationFrame` 对齐帧（见 concept/03）。

8. **滥用 `will-change` 制造过多合成层** —— `will-change:transform` 会给元素开独立 GPU 图层，乱用耗尽显存、反而更卡。✅ 仅对真正持续动画的元素使用，动画结束移除。
