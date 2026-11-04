# fs-ch14 · Agent × 全栈工程接缝：流式、长任务、幂等与成本 · 学习目标

- 能讲清「流式响应穿过网关：透传、背压与取消」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「长任务状态与断线重连：任务 id、幂等与进度持久化」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「工具调用的幂等与审计：唯一 id、重试幂等与不可篡改日志」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「成本与限流：token 计量、租户限流与降级预算」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 8 道题（含 2 道编程题）与 10 条错题辨析，并能复述 6 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [vercel/ai](https://github.com/vercel/ai) | 27,560 | §1.1 SSE 与 WebSocket 在协议层的差别 | 读 `vercel/ai` 的 `packages/ai/src/generate-text/stream-text.ts`：它把模型增量转成 data stream 协议（`0:"文本"` 这种带前缀的行），工具调用带 `toolCallId`——本节「SSE 之所以够用」的原因就在这里：单向、可断点续传、走普通 HTTP；而本章 §3.1「每次工具调用都要有唯一 id」的来源也正是这个协议字段 |
| 2 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 148,796 | §2.5 幂等恢复：同一个 id 可以重入 | 读 `langchain-ai/langchain` 的 `libs/core`：`Runnable` 组合子与 `with_retry` 让重试只重放同一次调用，跨轮状态由外层 graph / checkpoint 保存——这就对应本节「同一个 id 可以重入」；关键区别是「重试」与「重入」的边界：重试假设副作用没发生，重入必须假设可能已发生，所以要有 §3.2 的去重记录 |
| 3 | [gin-gonic/gin](https://github.com/gin-gonic/gin) | 89,466 | §1.2 网关透传流式的三种实现路径 | 读 `gin-gonic/gin` 的 `context.go` 的 `Stream` 方法与 SSE 相关中间件：逐块 flush 的最小实现（不设 `Content-Length`、显式 `Flush`）；这正是本节「三种实现路径」里最直接的一种；而 `middleware/` 里挂限流中间件正是本章 §4.3「三种经典限流算法」的落地位置——注意流式响应一旦开始，限流只能按「连接数」而不能按「请求数」计 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §4.1 token 计量：输入与输出分开算 | 读 `huggingface/transformers` 的 `src/transformers/tokenization_utils.py`：`encode` / `decode` 决定「一段文本值多少 token」，同一句中文不同 tokenizer 能差一倍——这就是本节「输入输出分开算」的前提；§4.4「降级与预算」里的预算阈值必须按实际 tokenizer 估，用字符数折算会在中文场景系统性低估 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 最新 Langchain1.0 入门【12】-Agent流式输出<br><sub>强哥学编程</sub> | [BV1sh1qBdEAp](https://www.bilibili.com/video/BV1sh1qBdEAp/) | §1.1 SSE 与流式透传 | 时长 15m42s |
| 2 | AI Agent 面试题：Agent 幂等性<br><sub>图灵AI大模型</sub> | [BV1UtTr6SE2v](https://www.bilibili.com/video/BV1UtTr6SE2v/) | §3.2 重试幂等 | 时长 5m15s |
| 3 | 怎么保证Agent工具幂等性？<br><sub>AI大模型-阿水</sub> | [BV1kKx76pEtm](https://www.bilibili.com/video/BV1kKx76pEtm/) | §3.1 唯一 id · §3.2 幂等 | 时长 4m0s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | 《Designing Data-Intensive Applications》第 11 章（流处理与一致性）—— 对应 §1 流式、§2 长任务状态 | §1 · §2 |
| 2 | OpenAI / Anthropic Function Calling 官方文档 —— 对应 §3.1 唯一 id、§3.2 幂等 | §3 |
| 3 | LangChain 官方文档《Streaming》《Tools》章节 —— 对应 §1.1、§3 | §1 · §3 |
