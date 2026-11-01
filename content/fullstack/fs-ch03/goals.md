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
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) | 196,715 | 全章 | JavaScript 算法与数据结构，含英文详解；本章先读与「值与类型」「相等性三兄弟」相关的部分 |
| 2 | [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129,384 | 全章 | 短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧；本章先读与「值与类型」「相等性三兄弟」相关的部分 |
| 3 | [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44,006 | 全章 | 前端面试手册：HTML/CSS/JS/浏览器/性能；本章先读与「值与类型」「相等性三兄弟」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | §3.1 原型链 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（typeof 对 7 种原始类型与对象/）核对 |
| 2 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | 全章 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex02`（== / === / Object.is）核对 |
| 3 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex03`（var 提升、let/const 的 T）核对 |
| 4 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | 全章 | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex04`（作用域闭包与循环 var 经典坑（let）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
