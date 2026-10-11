# 推理两阶段：Prefill 与 Decode

## 主题一：两阶段的计算本质与延迟指标

大模型自回归推理被切成两段：
**Prefill（预填充）**——一次性把整段 prompt 过一遍，做全序列自注意力，产出 KV Cache 与第一个 token；
**Decode（解码）**——自回归逐 token 生成，每步只算 1 个新 token，读取全部权重与新 KV。
与之对应的两个延迟指标：
**TTFT（Time To First Token，首 token 延迟）** ≈ 排队 + Prefill + 第一步 Decode；
**TPOT（Time Per Output Token，每 token 延迟）** 是 Decode 阶段的均摊步时，端到端 ≈ TTFT + TPOT × (输出长度 − 1)。
Prefill 的 FLOPs 随 prompt 长度近似线性（注意力项为二次），属**计算受限**；
Decode 每步要读完整个模型权重，属**带宽受限**——这正是「两阶段吃两种药」的根源。

```text
                 prompt (S tokens)                    output (N tokens)
  请求 ──► [ Prefill: 全序列注意力 ] ──► 首 token ──► [ Decode × 1 ] ──► [ Decode × 2 ] ──► ... 
                 计入 TTFT                            每步计入 TPOT
```

### 🧑‍💻 程序员视角
- **按 SLA 选指标**：交互式对话看 TTFT（用户 @ 首字要快），长文生成看 TPOT（否则中段卡住）。
- **P95 而非均值**：延迟长尾决定体验，SLO 必须用分位数，均值会把「1% 的 10 秒请求」平均掉。
- **排查顺序**：TTFT 高先查排队/批大小/prompt 长度（前缀缓存是否命中）；TPOT 高先查是否超长输出、是否并发打满显存而触发换页。
- **工程手段**：chunked prefill 把长 prompt 切片插入 decode 空档，避免一个长 prefill 阻塞整批（压低 P99 TTFT）。

### 🎓 博士生视角
- Prefill 的算力需求 ≈ 2·P·S（P 为参数量、S 为序列长），另有注意力的 O(S²·d) 项；Decode 单步 ≈ 2·P，但显存流量 ≈ 2·P·bytes/weight，故**算术强度**（FLOPs/Byte）在 decode 期降到约 1，远低于 GPU 的算力/带宽比，硬件利用率天然低。
- 因此 decode 的理论下限是 `t ≈ 2·P·b / BW`（b 为每权重字节），与序列长度无关——这解释了为什么「更小的 P」或「更少的 b（量化）」能直接压 TPOT，而提高算力对 TPOT 几乎无效。
- 两阶段的**批处理效率**不同：prefill 大 batch 摊薄权重读取的收益低（本就计算受限），decode 大 batch 几乎免费（同一份权重服务多个请求），所以调度器倾向于把 prefill 单独成批、decode 尽量堆批。

### 📚 考研者视角
- **标准定义**：TTFT＝从请求发出到收到第一个输出 token 的时间；TPOT＝首 token 之后每个 token 的平均生成时间。二者与吞吐（tokens/s）是三回事，切勿混谈。
- **常考口径**：端到端时延 ≈ TTFT + TPOT × (N − 1)；给定 P、S、有效算力 F 求 prefill 计算量 2·P·S，再除以 F 得时间口径。
- **易混点**：把「首 token 延迟」当成「整体延迟」；把吞吐高当成延迟低（批处理可以抬高吞吐同时抬高单请求延迟）。

## 主题二：两阶段对应的高效优化

针对 TTFT：**前缀缓存（prefix caching）**复用相同系统提示的 KV、**chunked prefill** 削峰、**prefill 批化**摊薄。
针对 TPOT：**权重量化**降低每步读取字节、**GQA/MQA** 缩小 KV 头数、**投机解码**用草稿模型一次验证多个 token、**连续批处理**让批始终填满。
两条路线互不替代：前缀缓存对 TPOT 无益，量化对 TTFT 的 prefill 计算也几乎无增益（prefill 是计算受限，8-bit 权重对算力帮助有限）。

### 🧑‍💻 程序员视角
- **优先级**：先在 Trace 上确认瓶颈落在 TTFT 还是 TPOT，再选手段；两者同时劣化通常是显存打满导致的排队与换页，先扩显存/降并发。
- **前缀缓存的前提**：系统提示必须**逐字节稳定**。任何动态插入时间戳、随机 ID 进 system，都会让缓存 100% miss——这是极常见的事故。
- **投机解码的收益条件**：草稿模型与目标模型分布越接近、任务越「可预测」（如代码补全、格式化输出），接受率越高，收益越大。
- **别忽视输出侧**：让模型少说废话（约束输出格式、限制 max_tokens）往往比任何推理加速都省时间与钱。

### 🎓 博士生视角
- 前缀缓存的正确性来自**自注意力对前缀的因果无关性**：前缀 KV 只依赖前缀本身，与后续 token 无关，因此可以安全复用并在不同请求间共享（配合 PagedAttention 的块级共享实现）。
- 投机解码的无损性来自**拒绝采样**：草稿 token 以 min(1, p_target/p_draft) 被接受，被拒处由目标分布重采样，因此最终采样分布与目标模型逐点一致——是「加速而非近似」。
- 数学期望：以接受率 α、草稿长度 k 计，每轮期望新增 token 数为 Σ_{i=0}^{k} α^i，理论加速上限受该值约束（见 ex05 实测 3.05）。

### 📚 考研者视角
- **笔面考点**：给定「前缀缓存命中/不命中」对比 TTFT 的差异，判断哪一阶段被优化；给出接受率 α 与草稿步数 k，估算投机解码的平均产出 token 数 Σα^i。
- **易错口径**：以为「量化能让 prefill 更快」——prefill 计算受限，权重位宽降低对算力利用提升有限；量化的主战场是 decode 的带宽。
- **术语**：Prefill / Decode、TTFT / TPOT、prefix caching、chunked prefill、speculative decoding（含 draft model / verification）。
