# ai-ch03 · Transformer 与大语言模型原理

> 先修：ai-ch02（CNN/RNN/注意力演进）。衔接：ai-ch04（微调与对齐）、ai-ch05（提示工程）。
> 学科线：AI / Agent 开发 · A2 大模型原理与训练。面试权重：★★★★★（算法/大模型岗必考）

## 本章目标

学完你应该能：

1. **说清自注意力的计算与第一性原理**：Q/K/V 的来历、√d_k 缩放的必要性、softmax 的温度形式化，
   以及为什么纯自注意力是「置换等变」的——这正是位置编码存在的根本动机。
2. **手写多头注意力的维度变换**：reshape + transpose 拆头、拼接合并，并说出参数量
   `4·d_model²` 与头数无关这一常被误算的结论。
3. **讲清位置编码的演进与 RoPE 的相对位置性质**：正弦→可学习→相对位置→RoPE/ALiBi，
   并能形式化说明「RoPE 旋转后 Q·K 内积只依赖相对距离 m−n」。
4. **理解 Decoder-only 自回归的两阶段（prefill / decode）与 KV Cache 显存账**：
   能给定层数/头数/head_dim/序列长度/dtype 估算 KV Cache 字节数，说清 decode 是 memory-bound。
5. **掌握采样策略与生成控制**：greedy / temperature / top-k / top-p 在同一批 logits 上的差异，
   以及困惑度 PPL = exp(CE) 与交叉熵的关系。
6. **说清架构取舍、训练目标与 Scaling Law**：Encoder-Decoder vs Decoder-only、GPT 的 next-token 目标、
   LayerNorm vs BatchNorm、残差 + LayerNorm 的梯度路径、Scaling Law 与 Chinchilla 最优。

## 关键认知（本章最值钱的三句）

- **纯自注意力对词序盲目**：它置换等变，位置信息必须显式注入——这是一切位置编码的出发点。
- **√d_k 缩放 = softmax 温度**：把 logits 除以 √d_k 与「程序员调 temperature」是同一机制，
  softmax 对输入尺度极敏感，不缩放会在大 d_k 下饱和、梯度趋零。
- **decode 是显存带宽瓶颈不是算力瓶颈**：每步只算 1 个 query，却要读全部历史 KV Cache，
  所以长上下文的成本首先在 KV 显存，而非 FLOPs。

## 本章 GitHub 资源（大纲实时抓取，star 最高）

- `huggingface/transformers` — 167014★：Transformer 模型定义框架（BERT/GPT/RoPE 全量实现）
- `karpathy/nanoGPT` — 极简 GPT 训练范例（因果自注意力 + 采样）
- `tensorflow/tensorflow` — 200724★：工业级框架参考
- `langchain-ai/langchain` / `langgenius/dify` — Agent / RAG 工程落地


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 吴恩达 · 深度学习专项课程（中英字幕） | [视频](https://www.bilibili.com/video/BV164411b7dx/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 跟李沐学 AI · 动手学深度学习 v2 | [视频](https://space.bilibili.com/1567748478/lists/358497/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 炮哥带你学 · PyTorch 框架与经典 CNN 实战 | [视频](https://www.bilibili.com/video/BV1eP411w7Re/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 李宏毅 · 机器学习 2021 | [视频](https://www.bilibili.com/video/BV1JA411c7VT/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）

- 线性代数（矩阵乘法、softmax、向量内积）与 `ai-ch01`（反向传播）有助于理解梯度路径；
  不掌握也可先学本章工程视角，机制视角留待回看。
