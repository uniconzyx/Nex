# ai-ch12 · SFT 数据工程：任务 schema、合成数据过滤、去重与污染、难例挖掘、标注一致性 Kappa · 学习目标

- 能讲清「任务 schema 与指令设计：从一句话需求到可训练样本」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「合成数据过滤与去重/污染：规则、语义、留验隔离」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「难例挖掘与标注一致性：hard negative 与 Cohen's Kappa」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 2 道编程题）与 10 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.2 二、为什么需要 schema 与模板三层 | 读 `src/transformers/tokenization_utils_base.py` 的 `apply_chat_template`：它按角色拼 token、并用 `{% generation %}` 段标出该算 loss 的部分，非 assistant 内容置 -100——本章「模板三层」的第三层就在这里；配合 `src/transformers/models/llama/tokenization_llama.py` 的具体模板，就能把「格式漂移」追溯到模板版本变更 |
| 2 | [huggingface/datasets](https://github.com/huggingface/datasets) | 22,091 | §2.1 一、前两段：规则过滤与语义去重 | 读 `src/datasets/arrow_dataset.py` 的 `map`/`filter`：`filter` 支持 `batched=True` 与多进程，正是本章「先按规则粗筛、再做语义去重」两段流水线要的吞吐能力；配合 §2.3「三、工程判据」，就知道去重阈值该怎么定才不至于把长尾样本一起删掉 |
| 3 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 96,022 | §3.1 一、难例挖掘与 Kappa 的必要性 | 读 `vllm/v1/engine/llm_engine.py` 的批量接口：用强模型批量生成候选、再用规则或弱模型打分，是本章「合成数据规模化」的常见流水线；但生成质量要靠 §2.2「二、污染检测与留验隔离」守——强模型见过的题会被它自己答对，混进训练集就是污染 |
| 4 | [facebookresearch/llama](https://github.com/facebookresearch/llama) | 59,628 | §1.1 一、schema 样例、配比与格式漂移事故 | 读 `README.md` 里给出的对话格式：`[INST]` / `<<SYS>>` 标记与角色轮次是硬约定，换一个模板而不同步改数据，就是本章「格式漂移事故」的经典形态；先读 §1.2 的三层模板，再对照这份 README，就能把「schema 是什么」落到具体字符上 |

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
