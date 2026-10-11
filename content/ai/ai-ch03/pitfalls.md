# ai-ch03 · Transformer 与大语言模型 —— 高频陷阱

1. **训练自回归模型忘了因果掩码** —— 不把未来位置遮成 −inf，模型在训练时就「偷看」答案，验证集指标虚高、推理全错。必须用上三角掩码（含对角线自身）保证位置 i 只看 0..i。

2. **在远超训练长度的位置上直接推理** —— 正弦 / 可学习绝对位置编码在未见过的 pos 上分布漂移，长上下文外推崩。应按需做 RoPE 的 NTK-aware base 调整或位置插值 / 继续微调。

3. **把多头注意力的参数量误算成与头数成正比** —— 实际每层 Q/K/V/O 四个投影各 d_model²，共 4·d_model²，与头数 h 无关；h 只切分子空间维度 d_k=d_model/h。翻倍头数不翻倍参数。

4. **以为 LayerNorm 推理期也要维护 batch 统计量** —— 错：LN 沿特征维、逐样本计算，与 batch 无关，没有 running_mean/var；那是 BatchNorm 的机制。两者归一化轴不同，别混。

5. **认为 Q/K/V 维度必须各不相同** —— 标准实现 d_k=d_v=d_model/h，Q 与 K 必须同维才能点积；V 维度可与 Q/K 不同但通常取相等以简化。

6. **把 padding token 也算进损失** —— 未对 padding 位置做 loss mask，会把「预测填充符」当作有效监督，拉低有效学习的信噪比。训练前必须用 attention mask / loss mask 屏蔽 pad。

7. **在 Transformer 里用 BatchNorm 替代 LayerNorm** —— BN 沿 batch 维、需大 batch 且对变长序列不友好；序列模型（尤其小 batch / 变长）应用 LayerNorm，这也是标准做法。

8. **temperature=0 时还做随机采样** —— T=0 的 softmax 退化为 argmax，输出应确定；若此时仍按分布随机抽，会得到「同样输入不同输出」的矛盾行为。低温即用贪心。

9. **top-k 与 top-p 同时设却不分清顺序** —— 先 top-k 再 top-p，还是先 top-p 再 top-k，结果可能不同。工程上必须显式固定截断顺序并用配置写死，否则无法复现。

10. **忽视 KV Cache 显存随序列线性增长** —— 误以为推理成本只在算力，结果长上下文直接 OOM。上线前先用 layers×kv_heads×head_dim×2×dtype×seq 估算峰值 KV 显存。

11. **认为 Decoder-only 不能做理解类任务** —— GPT 经指令微调 / RLHF / 思维链后完全能做分类、抽取、问答等 NLU；是否「适合」取决于训练目标与数据，不是架构封死。

12. **把 softmax 温度写成乘在 logits 外面** —— 正确是「除以温度」：$p_i=exp(z_i/T)/Σexp(z_j/T)$。写成 $exp(T·z_i)$ 会把方向搞反（T 大反而更尖锐），温度失去「平滑」语义。

13. **RoPE 外推不做任何处理直接拉长上下文** —— 直接把训练长度翻倍推理，低频分量在未见 pos 上剧烈摆动，长度外推失败。需 NTK-aware 缩放 base 或线性位置缩放再推理。
