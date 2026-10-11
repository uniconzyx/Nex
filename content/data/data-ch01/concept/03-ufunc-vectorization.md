# ufunc 与向量化：把循环从 Python 搬进 C

## 1. ufunc 是什么

**ufunc（universal function）** = 对 ndarray 逐元素执行、且在 **C 层面循环**的函数。
`np.add` / `np.sin` / `np.exp` / `np.sqrt` / 比较运算符 `>` 都是 ufunc。

```python
a + b        # 语法糖，等价于 np.add(a, b)，后者是 ufunc
np.sqrt(a)   # ufunc
```

**关键区别**：`a + b` 的循环发生在 **C 的紧循环里**，一百万次加法只付出**一次** Python 调用开销；
而 `for i in range(n): c[i] = a[i] + b[i]` 要付出一百万次：下标取值、查类型、构造 PyObject、写回。

## 2. 三个数量级的差距从哪来

| 因素 | Python 循环 | NumPy 向量化 |
|---|---|---|
| 解释器开销 | 每元素一次字节码分派 | 全数组一次调用 |
| 类型检查 | 每元素查 `ob_type` | 一次确定 dtype |
| 内存布局 | 指针跳转，cache miss | 连续，可预取 |
| SIMD | 无 | 编译器可发出 AVX2/AVX-512，一次处理 4/8 个 float64 |
| 临时对象 | 每元素一个新 PyObject | 结果区一次分配 |

实测（N = 10⁶，本机 3.13）：

```
Python for 循环      ~100 ms
list comprehension   ~50 ms
np.sum(a)            ~1 ms     ← 约 100 倍
```

**注意**：向量化**不是**万能的。以下情况反而更慢或更费内存：
- 数组很小（< 1000 元素）：NumPy 的固定调用开销（约 1 μs）占比过大；
- 需要大量中间数组：`a*b + c/d - e*f` 会产生 5 个临时数组，每个都是完整大小 → 内存峰值 5 倍。
  解决办法是分块（chunking）或用 `numexpr` / `np.add(..., out=...)` 显式复用缓冲。

## 3. ufunc 的四类常用方法

```python
np.add.reduce(a)      # 归约：等价于 np.sum(a)
np.add.accumulate(a)  # 累积：等价于 np.cumsum(a)
np.add.outer(a, b)    # 外积：得到 (len(a), len(b)) 的全体两两之和
np.add.at(a, idx, v)  # 无缓冲就地加：处理重复索引时结果正确（a[idx] += v 会丢重复项）
```

**`np.add.at` 是个隐藏陷阱的解药**：

```python
a = np.zeros(3)
idx = np.array([0, 0, 0, 1])
a[idx] += 1        # 结果 [1, 1, 0] —— 重复索引只生效一次！
np.add.at(a, idx, 1)  # 结果 [3, 1, 0] —— 正确
```

原因：`a[idx] += 1` 展开为「取值 → 加 → 赋值」，重复索引的三次加法各自基于**同一个旧值**，
最后只写入一次。这是花式索引 + 就地运算的经典 bug。

## 4. 用 np.where 取代 Python 层 if

```python
# 慢 + 啰嗦
out = np.empty_like(x)
for i in range(len(x)):
    out[i] = x[i] * 2 if x[i] > 0 else 0

# 快 + 简洁
out = np.where(x > 0, x * 2, 0)
```

**注意 `np.where` 的两个分支都会被求值**（不像 Python 的惰性 `?:`），
所以若某分支会除零，要先用 `np.errstate` 或改写为 `np.divide(..., where=...)`：

```python
np.divide(1.0, x, out=np.zeros_like(x), where=x != 0)
```

## 5. 聚合的 axis 语义（务必形成肌肉记忆）

```python
a.shape == (3, 4)
a.sum()         # 标量（全体求和）
a.sum(axis=0)   # shape (4,)  —— 沿行方向压掉第 0 维 → 每列的和
a.sum(axis=1)   # shape (3,)  —— 沿列方向压掉第 1 维 → 每行的和
a.sum(axis=(0,1))  # 标量（多轴聚合）
a.sum(keepdims=True)  # shape (1,1) —— 保留被压掉的维度，便于后续广播
```

**`keepdims=True` 是避免手动 `[:, None]` 升维的利器**，尤其在写归一化时：

```python
z = (x - x.mean(axis=0, keepdims=True)) / x.std(axis=0, keepdims=True)
```

## 6. 一句话总结

> **向量化的本质是把「解释器级循环」换成「C 级紧循环 + SIMD」；
> 代价是可能产生大量临时数组，所以超大数组要分块或用 out= 复用缓冲。**

---

## 三视角解析

### 🧑‍💻 程序员视角
- 铁律：**能向量化就别写 `for`**；`np.where` 取代 Python 层 `if`；聚合务必搞清 `axis` 语义。
- 性能上限判断：如果操作是「读一遍、写一遍」的简单逐元素运算，那它就是 **memory-bound**，再怎么优化也超不过内存带宽。
- 遇到必须写循环的场景（滚动窗口、状态依赖），优先考虑 `numba` / `Cython`，而不是硬凑向量化。

### 🎓 博士生视角
- ufunc 是「**逐元素 C 循环 + 类型特化**」的集合（loops），`add.reduce` 这类方法通过分派到特化实现避免了解释器开销与对象装箱。
- 向量化的三个加速来源要能分开讲清楚：① 去掉解释器逐元素开销；② 连续内存的缓存/预取友好；③ SIMD 指令级并行。三者量级不同，混为一谈就说不清「为什么快」。
- **BLAS 的分块矩阵乘**通过提高算术强度（计算量/访存量）把 memory-bound 转成 compute-bound——这是 NumPy 背后真正的性能工程。

### 📚 考研者视角
- **408 计组直接交叉**：**SIMD / 向量处理机**、**流水线**、**指令级并行**、**内存带宽与存储层次**——「向量化为什么快」在计组里就是「并行度与访存比」的问题。
- 若考数据结构的复杂度，注意区分「算法渐进复杂度」与「实际吞吐」：同一 O(n) 在 SIMD 与标量下可差数倍。
- 记忆锚点：**向量化三大来源 = 去解释器开销 + 连续内存局部性 + SIMD**；**memory-bound 的操作无法靠算法优化超越带宽上限**。
