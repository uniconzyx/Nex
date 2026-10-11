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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 373461 | 系统设计入门：HTTP/API/缓存/CDN/负载均衡的工程视角（英文） |
| [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186392 | 技术面试必备基础知识：计算机网络与 HTTP 专题的中文精华笔记 |
| [nodejs/node](https://github.com/nodejs/node) | 122410 | Node.js 运行时：lib/http.js 为标准库 HTTP 实现，本章示例即基于其公开 API |
| [hoppscotch/hoppscotch](https://github.com/hoppscotch/hoppscotch) | 80581 | 开源 API 调试工具：可直接观察请求头/响应头，配合本章 Network 面板学习 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-10-07) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |
