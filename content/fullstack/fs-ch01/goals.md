# fs-ch01 · Web 工作原理：HTTP 与浏览器-服务器交互 · 学习目标

> 本章是**全栈的第 1 章**，回答一个前置问题：**在写第一行 HTML/CSS/JS 之前，一次网页访问到底发生了什么？**
> 它把「URL → DNS → TCP/TLS → HTTP 请求/响应 → 浏览器渲染」这条链路讲透，为后续
> fs-ch02（HTML/CSS）、fs-ch03（JS）、fs-ch04（Node 后端）、fs-ch05（REST）提供统一的**协议视角**。

## 学习目标

- 能画出**一次网页请求的完整链路**：URL 解析 → DNS 解析 → TCP 三次握手 →（TLS 握手）→ 发送 HTTP 请求 → 服务端处理 → 返回响应 → 浏览器解析渲染；并能说出每一段的大致耗时量级。
- 掌握 **HTTP 报文结构**：请求行/状态行、头部（Header）、空行、消息体；理解「文本协议」这一设计带来的可调试性。
- 掌握 **HTTP 方法的语义**：GET/POST/PUT/PATCH/DELETE 的**安全性（safe）**与**幂等性（idempotent）**，以及为什么这两个性质对缓存、重试、爬虫至关重要。
- 掌握 **状态码的五类语义**（1xx/2xx/3xx/4xx/5xx），能区分 301/302/307/308、401/403、502/503/504 的工程差别。
- 理解 **HTTP 头部大家族**：内容协商（Accept/Content-Type）、缓存（Cache-Control/ETag/Last-Modified）、认证（Authorization）、Cookie（Cookie/Set-Cookie）。
- 理解 **HTTP 无状态（stateless）**这一本质，以及 Cookie / Session / Token 三种「在无状态协议上模拟状态」的方案及其安全属性（HttpOnly / Secure / SameSite）。
- 理解 **同源策略与 CORS**：为什么需要预检（OPTIONS）、为什么「前端加个头」解决不了跨域。
- 会用**浏览器开发者工具 Network 面板**读懂一次请求：General / Request Headers / Response Headers / Timing。

## 先修与衔接

- **先修**：无（本章是全栈起点，只需会基本命令行操作）。
- **后续衔接**：
  - → fs-ch02：HTML/CSS 负责「响应体的结构」与「渲染表现」。
  - → fs-ch03：JavaScript 负责「浏览器端的请求发起（fetch/XHR）」与事件循环。
  - → fs-ch04：Node.js 负责「服务端如何接收请求、生成响应」。
  - → fs-ch05：REST API 设计 = HTTP 方法 + 资源 URL + 状态码的规范化组合。
  - → tooling-ch01：DNS/TCP 的更底层细节（进程、socket、文件描述符）见工程工具学科。

## 面试权重

**高**（后端/全栈/前端岗必考）。高频问题集中在：

1. 「输入 URL 到页面展示发生了什么」——考察**链路完整性与分层思维**，是最经典的开场题。
2. HTTP 方法的幂等性/安全性——考察你**是否真理解协议语义**（而非会用 `axios.get`）。
3. 状态码辨析（301 vs 302 vs 307；401 vs 403；502 vs 503 vs 504）。
4. 强缓存 vs 协商缓存、`Cache-Control` 指令、ETag 生成方式。
5. Cookie / Session / Token(JWT) 的对比与安全属性。
6. CORS 预检请求与简单请求的边界。

## 学完能做什么

- 打开任意网页，在 Network 面板里**独立读懂**一次请求-响应的每一层细节，并能定位「为什么这个请求慢/为什么这个接口 401」。
- 手写一个最小 HTTP 服务端与客户端（Node.js 原生 `http` 模块），亲眼看请求行、头部与状态码在两端的样子。
- 为后续 REST API 设计打下**协议正确性**的基础（方法用对、状态码用对、缓存用对）。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376,373 | 全章 | 系统设计入门：HTTP/API/缓存/CDN/负载均衡的工程视角（英文） |
| 2 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186,408 | 全章 | 技术面试必备基础知识：计算机网络与 HTTP 专题的中文精华笔记 |
| 3 | [nodejs/node](https://github.com/nodejs/node) | 122,410 | 全章 | Node.js 运行时：lib/http.js 为标准库 HTTP 实现，本章示例即基于其公开 API |
| 4 | [hoppscotch/hoppscotch](https://github.com/hoppscotch/hoppscotch) | 80,699 | 全章 | 开源 API 调试工具：可直接观察请求头/响应头，配合本章 Network 面板学习 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | 全章 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（URL 的解剖）核对 |
| 2 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | §1.1 HTTP 是「无状态的文本… | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex02`（最小 HTTP 往返）核对 |
| 3 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | §1.1 HTTP 是「无状态的文本… | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex03`（HTTP 报文结构）核对 |
| 4 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex04`（状态码的五类语义与可重试判定）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 4 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
