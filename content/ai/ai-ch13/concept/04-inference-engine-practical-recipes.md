# 推理引擎实战手记：凯喵的十二次显存爆炸与延迟翻车

> 这一篇来自凯喵把一个大模型服务从「单卡跑通」推到「多并发上线」的过程。模型只有一个，接口只有一行 `generate`，但整条上线路径上炸了十二次：显存 OOM、吞吐上不去、首 token 延迟抖、量化后精度掉、多请求互相拖累。每一次都指向推理引擎里一个具体机制。这篇按「显存 → 调度 → 量化」的顺序，把这十二个现场逐个还原。

## 开场：为什么 7B 模型在一张 24G 卡上跑不了长上下文

凯喵第一次部署时算的账是：7B 参数，FP16 每个参数 2 字节，权重占 14GB，卡有 24GB，剩下 10GB 够用。结果并发开到 8 路、上下文长度 4096 时，直接 OOM。

漏算的部分是 KV Cache。这个缓存的大小与「层数 × 头数 × 头维度 × 序列长度 × batch 大小 × 精度字节」成正比，与参数量无关。序列一长、并发一多，它就超过了权重本身。

理解这一点之后，整篇的内容就有了主线：**推理服务的显存预算 = 权重 + KV Cache + 激活峰值 + 框架开销**，而 KV Cache 是唯一随流量线性增长的那一项，所以它是推理引擎所有调度策略的核心目标。

## 现场一：KV Cache 到底缓存了什么

Transformer 的自注意力里，每个 token 都要和之前所有 token 算注意力。如果每生成一个新 token 就把前面的 K、V 重算一遍，复杂度是平方级的浪费。KV Cache 就是把历史 token 的 Key 和 Value 张量存下来，新 token 只算自己的 Q、K、V，然后拿自己的 Q 去和缓存的全部 K、V 做注意力。

```python
# 概念示意：有 cache 与无 cache 的差别
def attend_with_cache(q_new, k_cache, v_cache):
    # q_new: [B, H, 1, D]
    # k_cache/v_cache: [B, H, T, D]，包含历史 + 当前
    scores = q_new @ k_cache.transpose(-1, -2) / (q_new.size(-1) ** 0.5)
    probs = scores.softmax(dim=-1)
    return probs @ v_cache           # [B, H, 1, D]
```

代价是：每层每个头都要存一份 `k_cache` 和 `v_cache`。以 7B 模型（32 层、32 头、头维度 128）为例，单 token 单层的 KV 大小是 `2 × 32 × 128 × 2 字节 = 16KB`，32 层就是 512KB/token。4096 长度的单条请求就要 2GB，8 路并发直接 16GB。

凯喵算完这个账才明白：**长上下文服务的瓶颈从来不是权重，而是 KV Cache**。这也解释了为什么后来的模型都在往 GQA、MQA 方向走——减少 KV 头数是压缩这块开销最直接的手段。

## 现场二：预分配最大长度，等于给每个请求留一间空房

第一版实现是「按 max_length 预分配 KV 张量」。逻辑简单，但浪费惊人：请求只用了 200 个 token，却占了 4096 的空间，剩下的 3896 个位置空着，别的请求也用不了。

这就是 PagedAttention 要解决的问题。它借鉴操作系统的虚拟内存分页：把 KV Cache 切成固定大小的块（比如 16 个 token 一块），用一个块表记录「逻辑位置 → 物理块」的映射。请求用到多少就分配多少块，块之间不需要连续。

```python
# 分页注意力的核心：通过块表间接寻址
def gather_kv(block_table, k_blocks, seq_len, block_size=16):
    idx = []
    for pos in range(seq_len):
        logical_block = pos // block_size
        offset = pos % block_size
        idx.append(block_table[logical_block] * block_size + offset)
    return k_blocks[idx]        # 按逻辑顺序取回不连续的物理块
```

收益有两个：内部碎片从「平均浪费一半」降到「最多浪费一块」；并且不同请求之间可以共享物理块——如果两个请求的 prompt 前缀相同，它们的块表可以指向同一批物理块，这就是前缀缓存。

