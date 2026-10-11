# fs-ch03 · JavaScript 核心：类型、原型链、DOM 与事件、异步(Promise/async) · 学习目标

## 学习目标
完成本章后，你能：
1. 区分**原始类型（7 种）与引用类型**，说清 `typeof` 的 7 种返回值与两个著名坑（`typeof null === 'object'`、`typeof fn === 'function'`）。
2. 掌握**相等性三兄弟**：`==`（隐式转换）、`===`（严格）、`Object.is`（处理 `NaN` 与 `+0/-0`），并能在工程里默认用 `===`。
3. 理清**作用域、变量提升与 TDZ**：`var` 提升并初始化为 `undefined`，`let/const` 存在暂时性死区；理解闭包的内存模型与循环 `var` 经典坑。
4. 讲清 **`this` 五条绑定规则**（默认 / 隐式 / 显式 / `new` / 箭头），并解释箭头函数为何没有自己的 `this`。
5. 推演**原型链查找**：`Object.create` 与 `class` 语法糖、`instanceof`、`Object.getPrototypeOf`、`hasOwnProperty`，以及 V8 隐藏类（shape/map）对属性访问的影响。
6. 精确描述**事件循环**：调用栈 / 宏任务 / 微任务的调度顺序，能用 `console.log` 确定性地预测 `Promise.then` / `queueMicrotask` / `setTimeout` / `await` 的输出次序。
7. 用 **Promise 与 async/await** 组织异步代码，正确捕获错误；辨析 `Promise.all / allSettled / race / any` 的差异与 reject 行为。
8. 在脑中模拟 **DOM 事件流**（捕获 / 目标 / 冒泡）与事件委托机制（本机无浏览器，用 Python 从零模拟）。

## 前置
- fs-ch02 前端基础：HTML 语义化与 CSS 盒模型/布局 —— 本章负责其中的**行为层（JavaScript）**，以及 DOM 树上的事件机制。

## 真题依据（真实可查，仅存元数据）
- MDN / ECMAScript 规范：类型、抽象相等比较算法（Abstract Equality Comparison）、Promise、Jobs and Job Queues。
- LeetCode 20 有效的括号（valid-parentheses）、LeetCode 2621 Sleep（async/await 实践），详见 exercises.json，仅存元数据与链接，不抄题面。

## 验收标准
- 给定任意 `typeof` 表达式或 `==` / `===` / `Object.is` 比较，能口算结果并解释原因。
- 给定一段含 `var/let` 循环闭包或 `this` 绑定的代码，能预测输出。
- 给定一段事件循环代码，能写出确定的输出顺序。
- 能独立写出一个带事件委托的小练习（用 Python 模拟亦可）。


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
