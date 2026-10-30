# fs-ch10 · Vue 3 + TypeScript + Pinia：响应式原理与 ref/reactive 边界 · 学习目标

- 能讲清「响应式原理与依赖追踪」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「ref 与 reactive 的边界」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「Pinia 状态管理与组合式 store」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 1 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [vuejs/core](https://github.com/vuejs/core) | 54,801 | §1.1 Proxy · §1.6 心智模型 | 响应式内核：读 `packages/reactivity/src` 的 `effect.ts` 与 `dep.ts`，依赖收集与触发正是 §1.1、§1.6 讲的那套 |
| 2 | [vuejs/pinia](https://github.com/vuejs/pinia) | 14,755 | §3.1 两种写法 | 状态管理实现：读 `src/store.ts` 的 `defineStore`，options 与 setup 两套入口对应 §3.1 |
| 3 | [vuejs/router](https://github.com/vuejs/router) | 4,706 | §2.1 路由 | 前端路由：历史模式与导航守卫，对应 §2.1 的路由边界 |
| 4 | [vuejs/rfcs](https://github.com/vuejs/rfcs) | 4,926 | §1.3 ref.value · §2.1 | RFC 文本：ref 必须 .value、响应式边界的设计讨论，直接对应 §1.3、§2.1 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 13.Vue 2.0和Vue3.0 响应式原理的区别<br><sub>程序员铁蛋儿</sub> | [BV1Zb4y1H7XY](https://www.bilibili.com/video/BV1Zb4y1H7XY/) | §1.1 Proxy 与依赖收集 | 时长 28m17s |
| 2 | 【前端面试必备】Vue2与Vue3核心之『响应式原理』<br><sub>野sir的AI世界1</sub> | [BV1Dk4y127Ha](https://www.bilibili.com/video/BV1Dk4y127Ha/) | §1.3 ref 必须 .value · §1.6 心智模型 | 时长 220m39s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | 霍春阳《Vue.js 设计与实现》第3章『响应式系统』—— 对应 §1.1、§1.6 | §1.1 · §1.6 |
| 2 | Vue 官方文档《Reactivity in Depth》—— 对应 §1 全章、§2 ref/reactive 边界 | §1 · §2 |
| 3 | TC39 `Proxy`/`Reflect` 规范与 Decorators 提案 —— 对应 §1.1 为什么是 Proxy | §1.1 |
