# §5 ai-ch01 实战手记：凯喵带你把机器学习用「翻车」

> 前四节把张量、自动求导、优化器、正则讲透了。这一节凯喵把训练模型最容易「loss 不降 / 显存爆 / 精度奇低」的 12 个现场搬出来——每个都是调参调到怀疑人生换来的教训。

### 现场一：张量维度对不上，矩阵乘直接报错

凯喵第一次手写线性层，`x` 是 `(batch, 784)`、`W` 是 `(10, 784)`，一乘就 `shape mismatch`。矩阵乘要求**前者最后一维 == 后者倒数第二维**。记不住就画图：行乘列，对齐中间那维。

```python
import torch
x = torch.randn(32, 784)        # (B, in)
W = torch.randn(10, 784)        # 错：应是 (out, in)
# y = x @ W.T                   # 要转置成 (784, 10)
W = W.t()                       # (784, 10)
y = x @ W                       # (32, 10) ✅
```

### 现场二：autograd 没清梯度，loss 越训越怪

凯喵的 loss 跑着跑着数值爆炸。原因：PyTorch 默认**梯度累加**，不在每个 step 前 `zero_grad()`，梯度越积越大，更新步长失控。训练循环第一步永远是清梯度。

```python
for x, y in loader:
    opt.zero_grad()             # ✅ 必须清，否则梯度累加
    loss = model(x).loss(y)
    loss.backward()
    opt.step()
```

### 现场三：PyTorch 默认 train/eval 模式不分，BN/Dropout 乱来

凯喵训练时 ACC 98%、一测试掉到 50%。忘了切 `model.eval()`，测试时 BN 用当前 batch 统计量、Dropout 还在随机丢神经元。推理前一定 `model.eval()`，训练前 `model.train()`。

```python
model.eval()                    # ✅ 关 Dropout、用全局 BN 统计量
with torch.no_grad():
    for x, y in test_loader:
        pred = model(x)
# model.train()                 # 回来再切回训练
```

### 现场四：学习率太大，loss 直接 NaN

凯喵抄了个 lr=0.1 的配置训 Transformer，loss 三步变 NaN。学习率决定每一步迈多大，太大一脚跨过谷底发散。常见起点：SGD 1e-2、Adam 1e-3~3e-4；用 **学习率预热 + 余弦退火**更稳。

```python
import torch
opt = torch.optim.Adam(model.parameters(), lr=3e-4)  # ✅ 温和起点
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=10)
```

### 现场五：特征没归一化，梯度东倒西歪

凯喵的房价预测里「面积」是几百、「房龄」是个位数，SGD 在细长椭圆等高线上 zigzag 半天不收敛。不同量纲的特征要先**标准化（减均值除标准差）或归一化**，让等高线接近正圆，收敛快十倍。

```python
from sklearn.preprocessing import StandardScaler
X = StandardScaler().fit_transform(X_raw)   # 均值0方差1
```

### 现场六：过拟合——训练集 100% 测试集拉胯

凯喵的模型把训练样本背得滚瓜烂熟，测试却一塌糊涂。经典过拟合：模型容量远大于数据。解法三件套：更多数据 / 正则（L1、L2、Dropout、BN）/ 早停（监控验证集，不再下降就停）。

```python
# L2 权重衰减
opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
# Dropout 在训练时随机置零一部分神经元
```

### 现场七：类别不平衡，模型全猜多数类

凯喵做风控，正负比 1:99，模型无脑预测「正常」也有 99% 准确率，毫无用处。不平衡数据要：加权损失（`class_weight`）、过采样少数类（SMOTE）、或看 PR 曲线 / F1 而非准确率。

```python
from sklearn.utils.class_weight import compute_class_weight
w = compute_class_weight("balanced", classes=[0,1], y=y_train)
# 把权重喂进损失函数
```

### 现场八：把测试集泄露进训练（数据泄漏）

凯喵先对整个数据集做 `StandardScaler` 再切分，测试集的统计量混进了训练，结果虚高。任何用到标签或未来信息的变换都必须在**训练集上 fit、再 transform 验证/测试**，绝对不能全量 fit。

```python
from sklearn.model_selection import train_test_split
X_tr, X_te, y_tr, y_te = train_test_split(X, y)
sc = StandardScaler().fit(X_tr)        # ✅ 只在训练集 fit
X_te = sc.transform(X_te)              # 测试集只 transform
```

### 现场九：one-hot 后树模型反而更慢

凯喵给随机森林喂了高基数 one-hot（城市名几千类），训练和预测都卡。高基数类别对**树模型**应该用**有序编码 / 目标编码**而非 one-hot；one-hot 更适合线性模型和神经网络。

```python
# 树模型：用 LabelEncoder / 频率编码即可
# 神经网络 / 线性：才考虑 one-hot 或 embedding
```

### 现场十：激活函数选错，梯度消失

凯喵用纯 `sigmoid` 堆 10 层，反向传播梯度连乘趋近于 0，前面层几乎不更新。深层网络用 `ReLU` 系（LeakyReLU、GELU）缓解；RNN 用 `tanh`/`LSTM`；输出层按任务选（二分类 sigmoid、多分类 softmax、回归线性）。

```python
import torch.nn as nn
nn.Sequential(nn.Linear(64, 64), nn.ReLU())   # ✅ 现代默认
# nn.Sigmoid() 深层易梯度消失
```

### 现场十一：用 MSE 做多分类，收敛极慢

凯喵多分类配了 `MSELoss` + softmax，loss 卡在半山腰。多分类应配**交叉熵**（对应类别分布假设），梯度在饱和区也健康。PyTorch 的 `CrossEntropyLoss` 已内含 softmax，别手写再套。

```python
# ✅ 多分类：CrossEntropyLoss 内含 softmax，label 用类别索引
loss = nn.CrossEntropyLoss()(logits, y_long)
# ❌ 手写 softmax + MSELoss 收敛极慢
```

### 现场十二：BatchNorm 与 Dropout 顺序乱放

凯喵把 Dropout 放 BN 前面，统计量被随机置零破坏，训练不稳。常见做法：Dropout 放 BN **之后**，或 Transformer 直接改用 LayerNorm（对 dropout 更鲁棒）。

```python
# 常见顺序：Linear -> BN -> Activation -> Dropout
nn.Sequential(nn.Linear(64,64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.2))
```

> 凯喵总结：ML 的坑 90% 在「维度」「模式」「数据泄漏」「不平衡」「过拟合」。把这 12 个现场刻进调参肌肉记忆，少熬几个通宵。
