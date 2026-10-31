# 卷积：局部连接、权值共享与感受野
> CNN 的核心不是「很多层」，而是两个结构先验：局部连接 + 权值共享。它们同时带来参数量骤降与平移等变，是视觉建模能成立的根基。

## 1. 卷积运算：局部连接与权值共享

卷积层用一组可学习的卷积核在输入上滑动，每个位置做局部加权和。与全连接相比，它有两个关键性质：**局部连接**（每个输出仅依赖一个局部窗口）与**权值共享**（同一核在所有空间位置复用）。工程里的 Conv 实际是互相关（核不翻转），因为核可学习，翻转与否不影响拟合能力。

### 🧑‍💻 程序员视角
- 选型：3×3 是工业默认（ResNet/Inception 都这么用）；大核不如堆叠小核——3 个 3×3 感受野等同 1 个 7×7，但参数量 27C² < 49C² 且夹了更多非线性。
- 计算三连：输出尺寸 out = (n + 2p − k)//s + 1；参数量 Params = Cout·Cin·k·k + Cout；乘加 FLOPs ≈ Cout·Cin·k·k·Hout·Wout。
- 降本手法：通道翻倍时参数按 Cout·Cin 增长，先用 1×1 卷积做通道升降再接 3×3（瓶颈结构）是标准操作。

### 🎓 博士生视角
- **平移等变性**是核心：设 T 为平移算子，则 f(T(x)) = T(f(x))。权值共享正是等变性的来源——核不随位置变，平移输入等价于平移输出。注意等变 ≠ 不变（后者要额外池化/全局池化）。
- 严格的卷积在数学上带核翻转，而深度学习用的是互相关；推导雅可比时务必清楚二者差别，否则梯度方向会错。
- 权值共享把参数从全连接的 H_in·H_out 压到 Cout·Cin·k²，是 CNN 能在图像上泛化的结构基础，也解释了它为何数据效率高于 MLP。

### 📚 考研者视角
- **参数量公式必须背**：Params = Cout·Cin·k·k + Cout（偏置）。易错点：把 Cin 省掉，或漏加偏置项。
- **输出尺寸公式**：out = floor((n + 2p − k)/s) + 1，注意是**向下取整**；常给 n、k、p、s 让你算输出尺寸与参数量。
- 概念题高频：「为什么 CNN 具有平移等变性」「池化如何带来平移不变」——能口述等变与不变的区别通常即给分。
## 2. 感受野与尺寸递推

感受野（receptive field）是输出一个像素「看到」的原始输入区域大小。堆叠多层卷积时感受野并不简单相加，而是随 stride 跳跃式增长。递推式：对第 l 层（kernel k_l、stride s_l），
RF_l = RF_{l-1} + (k_l − 1)·jump_{l-1}，jump_l = jump_{l-1}·s_l，初值 RF_0 = 1，jump_0 = 1。

### 🧑‍💻 程序员视角
- 学术上有「有效感受野」是高斯状且远小于理论最大值；但面试/笔试按理论递推作答即可。
- 想快速扩大感受野：用 stride>1 的下采样（跳跃大）比堆 stride=1 更省算力；**空洞（dilated）卷积**在不增参数量下指数级扩大感受野。
- 工程经验：分类网络末端感受野应覆盖整图；检测/分割常用 FPN 让浅层也保留大感受野。

### 🎓 博士生视角
- 递推的几何含义：第 l 层的一个 kernel 覆盖上一层 jump_{l-1} 步距的像素，故新增 (k_l−1)·jump_{l-1} 视野。这是卷积下采样的必然结果，可用归纳法严格证明。
- 空洞卷积把跳跃替换为膨胀率 d：RF = RF_prev + (k−1)·(s·d)_prev，d 越大感受野越大而参数不变，代价是空间分辨率采样的稀疏化。

### 📚 考研者视角
- **必考递推**：3 层 3×3 stride=1 卷积，感受野 = 1 + 2 + 2 + 2 = 7；含 stride=2 的层要把跳跃乘上去。
- **对比题**：1 个 7×7 卷积 vs 3 个 3×3 卷积，感受野相同（7）但后者参数更少、非线性更多——这是 ResNet 的经典论据。
- 易错：直接用 (k−1)×L 相加，忽略 stride 造成的跳跃放大，结果偏小。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 滑窗卷积：输出尺寸、参数量与感受野

