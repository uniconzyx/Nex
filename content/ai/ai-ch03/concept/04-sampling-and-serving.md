# ai-ch03 · 核心概念（四）：采样策略与推理效率工程

> 视角覆盖：程序员（采样参数/KV 账）/ 博士生（温度形式化、O(n²) 来源）/ 考研者（PPL、参数量估算）。三者互补、不重复。

## 1. 采样策略：怎么控制生成

给定末层 logits z，先 softmax 得概率分布，再决定取哪个 token：贪心取 argmax；温度重缩放；top-k / top-p 先做候选截断。

### 🧑‍💻 程序员视角
- 工程决策：temperature 控随机度（高更发散、低更确定）；top-k 限制只看概率最高的 k 个；top-p（核采样）按累积概率截断；repetition penalty 惩罚已出现 token 防复读。对话常用 temp≈0.7 / top-p≈0.9，代码与事实问答用贪心或低温。
- 三者常组合：先 top-k 再 top-p，或反之，取决于实现；务必在配置里显式写明顺序，否则复现不一致。

### 🎓 博士生视角
- **softmax 温度形式化**：$p_i=\frac{\exp(z_i/T)}{\sum_j\exp(z_j/T)}$。$T\to0$ 退化为 argmax（确定），$T\to\infty$ 趋均匀（最随机）；T 是缩放因子，与自注意力的 $\sqrt{d_k}$ 同源——都在调 softmax 的输入尺度。
- 温度改变的是分布的「锐度」而非改变 argmax 的相对次序（单调变换），所以低温不会让次优 token 反超，只会压低长尾。

### 📚 考研者视角
- **困惑度 PPL = $\exp(CE)$**：给定真实分布，PPL 等于模型给真实下一 token 概率的倒数；PPL 越低模型越准。笔试常考「PPL 与交叉熵的关系」「temperature 的作用」。
- 易错：PPL 是对数平均而非算术平均；T=0 时若仍做随机采样会得到非确定性输出，矛盾——T=0 即贪心。

## 2. 注意力效率工程：KV Cache / FlashAttention / MQA-GQA

自回归推理要把历史 K、V 缓存复用；长序列下 KV 显存与注意力 FLOPs 是两大成本。

### 🧑‍💻 程序员视角
- **KV Cache 显存账**：单样本 = layers × kv_heads × head_dim × 2 × dtype_bytes × seq_len；MQA（1 个 KV 头）/ GQA（少数 KV 头）直接砍这块，是「小显存跑长上下文」的关键。
- FlashAttention 用分块 + 在线 softmax + 重算，省 HBM 访存、降显存峰值；prefill 阶段吃满算力，decode 阶段受限于 KV 读取带宽。

### 🎓 博士生视角
- **O(n²) 来源**：注意力核心是 $QK^\top$（n×n），softmax 与加权求和也都是 n 相关；FLOPs 随序列长度**平方**增长，是长上下文的主要算力成本，也是 MQA/GQA/FlashAttention 要解决的靶点。
- 记：prefill 的算力 dominated by 大矩阵乘（compute-bound），decode 的延迟 dominated by 逐 token 读 KV（memory-bound）——同一份注意力，两阶段瓶颈不同。

### 📚 考研者视角
- **参数量估算**：embedding $V\cdot d_{model}$，每层 attention $4\,d_{model}^2$（Q/K/V/O），FFN $2\cdot d_{model}\cdot d_{ff}$，LM head 常复用 embedding 不计或另算；FFN 通常占大头（d_ff≈4d_model 时约 2/3）。
- MQA/GQA 的意义（笔面）：用更少 KV 头换显存与带宽，几乎不损质量，是推理端性价比最高的改动之一。

---
### 三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| 采样 | temp/top-k/top-p/重复惩罚 | 温度形式化、单调尺度 | PPL=exp(CE)、T=0 即贪心 |
| 效率 | KV 显存账、FlashAttention | O(n²) 来源、两阶段瓶颈 | 参数量估算、MQA/GQA 意义 |
