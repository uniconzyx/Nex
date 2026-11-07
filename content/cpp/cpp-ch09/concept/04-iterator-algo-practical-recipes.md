# 迭代器与算法实战手记：凯喵的十二次「编译过了，结果就是不对」

> 这一篇来自凯喵给一个日志分析工具做重构的经历。原来是一堆手写循环，重构目标是全部用 STL 算法 + C++20 ranges 表达。重构后代码短了一半，但线上开始出现三类问题：排序结果不稳定导致对账失败、迭代器失效导致随机崩溃、以及某个 ranges 管道跑得比手写循环慢十倍。十二个现场记录下来的结论是：**STL 算法的坑几乎全在「前置条件」和「迭代器范畴」这两件事上**。

## 开场：算法不是函数，是契约

`std::sort` 不检查你的比较器是否是严格弱序，`std::lower_bound` 不检查你的区间是否已排序，`std::copy` 不检查目标区间是否够大。它们全部信任调用者——因为检查的代价太高，而且这些前置条件在编译期无法验证。

所以用 STL 的正确姿势不是「知道有这个算法」，而是**知道它要求什么**。凯喵把这句话总结成一句：算法是契约，不是工具。违反了契约，行为是未定义，可能崩、可能静默出错、可能换个编译器就对。

这篇的十二个现场，几乎全是「违反了某个契约」。

### 现场一：五类迭代器是能力层级，不是分类标签

输入迭代器：只能读一次，单向。输出迭代器：只能写一次，单向。前向迭代器：可多次读，单向。双向迭代器：可前后移动。随机访问迭代器：可 `+n`、可相减、可比较大小。C++20 又加了连续迭代器（内存连续）。

关键点是**层级是包含关系**：随机访问 ⊃ 双向 ⊃ 前向 ⊃ 输入。所以要求前向迭代器的算法，传随机访问迭代器也能用；反过来不行。

```cpp
#include <iterator>
#include <list>
#include <vector>

static_assert(std::is_same_v<
    std::iterator_traits<std::vector<int>::iterator>::iterator_category,
    std::random_access_iterator_tag>);

// list 是双向：支持 ++/--，不支持 it + 3
std::list<int> lst{3, 1, 2};
// auto x = lst.begin() + 1;   // 编译错误
auto y = std::next(lst.begin(), 1);   // 正确：用 std::next
```

凯喵的体会：**这个层级决定了算法复杂度**。`std::sort` 要求随机访问，所以不能用于 `list`（因此 `list` 提供了成员 `sort`）；`std::find` 只要求输入迭代器，所以任何容器都能用。

### 现场二：sort 的比较器必须满足严格弱序

严格弱序（strict weak ordering）要求：非自反（`cmp(a,a)` 为 false）、非对称（`cmp(a,b)` 则 `!cmp(b,a)`）、传递（`cmp(a,b) && cmp(b,c)` 则 `cmp(a,c)`）、以及等价关系的传递性。

最常见的违反是 `<=`：

```cpp
std::vector<int> v{3, 1, 2};
std::sort(v.begin(), v.end(), [](int a, int b) { return a <= b; });  // UB！
```

`a <= a` 为 true，违反非自反。在 libstdc++ 上可能崩（`std::sort` 内部做越界检查时触发），也可能静默产生错误结果。用 `<` 才对。

另一个常见违反是「多字段比较漏了兜底」：

```cpp
// 错误：id 相等时返回 false 是没问题的，但如果写成
// return a.id <= b.id; 就违反了非自反
struct Item { int id; int score; };
std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
    if (a.id != b.id) return a.id < b.id;
    return a.score < b.score;    // 正确：严格的 <
});
```

凯喵的经验是：**手写比较器只允许出现 `<`，永远不要出现 `<=`**。这条规则能挡掉九成的严格弱序问题。

### 现场三：stable_sort 的代价是内存

`std::sort` 不稳定（相等元素的相对顺序可能改变），`std::stable_sort` 稳定。代价是 `stable_sort` 通常需要额外 O(n) 的内存（归并排序思路）。

