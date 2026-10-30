# fs-ch13 · 前端测试与质量门禁：测试金字塔、E2E、契约测试 · 学习目标

- 能讲清「测试金字塔：分层策略与测试替身」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「E2E 与组件测试：稳定性与选择器策略」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「契约测试与质量门禁：消费者驱动契约与 CI 门禁」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [microsoft/playwright](https://github.com/microsoft/playwright) | 98,704 | §2.1 等待条件 · §2.2 选择器 | E2E 框架：读 `docs` 的 auto-waiting 与 locator 策略，对应 §2.1、§2.2 |
| 2 | [cypress-io/cypress](https://github.com/cypress-io/cypress) | 51,015 | §2.8 选型 | 另一 E2E 实现：对比 Playwright 的时间旅行调试，对应 §2.8 |
| 3 | [pact-foundation/pact-js](https://github.com/pact-foundation/pact-js) | 1,825 | §3.1 消费者驱动契约 | 契约测试：读 `packages/.../message` 看 CDC 工作流，对应 §3.1 |
| 4 | [facebook/react](https://github.com/facebook/react) | 251,766 | §1 测试金字塔 | 组件测试范式：Testing Library 思路对应 §1、§2.3 组件测试 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 2小时学会playwright自动化测试框架<br><sub>AI智能测试平台</sub> | [BV1Fsx56CEsA](https://www.bilibili.com/video/BV1Fsx56CEsA/) | §2.1 稳定性第一原则 | 时长 89m44s |
| 2 | Playwright+Electron 自动化测试框架<br><sub>前端飞行手册</sub> | [BV1JQ3BzHEfC](https://www.bilibili.com/video/BV1JQ3BzHEfC/) | §2.2 选择器策略 | 时长 8m28s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | Kent Beck《Test-Driven Development》—— 对应 §1 测试金字塔理念 | §1 |
| 2 | 《Software Engineering at Google》第 11-12 章（测试规模与模式）—— 对应 §1、§3 门禁 | §1 · §3 |
| 3 | Jez Humble《Continuous Delivery》第 10 章（部署流水线门禁）—— 对应 §3.3 质量门禁 | §3 |
