# ai-ch10 · 训练工程 —— 高频陷阱

1. **把所有参数初始化成同一个值（包括全 0）** —— 神经元完全对称，反向梯度相同，等价于只有一个神经元。正确做法：随机初始化（He/Xavier），并保证每层方差约等于输入方差。

2. **用 Xavier 配 ReLU、或用 He 配 tanh** —— Xavier 假设激活近似线性（$2/(n_{in}+n_{out})$），不补偿 ReLU 砍掉一半方差的问题，深网会逐层衰减；He 的 $2/n_{in}$ 正是为 ReLU 补偿的。正确做法：tanh/sigmoid → Xavier，ReLU/GELU → He。

3. **以为「有 BN/LN 了就不用管初始化」** —— 归一化只钉住激活的统计量（前向），不保证反向 Jacobian 的条件数；残差分支初始化过大仍会让深网不稳。正确做法：归一化 + 合适初始化 + scaled init（残差末层乘 $1/\sqrt{2N}$）三者并用。

4. **Transformer 用 BatchNorm** —— 序列长度可变、batch 常偏小、推理逐 token，BN 的 batch 统计量不可用（推理时还得靠滑动平均，长尾分布下会漂）。正确做法：LN / RMSNorm。

5. **推理时忘记 `model.eval()`（或 BN 的 running stats 未更新）** —— 训练用 batch 统计量、推理用全局统计量；不切 eval 会让结果随 batch 组成变化，且同一条样本在不同 batch 里输出不同。这是线上「结果不稳定」的高频原因。

6. **把 weight decay 加进梯度后交给 Adam** —— Adam 会把 $\lambda\theta$ 丢进 $v$ 里自适应缩放，等效衰减强度被 $\sqrt{\hat v}$ 除掉，梯度大的参数几乎不衰减。正确做法：用 **AdamW**（解耦衰减），并把 bias/LayerNorm 的 $\gamma$ 排除在 decay 之外。

7. **Adam 不做偏差校正** —— $m_0=v_0=0$ 使前几步的矩估计系统性偏小，不除 $(1-\beta^t)$ 等于前几步学习率被暗中缩小；$t$ 大时影响消失，但「warmup 期特别慢」常与此叠加。

8. **梯度累积时忘了 `loss / K`** —— micro-batch 的 loss 直接 backward 会让梯度变成 $K$ 倍，等效学习率 ×K，表现为「累积后训练发散」。正确做法：`loss = loss / K` 后再 backward，且 step 每 K 次调用一次（scaler 同步）。

9. **以为梯度累积与「真大 batch」完全等价** —— 无状态层（Linear/Conv/LN/残差）等价，但 **BatchNorm 不等价**（每个 micro-batch 的统计量不同）。需要真大 batch 的对比学习/BN 网络必须用 DDP + SyncBN。

10. **混合精度下直接 `clip_grad_norm_`** —— 裁剪的是被 loss scale 放大过的梯度，阈值全部失效（等于没裁或裁爆）。正确做法：`scaler.unscale_(optimizer)` 还原后再裁，然后 `scaler.step()`。

11. **以为开 AMP 能省一半训练显存** —— 混合精度**不减少模型状态**（fp16 参数 2 + 梯度 2 + fp32 主权重 4 + $m$ 4 + $v$ 4 = 16 B/参数，与全 fp32 相同），省的是激活与带宽。规划显存时按 16 B/参数算，别按 2 B 算。

12. **fp16 训练不做 loss scaling** —— 梯度常小于 fp16 的最小正规数 $6\times10^{-5}$，直接下溢成 0，表现为「loss 不降但也不报错」。正确做法：用 AMP 的 GradScaler（动态缩放），或直接用 bf16。

13. **用 fp16 存参数更新的累加** —— 小学习率下 $\theta+\Delta\theta$ 在 fp16 里被舍入成 $\theta$（ulp 太大），训练「看起来在跑但参数不变」。正确做法：保留 fp32 主权重（master weights）。

14. **认为 ZeRO-3 一定比 ZeRO-2 好** —— ZeRO-3 分片参数，前向/反向要逐层 gather，通信量约为基线 1.5 倍；小模型或带宽受限时反而更慢。正确做法：先 ZeRO-2（几乎无额外通信、收益大），装不下再 ZeRO-3/FSDP。

15. **在跨机链路上做张量并行（TP）** —— TP 每层两次 AllReduce、对延迟极敏感，跨机 IB 带宽比 NVLink 低一个数量级，会被通信拖死。正确做法：TP 限制在单机 NVLink 域内，跨机用 PP + DP。

16. **流水线并行用很小的 micro-batch 数** —— bubble 比例约 $(P-1)/(M+P-1)$，$M$ 太小时 GPU 大量空转（$M=4$、$P=8$ 时空转 64%）。正确做法：$M\ge4P$，并用 1F1B 调度。

17. **拿「参数量 × 2 字节」估算训练显存** —— 2 B/参数是**推理**的账（fp16 权重）。训练是 16 B/参数，差 8 倍。7B 训练需 ≥112GB，单张 80GB 卡装不下。

18. **把 Chinchilla 的 20 tokens/参数当成铁律** —— 那是「训练算力最省」的解；产品要算「训练 + 推理」总成本，因此实际普遍**过训练**（7B 训 2T+ tokens）。反过来，在数据受限时强行按 20:1 配比会导致模型欠训练。

19. **loss 出现尖峰就重启训练** —— 直接重启会浪费已训算力且可能再遇同一批数据。正确做法：回滚到 spike 前的 checkpoint、跳过该 batch、必要时降 lr/加 warmup；并记录该 batch 的数据 id 做归因。

20. **只用一个 seed 就宣布「提升 0.3%」** —— 单次运行的方差常大于该提升。正确做法：3-5 个 seed 报均值±标准差，并固定 config + git hash + 数据版本以保证可复现。
