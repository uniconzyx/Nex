# 训练工程代码速查：凯喵的七段可复制片段

> 这一篇是配套速查。前四篇讲了初始化、优化器、混合精度与并行策略的机制，这一篇把它们落成代码。每段都标注用途与坑点，直接取用即可。

## 一、参数分组：weight decay 不该作用于 norm 与 bias

最常见的一个精度损失来源：把 weight decay 一视同仁地加在所有参数上，结果 LayerNorm 的缩放和偏置被持续拉向零。

```python
def split_params(model):
    decay, no_decay = [], []
    for n, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim < 2 or n.endswith(".bias") or "norm" in n.lower():
            no_decay.append(p)      # norm 权重、bias 不做衰减
        else:
            decay.append(p)
    return [
        {"params": decay, "weight_decay": 0.1},
        {"params": no_decay, "weight_decay": 0.0},
    ]
```

判据是「维度小于 2」或「名字含 norm/bias」。这条规则几乎是所有开源训练脚本的共识，因为它对应「只有矩阵乘法的权重才需要正则化」这个事实。

## 二、warmup + 余弦衰减

前面讲过的调度器，落成代码时要能按 step 取学习率。

```python
import math

def lr_at(step, peak, warmup=2000, total=100000, min_ratio=0.1):
    if step < warmup:
        return peak * (step + 1) / warmup
    if step >= total:
        return peak * min_ratio
    progress = (step - warmup) / max(1, total - warmup)
    return peak * (min_ratio + (1 - min_ratio) * 0.5 * (1 + math.cos(math.pi * progress)))
```

`min_ratio` 让学习率衰减到一个地板而不是 0——完全归零会让模型最后阶段几乎停止学习，损失一点收敛速度。

## 三、梯度裁剪与梯度范数监控

裁剪是必需品，同时把裁剪前的范数记下来，它是「训练是否健康」最灵敏的指标。

```python
import torch

def clip_and_log(model, max_norm=1.0):
    total = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm)
    return float(total)     # 裁剪前的总范数，建议写进日志
```

如果这个值长期远大于 `max_norm`，说明学习率偏大或数据有问题；如果长期接近 0，说明梯度消失了。

## 四、混合精度与 GradScaler

fp16 训练必须配 GradScaler，否则小梯度会下溢成 0。

```python
scaler = torch.cuda.amp.GradScaler()

for batch in loader:
    optimizer.zero_grad(set_to_none=True)
    with torch.cuda.amp.autocast(dtype=torch.float16):
        loss = model(**batch).loss
    scaler.scale(loss).backward()
    scaler.unscale_(optimizer)          # 裁剪前必须先反缩放
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    scaler.step(optimizer)
    scaler.update()
```

顺序是关键：`scale → backward → unscale → clip → step → update`。漏掉 `unscale_` 就裁剪，裁的是放大后的梯度，等于没裁。

## 五、梯度累积模拟大 batch

显存不够时用小 batch 累积。

```python
def train_step(model, micro_batches, accum=4):
    optimizer.zero_grad(set_to_none=True)
    for i, batch in enumerate(micro_batches):
        loss = model(**batch).loss / accum     # 必须除以累积步数
        loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
```

`/ accum` 这一行最容易漏。漏了之后梯度是累加和的平均值放大 accum 倍，等效学习率变大，训练直接发散。

## 六、梯度检查点

用计算换显存，代价是反向时重算前向。

```python
from torch.utils.checkpoint import checkpoint

def block_forward(x, block):
    if x.requires_grad and training:
        return checkpoint(block, x, use_reentrant=False)
    return block(x)
```

`use_reentrant=False` 是新版本推荐值，兼容性更好且支持更多场景。注意 checkpoint 只对「输入需要梯度」的段生效，否则不会节省任何东西。

## 七、损失尖峰检测与自动回滚

长训练里偶尔出现 loss 尖峰，一次就足以毁掉模型。检测加回滚是最便宜的保险。

```python
class SpikeGuard:
    def __init__(self, factor=3.0):
        self.factor = factor
        self.ema = None
    def bad(self, loss: float) -> bool:
        if self.ema is None:
            self.ema = loss
            return False
        self.ema = 0.9 * self.ema + 0.1 * loss
        return loss > self.factor * self.ema
```

检测到尖峰时，回滚到上一个 checkpoint 并跳过这批数据，比「继续训看看」可靠得多。

## 三视角解析
### 🧑‍💻 程序员视角
训练工程的第一原则是「先跑通再跑快」：先用小模型、小数据跑 100 步确认 loss 下降，再谈分布式。混合精度（AMP）能省一半显存、提速 30%，但要用 `GradScaler` 防梯度下溢，且 LayerNorm 等数值敏感算子应保持 fp32。梯度累积用小 batch 模拟大 batch，但 BatchNorm 的统计量仍按 micro-batch 算，和真正的大 batch 不等价。checkpoint 要存「模型 + 优化器状态 + 调度器 + 随机数状态」，少一样都续不上。

### 🎓 博士生视角
分布式训练的三条并行轴：数据并行（切 batch，梯度 AllReduce）、张量并行（切单层矩阵，通信频繁）、流水线并行（切层，需处理气泡）。ZeRO 通过「分片优化器状态/梯度/参数」把显存占用从 16Ψ 降到 16Ψ/N，代价是更多通信。这些技术的共同约束是「计算通信比」：通信量超过计算量时，加卡反而不加速。理解这一点，才能解释「为什么小模型多卡不如单卡」。

### 📚 考研者视角
算法工程岗面试高频：
1. **显存估算**：参数（P）、梯度（P）、优化器状态（Adam 为 2P）、激活值，混合精度下的变化。
2. **并行策略**：数据/张量/流水线并行的适用规模与通信开销。
3. **混合精度**：fp16 与 bf16 的差异（bf16 动态范围大、不易溢出）、loss scaling 的作用。
4. **训练稳定性**：梯度裁剪、warmup、学习率调度、NaN 排查顺序。

## 收尾

这七段代码覆盖了训练工程里最容易做错的七件事：参数分组、学习率调度、梯度裁剪、混合精度顺序、梯度累积的归一化、显存换计算、以及尖峰防护。凯喵的经验是，训练能不能跑出好结果，往往不取决于模型结构多新，而取决于这些工程细节有没有做对——因为它们决定了「模型有没有机会学到东西」。

```text
05-training-engineering-snippets.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 一、参数分组：weight decay 不该作用于 norm 与 bias  (python)
    |
    v
  [02] 二、warmup + 余弦衰减  (python)
    |
    v
  [03] 三、梯度裁剪与梯度范数监控  (python)
    |
    v
  [04] 四、混合精度与 GradScaler  (python)
    |
    v
  [05] 五、梯度累积模拟大 batch  (python)
    |
    v
  [06] 六、梯度检查点  (python)
    |
    v
  [07] 七、损失尖峰检测与自动回滚  (python)
    |
    v
  [08] 收尾  (-)
    |
    v
  [END] 三视角解析收口
```
