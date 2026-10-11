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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) | 196855 | JavaScript 算法与数据结构，含英文详解 |
| [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129326 | 短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧 |
| [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44008 | 前端面试手册：HTML/CSS/JS/浏览器/性能 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |
