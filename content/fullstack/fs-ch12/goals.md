# fs-ch12 · 服务拆分与网关：拆分判断、网关职责、配置中心 · 学习目标

- 能讲清「什么时候该拆：单体到微服务的触发条件与代价」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「网关的职责边界：该管什么、不该管什么」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「配置中心与动态配置：外置、隔离、热更新、密钥」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [spring-cloud/spring-cloud-gateway](https://github.com/spring-cloud/spring-cloud-gateway) | 4,917 | §2.1 一、职责边界：该管与不该管 | 读 `spring-cloud/spring-cloud-gateway` 的 `RoutePredicateHandlerMapping` 与同模块的过滤器链：谓词决定「这个请求归哪条路由」，过滤器链决定「沿途改什么」——两段职责分开，就是本节「该管与不该管」的框架侧表达；本章 §2.2「四项核心能力与反模式」里的反模式，多半是把业务判断塞进了过滤器 |
| 2 | [nestjs/nest](https://github.com/nestjs/nest) | 76,927 | §1.1 一、先想清楚：为什么拆、按什么切 | 读 `nestjs/nest` 的 module/provider 模型：它的边界设计（一个 module 显式声明 imports/providers/exports）与本节「按什么切」的判据同构——能写清「这个模块对外只暴露哪几个 provider」的服务边界才是真的，写不清的其实就是「一组文件的命名空间」 |
| 3 | [vercel/next.js](https://github.com/vercel/next.js) | 143,173 | §2.2 二、四项核心能力与反模式 | 读 `vercel/next.js` 的中间件与 BFF 用法（`middleware.ts` 与 `app/api/` 路由）：BFF 是「为某一前端定制的聚合层」，而框架里的 middleware 只能改请求/响应、不能做重业务——这个能力边界正好划出本节「四项核心能力」里「聚合」与「编排」该放在 BFF、不该放进网关的那条线 |
| 4 | [google/guava](https://github.com/google/guava) | 51,918 | §3.1 一、外置、隔离、热更新与密钥 | 读 `google/guava` 的 `RateLimiter`：它是「令牌桶」的原语实现，而本节要讲的是「限流参数本身就是配置中心最常见的动态项」——把 `RateLimiter` 的速率做成可热更新的配置，就同时踩了「热更新」与「密钥/阈值治理」两条；注意 `RateLimiter` 是单机限流，集群维度要靠配置中心下发一致的配额 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | Spring Cloud Gateway过滤器执行优先级<br><sub>凉城昔忆iii</sub> | [BV1wC3zeTEmS](https://www.bilibili.com/video/BV1wC3zeTEmS/) | §2.3 路由的坑：匹配顺序 | 时长 3m30s |
| 2 | 2小时吃透GateWay微服务网关！<br><sub>图灵FOX老师</sub> | [BV11g4nznErU](https://www.bilibili.com/video/BV11g4nznErU/) | §2.1 网关该管什么 · §2.5 限流 | 时长 169m12s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | Sam Newman《Building Microservices》第 1、5 章（单块边界、服务拆分）—— 对应 §1 何时该拆 | §1 |
| 2 | 《Spring Microservices in Action》第 4 章 Gateway —— 对应 §2 网关职责 | §2 |
| 3 | Chris Richardson《Microservices Patterns》第 3 章（配置中心）—— 对应 §3 配置外置 | §3 |
