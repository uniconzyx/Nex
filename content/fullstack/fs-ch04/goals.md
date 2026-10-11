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