凯喵的体会是：这个设计的思想价值大于实现细节。**凡是「按最大需求预分配」的地方，都值得问一句能不能改成分页/按需**。

## 现场三：连续批处理让 GPU 不再等最慢的那个

传统批处理是「凑够一批，一起算到全部结束」。问题很明显：一批里如果有条请求要生成 1000 个 token，其他只生成 10 个的请求就得陪着等 990 步，GPU 在这期间大量算力空转。

连续批处理（continuous batching，也叫 iteration-level scheduling）改成「每生成一个 token 就重新组批」：谁生成完了就退出去，队列里有新请求就补进来。

```python
# 调度循环的核心结构
while running or waiting:
    # 1. 把已完成的请求移出
    running = [r for r in running if not r.finished]
    # 2. 用空出来的槽位接纳新请求
    while waiting and len(running) < max_batch:
        running.append(waiting.popleft())
    # 3. 所有 running 请求各前进一步
    step(running)
```

这个改动带来的吞吐提升往往是数倍，而且不需要改模型。凯喵实测过：在混合长短请求的场景下，连续批处理的吞吐是静态批处理的 3 到 5 倍，P99 延迟还更低——因为短请求不再被长请求拖着。

## 现场四：chunked prefill 解决长 prompt 抢占

连续批处理解决了生成阶段的效率，但 prefill 阶段还有个问题：一条 8000 token 的长 prompt 进来，prefill 要一次性算完，这期间所有正在生成的请求都被卡住，延迟尖刺非常明显。

chunked prefill 的思路是把长 prompt 切成若干块，每块和生成请求混在同一批里算。代价是单条长 prompt 的首 token 延迟略微变大，收益是所有其他请求的延迟变得平滑。

```python
def schedule_prefill_chunks(req, chunk_size=512):
    for start in range(0, len(req.prompt_tokens), chunk_size):
        yield req.prompt_tokens[start:start + chunk_size]
```

凯喵的经验是：**在混合负载下，延迟的稳定性比平均延迟更重要**。用户对「偶尔等 8 秒」的容忍度远低于「稳定等 1.5 秒」。chunked prefill 用一点点平均延迟换来了大幅降低的抖动，这笔交易通常划算。

## 现场五：量化不是「把权重压小」这么简单

量化的目标是把 FP16 权重压到 INT4/INT8，省显存、提带宽。但朴素地做「四舍五入到最近整数」会让精度崩掉，因为权重分布很不均匀：大部分值集中在零附近，少数离群值跨度很大。

所以真正的量化方案都要处理「离群值」。GPTQ 的做法是逐层做最优量化，用 Hessian 信息决定每个权重该舍入到哪一侧，把误差补偿到其他权重上。AWQ 的观察是「激活值大的通道更重要」，于是对这些显著性通道保持较高精度，其余通道激进量化。

```python
# 分组量化的基本形式：每组独立算 scale 和 zero point
def quantize_group(w, bits=4, group_size=128):
    g = w.reshape(-1, group_size)
    w_min, w_max = g.min(dim=1, keepdim=True).values, g.max(dim=1, keepdim=True).values
    scale = (w_max - w_min) / (2 ** bits - 1)
    zero = (-w_min / scale).round()
    q = ((g - w_min) / scale).round().clamp(0, 2 ** bits - 1)
    return q.to(torch.uint8), scale, zero
```

分组的目的是让同一组内的动态范围尽量小，量化误差就小。组越小精度越高，但元数据（scale/zero）占的空间越大。128 是常见的折中点。

## 现场六：GPTQ 与 AWQ 的取舍

GPTQ 是「事后量化 + 误差补偿」，需要一个校准集跑一遍前向，逐层求解。优点是通用、支持多种位宽；缺点是校准集选不好会明显掉点，而且量化过程本身要花时间。

AWQ 是「激活感知的权重量化」，核心是识别显著通道并保护它们。优点是量化速度快、对指令微调模型更友好；缺点是实现相对绑定特定结构。

凯喵的选择标准是：**先看有没有官方量化好的权重**。社区上常见的模型基本都有现成的 GPTQ/AWQ/GGUF 版本，直接下载比自己做量化省事得多，而且效果已经被验证过。自己量化只在「模型太新还没人做」或者「有特殊数据分布」时才值得。

