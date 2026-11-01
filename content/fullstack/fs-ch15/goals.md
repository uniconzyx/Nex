# fs-ch15 · Go + Gin 后端：并发模型、接口契约与 Java 路线对照 · 学习目标

- 能讲清「Goroutine 与 Channel：轻量并发与「不要通过共享内存通信」」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「Gin 路由与中间件：路由树、洋葱链与 Context」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「接口契约与错误处理：error 作为值与「消费者定义接口」」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 9 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [gin-gonic/gin](https://github.com/gin-gonic/gin) | 89,466 | §2.1 路由树 · §2.2 中间件 | Web 框架：读 `routergroup.go` 与 `context.go` 的 `Next()`，对应 §2.1、§2.2 |
| 2 | [gofiber/fiber](https://github.com/gofiber/fiber) | 40,232 | §2 对照 | Express 风格对照：与 Gin 中间件模型对比，对应 §2.6 |
| 3 | [golang/go](https://github.com/golang/go) | 139,482 | §1.1 goroutine · §3.1 error | 语言本体：读 `src/runtime` 的 GMP 调度，对应 §1.1；error 即值对应 §3.1 |
| 4 | [spring-projects/spring-framework](https://github.com/spring-projects/spring-framework) | 60,300 | §2.5 对照 · §3.4 对照 | Java 路线对照：拦截器/受检异常对照，对应 §2.5、§3.4 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 【最新Go Web开发教程】基于gin框架和gorm的web开发实战<br><sub>七米老师</sub> | [BV1gJ411p7xC](https://www.bilibili.com/video/BV1gJ411p7xC/) | §2.1 路由树 · §2.2 中间件 | 时长 727m56s |
| 2 | [面试]Gin框架在面试被问到最多的问题：动态路由&中间件<br><sub>guangju_</sub> | [BV1hv4y1h7Qn](https://www.bilibili.com/video/BV1hv4y1h7Qn/) | §2.2 中间件链 | 时长 4m13s |
| 3 | gin框架快速上手入门教程<br><sub>枫枫讲Go语言</sub> | [BV12JefzVEEy](https://www.bilibili.com/video/BV12JefzVEEy/) | §2.1 路由 | 时长 196m11s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | Alan Donovan《The Go Programming Language》第 8、9 章（goroutine、channel）—— 对应 §1 | §1 |
| 2 | 《Go in Action》第 3、4 章（并发与通道）—— 对应 §1.2、§1.3 | §1 |
| 3 | Go 官方《Effective Go》—— 对应 §3.1 error 作为值、§3.2 panic | §3 |