凯喵的对账失败就是踩了这个：原本按「时间」排序的日志，再用 `sort` 按「级别」排一次，同一级别内的顺序被打乱，导致两次对账的哈希不一致。

```cpp
// 不稳定的多级排序：先按次要键排，再按主要键稳定排序
std::stable_sort(logs.begin(), logs.end(),
                 [](const Log& a, const Log& b) { return a.ts < b.ts; });
std::stable_sort(logs.begin(), logs.end(),
                 [](const Log& a, const Log& b) { return a.level < b.level; });
```

更省事的做法是把两个键写进一个比较器（比较器本身是稳定的语义，不需要 `stable_sort`）。凯喵的建议：**能不依赖稳定性就别依赖**，因为 `sort` 更快且不占额外内存。

### 现场四：lower_bound 的前置条件是「已排序」

`std::lower_bound` 用二分查找，要求区间已按同一比较器排好序。传一个未排序的区间，结果是「某个位置」，不报错，但答案无意义。

```cpp
std::vector<int> v{5, 1, 3};    // 未排序
auto it = std::lower_bound(v.begin(), v.end(), 3);   // 结果无意义
```

而且比较器必须与排序时用的一致。如果排序用 `greater<>` 排成降序，查找时必须也用 `greater<>`：

```cpp
std::sort(v.begin(), v.end(), std::greater<>{});
auto it = std::lower_bound(v.begin(), v.end(), 3, std::greater<>{});
```

凯喵见过最隐蔽的版本是：容器先被 `push_back` 追加了新元素（破坏了有序性），然后继续用 `lower_bound`。这种 bug 只在「追加的元素恰好打乱顺序」时暴露，测试很容易漏掉。

规约：**凡是维护有序容器，追加后必须重新排序，或者改用 `std::set`/`std::map` 自动维护**。

### 现场五：find 与 binary_search 是两种完全不同的东西

`std::find` 是线性扫描，任何迭代器都能用，复杂度 O(n)。`std::binary_search` 是二分，要求随机访问 + 已排序，复杂度 O(log n)。

很多人看到「查找」就想到 `binary_search`，结果在小数据上写了个错误的（未排序）调用，反而不如 `find` 正确。

```cpp
// 数据量小、无序：用 find
auto it = std::find(v.begin(), v.end(), target);

// 数据量大、已排序：用 binary_search / lower_bound
bool found = std::binary_search(sorted.begin(), sorted.end(), target);
```

凯喵的判断标准：**元素数小于几百，直接 `find`**；超过几千且要反复查，才值得维护有序或用哈希容器。过早优化成二分，反而引入「忘了排序」的 bug。

### 现场六：迭代器失效是「静默 UB」的重灾区

容器操作可能让已有迭代器失效。`vector` 在扩容时所有迭代器失效；`erase` 让被删位置及之后的迭代器失效；`deque` 在头尾插入时只失效部分，中间插入全失效；`list`/`map`/`set` 只在删除被删元素时失效该元素的迭代器。

```cpp
std::vector<int> v{1, 2, 3, 4};
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it % 2 == 0) v.erase(it);    // UB：it 已失效，且 ++it 跳过元素
}
```

正确写法是用 `erase` 的返回值：

```cpp
for (auto it = v.begin(); it != v.end(); ) {
    if (*it % 2 == 0) it = v.erase(it);
    else ++it;
}
```

或者用 C++20 的 `std::erase_if`：

```cpp
std::erase_if(v, [](int x) { return x % 2 == 0; });
```

凯喵的规矩：**循环里改容器，一律用 `erase` 返回的新迭代器，或者干脆用 `erase_if`**。

### 现场七：erase-remove 惯用法，不是历史包袱

`std::remove` 不删除元素，它把要保留的元素往前挪，返回新的逻辑结尾。真正的删除要靠 `erase`。这个「两步走」叫 erase-remove 惯用法。

```cpp
std::vector<int> v{1, 2, 3, 2, 4};
v.erase(std::remove(v.begin(), v.end(), 2), v.end());
// v == {1, 3, 4}
```

为什么不能一步完成？因为算法只操作迭代器区间，不知道容器本身，没法调用容器的 `erase`。这是 STL 设计的必然结果——算法与容器解耦。

