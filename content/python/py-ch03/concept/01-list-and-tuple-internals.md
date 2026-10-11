# list 与 tuple 的底层：动态指针数组 vs 定长引用数组

## 1. list 不是链表，是「过度分配的动态指针数组」

CPython 的 `list` 对象（`Objects/listobject.c`）结构可简化为：

```c
typedef struct {
    PyObject_VAR_HEAD      // 含 ob_size（已用长度）
    PyObject **ob_item;    // 指向「指针数组」的指针：每个槽位是一个 PyObject*
    Py_ssize_t allocated;  // 已分配的槽位数（>= ob_size）
} PyListObject;
```

关键结论：

- **数组里存的是指针，不是对象本体**。`a = [1, "x", obj]` 中三个元素类型不同也没关系，因为槽位统一是 `PyObject*`（8 字节，64 位）。这也解释了为什么 list 是「异构容器」。
- **`allocated` 与 `len()` 不相等**。list 会**过度分配（over-allocate）**，预留下次 append 的空间，避免每次都 `realloc`。

```
len(a)=4, allocated=8
ob_item -> [ p0 | p1 | p2 | p3 | -- | -- | -- | -- ]
                 ^^^^^^^^^^^^已用       ^^^^^^^^^^^^预留（未初始化）
```

### 扩容策略（CPython 的实际公式）

```c
new_allocated = (size_t)newsize + (newsize >> 3) + (newsize < 9 ? 3 : 6);
// 即：新容量 = 需求 + 需求/8 + (3 或 6)
```

这不是教科书里的「2 倍扩容」，而是 **1/8 的渐进增长 + 小列表固定余量**。原因（工程取舍）：

- 2 倍扩容在大数据量下**浪费内存**（最坏浪费 50%），且 `realloc` 可能需要拷贝大量指针。
- 1/8 增长让**摊销成本仍是 O(1)**：虽然单次扩容更频繁，但分摊到每次 append 仍是常数。
- 小列表 `+3/+6` 避免前几次 append 反复扩容（0→4→8→16… 的经典序列就是这套公式的结果）。

可用下面代码观察容量变化（注意 `getsizeof` 只算容器本身，不算元素对象）：

```python
import sys
a = []
prev = 0
for i in range(30):
    a.append(i)
    size = sys.getsizeof(a)
    if size != prev:
        print(f"len={len(a):2d} -> sizeof={size}")
        prev = size
```

## 2. 复杂度：为什么 append 摊销 O(1)、insert(0) 是 O(n)

| 操作 | 复杂度 | 原因 |
|---|---|---|
| `a[i]` 索引 | O(1) | 连续数组随机访问，`ob_item[i]` |
| `append(x)` | **摊销 O(1)** | 有预留就直接写；偶尔扩容 O(n) 但分摊后为常数 |
| `pop()`（尾） | O(1) | 只减 `ob_size`，不搬移 |
| `pop(0)` / `insert(0, x)` | **O(n)** | 需整体 `memmove` 搬移 n 个指针 |
| `x in a`（成员判断） | O(n) | 线性扫描并逐个 `__eq__`，**无哈希** |
| `del a[i]`（中间） | O(n) | 搬移 + 可能的缩容 |
| `len(a)` | O(1) | 直接读 `ob_size`，不是遍历 |

**工程结论**：需要频繁在**头部**增删，用 `collections.deque`（双端队列，两端 O(1)）；需要频繁 `in` 判断，把 list 换成 `set`（O(1) 平均）。这是本章最重要的**选型直觉**。

注意一个反直觉点：**list 缩容也会发生**。`pop` 后若 `ob_size` 掉到 `allocated/2` 以下，CPython 会 `realloc` 缩小，避免长期持有大数组——但这会让「反复 append/pop」在临界点抖动。

## 3. tuple：不可变 ≠ 内容不可变

`tuple` 是**定长的引用数组**：

```c
typedef struct {
    PyObject_VAR_HEAD
    PyObject *ob_item[1];   // 定长，创建时确定，不可扩容
} PyTupleObject;
```

