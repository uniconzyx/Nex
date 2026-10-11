# 过拟合、正则化与训练循环工程

## 1. 偏差-方差分解：过拟合的定量定义

```
E[(y − f̂(x))²] = Bias²(f̂) + Var(f̂) + σ²(不可约误差)
```

- **欠拟合**：Bias 大 —— 模型能力不足，训练集和测试集都差；
- **过拟合**：Var 大 —— 模型记住了训练集的噪声，训练好、测试差。

**一个反直觉的现代结论（双下降，double descent）**：
模型参数量超过「插值阈值」后，测试误差会先升后**再降**。
传统偏差-方差曲线无法解释这一点；现代大模型（参数远超样本数）恰恰工作在
「过参数化反而泛化更好」的区域。这说明经典理论在深度学习里并不完备。

## 2. 正则化手段分类

### 2.1 参数层面：L1 / L2

```
L1:  λ Σ|w|        → 产生稀疏解（部分权重精确为 0）
L2:  λ Σ w²        → 权重整体变小、更平滑
```

**为什么 L1 稀疏、L2 不稀疏**（几何解释）：
在约束区域 `|w| ≤ C`（菱形）与 `w² ≤ C`（圆）下找损失等高线的首个交点。
菱形的**尖角在坐标轴上**，交点落在尖角的概率高 → 某些维度恰好为 0。
圆形没有尖角，交点落在坐标轴的概率几乎为 0。

### 2.2 结构层面：Dropout

训练时以概率 p 随机置零神经元，测试时**不置零**而是把权重乘以 (1−p)
（或训练时用 inverted dropout 直接除以 (1−p)，测试时什么都不做——主流实现）。

**为什么有效**：
- 打破神经元之间的**共适应（co-adaptation）**：不能依赖某个特定邻居必须存在；
- 等价于训练 `2^n` 个子网络并做**集成平均**（近似）；
- 从贝叶斯角度近似于对权重的变分推断。

**注意**：Dropout 与 BatchNorm 同时使用时要小心——Dropout 的随机置零会破坏
BN 统计量估计，实践中常把 Dropout 放在 BN **之后**或直接改用 LayerNorm（Transformer 的做法）。

### 2.3 数据层面：数据增强

图像：翻转/裁剪/色彩抖动/Mixup/CutMix；
文本：回译/同义词替换/EDA；
**本质都是「人为扩大数据流形」**，让模型见到更多不变性。

### 2.4 过程层面：早停（Early Stopping）

监控验证集损失，连续 k 轮不下降就停止。**优点**是几乎零成本；
**缺点**是需要留出验证集，且停止点本身是对验证集的过拟合。

## 3. 归一化：BatchNorm vs LayerNorm

| | BatchNorm | LayerNorm |
|---|---|---|
| 归一化维度 | 沿 **batch 维**（对每个特征通道） | 沿 **特征维**（对每个样本） |
| 依赖 batch size | **是**（小 batch 统计量不稳） | 否 |
| 训练/推理差异 | 需要维护 running mean/var | 无 |
| 适用 | CNN | **Transformer / RNN（标配）** |

**为什么 Transformer 用 LayerNorm**：
序列长度可变 + batch 小 + 需要在线推理，BN 的 batch 统计量会失效。
另外 RNN 中不同时间步的统计量不同，BN 也难以处理。

**BN 为什么能加速训练**（机理仍在讨论，主流解释是**平滑了损失曲面**）：
它让每层输入的分布稳定，使得后续层不必不断适应输入分布的变化
（这被称为 Internal Covariate Shift），从而**允许更大的学习率**。

## 4. 训练循环的标准骨架（含所有工程细节）

```python
for epoch in range(epochs):
    model.train()                      # 启用 Dropout / BN 更新统计量
    for x, y in loader:
        opt.zero_grad()                # ① 清空梯度（否则会累加！）
        loss = criterion(model(x), y)
        loss.backward()                # ② 反向传播，累积到 .grad
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)   # ③ 梯度裁剪（防爆炸）
        opt.step()                     # ④ 更新参数
    scheduler.step()                   # ⑤ 学习率调度
    model.eval()                       # ⑥ 评估前切 eval：关闭 Dropout，冻结 BN
    with torch.no_grad():              # ⑦ 推理不建图，省显存
        ...
```

**新手最容易漏的三件事**：
1. **`zero_grad()`** —— 梯度默认累加，不清空会导致跨 batch 的错误累积
   （除非你刻意做梯度累积来模拟大 batch）；
2. **`model.eval()`** —— 忘记切换会让 Dropout 在评估时继续随机置零，指标错误；
3. **`torch.no_grad()`** —— 评估时建图会白白占几 GB 显存。

## 5. 梯度累积：显存不够时的等效大 batch

```python
for i, (x, y) in enumerate(loader):
    loss = criterion(model(x), y) / accum_steps
    loss.backward()                    # 梯度累加，不 zero_grad
    if (i + 1) % accum_steps == 0:
        opt.step(); opt.zero_grad()
```

把 N 个 mini-batch 的梯度累加起来再更新，等效于 batch size × N。
**代价是不增加并行度（时间不变），只省显存**。

## 6. 一句话总结

> **正则化的四条战线：参数（L1/L2）、结构（Dropout）、数据（增强）、过程（早停）。
> 训练循环里最容易漏的是 zero_grad、eval 模式与 no_grad——这三处的错误都不会报错，只会静默给错结果。**

---

## 三视角解析

### 🧑‍💻 程序员视角
- **训练循环骨架**（务必背熟）：`zero_grad → forward → loss → backward → clip → step`；漏掉 clip 在大模型上极易炸。
- 显存不够时用**梯度累积**模拟大 batch（累加若干 step 的梯度再 step 一次），数学上等效但 BN 统计会略有差异。
- Dropout / BatchNorm 在**推理时必须切到 eval 模式**（`model.eval()`），否则预测结果会随机漂移——这是最经典的上线事故。

### 🎓 博士生视角
- **偏差-方差分解**：`E[(y − ŷ)²] = 偏差² + 方差 + 不可约噪声`。过拟合就是方差项主导，正则化就是在**偏差与方差之间做权衡**。
- 正则化等价于**对假设空间施加先验**：L2 ↔ 高斯先验 → MAP 估计；L1 ↔ 拉普拉斯先验 → 稀疏解。这一视角把「调参玄学」变成贝叶斯推断。
- **BatchNorm 与 LayerNorm 的差异在统计维度**：BN 跨 batch 维统计（依赖 batch 大小、需维护 running stats），LN 跨特征维统计（与 batch 无关、适合变长序列），这就是 Transformer 选 LN 的原因。
- Dropout 可解释为**对指数多个子网络的隐式集成**（推理时用期望值近似）。

### 📚 考研者视角
- **数理统计直接考点**：**偏差-方差分解**、**最大似然 vs 最大后验（MAP）**——「L2 正则 = 高斯先验下的 MAP」是可以直接写在答题纸上的加分句。
- 若专业课含模式识别，常考「过拟合的成因与缓解手段」（样本量、正则化、交叉验证、早停、数据增强），要求分点作答。
- 记忆锚点：**L2 = 高斯先验、L1 = 拉普拉斯先验、Dropout = 子网络集成、BN 依赖 batch、LN 不依赖**。
