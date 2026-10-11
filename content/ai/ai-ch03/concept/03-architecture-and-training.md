# ai-ch03 · 核心概念（三）：架构取舍、归一化与训练目标

> 视角覆盖：程序员（上下文/工程）/ 博士生（梯度路径、Scaling Law）/ 考研者（LN vs BN、GPT 目标）。三者互补、不重复。

## 1. Encoder-Decoder vs Decoder-only

Encoder 双向编码上下文（BERT/翻译源端），Decoder-only 自回归生成（GPT 系列），Encoder-Decoder 二者结合（原始 Transformer 翻译、T5）。

### 🧑‍💻 程序员视角
- 上下文窗口与截断：长文档超窗时常见做法是截断（丢尾/丢中）、滑动窗口、或层次压缩；KV Cache 随上下文线性增长，必须按预算规划最大长度，否则 OOM。
- 生产默认 Decoder-only：统一预训练目标、推理栈简单，且经指令微调 / RLHF 后能做理解类任务，不必强分 NLU/NLG。

### 🎓 博士生视角
- **Scaling Law（经验规律）**：测试损失随规模幂律下降，$L(N)\propto N^{-\alpha}$（参数量 N）、$L(D)\propto D^{-\beta}$（数据量 D）、$L(C)\propto C^{-\gamma}$（算力 C）；三者共同决定最终损失，存在可预测的缩放曲线。
- **Chinchilla 最优**：在固定算力下，模型参数与训练 token 应近似 1:20（data≈20×params），而非早期「大模型少数据」的做法；这重新定义了「最优模型大小」。

### 📚 考研者视角
- **GPT 的 next-token 训练目标**：自回归交叉熵，最大化 $p(x_t\mid x_{<t})$，对所有位置并行算（靠因果掩码）。BERT 用 MLM（遮住后预测），是双向但非自回归。
- 笔试常考「GPT 与 BERT 训练目标 / 结构区别」「为什么 GPT 适合生成、BERT 适合理解」。

## 2. 残差 + LayerNorm 的梯度路径

每个子层包成 `Add&Norm(SubLayer(x) + x)`，归一化有两种放置：Post-LN（原版，Norm 在外）与 Pre-LN（Norm 在内，大模型默认）。

### 🧑‍💻 程序员视角
- 工程上 **Pre-LN 训练更稳定**：梯度不依赖深层归一化的尺度，深层网络（数十到上百层）默认 Pre-LN；Post-LN 需极小心warmup，否则初期梯度爆炸。
- 归一化与残差是「能训上百层」的工程前提，不是锦上添花。

### 🎓 博士生视角
- **残差梯度路径**：设第 l 块输入为 $x_l$，则 $\frac{\partial L}{\partial x_l}=\frac{\partial L}{\partial x_{l+1}}\left(I+\frac{\partial Block}{\partial x_l}\right)$。恒等分支给梯度**至少 1** 的直通路，即使 Block 梯度趋零，深层信号也能回流，从根本上缓解梯度消失。
- LayerNorm 把每样本特征维拉到零均值单位方差，稳定了每层分布，使残差路的尺度不发散。

### 📚 考研者视角
- **LayerNorm vs BatchNorm**：LN 沿**特征维**归一化、与 batch 无关，适合变长序列 / 小 batch；BN 沿 **batch 维**归一化、需大 batch 且对序列长度不友好。Transformer 全用 LN。
- 易混：BN 的 running_mean 是推理期用的（训练期用 batch 统计），LN **没有** batch 统计量、推理期照常逐样本算，别把两者归一化机制搞反。

---
### 三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 架构取舍 | 上下文截断、KV 预算 | Scaling Law、Chinchilla | GPT next-token vs BERT |
| 残差+LN | Pre-LN 更稳定 | 恒等梯度路≥1 | LN vs BN、 LN 无 batch 统计 |
