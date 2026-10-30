# fs-ch12 · 服务拆分与网关：拆分判断、网关职责、配置中心 · 学习目标

- 能讲清「什么时候该拆：单体到微服务的触发条件与代价」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「网关的职责边界：该管什么、不该管什么」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「配置中心与动态配置：外置、隔离、热更新、密钥」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [spring-cloud/spring-cloud-gateway](https://github.com/spring-cloud/spring-cloud-gateway) | 4,917 | §2.1 网关该管什么 · §2.3 路由 | 网关实现：读 `RoutePredicateHandlerMapping` 与过滤器链，对应 §2.1、§2.3 |
| 2 | [nestjs/nest](https://github.com/nestjs/nest) | 76,927 | §1 拆分 · §2 网关 | 模块化后端框架：module/provider 的边界设计与 §1 分层异曲同工 |
| 3 | [vercel/next.js](https://github.com/vercel/next.js) | 143,173 | §2.6 BFF | BFF 范式：前端定制的聚合层，对应 §2.6 BFF 模式 |
| 4 | [google/guava](https://github.com/google/guava) | 51,918 | §3.5 配置中心 | 限流与缓存原语：RateLimiter 思路对应 §2.5 限流、§3.5 配置推送 |

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