- **不可变指的是「槽位里的指针不能改」**，不是「指针指向的对象不能改」。
  ```python
  t = ([1, 2], "a")
  t[0].append(3)     # 合法！元组"包含"的列表被原地修改
  print(t)           # ([1, 2, 3], 'a')
  t[0] = [9]         # TypeError: 'tuple' object does not support item assignment
  ```
  这就是「元组里有列表」的经典陷阱：元组**自身**不可变，但它**引用的对象**可变。想真正不可变，元素也必须是不可变的（如 `tuple` 里放 `tuple`）。
- **内存更省**：`sys.getsizeof(())` = 40，而 `sys.getsizeof([])` = 56（64 位 CPython 3.11 附近）。因为 tuple 不带 `allocated` 预留，也没有过度分配。
- **可哈希**：因为不可变，tuple 可作为 dict 的键（`{(1,2): "x"}`）；list 不行（`TypeError: unhashable type: 'list'`）。前提是**所有元素也可哈希**——`([1], 2)` 作为键会失败，因为 list 不可哈希。
- **性能**：tuple 的构造与索引略快于 list（无需检查扩容、内存更紧凑），CPython 还对**空 tuple 做了单例缓存**（`() is ()` 恒为 True）。

## 4. 与 C++ / Java 的对照（帮助建立直觉）

| 容器 | CPython | C++ | Java |
|---|---|---|---|
| 动态数组 | `list`（存 PyObject*） | `std::vector<T>`（存值） | `ArrayList<E>`（存引用） |
| 扩容 | ~1.125× + 余量 | 通常 2×（libstdc++） | 1.5× |
| 内存局部性 | **差**（指针跳转，元素散落堆上） | **好**（值连续） | 差（同 CPython） |

**博士视角的关键差异**：`std::vector<int>` 是真的把 int 连续排布，CPU 缓存友好、可向量化；CPython 的 `list` 存的是指针，遍历时要**间接跳转**到堆上的各个 int 对象，缓存局部性差得多。这正是「Python 比 C++ 慢一个数量级」在数据结构层的根源之一，也是 `array` 模块（`array('i')` 存紧凑的 C int）与 NumPy（连续类型化缓冲区）存在的意义。

## 5. 速记

- list = 过度分配的**指针**数组；append 摊销 O(1)，`insert(0)`/`pop(0)` 是 O(n)。
- `x in list` 是 O(n) → 需要频繁查找就换 set/dict。
- tuple 不可变的是**引用**，内层可变对象仍可改；不可变才可哈希。
- 缓存局部性：C++ `vector` 存值（快），Python `list` 存指针（慢），NumPy 存紧凑类型化缓冲区（快）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `list` 可变、`tuple` 定长；`tuple` 能作 `dict` 的键，**前提是其元素也都不可变**（含可变元素就不可哈希，会报错）。
- 已知规模就预分配（`[None] * n`）或批量构建，避免反复扩容搬移。
- `list` 元素的增删在中间是 O(n)（要搬移指针），大量中间操作考虑 `collections.deque`（两端 O(1)）。

### 🎓 博士生视角
- `list` 是**动态指针数组**：元素是 `PyObject*` 引用而非值本身，因此连续存储的是「引用」而非「对象」。这与 C 的 `int arr[]` 有本质区别。
- 扩容采用约 **`n + n>>3`** 的过度分配公式（约 1.125 倍，**不是 2 倍**），比倍增更省内存但需要更频繁扩容——这是内存/时间取舍的实证结果。
- `tuple` 是定长引用数组，创建后不可变，因此可被解释器缓存复用（小 tuple 常量折叠）；不可变性还带来「可哈希」与「线程安全共享」两个额外好处。

### 📚 考研者视角
- 与 408 的**顺序表**完全对应：随机访问 O(1)、中间插入删除 O(n)；常考的「顺序表平均移动次数」可直接在此对照。
- 与 C 数组的差异值得写清：**Python list 存的是指针**，所以 `[[0]*3]*3` 会得到三行同一对象的经典陷阱。
- 记忆锚点：**list 扩容约 1.125 倍**；**list 存引用、C 数组存值**。