```python
import numpy as np
np.random.seed(42)
X = np.random.randn(1, 1, 5, 5)                 # (N, Cin, H, W)
K = np.random.randn(3, 1, 3, 3)                 # (Cout, Cin, kh, kw)
b = np.zeros(3)

def conv2d_slide(x, k, bias, stride=1, padding=0):
    if padding:
        x = np.pad(x, ((0,0),(0,0),(padding,padding),(padding,padding)))
    N, Cin, H, W = x.shape
    Cout, _, kh, kw = k.shape
    oh = (H - kh)//stride + 1
    ow = (W - kw)//stride + 1
    out = np.zeros((N, Cout, oh, ow))
    for n in range(N):
        for c in range(Cout):
            for i in range(oh):
                for j in range(ow):
                    patch = x[n,:, i*stride:i*stride+kh, j*stride:j*stride+kw]
                    out[n,c,i,j] = np.sum(patch*k[c]) + bias[c]
    return out

out = conv2d_slide(X, K, b, stride=1, padding=0)
params = K.size + b.size
print("输入形状:", X.shape, " 核形状:", K.shape)
print("输出特征图形状:", out.shape)
print("参数量:", params, "(= Cout*Cin*k*k + Cout =", K.size, "+", b.size, ")")
print("输出尺寸公式: floor((5 + 0 - 3)/1) + 1 =", (5+0-3)//1 + 1)
# 感受野递推：单层 3x3 stride1 感受野 = 1 + (3-1)*1 = 3
print("单层 3x3 stride1 感受野:", 1 + (3-1)*1)
```

实际输出：

```text
输入形状: (1, 1, 5, 5)  核形状: (3, 1, 3, 3)
输出特征图形状: (1, 3, 3, 3)
参数量: 30 (= Cout*Cin*k*k + Cout = 27 + 3 )
输出尺寸公式: floor((5 + 0 - 3)/1) + 1 = 3
单层 3x3 stride1 感受野: 3
```

> 出处：`examples/ex01-conv-slide.json`。改一处再看输出变没变，比读三遍解释有用。

### im2col 卷积：与滑窗结果一致

```python
import numpy as np
np.random.seed(0)
X = np.arange(1*1*4*4, dtype=np.float64).reshape(1,1,4,4)
K = np.random.randn(2,1,2,2)

def conv2d_slide(x, k, stride=1):
    N,Cin,H,W = x.shape
    Cout,_,kh,kw = k.shape
    oh=(H-kh)//stride+1; ow=(W-kw)//stride+1
    out=np.zeros((N,Cout,oh,ow))
    for n in range(N):
        for c in range(Cout):
            for i in range(oh):
                for j in range(ow):
                    p=x[n,0,i*stride:i*stride+kh, j*stride:j*stride+kw]
                    out[n,c,i,j]=np.sum(p*k[c])
    return out

def conv2d_im2col(x, k, stride=1):
    N,Cin,H,W = x.shape
    Cout,_,kh,kw = k.shape
    oh=(H-kh)//stride+1; ow=(W-kw)//stride+1
    cols=[]
    for i in range(oh):
        for j in range(ow):
            cols.append(x[0,0,i*stride:i*stride+kh, j*stride:j*stride+kw].reshape(-1))
    cols=np.stack(cols).T                      # (Cin*kh*kw, oh*ow)
    Wcol=k.reshape(Cout,-1)
    out=Wcol @ cols                            # (Cout, oh*ow)
    return out.reshape(Cout, oh, ow)[None]

a = conv2d_slide(X, K)
b = conv2d_im2col(X, K)
print("滑窗输出形状:", a.shape)
print("im2col 输出形状:", b.shape)
print("两种方式最大绝对误差:", float(np.max(np.abs(a-b))))
print("结论: 误差为 0 即两者等价 ->", bool(np.max(np.abs(a-b)) < 1e-12))
```

实际输出：

```text
滑窗输出形状: (1, 2, 3, 3)
im2col 输出形状: (1, 2, 3, 3)
两种方式最大绝对误差: 7.105427357601002e-15
结论: 误差为 0 即两者等价 -> True
```

> 出处：`examples/ex02-im2col.json`。改一处再看输出变没变，比读三遍解释有用。

## 三视角小结

| 视角 | 关注 | 本文件要点 |
|---|---|---|
| 程序员 | 工程选型与性能 | 3×3 默认、瓶颈结构降本、尺寸/参数/FLOPs 三连公式 |
| 博士生 | 第一性原理 | 平移等变性的第一性原理与互相关 vs 严格卷积 |
| 考研者 | 标准问法与公式 | 背参数量与输出尺寸公式、感受野递推、7×7 vs 3×3×3 对比 |
