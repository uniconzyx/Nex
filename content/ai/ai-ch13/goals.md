# ai-ch13 · 推理引擎与量化部署：KV Cache 分页、continuous batching、GPTQ/AWQ/GGUF · 学习目标

- 能讲清「KV Cache 与分页注意力：显存账、碎片与复用」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「Continuous batching：从「凑批后算」到「迭代级调度」」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「量化取舍：GPTQ / AWQ / GGUF 权重量化」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 2 道编程题）与 9 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 95,746 | §1.1 显存账 · §2.2 连续批 | 推理引擎：读 `vllm/core/scheduler.py` 的 continuous batching，对应 §1.1、§2.2 |
| 2 | [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) | 132,583 | §3.4 GGUF | 本地推理与 GGUF 格式：量化权重加载，对应 §3.4 |
| 3 | [mlc-ai/mlc-llm](https://github.com/mlc-ai/mlc-llm) | 23,284 | §3.1 量化 · §3.5 选型 | 端侧推理与量化后端，对应 §3.1、§3.5 |
| 4 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,266 | §3.1 GPTQ/AWQ 加载 | 量化模型加载：bitsandbytes/GPTQ 集成，对应 §3.1 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 【2026最新版】这绝对是B站唯一将vLLM推理优化从入门到精通讲明白的<br><sub>码士集团-马小萱</sub> | [BV14YopBEEGs](https://www.bilibili.com/video/BV14YopBEEGs/) | §1.1 显存账 · §2.2 连续批 | 时长 1123m23s |
| 2 | vLLM验证AWQ和GPTQ量化后的模型以及GGUF介绍<br><sub>智驭导师授AI</sub> | [BV1tujozhEkF](https://www.bilibili.com/video/BV1tujozhEkF/) | §3.1 量化位宽 | 时长 16m7s |
| 3 | 【13】GPTQ、AWQ、GGUF等模型量化概念讲解<br><sub>LLM张老师</sub> | [BV1euPkerEun](https://www.bilibili.com/video/BV1euPkerEun/) | §3.2 GPTQ · §3.3 AWQ | 时长 18m15s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | 《Efficient Memory Management for LLM Serving with PagedAttention》(vLLM, SOSP 2023) —— 对应 §1.1 PagedAttention、§2.2 连续批 | §1 · §2 |
| 2 | 《Orca: A Distributed Serving System for Transformer-Based Generative Models》(OSDI 2022) —— 对应 §2.2 continuous batching | §2 |
| 3 | 《GPTQ: Accurate Post-Training Quantization》(ICLR 2023) 与《AWQ: Activation-aware Weight Quantization》(CVPR 2024) —— 对应 §3.1、§3.2 | §3 |
