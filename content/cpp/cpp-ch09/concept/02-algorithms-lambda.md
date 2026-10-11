# 02 · 常用算法与 lambda：sort/find/transform/accumulate 内部机理

## 一、理论根基：泛型算法 = 「对迭代器区间施加的纯函数式操作」

STL 算法的第一性原理是 **「数据结构的操作」与「数据结构本身」正交**：`<algorithm>` 里几乎所有函数都形如 `f(first, last, ...)`，操作的是**半开区间 `[first, last)`**，与容器类型无关。这本质是函数式编程的 `map`/`filter`/`fold` 思想在 C++ 里的零开销落地（见 `examples/ex05`、`ex06`）。

> 设计哲学：**算法不持有数据，只持有一段「可遍历的视图」**。所以 `sort(v.begin(), v.end())` 与 `sort(v.begin(), v.begin()+k)` 用的是同一个函数——区间粒度由调用方决定。

## 二、实现机制：sort 的 introsort（混合排序）

`std::sort` 的复杂度要求是 **O(N log N) 平均、且最坏不能退化成 O(N²)**。libstdc++ / libc++ 均采用 **introsort（introspective sort，Musser 1997）**：

1. 先跑 **快速排序**（三数取中 / 中位元分区），平均 O(N log N)、缓存友好。
2. 递归深度一旦超过 `2·log2(N)`（即快排开始最坏退化），**切换到堆排序 `std::make_heap` + `sort_heap`**，把最坏复杂度锁在 O(N log N)。
3. 子区间小到某个阈值（约 16）时，**改用插入排序**（小数据上常数极小、分支少）。

因此：**`std::sort` 不仅快，而且「保证」不被刻意构造的恶意输入打穿**——这是它相对「裸快排」的工程优势。

### 严格弱序（Strict Weak Ordering）—— sort 的硬约束

比较器 `comp(a,b)` 必须满足**严格弱序**，等价于「小于」应有的四条性质：
- **非自反**：`comp(a,a) == false`
- **非对称**：若 `comp(a,b)` 则 `!comp(b,a)`
- **传递**：`comp(a,b) && comp(b,c) ⇒ comp(a,c)`
- **不可比传递（等价类）**：`!comp(a,b) && !comp(b,a)` 且 `!comp(b,c) && !comp(c,b)` ⇒ `!comp(a,c) && !comp(c,a)`

> **为什么写错比较器是 UB？** `sort` 内部会拿比较器做「相等」判定（两块「不可比」就视为相等、可交换）。若比较器不对称（如 `>=`），两个「应相等」的元素会被反复交换，算法会在分区时**越过区间边界读写**，结果是未定义行为——往往表现为崩溃、死循环或数据错乱，且**编译器不会报错**。常见错误：`comp = [](a,b){ return a <= b; }`（用了 `<=` 而非 `<`）。

## 三、工程实践：lambda 配合算法

- **无捕获 lambda 可隐式转换为函数指针**，因此 `std::sort(v.begin(), v.end(), [](int a,int b){ return a > b; })` 这种无捕获写法零开销；而有捕获的 lambda 是带状态的闭包对象（不可转函数指针，但内联友好）。
- **`transform` 的目标区间容量必须足够**（`examples/ex05` 用 `b(a.size())` 预分配），否则写到未分配空间是 UB。
- **`accumulate`（在 `<numeric>`）是通用 fold**：初值类型决定结果类型——用 `0` 得 `int`，用 `0.0` 得 `double`，用 `std::string("")` 可拼接。
- 能用算法就别手写 `for`：**可读性更高、且天然避免越界/边界 bug**。

### 与 Python / Java 的对比

| 操作 | C++ | Python | Java Stream |
|---|---|---|---|
| 映射 | `std::transform` | `map(f, xs)` | `xs.stream().map(f)` |
| 过滤 | `std::copy_if` | `[x for x in xs if p]` | `xs.stream().filter(p)` |
| 归约 | `std::accumulate` | `functools.reduce` / `sum` | `xs.stream().reduce` |
| 惰性强弱 | **ranges 惰性**（ch03） | 生成器惰性 | Stream 惰性 |

> 关键区别：C++ 的传统算法（`transform`/`copy_if`）**默认立即执行、写回容器**；只有 C++20 ranges 才提供真正的**惰性管道**（见 `examples/ex08`、`concept/03`）。

## 四、边界与陷阱

- `find` 找不到返回 `end()`，**必须判 `!= end()` 再解引用**，否则 UB（见 `examples/ex03`）。
- `sort` 对**自定义类型**必须提供比较器或重载 `operator<`；比较器违反严格弱序 ⇒ UB。
- `partition` 不保证稳定性；要保证「相等元素相对顺序不变」用 `stable_partition` / `stable_sort`。

## 五、可运行示例

见 `examples/ex01`（sort）、`ex02`（stable_sort）、`ex03`（find）、`ex04`（count）、`ex05`（transform）、`ex06`（accumulate）、`ex07`（stable_partition）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **比较器必须严格弱序**：`return a >= b` 这类「非严格」写法会触发 UB（可能崩溃在 `sort` 内部）；正确写法是 `return a < b` 或用 `std::greater<>()`。
- lambda 捕获要明确：`[&]` 谨慎用于异步/回调（悬垂引用），`[=]` 在成员函数里不会捕获 `this` 的成员（C++20 起 `[=, this]` 明确）。
- `accumulate` 的类型是**初值类型**：`accumulate(v.begin(), v.end(), 0)` 对 `double` 会截断，要写 `0.0`。

### 🎓 博士生视角
- `std::sort` 实际是 **introsort**（快排 + 堆排 + 插入排序）：递归深度超限转堆排保证 O(N log N) 最坏，小区间用插入排序降低常数——这是「平均快 + 最坏可控」的工程典范。
- **无捕获 lambda 可隐式转换为函数指针**，因此能作为 C 回调；有捕获的则不行（需要闭包对象）。这是「零开销抽象」的一个具体体现。
- `stable_sort` 用归并，代价是 O(N) 额外空间；**稳定性**是「相等元素的相对顺序保持」，在按多关键字排序时是必需的（先按次关键字排，再按主关键字稳定排）。

### 📚 考研者视角
- 408 排序专题：**快排（平均 O(n log n)、最坏 O(n²)、不稳定）、归并（稳定、需 O(n) 辅助空间）、堆排（不稳定、空间 O(1)）**——对比表必背。
- 会算：给定序列走一遍快排/归并的每趟结果；比较次数与移动次数。
- 记忆锚点：**快排最坏 O(n²) 出现在「已有序 + 取首元素为枢轴」**；稳定性是「相等元素相对次序不变」。

---