## 现场七：GGUF 是格式，不是量化算法

这是个高频误解。GGUF 是 llama.cpp 定义的文件格式，里面可以装各种量化类型（Q4_K_M、Q5_K_S、Q8_0 等）。它和 GPTQ/AWQ 不是同一层的东西——后两者是量化方法，GGUF 是容器格式。

选型的实际考量是**部署环境**：GPU 服务用 vLLM + AWQ/GPTQ；CPU 或混合推理用 llama.cpp + GGUF；Mac 上用 Metal 加速的 GGUF。凯喵见过有人拿 GGUF 去喂 vLLM，然后困惑为什么加载不了——格式不匹配，不是量化的问题。

## 现场八：量化后精度掉了，先看是不是校准集的问题

凯喵遇到过一次：同一个模型，GPTQ 量化后在一批业务数据上准确率掉了 6 个点。排查了半天，最后发现校准集用的是通用语料，而业务数据里有大量专业术语和特殊格式，量化时这些分布完全没被覆盖。

修法很简单：**校准集要贴近真实流量分布**。从线上采样几百条真实输入，比用公开数据集效果好得多。这个道理和「测试集要贴近生产数据」是一样的——量化的本质是用少量样本估计权重的敏感度，样本不 representative，估计就不准。

另一个常见原因是量化位宽选得太激进。4bit 在多数场景可用，但代码生成、数学推理这类对数值精度敏感的任务，往往需要 5bit 或 8bit。

## 现场九：批大小不是越大越好

直觉上 batch 越大吞吐越高，因为 GPU 并行度更高。但实际存在一个拐点：超过某个 batch 之后，吞吐不再增长，延迟却线性上升。

原因是瓶颈从「算力」转移到了「显存带宽」。生成阶段每步要做的是「读全部权重 + 读全部 KV + 算一个小矩阵乘」，这是典型的 memory-bound 操作。batch 增大能摊薄权重读取的成本，但当 KV Cache 读取成为主导时，再增大 batch 只会增加访存压力。

```python
# 粗略的 roofline 判断：算力受限还是带宽受限
def is_memory_bound(batch, hidden, params_bytes, bw_gbps, tflops):
    flops = 2 * batch * hidden * hidden          # 近似
    bytes_moved = params_bytes + batch * hidden * 2
    return (flops / tflops) < (bytes_moved / bw_gbps)
```

凯喵的调参方法是：**从 batch=1 开始逐步翻倍，记录吞吐和 P99，找到吞吐曲线明显变平的那个点**，然后回退一档作为默认值。这个点在不同模型、不同卡上都不一样，必须实测，不能照抄别人的数字。

## 现场十：首 token 延迟和每 token 延迟是两个指标

很多人只盯「每秒生成多少 token」，但用户体验由两个独立指标决定：TTFT（time to first token，首 token 延迟）和 TPOT（time per output token，每 token 延迟）。

TTFT 由 prefill 决定，与 prompt 长度近似线性相关；TPOT 由 decode 决定，与模型大小和 batch 相关。两者的优化手段完全不同：TTFT 靠 prefix caching、chunked prefill、更快的 prefill 内核；TPOT 靠更大的 batch、量化、投机解码。

凯喵的监控面板上这两个指标分开画。曾经有一次「吞吐看起来正常但用户投诉变慢」，一看 TTFT 从 300ms 涨到 2s——原因是缓存命中率掉了，每次都要重新 prefill 整段 system prompt。

## 现场十一：前缀缓存省下的不只是时间

多轮对话、few-shot、长 system prompt 的场景，每次请求都带着一段完全相同的前缀。不开前缀缓存的话，这段前缀每次都要重新算一遍 KV，既浪费时间又浪费显存。

开启之后，相同前缀的 KV 块在物理上共享，块表指向同一批块。收益是双份的：prefill 的计算量减少，KV 占用的显存也减少。

