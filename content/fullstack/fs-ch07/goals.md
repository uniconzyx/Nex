# fs-ch07 · 全栈项目实战（GitHub 资源驱动）· 学习目标

## 学习目标
完成本章后，你能：
1. 按「依赖方向单一、shared 只放纯逻辑、契约置于依赖图下游」三条硬规则组织一个全栈仓库的分层目录（`apps/web`、`apps/api`、`packages/shared`、`packages/contract`），并说清 monorepo 与 multirepo 的取舍。
2. 用契约优先（design-first）的思路，从一份 OpenAPI schema 同时生成前端类型、服务端校验器与 CI 契约断言；并能对请求体与响应体做**双向** schema 校验（正反用例各一组）。
3. 区分服务端状态与客户端状态，为两者选择正确工具，并说出「把所有状态塞进全局 store」的三类具体代价。
4. 实现服务端状态的三种核心能力：请求去重与取消（并发同 key 只发 1 次）、乐观更新与失败回滚、分页合并（乱序到达下 id 去重 + 稳定顺序），并用布尔判据验证。
5. 用 TTL / stale-while-revalidate 设计缓存失效策略，并解释 `fresh` / `stale` / `expired` 三态的边界（用整数逻辑时钟给出精确的时序判据）。
6. 用 normalize / denormalize 消除服务端返回中的实体冗余，并证明往返无损（`roundtrip_equal=true`）。
7. 设计组件之间的状态流动：受控/非受控的判定、状态提升、Context 与 props drilling 的取舍，并说出 Context 的性能代价。
8. 实现表单校验的前后端双重防线：前端拦体验、后端守边界，二者共享同一份 schema，错误按字段路径（JSON Pointer 风格）定位。
9. 把数据驱动视图建模为 `loading / success / empty / error` 四态状态机，覆盖可重试与不可重试错误、部分失败隔离与异步错误处理。
10. 用四把性能刀优化前端：代码分割与懒加载（部件级分割点）、列表虚拟化（O(1) 渲染窗口）、请求去重与取消、优先级队列 + 并发上限（峰值不超限）。
11. 掌握可访问性基础四件事（语义化标签、可访问名、表单关联、键盘可达），并能用**静态遍历**自动判定 `img-alt`、`button-name` 两类硬约束。
12. 具备「读得懂大厂源码」的能力：按「入口 → 路由 → 数据层 → 组件树 → 契约」五步走通一个陌生全栈仓库，并从 `trekhleb/javascript-algorithms`、`Chalarangelo/30-seconds-of-code`、`yangshun/front-end-interview-handbook` 三个范式仓库中各练一种读法。

## 前置
- **fs-ch03 JavaScript 核心**（异步 Promise/async、事件循环、模块、闭包）——本章的请求去重/取消、乐观更新、状态机全部建立在这些语言机制之上。
- **fs-ch05 数据库与 REST API 设计**（REST 资源语义、分页（游标）、请求校验、OpenAPI、Problem Details）——本章把 fs-ch05 的后端契约接到前端数据层，游标分页与校验规则直接复用。


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch03 与 fs-ch05；不要求预先掌握任何具体前端框架（React/Vue 等），所有示例用**纯函数与纯 JS 数据流**表达框架无关的工程模式，装不上框架也能跑。

## 真题依据（真实可查，仅存元数据）
- GitHub 资源（见 `_manifest.json`）：trekhleb/javascript-algorithms（196855★）、Chalarangelo/30-seconds-of-code（129326★）、yangshun/front-end-interview-handbook（44008★）。
- LeetCode 题仅存元数据与链接，不搬运题面正文，详见 `exercises.json`。
- 规范原文：RFC 9457（Problem Details for HTTP APIs）、RFC 9110（HTTP Semantics）、OpenAPI Specification 3.1.0、WCAG 2.2（WAI-ARIA 1.2）。

## 验收标准
- 给出一个全栈功能的目录草图，能指出任何一处反向依赖并说明为什么违反依赖 DAG 不变量。
- 给定一份请求 schema，能写出一组合法样例与 ≥6 类非法样例（缺必填/下界/正则/类型/上界/多余字段），并断言「合法全过、非法全拒」且每个错误带字段路径。
- 给定一段「把所有状态放全局 store」的伪代码，能指出其中至少两类状态放错了位置，并给出正确归属。
- 能实现并断言：并发同 key 请求只发 1 次（`sent_while_inflight=1`）；乐观更新成功保留、失败回滚（`success_count_kept=true` 且 `failure_state_restored=true`）。
- 能给出 TTL/SWR 的状态序列（`fresh → stale → expired`）并解释 `stale` 仍返回旧值、`expired` 返回 `null` 的区别。
- 能实跑 normalize/denormalize 并证明往返无损，同时给出实体去重前后数量（`dedup_saved`）。
- 能写出一份四态状态机，使非错误态的 `RETRY` 是幂等无操作、错误态的 `RETRY` 回到 `loading`。
- 能用虚拟化窗口公式算出给定 `scrollTop` 下的渲染区间，并保证 `end ≤ total`（不越界）。
- 能实现优先级队列 + 并发上限，并断言峰值并发不超过上限（`max_concurrency_respected=true`）。
- 能对一棵组件描述树做静态遍历，输出懒加载分割点与两类 a11y 违规。
- 能在半天内对任一 GitHub 全栈仓库写出「入口 → 路由 → 数据层 → 组件树 → 契约」的数据流笔记。
