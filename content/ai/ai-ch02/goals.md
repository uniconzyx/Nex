# ai-ch02 · 视觉与序列建模：CNN、RNN 到注意力机制

> 先修：ai-ch01（张量、前向与反向传播、梯度消失/爆炸、优化器）。
> 衔接：ai-ch03（Transformer 与大语言模型原理）。
> 面试权重：★★★★★（视觉岗/序列建模/大模型岗必考；理解注意力是读懂 LLM 的前提）
> 本机无 PyTorch/TensorFlow，全部示例用 **NumPy 从零实现并真实运行**（见 examples/）。

## 本章目标

学完你应该能：

1. **说清卷积的两个结构性质**：局部连接与权值共享，以及它们如何把参数量从 O(H_in·H_out) 降到 O(Cout·Cin·k²)，并带来**平移等变**而非不变。
2. **手算输出尺寸、参数量、感受野**：掌握 out = floor((n+2p−k)/s)+1、Params = Cout·Cin·k·k + Cout、感受野递推，并能解释「3 个 3×3 感受野 = 1 个 7×7」的 ResNet 论据。
3. **从数学上理解 RNN 的梯度消失**：用 BPTT 连乘 W_hh 与 tanh 导数，证明长程梯度按谱半径指数衰减；说清 LSTM/GRU 的门控如何缓解（而非根治）。
4. **完整推导并手写缩放点积注意力**：Q·K^T / sqrt(d_k) → softmax → 加权 V，含因果掩码；说清除以 sqrt(d_k) 防止 softmax 饱和的动机。
5. **讲透复杂度与位置编码**：自注意力 O(n²d) vs RNN O(nd²) 的适用分野；正弦位置编码为何相加、为何用不同频率。

## 关键认知（本章最值钱的三句）

- **卷积的「等变」不是「不变」**：权值共享让平移输入等价于平移输出（等变）；要平移**不变**需额外池化/全局池化。
- **梯度消失是连乘的谱半径衰减**：RNN 的反向传播把 W_hh 与 tanh 导数沿时间连乘，谱半径 < 1 即指数衰减——LSTM 用门控把「记忆」走恒等通路来缓解。
- **注意力的二次复杂度是它最大的软肋**：O(n²d) 让长序列昂贵，这正是后续 FlashAttention / 稀疏注意力 / MQA 要解决的工程问题。

## 本章 GitHub 资源（star 最高，实时抓取）

- `tensorflow/tensorflow` — 200724★：工业级框架，看它的卷积与 RNN 算子实现
- `huggingface/transformers` — 167014★：现代 Transformer 的定义框架
- `karpathy/nanoGPT` — 极简 GPT 实现，注意力与位置编码的最佳入门
- `microsoft/ML-For-Beginners` — 微软官方机器学习 12 周课程


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 吴恩达 · 深度学习专项课程（中英字幕） | [视频](https://www.bilibili.com/video/BV164411b7dx/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 跟李沐学 AI · 动手学深度学习 v2 | [视频](https://space.bilibili.com/1567748478/lists/358497/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 炮哥带你学 · PyTorch 框架与经典 CNN 实战 | [视频](https://www.bilibili.com/video/BV1eP411w7Re/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 李宏毅 · 机器学习 2021 | [视频](https://www.bilibili.com/video/BV1JA411c7VT/) | 本学科配套视频，建议结合本章示例与习题观看 |