```python
# 前缀缓存的键通常是对 token 序列做哈希
def prefix_key(token_ids, block_size=16):
    blocks = [tuple(token_ids[i:i + block_size])
              for i in range(0, len(token_ids), block_size)]
    return tuple(hash(b) for b in blocks)
```

注意一个细节：前缀必须**逐块完全一致**才能命中，差一个 token 就整块失效。所以 prompt 模板里如果有时间戳、随机 id 这类动态内容，一定要放在末尾，不要放在开头，否则缓存永远不命中。凯喵见过一个项目把当前时间放在 system prompt 第一行，导致全站缓存命中率为零。

## 现场十二：投机解码的收益取决于接受率

投机解码（speculative decoding）的思路是：用一个小模型快速猜出接下来几个 token，然后用大模型一次性验证这几个 token 是否可接受。如果小模型猜得准，就能用一次大模型前向换多个 token，显著提速。

关键在于「接受率」。如果小模型和大模型的分布差异大，猜的 token 大量被拒，那不仅没有加速，还多花了小模型的计算。

```python
# 简化示意：验证阶段按概率接受
def verify(draft_tokens, target_probs, draft_probs):
    accepted = []
    for t, p_target, p_draft in zip(draft_tokens, target_probs, draft_probs):
        r = random.random()
        if r < min(1.0, p_target[t] / max(p_draft[t], 1e-9)):
            accepted.append(t)
        else:
            break
    return accepted
```

凯喵的实测经验：同系列的小模型（比如 1B 配 7B）接受率通常在 60% 到 80%，能拿到 1.5 到 2 倍加速；跨系列的模型接受率往往低于 40%，基本没有收益。所以选 draft 模型时，**同 tokenizer、同训练分布**比「越小越好」更重要。

## 三视角解析
### 🧑‍💻 程序员视角
推理显存 = 权重 + KV Cache + 激活。7B 模型 fp16 权重约 14GB，KV Cache 在 8k 上下文、并发 16 时能再吃十几 GB——只算权重必然 OOM。`max_model_len` 设太大是常见的「显存爆炸」原因，应按业务实际长度设。PagedAttention 把 KV Cache 切成固定大小的块，消除碎片，这是 vLLM 吞吐高的关键。连续批处理（continuous batching）让新请求随时插入，比静态批处理的吞吐高数倍。

### 🎓 博士生视角
推理优化的三条主线：降低计算量（量化 INT8/INT4、蒸馏）、降低访存（KV Cache 管理、算子融合）、提高并行度（连续批处理、张量并行）。LLM 推理是「显存带宽受限」而非「算力受限」：每生成一个 token 都要把全部权重读一遍，因此 batch 越大越能摊薄权重读取成本——这解释了「为什么大 batch 吞吐高但延迟也高」的权衡。投机解码（speculative decoding）用小模型草稿 + 大模型验证，在保持分布不变的前提下提速。

### 📚 考研者视角
AI 工程岗面试高频：
1. **KV Cache 计算**：`2 × 层数 × 头数 × head_dim × 序列长 × 并发 × 字节数`，要能估算。
2. **量化**：INT8/INT4 的精度损失、GPTQ/AWQ 的区别、量化后为什么还能保持效果。
3. **批处理**：静态批与连续批的差异、vLLM 的 PagedAttention 解决什么问题。
4. **延迟指标**：TTFT（首 token 时间）与 TPOT（每 token 时间），分别受什么影响。

## 收尾：推理优化是一条预算线，不是一个技巧

凯喵最后总结：推理引擎的所有优化，本质上都在同一条预算线上做取舍——**显存、吞吐、延迟、精度，四个量互相拉扯**。分页注意力用一点实现复杂度换显存；连续批处理用一点调度开销换吞吐；量化用一点精度换显存和带宽；投机解码用一点额外计算换延迟。

没有「全都更好」的方案，只有「在当前约束下最合适」的方案。所以调优的第一步永远不是改参数，而是**先量出瓶颈在哪**：是显存不够、是带宽打满、还是算力空转。量错了方向，再多的技巧都是白费。

这十二个现场的共同点是：每一个都源于对某个机制的误解，而不是某个 API 用错。机制理解对了，API 查文档就行；机制理解错了，文档看得再熟也会踩坑。
