# ai-ch04 · 高效微调与对齐：LoRA、RLHF 与 DPO

## 本章目标

学完本章，你应当能够：

1. **算清一笔显存账**：给定模型规模与训练方式（全参 / LoRA / QLoRA），估出权重、梯度、优化器状态、激活四部分占用，并判断「单卡能不能训」。
2. **说清 LoRA 到底在做什么**：低秩假设从哪来、A/B 为什么一个高斯初始化一个置零、`rank` 与 `alpha` 分别控制什么、`target_modules` 该选谁。
3. **讲明白对齐的三条路线**：RLHF（奖励模型 + PPO）、DPO（跳过奖励模型的闭式解）、RLAIF/GRPO 等替代方案，以及各自要付的工程代价。
4. **避开奖励黑客（reward hacking）**：知道 KL 约束为什么不可省，以及它会带来什么副作用（alignment tax）。
5. **建立选型直觉**：**注知识用 RAG、改行为用微调**——别再拿微调去背文档。

## 关键认知（本章最值钱的三句）

- **微调改的是「怎么说」，RAG 改的是「说什么」。** 想让模型记住你公司的内部文档，微调是又贵又差的选择；想让它稳定输出某种语气/格式/决策偏好，微调才是对的工具。
- **LoRA 不是「小一号的全参微调」**。它的假设是「任务适配所需的权重改变量 ΔW 是低秩的」，因此只用 A(d×r)·B(r×k) 两个小矩阵去近似它。这个假设在「行为对齐」上通常成立，在「注入海量新知识」上往往不成立。
- **RLHF 的难点不在 PPO，在奖励模型。** 奖励模型是人类偏好的代理（proxy），而任何代理都会被优化器钻空子——KL 惩罚就是给这个代理上的保险栓。

## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [huggingface/transformers](https://github.com/huggingface/transformers) | 167014 | PEFT/LoRA 的官方集成入口，`Trainer` + `peft` 的标准写法 |
| [huggingface/peft](https://github.com/huggingface/peft) | — | LoRA / QLoRA / Prefix-Tuning / Adapter 的统一实现 |
| [microsoft/DeepSpeed](https://github.com/microsoft/DeepSpeed) | — | ZeRO 分片 + 分页优化器，QLoRA 论文里的关键组件 |
| [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow) | 200724 | 深度学习框架官方仓库，工业级模型工程范例 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at` 为准。


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 吴恩达 · 深度学习专项课程（中英字幕） | [视频](https://www.bilibili.com/video/BV164411b7dx/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 跟李沐学 AI · 动手学深度学习 v2 | [视频](https://space.bilibili.com/1567748478/lists/358497/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 炮哥带你学 · PyTorch 框架与经典 CNN 实战 | [视频](https://www.bilibili.com/video/BV1eP411w7Re/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 李宏毅 · 机器学习 2021 | [视频](https://www.bilibili.com/video/BV1JA411c7VT/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）

- **ai-ch02（注意力机制）**：理解 QKV 与多头注意力的维度变换，有助于看懂 LoRA 为什么只挂在 `q_proj`/`v_proj` 上。
- **ai-ch03（Transformer 与 LLM 原理）**：本章反复引用「参数量估算」「KV Cache」「logits 与 softmax」这些概念，若已在 ch03 建立直觉，本章会顺畅很多。
- 本线**独立自足**：若你熟悉 PyTorch 的张量运算与反向传播，可直接从本章开始；章内所有定量结论都有 numpy 从零实现的可运行示例托底。