C++20 之后有 `std::erase`（容器成员版本），一步到位：

```cpp
std::erase(v, 2);    // C++20
```

### 现场八：lambda 的捕获方式决定生命周期

`[=]` 按值捕获，`[&]` 按引用捕获。按引用捕获的变量如果活得比 lambda 短，就是悬垂引用。

```cpp
std::function<void()> make_bad() {
    int x = 42;
    return [&]() { return x; };    // 悬垂：x 已销毁
}

std::function<void()> make_good() {
    int x = 42;
    return [=]() { return x; };    // 安全：按值拷贝
}
```

在算法里这个坑最常出现在异步回调。凯喵见过把 `for` 循环变量按引用捕获进 `std::thread`，线程启动时循环早已结束，`i` 是最终值。

初始化捕获（C++14）可以解决大部分问题：

```cpp
auto fn = [i = i, data = std::move(data)]() { /* 用 i 和 data */ };
```

`std::move` 进 lambda 是移动捕获的标准手法，避免了拷贝大对象。

### 现场九：无捕获 lambda 能转函数指针，这是唯一免费的

无捕获的 lambda 可以隐式转换成函数指针，有捕获的不行（因为需要携带状态）。这个差异在作为 C 接口回调时至关重要。

```cpp
void c_api(void (*cb)(int));

c_api([](int x) { /* 无捕获 */ });        // OK：隐式转换
int k = 0;
// c_api([k](int x) { });                 // 错误：有捕获，不能转
```

凯喵的用法：**给 C 库传回调时优先用无捕获 lambda**，实在需要状态就传一个 `void*` 上下文参数（如果库支持），或者用全局变量（不推荐）。

顺带一提：无捕获 lambda 是零开销的——它就是一个普通函数，没有对象、没有构造、没有间接调用。

### 现场十：accumulate 的初值类型决定整个表达式的类型

`std::accumulate(first, last, init)` 的类型由 `init` 决定，不是由元素类型决定。用 `0` 作为初值累加 `double`，结果会被截断成整数。

```cpp
std::vector<double> v{1.5, 2.5, 3.0};
auto wrong = std::accumulate(v.begin(), v.end(), 0);     // 7（int）
auto right = std::accumulate(v.begin(), v.end(), 0.0);   // 7.0
```

这个坑的隐蔽性在于：结果类型是 `int`，但表达式能编译，只是丢精度。凯喵见过累加金额用 `0` 做初值，跑了半年才被财务发现差了几毛钱。

同一类问题还有：累加 `long long` 用 `0LL`，累加字符串用 `std::string{}`（用 `""` 会退化成 `const char*`，编译失败）。

### 现场十一：ranges 是惰性的，但可能比你想象的更惰性

C++20 ranges 的 `views::filter | views::transform` 是惰性求值：只有迭代时才计算。这意味着**每个元素可能被 filter 和 transform 各算一次**，而且如果 view 被遍历多次，计算会重复。

```cpp
#include <ranges>

auto r = data
    | std::views::filter([](int x) { return x % 2 == 0; })
    | std::views::transform([](int x) { return x * x; });

for (int x : r) { /* 每次迭代都重新执行 filter + transform */ }
for (int x : r) { /* 再来一遍 */ }
```

凯喵的项目里，`transform` 里做了一次字符串解析，结果遍历三次就解析三次，比手写循环慢十倍。修法是先 `to<std::vector>()` 物化（C++23），或者手动存下来。

```cpp
std::vector<int> materialized;
for (int x : r) materialized.push_back(x);
```

结论：**ranges 适合「一次遍历的管道」，不适合「需要多次访问的结果」**。

### 现场十二：ranges 的条件求值次数是有保证的

有个容易被误解的点：`views::filter` 对谓词的调用次数是「每个元素最多一次」，这是标准保证的。但 `transform` 的调用次数取决于下游——如果下游是 `take(3)`，那么只算 3 个。

```cpp
auto r = data
    | std::views::transform(expensive)
    | std::views::take(3);      // 只对前 3 个元素调用 expensive
```

