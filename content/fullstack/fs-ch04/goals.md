# fs-ch04 · Node.js 与后端 API · 学习目标

## 学习目标
完成本章后，你能：
1. 说清 **Node 运行时模型**：单线程 JS 调用栈 + libuv 事件循环六阶段 + 线程池分工，解释「为什么 Node 适合 I/O 密集、不适合 CPU 密集」。
2. 精确预测 **事件循环顺序**：sync → process.nextTick → Promise.then → setImmediate / setTimeout（宏任务），并解释 nextTick 与微任务的优先级关系与微任务饥饿。
3. 用 **内置 http 模块从零手写迷你 REST 服务器**：方法+路径路由表、路径变量 `/items/:id`、JSON body 解析、查询串解析、状态码语义，并意识到框架只是这层封装。
4. 实现 **中间件链**：compose、next 传递、洋葱模型，并写出「四参数错误中间件」且正确处理 async 抛错（必须 next(err)）。
5. 讲清 **流与背压**：highWaterMark、write() 返回值 false、drain 事件，理解 pipe() 自动背压与「按字节切分 Buffer 会乱码」的根因。
6. 辨析 **CommonJS 与 ESM**：模块包装、exports/module.exports 关系、require 缓存、循环依赖差异，并能在新项目正确选型。
7. 用 **worker_threads** 卸载 CPU 密集任务、用 cluster 利用多核，说清二者（线程/进程、内存共享/独立）的边界。
8. 用 **EventEmitter** 组织事件（on/once/error），理解错误事件必须被监听否则进程崩溃。

## 前置
- fs-ch02 前端基础（HTTP/浏览器-服务器交互）+ fs-ch03 JavaScript 核心（异步/Promise/事件循环）——本章在其事件循环基础上进入「后端运行时与 API」。

## 真题依据（真实可查，仅存元数据）
- Node.js 官方文档：Events、Stream、Worker threads、HTTP、Buffer、Modules（CJS/ESM）。
- LeetCode 1 two-sum（算法素养补充，见 exercises.json，仅存元数据与链接，不抄题面）。

## 验收标准
- 给定一段含 nextTick/Promise/setImmediate/setTimeout 的代码，能写出确定的打印顺序。
- 能不依赖任何框架手写一个含路由、路径变量、JSON body、正确状态码的 REST 服务器。
- 给定一段内存膨胀的流代码，能指出背压缺失并修复（检测 write 返回值 / drain）。
- 能口述 CommonJS 循环依赖为何拿到 undefined、ESM 为何更安全。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-11-02** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [nodejs/node](https://github.com/nodejs/node) | 123,194 | §1.2 二、process.nextTick / Promise.then / setImmediate 三者顺序 | 读 `nodejs/node` 的 `lib/internal/process/task_queues.js`：它是 nextTick 与微任务队列的真实调度，配合 `lib/internal/streams/readable.js` 里 `highWaterMark` 与 `readableFlowing` 的状态迁移，就构成本章 §3.1「Stream 流控与背压」的机器版本；先看 §1.1 的六阶段图，再看这份调度代码，才会明白「nextTick 在自己那一层内递归，能把事件循环饿死」 |
| 2 | [expressjs/express](https://github.com/expressjs/express) | 69,585 | §2.1 一、从零手写 HTTP 服务器（路由 / 路径变量 / JSON body / 状态码） | 读 `expressjs/express` 的 `lib/application.js`：`app.use` 把中间件压进栈、`app.handle` 作为 `http.createServer` 的回调把 req/res 交出去；四参数错误中间件的识别就发生在这一层——它靠 `fn.length === 4` 判断，这个「用参数个数编码语义」的做法正是本章 §2.3「中间件模型与 compose」的起点 |
| 3 | [koajs/koa](https://github.com/koajs/koa) | 35,683 | §2.2 可运行代码：compose 的洋葱模型 | 读 `koajs/koa` 的 `lib/application.js`：它的 `callback()` 用 `compose(this.middleware)` 把数组折成嵌套函数，`await next()` 前后各写一段——这就是 §2.3「进去一层、出来一层」的原始代码；对照 express 的「线性 next()」，能看清 koa 的洋葱之所以可能，靠的是 async/await 的 Promise 链，而不是回调栈 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | §2.1 从零手写 HTTP 服务器 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（事件循环阶段顺序）核对 |
| 2 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | §1.1 Node 单线程模型与 l… | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex02`（用内置 http 从零手写迷你 REST）核对 |
| 3 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | §2.1 从零手写 HTTP 服务器 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex03`（手写中间件链）核对 |
| 4 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex04`（流与背压）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
