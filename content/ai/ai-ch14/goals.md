# ai-ch14 · 多模态落地：图文对齐、OCR→VLM 流水线、多模态 RAG、成本与延迟 · 学习目标

- 能讲清「图文对齐与表征：CLIP 式对比学习、投影层、跨模态检索」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「OCR→VLM 流水线：文档理解链路与失败模式」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 能讲清「多模态 RAG 与成本/延迟：视觉检索增强、预处理成本、延迟预算」：说得出机制、写得出最小可运行代码、指得出它在本章示例与项目里的落点
- 完成本章 7 道题（含 3 道编程题）与 9 条错题辨析，并能复述 5 个面试高频问题的要点

## 本章 GitHub 学习路线（按阅读顺序）

> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | Star | 对应本章 | 读什么 |
| --- | --- | ---: | --- | --- |
| 1 | [huggingface/transformers](https://github.com/huggingface/transformers) | 168,400 | §1.1 一、对比学习与投影层 | 读 `src/transformers/models/llama/modeling_llama.py` 的最后一层投影：文本塔把隐状态投到词表空间，CLIP 把图文各投到同一对比空间，两者都是「先把表示拉到目标空间、再算相似度」；认识这一点，就能理解 §1.1 里「投影层与归一化决定能不能对齐」；对照 §1.2「二、检索与模态鸿沟」就明白为什么换塔必须重算索引 |
| 2 | [openai/CLIP](https://github.com/openai/CLIP) | 34,550 | §1.2 二、检索与模态鸿沟 | 读 `clip/model.py` 与 `clip/clip.py`：`build_model` 里视觉塔与文本塔各出一个向量，再经 `ln_final` 投影后做归一化点积——这就是「对比学习把两种模态拉到同一球面」；`clip.py` 的 `tokenize` 决定了文本侧输入长度上限，而视觉侧的分辨率上限在视觉塔里，两侧不对称正是「模态鸿沟」的来源 |
| 3 | [OpenGVLab/InternVL](https://github.com/OpenGVLab/InternVL) | 10,171 | §1.2 二、检索与模态鸿沟（续） | 读 `internvl_chat/README.md`：它给出了图像切块（dynamic tiling）后每块各占多少视觉 token，切得越细越准但成本线性上涨——这正是本章「鸿沟不只在语义，也在分辨率与 token 预算」的落点；配合 §3.1「一、形态与图像预处理成本」，就能把预处理成本算进端到端预算 |
| 4 | [microsoft/OmniParser](https://github.com/microsoft/OmniParser) | 25,578 | §2.1 一、链路拆解与成本口径 | 读 `README.md` 与 `omnitool/omniparserserver`：版面检测 → 元素识别 → VLM 理解三段，每段的输入输出尺寸直接决定成本口径；这正是本章「OCR→VLM 流水线的钱花在哪一段」的现成样本；对照 §3.2「二、延迟预算、成本模型与兜底」，就能定位误识别该在哪一段拦截、兜底该挂在哪一段之后 |

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