这是 ranges 相对手写循环的真正优势：**它能短路**。手写循环要先全部 transform 再取前 3 个，ranges 在管道层面就避免了。

凯喵的体会：理解「惰性」不是「慢」的同义词，关键是**上游会被下游的需求量约束**。所以把 `take` 放在管道前面能省大量计算。

## 三视角解析
### 🧑‍💻 程序员视角
`sort` 的比较器返回 `a <= b` 会在相等元素上让算法陷入未定义行为——严格弱序要求「相等必须返回 false」。`lower_bound` 在未排序区间上调用不会报错，只会返回一个看似合理的错误位置，这是最难查的一类。`stable_sort` 保证相等元素相对次序，代价是额外内存或更慢的算法；而 `erase-remove` 惯用法漏掉 `erase` 时，容器大小不变、尾部残留「已移走的垃圾值」。

### 🎓 博士生视角
迭代器按能力分五类（输入、前向、双向、随机访问、连续），算法通过迭代器标签在编译期选择最优实现——`std::distance` 对随机访问迭代器是 O(1)、对链表是 O(n)，靠的就是标签分派。严格弱序是排序算法的数学前提：它要求「不可比较」（`a<b` 与 `b<a` 同假）构成等价类，算法才能保证 O(n log n) 与终止性。这也是为什么「用 `<=` 当比较器」会破坏不变量——等价类退化成空集，分区可能永不收敛。

### 📚 考研者视角
面试常考：
1. **五种迭代器类型**：各自支持的操作（`++`、`--`、`+n`、随机访问），以及算法对迭代器的最低要求。
2. **`remove` 为什么不删元素**：它只做「把不删除的元素前移」，返回新逻辑末尾，必须配 `erase`。
3. **`lower_bound` / `upper_bound`**：前者第一个 `>=`，后者第一个 `>`，都要求有序。
4. **`sort` 与 `stable_sort`**：时间 O(n log n) vs O(n log² n)（内存不足时），稳定性差异。

## 收尾：用 STL 的三条纪律

凯喵最后总结：STL 算法用得好不好，取决于三条纪律。

**第一条，先确认前置条件**。排序了吗？比较器一致吗？目标区间够大吗？迭代器范畴满足吗？这四个问题答完再动手。

**第二条，比较器只用 `<`**。任何 `<=`、`>`、`>=` 都是隐患，因为它们违反了严格弱序的非自反要求。

**第三条，改容器就用返回的迭代器**。`erase` 会返回下一个有效位置，`insert` 也可能让迭代器失效。凡是「循环里改容器」，都要重新审视迭代器。

至于 ranges，它的价值在于可组合和可短路，但惰性意味着「看起来一次遍历，实际可能多次计算」。用它写「读一遍就出结果」的管道很舒服，用它做「需要反复访问的数据源」就要小心。

STL 的设计哲学是「零开销抽象」——但这个「零开销」是建立在你遵守契约的前提下的。违反契约不会降低性能，而是让程序进入未定义行为。这大概是 C++ 标准和 Java 集合框架最大的区别：前者信任你，后者保护你。

再补一句关于选型的经验：如果一段代码用 STL 算法写出来比手写循环更长、更难懂，那就该手写循环。算法库的价值在于表达意图清晰，而不是「用上它才算专业」。凯喵见过为了用 `accumulate` 而把简单加法写成三行 lambda 的代码，可读性反而下降。工具服务于表达，不要反过来。

```text
04-iterator-algo-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：五类迭代器是能力层级，不是分类标签  (cpp)
    |
    v
  [02] 现场二：sort 的比较器必须满足严格弱序  (cpp)
    |
    v
  [03] 现场三：stable_sort 的代价是内存  (cpp)
    |
    v
  [04] 现场四：lower_bound 的前置条件是「已排序」  (cpp)
    |
    v
  [05] 现场五：find 与 binary_search 是两种完全不同的东西  (cpp)
    |
    v
  [06] 现场六：迭代器失效是「静默 UB」的重灾区  (cpp)
    |
    v
  [07] 现场七：erase-remove 惯用法，不是历史包袱  (cpp)
    |
    v
  [08] 现场八：lambda 的捕获方式决定生命周期  (cpp)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
