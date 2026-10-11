# 02 · List 的双实现：ArrayList 动态数组扩容 与 LinkedList 双向链表

## 一、理论根基：两种「有序序列」的内存模型

`List` 承诺「有序、可重复、支持下标」。但「有序」在内存里可以有两种完全不同的实现，对应两种时间/空间权衡：

- **动态数组（ArrayList）**：元素在**连续内存**中，下标即偏移量。优势是随机访问 O(1)、CPU 缓存命中率高；代价是中间插入/删除要搬移元素 O(n)，以及扩容时的数组拷贝。
- **双向链表（LinkedList）**：每个节点存 `prev`/`next`/值，节点**散落堆上**。优势是已知节点时插入/删除 O(1)；代价是随机访问要沿指针走 O(n)，且节点分散导致**缓存局部性极差**（这是链表在现代 CPU 上慢得离谱的隐藏主因，而非单纯算法复杂度）。

## 二、实现机制：ArrayList 扩容的 1.5 倍与 JVM 细节

打开 `ArrayList` 源码，关键字段是 `transient Object[] elementData` 与 `size`。容量（capacity）是数组长度，大小（size）是有效元素数。

- **默认构造**：JDK 7+ 默认构造时 `elementData` 指向一个共享的空数组（`DEFAULTCAPACITY_EMPTY_ELEMENTDATA`），容量记为 0，**首次 `add` 才扩容到 `DEFAULT_CAPACITY = 10`**。这避免了「一 new 就分配 10 个引用」的浪费。
- **扩容公式**：`newCapacity = oldCapacity + (oldCapacity >> 1)`，即 **约 1.5 倍**（奇数向下取整，如 15→22）。扩容时调用 `Arrays.copyOf(elementData, newCapacity)`，分配新数组并 `System.arraycopy` 拷贝旧数据，旧数组等待 GC。
- **为什么是 1.5 而不是 2**？这是「均摊拷贝成本」与「内存浪费」的折中。按等比数列，容量按 1.5 增长时，累计拷贝的元素总数约为最终容量的常数倍（均摊 O(1)）；倍数越大内存浪费越多，倍数过小（如 1.1）则拷贝次数过多。1.5 让均摊成本与空间浪费都较优。
- `ensureCapacity(int)` 可提前扩容避免多次拷贝；`trimToSize()` 收缩到 size 释放多余内存。

实测见 `examples/ex01-arraylist-capacity.json`：初始容量 0，加 11 个元素后容量变为 15（10 满后 10→15），`get(5)` 是 O(1) 随机访问。

## 三、实现机制：LinkedList 为什么「随机访问慢」

`LinkedList` 的 `get(int index)` 实现是：判断 index 在前半还是后半，再从 `first` 或 `last` 沿 `next`/`prev` 指针逐个走 index 步——**O(n)**。更致命的是缓存：`ArrayList` 的连续数组一次预取能装进多级缓存；链表节点在堆上零散分配，每次解引用都可能 cache miss，实测中即便同是 O(n) 遍历，链表也比数组慢几十倍（见 `examples/ex02-list-traversal-perf.json`：10 万次下标访问，LinkedList 比 ArrayList 慢数千倍）。

## 四、工程实践：怎么选

| 场景 | 选 |
|---|---|
| 读多写少、随机访问、尾部追加 | **ArrayList** |
| 频繁在已知节点处插入/删除（如实现队列/栈的中间操作） | 可考虑 LinkedList |
| 频繁在列表中间按下标插入/删除 | 两者都 O(n)；数据量大时用 `LinkedList`，但多数业务场景 ArrayList 更优（缓存友好） |

> 现代经验法则：**默认用 `ArrayList`**。只有确实需要「头尾 O(1) 增删且几乎不随机访问」时才用 `LinkedList`。`Stack` 已被 `ArrayDeque` 取代（见 concept 05）。

## 五、边界与陷阱

1. `ArrayList` 的 `subList(a,b)` 返回的是**原列表的视图**，对子列表的修改会反映到原列表，且原列表结构性修改会使子列表失效（抛 CME）。
2. `LinkedList` 实现了 `Deque`，优先用 `addFirst/removeLast` 等双端操作，而非 `get(i)`。
3. 用 `List.of(...)` 得到的是**不可变**列表，调用 `add` 抛 `UnsupportedOperationException`。

## 六、可运行代码

- `examples/ex01-arraylist-capacity.json`：复刻 JDK 的扩容公式（`old + (old>>1)`），观察 11 次 `add` 后容量从 0 → 10 → 15。（JDK 9+ 模块化后无法再反射读取 `java.util` 的内部字段 `elementData`，故示例改为等价复刻实现。）
- `examples/ex02-list-traversal-perf.json`：下标遍历 vs 迭代器遍历，量化 LinkedList 的缓存劣势。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **默认用 `ArrayList`**：随机访问 O(1)、缓存友好。能预估规模就 `new ArrayList<>(capacity)`，避免反复扩容。
- `LinkedList` 的 O(1) 插入**前提是已持有节点引用**；若要先 `get(i)` 定位，那一步就是 O(n)，实际常比 `ArrayList` 慢。
- 频繁在两端增删（队列/栈语义）用 `ArrayDeque`，而不是 `LinkedList` 或遗留的 `Stack`。

### 🎓 博士生视角
- `ArrayList` 扩容策略是 **1.5 倍**（`oldCapacity + (oldCapacity >> 1)`）：比倍增省内存（更容易复用先前释放的块），但扩容更频繁。这是内存碎片与搬移成本的实证折中。
- `LinkedList` 是双向链表且实现了 `Deque`，因此两端操作 O(1)；但它每元素多两个引用（prev/next），内存密度低、缓存不友好——这就是**理论上 O(1) 却实测更慢**的原因。
- 与 408 顺序表/链表的分析完全对应：中间插入的搬移次数、随机访问的地址计算，两边是同一套结论。

### 📚 考研者视角
- **408 直接对应**：顺序表与链表的存储结构、插入删除的**平均移动次数**（插入 n/2、删除 (n−1)/2）、时间复杂度对照表。
- 常考算法题：就地逆置、快慢指针找中点/判环等，在 Java 中用 `ArrayList`/`LinkedList` 实现时注意索引与迭代器的差异。
- 记忆锚点：**`ArrayList` 扩容 1.5 倍**；**`LinkedList` 要先定位，定位本身是 O(n)**。
