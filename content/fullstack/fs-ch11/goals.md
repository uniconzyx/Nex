# fs-ch11 · Spring Boot 3 工程骨架：分层边界、异常与校验收口 · 学习目标

- 能讲清「分层边界与依赖方向」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「统一异常处理与错误码」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「校验与边界收口」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 1 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [spring-projects/spring-boot](https://github.com/spring-projects/spring-boot) | 81,722 | §1.1 三层与依赖方向 | `spring-boot-autoconfigure` 的 `AutoConfiguration.imports` + `@ConditionalOnMissingBean`：starter 只在你没自己声明时才装配——分层边界在框架里的落地方式 |
| 2 | [spring-projects/spring-framework](https://github.com/spring-projects/spring-framework) | 60,307 | §2.1 统一异常收口 · §2.2 匹配顺序 | `spring-webmvc` 的 `ExceptionHandlerExceptionResolver` 按 `@ExceptionHandler` 的匹配精度挑方法，`@ControllerAdvice` 的 `basePackages` / `assignableTypes` 决定它盖住哪些 Controller——§2.2 的作用域规则 |
| 3 | [spring-projects/spring-security](https://github.com/spring-projects/spring-security) | 9,653 | §2.3 可观测性 · §1.2 职责边界 | `FilterChainProxy` 在 DispatcherServlet 之前就拦掉未认证请求，`AuthenticationEntryPoint` 决定 401/403 的响应体——业务层拿不到原始异常，堆栈自然不会漏到前端（§2.4） |
| 4 | [openjdk/jdk](https://github.com/openjdk/jdk) | 23,477 | §3.2 边界与性能 | `java.util.regex.Pattern` 的回溯实现：`(a+)+$` 这类嵌套量词能把校验入口的 CPU 打满（ReDoS）——§3.2「校验也要限长限深」不是洁癖 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | SpringBoot全局异常处理<br><sub>莲城的老李</sub> | [BV1BZ4tzhEi5](https://www.bilibili.com/video/BV1BZ4tzhEi5/) | §2.1 @ControllerAdvice | 时长 11m36s |
| 2 | springboot如何优雅地统一异常处理和信息返回<br><sub>源码人生</sub> | [BV1924y1o7Sm](https://www.bilibili.com/video/BV1924y1o7Sm/) | §2.2 业务异常 vs 系统异常 · §2.3 错误码 | 时长 38m37s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | Craig Walls《Spring in Action》第 4、6 章（Web、AOP）—— 对应 §1 分层、§2 异常 | §1 · §2 |
| 2 | 汪云飞《Spring Boot 实战》第 6 章数据校验 —— 对应 §3 校验收口 | §3 |
| 3 | Spring 官方 Reference：Validation / Exception Handling 章节 —— 对应 §2、§3 | §2 · §3 |
