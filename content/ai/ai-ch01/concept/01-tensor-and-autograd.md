# 张量、计算图与反向模式自动微分

## 1. 张量不是「多维数组」这么简单

张量（tensor）在计算框架里是**带梯度元数据的多维数组**：

```
Tensor 对象
┌────────────────────────────────────┐
│ data      : ndarray（真实数值）      │
│ grad      : ndarray（累积的梯度）    │
│ requires_grad : bool（是否需要梯度） │
│ grad_fn   : 产生它的操作（用于反向） │
│ _backward : 该操作的 VJP 闭包        │
└────────────────────────────────────┘
```

**张量的数学定义**（这才是「张量」区别于「矩阵」的地方）：
张量是**多重线性映射**，其分量在坐标变换下按特定规律变换。
但在深度学习工程语境里，它被简化为「N 维数组 + 自动微分元数据」。
这个简化丢失了几何意义，却换来了可用性——理解这一点能避免你在论文里看到
「张量分解」「张量网络」时产生概念混淆。

## 2. 计算图：前向建图，反向求导

```python
y = (w * x + b)          # 前向：构建计算图
                         #   mul -> add
y.backward()             # 反向：沿图拓扑逆序传播梯度
```

```
前向（实线）               反向（虚线，VJP）
  x ─┐                       x ←───────────┐
      ├─ mul ─┐                             │
  w ─┘        ├─ add ─→ y      w ← grad_w   │
            ┌┘                 b ← grad_b   │
  b ────────┘                               │
                              y ← dL/dy ────┘
```

执行 `backward()` 时，框架：
1. 对计算图做**拓扑排序**（保证一个节点的所有下游节点都已处理完）；
2. 从输出节点开始，逐节点调用它的 `_backward` 闭包，把上游梯度乘上**局部雅可比**传给输入；
3. 每个叶子张量把收到的梯度**累加**到 `.grad`。

**为什么要拓扑排序**：节点 A 的梯度依赖于它所有下游节点的梯度，
必须等下游都算完才能算 A。这就是「反向」二字的含义。

## 3. VJP（向量-雅可比积）：反向传播的真身

设 `y = f(x)`，其中 `x ∈ R^n`，`y ∈ R^m`。完整的雅可比矩阵是 `J ∈ R^{m×n}`。
**反向模式不显式构造 J**，而是计算：

```
vjp = v^T · J    其中 v = ∂L/∂y ∈ R^m（上游梯度）
结果 ∈ R^n       即 ∂L/∂x
```

**这不只是一点优化，而是本质差别**：

| | 前向模式 AD | 反向模式 AD |
|---|---|---|
| 计算 | JVP：J · v | VJP：v^T · J |
| 一次能求 | 一个**输入方向**的导数 | 一个**输出标量**对所有输入的导数 |
| 训练场景代价 | 每个参数一次前向 → O(P) 次 | **一次反向 → O(1) 次前向** |

深度学习的损失函数是**标量**（m=1），参数有 P 个：
- 前向模式要求 P 次前向传播（P 是十亿量级 → 不可行）；
- 反向模式只需 1 次前向 + 1 次反向 ≈ **2 倍前向代价**。

**这就是「训练十亿参数模型」在数学上可行的唯一原因。** 反向传播常被说成
「链式法则的应用」，但真正的洞察是**计算方向的选择**，不是链式法则本身。

## 4. 手写 autograd：50 行看懂 PyTorch

