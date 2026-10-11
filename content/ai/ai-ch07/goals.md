# ai-ch07 · Agent 开发：工具调用、记忆与多智能体

## 本章目标

学完本章，你应当能够：

1. **说清 Agent 的三要素**：目标（可判定的终止条件）、工具（可施加的动作集合）、循环（观察→思考→行动→再观察），并能指出「缺哪一要素会退化成什么」（见 ex01）。
2. **掌握 ReAct 范式**：Thought → Action → Observation 的交替结构，以及推理轨迹为什么能提升多跳任务的可靠性；能用 stub 工具离线跑通一个 ReAct 循环骨架（见 ex01）。
3. **按判据选架构**：单次工具调用 → ReAct → Plan-Execute → 多智能体四种模式的适用边界，牢记「**能用工作流（确定性 DAG）就别用 Agent**」——先问「步骤是否事先可知」，再决定要不要把控制权交给模型（见 ex03/ex09）。
4. **讲清 Function Calling 机制**：模型只产出结构化的调用意图（函数名 + JSON 参数），真正执行的是宿主程序；工具返回值会被回填进上下文进入下一轮（见 ex01/ex11）。
5. **按七条原则设计工具**：描述即提示词、参数强类型、返回精简、错误可行动、幂等、最小权限、危险操作人工确认；能写出 schema 校验器把幻觉参数挡在执行之前（见 ex02/ex06/ex07）。
6. **搭起三层记忆**：工作记忆（当前步骤草稿）、短期记忆（会话窗口）、长期记忆（跨会话事实），并会做写入触发、检索（相关度 + 新近度 + 重要性）与遗忘（LRU 容量淘汰 / TTL 过期 / 摘要压缩）（见 ex04/ex05）。
7. **会算预算与熔断**：给步数、token、工具调用次数、金额设硬上限，超限即熔断返回部分结果并如实告知，而不是无限重试烧钱（见 ex10）。
8. **识别多智能体的六种失败模式**：错误级联、通信爆炸、责任不清、循环死锁、一致性漂移、成本失控，并用「层级编排 + 显式状态机」给出工程解法，用消息签名去重检测循环（见 ex08/ex09）。
9. **理解 MCP 标准化与安全纵深防御**：用统一协议把「工具/资源/提示」暴露给任意宿主，降低 N×M 集成成本；同时按「输入净化 + 不可信内容隔离 + 工具权限隔离 + 人工确认」四层防提示注入（见 ex12）。

## 关键认知（本章最值钱的三句）

- **Agent = LLM 当决策器 + 工具当手 + 循环当心跳；没有可判定目标，循环就停不下来。** 先写清「什么算做完」，再谈智能。
- **能用工作流就别用 Agent。** 步骤事先可枚举 → 写确定性 DAG（可控、可测、便宜）；只有「下一步取决于上一步的观察」时才把控制权交给模型。
- **可靠性来自工程约束，不来自更聪明的提示词。** schema 强校验挡住幻觉参数、幂等键挡住重复副作用、预算熔断挡住成本失控、签名去重挡住死循环——这四件事比换模型更有效。

## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) | 187681 | 自主 Agent 的开创性项目，Agent 架构与工具循环的经典参考 |
| [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | 189309 | 为 AI Agent 提供网页数据：抓取到结构化数据的工程实现 |
| [langgenius/dify](https://github.com/langgenius/dify) | 157994 | Agentic 工作流与 RAG 流水线平台：生产级 LLM 应用工程范例 |
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 147524 | Agent 工程平台：工具、记忆、检索与编排的工业实现 |
| [huggingface/transformers](https://github.com/huggingface/transformers) | 167014 | Transformer 模型定义框架：工具调用模型的标准入口 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at` 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 小单说AI《从零实现 Agent》合集（9 期；含配套仓库 [TheSyart/claude-agent-examples](https://github.com/TheSyart/claude-agent-examples)、进阶 [emperor-agent](https://github.com/TheSyart/emperor-agent)） | [合集](https://space.bilibili.com/1452412374/lists/7764751?type=season) · [UP 主空间](https://space.bilibili.com/1452412374) | 从一次模型调用起，逐步加循环/history/system prompt/工具/Skills/记忆/规划/子代理/Team/MCP，对齐 ex01~ex12 |
| 马克的技术工作坊《Agent 概念、原理与构建模式》 | [空间](https://space.bilibili.com/1815948385/) | Agent 四组件、ReAct、构建模式，对齐 `concept/01`~`concept/02` |
| 《ReAct & CodeAct》工具调用的两种方法 | [BV1wXZfYRErX](https://www.bilibili.com/video/BV1wXZfYRErX/) | 工具调用与 Function Calling，对齐 ex02/ex11 |
| 《AI 智能体搭建教程》1 小时建立整体认知 | [BV11NNAz5EKn](https://www.bilibili.com/video/BV11NNAz5EKn/) | Agent 全貌速览，入门首选 |
| 《LLM 入门 + 提示词工程实战》 | [BV1n9CwYoEro](https://www.bilibili.com/video/BV1n9CwYoEro/) | LLM 能力与提示词基础，前置 ai-ch05 |

## 软前置（可选，不阻断学习）

- **ai-ch05（提示与上下文工程）**：本章的「工具描述即提示词」「ReAct 的 Thought 提示」「上下文预算」直接复用 ch05 的分层组织、位置策略与 token 预算方法。
- **ai-ch06（RAG）**：长期记忆的检索层与 RAG 的检索层同构（向量召回 + 重排）；把「知识库」换成「记忆库」即为本章的长期记忆。
- 本线**独立自足**：本章所有示例均为**离线可运行**（stub 工具 + 脚本化 LLM，不依赖网络与 API key）。

## 学习路径建议

1. 先跑 **ex01**（ReAct 骨架）建立直觉 → 再读 `concept/01`；
2. 再跑 **ex02/ex03**（schema 校验、工具路由）→ 读 `concept/02`；
3. 然后 **ex04/ex05**（三层记忆、遗忘）→ 读 `concept/03`；
4. 最后 **ex06—ex12**（幂等、可行动错误、循环检测、状态机、预算熔断、并行合并、注入防御）→ 读 `concept/04`；
5. 用 `project.json` 的综合项目把所有零件装成一台「可预算、可熔断、可防御」的 Agent。
