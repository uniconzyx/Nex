# fs-ch10 · Vue 3 + TypeScript + Pinia：响应式原理与 ref/reactive 边界 · 学习目标

- 能讲清「响应式原理与依赖追踪」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「ref 与 reactive 的边界」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「Pinia 状态管理与组合式 store」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 1 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [vuejs/core](https://github.com/vuejs/core) | 54,801 | §1.1 一、机制：Proxy 与依赖收集 | 读 `vuejs/core` 的 `packages/reactivity/src/effect.ts` 与同目录 `dep.ts`、`baseHandlers.ts`：`effect.ts` 建 effect 树、`dep.ts` 用 Set 存订阅者、`baseHandlers.ts` 在 get 时 `track`、set 时 `trigger`；再读 `computed.ts` 的 dirty 标记，就回答了本节 §1.2 里「computed 什么时候才重算」——只有依赖脏了才重算，否则直接返回缓存值 |
| 2 | [vuejs/pinia](https://github.com/vuejs/pinia) | 14,755 | §3.1 一、写法、依赖与 Vuex 对照 | 读 `vuejs/pinia` 的 `packages/pinia/src/store.ts`：`defineStore` 同时接受对象与函数两种入参，内部都归一成 reactive state + actions——这就是本节「两种写法不是两套机制」的源码依据；而 `storeToRefs` 是本章 §3.2「四个高频陷阱」里「解构丢响应式」的正解：直接解构 `const { count } = store` 会把 proxy 拆成裸值 |
| 3 | [vuejs/router](https://github.com/vuejs/router) | 4,706 | §2.1 一、选型与两个高频坑 | 读 `vuejs/router` 的 `src/router.ts`：守卫按 `beforeEach → 组件内钩子 → afterEach` 排序；路由切换后 store 该不该重置，取决于你把 store 放进守卫还是放进组件——本节「两个高频坑」里「跨路由共享的 store 状态残留」在这里有明确答案：守卫里 `store.$reset()` 能清，组件里 `onUnmounted` 只能清自己持有的那部分 |
| 4 | [vuejs/rfcs](https://github.com/vuejs/rfcs) | 4,926 | §1.3 三、调试、对照与取舍 | 读 `vuejs/rfcs` 的 `active-rfcs/` 下响应式相关提案（ref 拆包、reactivity transform）：这些讨论解释了为什么模板里不写 `.value`、JS 里必须写——本节「调试」那一半的工具（`effectScope` 的 on 钩子、`triggerRef`）之所以存在，也是因为这些提案没有走到「自动拆包所有场景」；这与 §2.3「设计取舍与跨框架对照」一起说明：边界是设计决议，不是实现巧合 |

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