```python
import numpy as np

class Tensor:
    def __init__(self, data, _children=()):
        self.data = np.asarray(data, dtype=np.float64)
        self.grad = np.zeros_like(self.data)
        self._backward = lambda: None
        self._prev = set(_children)

    def __add__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        out = Tensor(self.data + other.data, (self, other))
        def _backward():
            # 加法的局部雅可比是单位矩阵，梯度原样传递
            self.grad  += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        out = Tensor(self.data * other.data, (self, other))
        def _backward():
            self.grad  += other.data * out.grad   # ∂(a*b)/∂a = b
            other.grad += self.data  * out.grad   # ∂(a*b)/∂b = a
        out._backward = _backward
        return out

    def backward(self):
        topo, visited = [], set()
        def build(v):                     # 拓扑排序（DFS 后序）
            if v not in visited:
                visited.add(v)
                for c in v._prev: build(c)
                topo.append(v)
        build(self)
        self.grad = np.ones_like(self.data)   # 起点：∂y/∂y = 1
        for v in reversed(topo):              # 逆序传播
            v._backward()
```

**三个必须理解的细节**：

1. **`grad` 用 `+=` 累加而非 `=` 赋值**：一个张量可能被多个下游使用（如 `y = x*x` 中 x 用了两次），
   梯度必须求和。这也是为什么 PyTorch 每轮训练前要 `optimizer.zero_grad()`。
2. **`self.grad += other.data * out.grad` 里的 `other.data` 是前向时的值**：
   反向传播需要用到前向的中间结果，这就是**显存占用的主要来源**——
   你不能在前向时释放中间激活，否则反向算不了。这也是「梯度检查点（checkpointing）」
   要拿计算时间换显存的原因。
3. **`backward()` 的起点是 `∂L/∂L = 1`**：所以代码里 `self.grad = ones_like`。

## 5. 框架在做但你该知道的事

- **PyTorch 是动态图（define-by-run）**：每次前向都重建图，灵活但调度开销大；
  TensorFlow 1.x 是静态图（先定义后运行），可全局优化但调试难。现代 TF2 默认 eager，向 PyTorch 靠拢。
- **`torch.no_grad()` 的作用**：推理时不建图，省掉反向所需的元数据与显存。
- **`detach()` vs `requires_grad=False`**：前者切断当前张量的图连接，后者声明不需要梯度。

## 6. 一句话总结

> **反向传播的精髓不是链式法则，而是「反向模式」这个计算方向的选择：
> 它把「P 次前向」压缩成「1 次反向」，代价是必须保留全部中间激活（显存换时间）。**

---

## 三视角解析

### 🧑‍💻 程序员视角
- 用框架时的三个必备认知：**梯度是累加的**（所以每个 step 前必须 `zero_grad()`）、`.backward()` 只对叶子张量填 `.grad`、推理时要 `torch.no_grad()` 关掉建图。
- 调试手段：用**数值梯度（中心差分）**校验手写反向传播——这是唯一能证明「导数算对了」的方法，相对误差应到 1e-6 以下。
- 工程取舍：别自己写 autograd 上生产（框架已做过算子融合与内存复用），但**必须会手推**，否则遇到 loss 不降时无从下手。

### 🎓 博士生视角
- 反向模式自动微分的代价是 **O(1) 次前向代价**（一次反向扫就能拿到所有输入的梯度），而前向模式需要 O(n) 次。神经网络恰好是「输入维度巨大、输出是标量 loss」的形态，因此反向模式是唯一可行选择。
- 计算图是 **DAG**，反向传播 = 拓扑逆序 + 链式法则；「复用中间结果」正是动态规划思想，所以 BP 可看作链式法则与 DP 的合体。
- 三种微分方式的分野：**符号微分**表达式膨胀、**数值微分**有截断误差且代价 O(n)、**自动微分**精确且代价可控——这是 AD 成为深度学习基石的真正原因。

### 📚 考研者视角
- 408 不直接考自动微分，但考**图/拓扑排序**与**递归**——计算图就是 DAG，反向传播就是拓扑逆序，两者是同一数据结构的不同包装。
- 若报考人工智能方向（自命题专业课），**BP 推导**是必考大题：写出链式法则逐层求导，并说明为什么反向比前向省算力。
- 记忆锚点：**反向传播 = 链式法则 + 动态规划（复用中间激活）**；答题时点出「复用」二字通常能拿分。
