# ai-ch14 · 多模态落地：图文对齐、OCR→VLM 流水线、多模态 RAG、成本与延迟 · 学习目标

- 能讲清「图文对齐与表征：CLIP 式对比学习、投影层、跨模态检索」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「OCR→VLM 流水线：文档理解链路与失败模式」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「多模态 RAG 与成本/延迟：视觉检索增强、预处理成本、延迟预算」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 3 道编程题）与 9 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,266 | §1.1 CLIP · §2.1 流水线 | 多模态模型库：CLIP/Blip/Intern 实现，对应 §1.1、§2.1 |
| 2 | [openai/CLIP](https://github.com/openai/CLIP) | 34,539 | §1.1 对比学习 | 图文对比学习本体：读 `model.py` 的 image-text 对比，对应 §1.1 |
| 3 | [OpenGVLab/InternVL](https://github.com/OpenGVLab/InternVL) | 10,171 | §1.4 对齐 · §2.1 链路 | 多模态大模型：VLM 与 OCR 链路，对应 §1.4、§2.1 |
| 4 | [microsoft/OmniParser](https://github.com/microsoft/OmniParser) | 25,578 | §2.1 OCR→VLM | 文档理解：版面检测+识别+VLM 端到端，对应 §2.1 |

> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。

| # | 视频 | BV | 对应本章 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | 图文多模态｜GLIP：给AI附上理解文本、理解图像且定位的能力<br><sub>魔傀面具</sub> | [BV18ZyJBnE4E](https://www.bilibili.com/video/BV18ZyJBnE4E/) | §1.1 CLIP 式对比学习 | 时长 15m59s |
| 2 | 阿里发布最强中文图文多模态模型：Chinese CLIP<br><sub>数源AI官方</sub> | [BV1F14y1K7bu](https://www.bilibili.com/video/BV1F14y1K7bu/) | §1.1 图文对齐 | 时长 0m45s |

## 本章配套论文与书（溯源用）

> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。

| # | 文献 | 对应本章 |
| --- | --- | --- |
| 1 | 《Learning Transferable Visual Models From Natural Language Supervision》(CLIP, ICML 2021) —— 对应 §1.1 对比学习 | §1 |
| 2 | 《BLIP-2》(ICML 2023) 与《InternVL》(CVPR 2024) —— 对应 §1.4 对齐、§2.1 OCR→VLM 链路 | §1 · §2 |
| 3 | 《Dense X Retrieval》/ 多模态 RAG survey —— 对应 §3.1 多模态 RAG | §3 |
