# fs-ch02 · 前端基础：HTML 语义化与 CSS 盒模型/布局 · 学习目标

## 学习目标
完成本章后，你能：
1. 用**语义化标签**（`header/nav/main/article/section/aside/footer` 等）组织页面骨架，理解其对可访问性（a11y）与 SEO 的意义。
2. 说清**浏览器渲染管线**（解析→样式计算→布局→绘制→合成）每一步在做什么、由哪个线程执行，以及 JS 在其中的位置。
3. 精确计算 **CSS 盒模型**（content/padding/border/margin）在 `content-box` 与 `border-box` 下的尺寸差异，并默认使用 `border-box`。
4. 解释 **BFC（块级格式化上下文）** 的触发条件，并用它解决浮动塌陷、外边距折叠、多列等高问题。
5. 掌握现代布局 **Flexbox（一维）与 Grid（二维）**，能实现居中、圣杯/双栏等常见布局。
6. 用**媒体查询 + 流式单位**实现响应式布局，理解 `viewport` 标签的作用。

## 前置
- fs-ch01 Web 工作原理：HTTP 协议与浏览器-服务器交互（一次请求的完整链路、报文与状态码、缓存与 Cookie/CORS）——本章负责其中的**响应体结构**与**渲染表现**部分。

## 真题依据（真实可查，仅存元数据）
- MDN / WHATWG 标准：HTML Living Standard、`box-sizing`、`BFC` 相关章节。
- LeetCode 344 反转字符串（`reverse-string`）作为算法素养补充（详见 exercises.json，不在此复述题面）。

## 验收标准
- 能独立写出一个语义正确、带 landmark、可访问的静态页面骨架。
- 给定任意 `width/padding/border/box-sizing`，能口算/笔算元素总占位宽与内容区宽。
- 能指出一段布局代码里的「强制同步布局（layout thrashing）」并给出修复。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-11-02** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [w3c/csswg-drafts](https://github.com/w3c/csswg-drafts) | 4,901 | §2.2 二、实现机制：`content-box` vs `border-box` | 读 `w3c/csswg-drafts` 的 `css-box-3/Overview.bs`，再读同仓 `css-display-3/Overview.bs` 里 flow-root 生成 BFC 的条文：「margin 为什么穿透父元素」在规范里是定义，不是经验——本章 §2.3「BFC：块级格式化上下文」之所以能当「补丁」用，就是因为规范把「谁与谁参与同一个格式化上下文」写成了可判定的条件 |
| 2 | [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129,352 | §4.4 四、工程实践 | 读 `Chalarangelo/30-seconds-of-code` 的 `snippets/` 下带 `css` / `browser` 标签的条目（水平垂直居中、等分布局、清除浮动）：每条都是可直接粘的最小实现，正好对照本章 §4.2「实现机制：Flexbox」与 §4.3「Grid」——同一件事在 flex 时代只需三行，在 float 时代要一个 clearfix 加一个负 margin，这个差就是「一维 vs 二维」判据的实际收益 |
| 3 | [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44,008 | §3.3 三、Reflow / Repaint / Composite-only 的区别（面试高频） | 读 `yangshun/front-end-interview-handbook` 的 `questions/html-questions.md` 与 `questions/css-questions.md`：前者用「全 div 堆出来的页面哪里坏了」讲语义化，后者把 reflow / repaint / 合成层分开问——与本章 §1.1「语义化不是好看，而是机器可读」、§3.3 的判据一一对应；注意题库里对「transform 为什么不触发 reflow」的回答，正是本节「合成层只改图层属性」的直接推论 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | §4.6 可运行示例 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（语义化页面骨架）核对 |
| 2 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex02`（标题层级与文档大纲（h1-h6 不可跳级）核对 |
| 3 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | §2.6 可运行示例 | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex03`（content-box 与 border）核对 |
| 4 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | 全章 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex04`（盒模型占位）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
