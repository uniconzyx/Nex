# fs-ch13 · 前端测试与质量门禁：测试金字塔、E2E、契约测试 · 学习目标

- 能讲清「测试金字塔：分层策略与测试替身」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「E2E 与组件测试：稳定性与选择器策略」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「契约测试与质量门禁：消费者驱动契约与 CI 门禁」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [microsoft/playwright](https://github.com/microsoft/playwright) | 98,704 | §2.1 一、稳定的两条铁律 | 读 `microsoft/playwright` 的 `docs/src/api/class-page.md` 里 auto-waiting 与 actionability checks 两节：可见、稳定、可接收事件三个条件同时满足才动手，等于把 `sleep` 换成「等状态」——这就是本节「两条铁律」的第一条；第二条「只断言用户可见的结果」则对应它强调的 locator 语义（按 role/label 定位而非 DOM 路径） |
| 2 | [cypress-io/cypress](https://github.com/cypress-io/cypress) | 51,015 | §2.3 三、flaky 归因、工具差异与可观测 | 读 `cypress-io/cypress` 的 `packages/driver/src/cy/commands/actions/click.ts`：时间旅行调试靠命令队列快照把每条命令执行后的 DOM 存下来，失败时能回放到出错那一步——与 Playwright 用 trace 达到的是同一目的；本节「工具差异」的关键不在 API，而在「失败时你能看到哪一刻的状态」 |
| 3 | [pact-foundation/pact-js](https://github.com/pact-foundation/pact-js) | 1,825 | §3.3 三、Pact 工作流与契约演进 | 读 `pact-foundation/pact-js` 的 `src/index.ts`：mock server 按消费者写的期望返回并生成 pact 文件，提供方用 `Verifier` 回放同一份契约——「契约是产物，不是文档」；本节 §3.1 讲的「值在哪」也由此落地：契约文件可以进 CI 当门禁（§3.2），而文档不能 |
| 4 | [facebook/react](https://github.com/facebook/react) | 251,766 | §2.2 二、组件测试与测试卫生 | 读 `facebook/react` 的 `packages/react/src/` 下 `jsx/__tests__/` 等测试目录：框架自身的测试配 `scripts/jest` 的自定义环境，断言的是渲染出来的树而非实现细节——这正是本节「组件测试该断言的层次」；反过来说，一旦测试里出现对内部 state 变量名的断言，它就已经从组件测试退化成实现测试 |

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
