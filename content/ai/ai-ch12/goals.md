# ai-ch12 · SFT 数据工程：任务 schema、合成数据过滤、去重与污染、难例挖掘、标注一致性 Kappa · 学习目标

- 能讲清「任务 schema 与指令设计：从一句话需求到可训练样本」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「合成数据过滤与去重/污染：规则、语义、留验隔离」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「难例挖掘与标注一致性：hard negative 与 Cohen's Kappa」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 2 道编程题）与 10 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.1 schema · §1.8 标注规范 | 训练数据范式：chat template 与 instruction 格式，对应 §1.1、§1.8 |
| 2 | [huggingface/datasets](https://github.com/huggingface/datasets) | 22,091 | §2.2 语义去重 | 数据处理：map/dedup 算子，对应 §2.2 语义去重 |
| 3 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 96,022 | §1.8 可追溯 | 推理侧数据契约：与训练数据 schema 对齐，对应 §1.8 |
| 4 | [facebookresearch/llama](https://github.com/facebookresearch/llama) | 59,628 | §1.1 多轮格式 | 对话格式范本：官方 `llama-recipes` 的 instruction 数据，对应 §1.1 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 【原理】如何构造微调数据集？对话数据、指令数据、Function call<br><sub>九天Hector</sub> | [BV1XXVHzYEK2](https://www.bilibili.com/video/BV1XXVHzYEK2/) | §1.1 可落地的 schema | 时长 25m25s |
| 2 | 大模型微调！手把手带你用LLaMA-Factory工具微调Qwen大模型<br><sub>大语言模型教程</sub> | [BV1Q8rYYdErf](https://www.bilibili.com/video/BV1Q8rYYdErf/) | §1.8 质量标注规范 | 时长 34m36s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | 《Training Language Models to Follow Instructions with Human Feedback》(InstructGPT, NeurIPS 2022) —— 对应 §1.1 schema、§1.8 标注 | §1 · §1.8 |
| 2 | 《Self-Instruct》(ACL 2023) —— 对应 §1.8 合成数据生成 | §1.8 |
| 3 | 《LIMA: Less Is More for Alignment》(NeurIPS 2023) —— 对应 §1.1 格式约束、§2.1 规则过滤 | §1 · §2 |
