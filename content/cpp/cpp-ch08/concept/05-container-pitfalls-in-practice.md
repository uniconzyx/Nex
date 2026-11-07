# cpp-ch08 · STL 容器实战选择：凯喵带你踩过的坑

> §1–§4 把每个容器讲透了，这一节用「真实场景」把选择标准钉死。凯喵在面试和工程里反复栽过的点，都在这。

### 真实场景：vector 扩容带来的隐性拷贝

凯喵写了 `vector<int> v; for(...) v.push_back(x);` 塞了十万个数，性能惨不忍睹。原因：capacity 不够时 vector 翻倍扩容、**整体搬迁**到新内存，平均每次 push 是 O(1) 摊还，但单次可能拷几千个元素。

```cpp
vector<int> v;
v.reserve(100000);           // 一次性预留，杜绝中途搬迁
for (int i = 0; i < 100000; ++i) v.push_back(i);
```

### 迭代器失效的三种现场

vector 插入/删除会让**指向其后**的迭代器、引用、指针全部失效（元素搬迁）；list 只有被删节点的迭代器失效；unordered 容器 rehash 时全体迭代器失效。凯喵曾在 `for` 循环里 `erase(it++)` 却在 vector 上用，直接 UB。

```cpp
// vector 正确删法：erase 返回下一个有效迭代器
for (auto it = v.begin(); it != v.end(); ) {
    if (*it % 2 == 0) it = v.erase(it);
    else ++it;
}
```

### emplace_back 省掉的这一次拷贝

`push_back(T(...))` 先构造临时对象再移动；`emplace_back(args...)` 直接在容器内存里**就地构造**，少一次移动/拷贝，对重对象收益明显。

```cpp
struct Big { string name; vector<int> data; };
v.push_back(Big{"a", {1,2,3}});   // 构造临时 + 移动
v.emplace_back("a", vector<int>{1,2,3});  // 原地构造，更省
```

### list 真的是 O(1) 插入吗（缓存视角）

list 中部插入确实是 O(1)，但**节点零散在堆上**，遍历时缓存命中率极低。凯喵做过基准：`vector` 顺序遍历比 `list` 快数倍，哪怕 list 插入更快。结论：除非「频繁中部增删 + 长期持有迭代器」，否则 vector 优先。

### map 还是 unordered_map 怎么选

`map` 是红黑树，key 有序、查找 O(log n)、内存紧凑；`unordered_map` 是哈希表，平均 O(1) 但最坏 O(n)、有哈希开销与重哈希。数据量小或需要有序遍历用 map，海量点查用 unordered_map。

### 用 reserve 消灭扩容抖动

不仅是 vector，unordered 容器用 `reserve(n)` 预分配桶，能避免插入时反复 rehash（rehash 会让所有迭代器失效且耗时）。已知规模就先 reserve。

### 用 shrink_to_fit 归还多余容量

vector 删掉大量元素后 capacity 不变，内存白占。`shrink_to_fit()` 请求归还，但标准只要求「请求」——多数实现会真的缩。

```cpp
v.clear();
v.shrink_to_fit();   // 真正释放多余内存
```

### 自定义 key 时的相等与哈希

unordered 容器用自定义 struct 当 key，必须同时提供**相等比较**和**哈希函数**，否则要么编译不过要么运行时行为错乱。凯喵见过只写哈希不写 `==` 导致查不到的 bug。

```cpp
struct Pt { int x, y; };
bool operator==(const Pt& a, const Pt& b){ return a.x==b.x && a.y==b.y; }
struct PtHash { size_t operator()(const Pt& p) const {
    return hash<int>()(p.x) ^ (hash<int>()(p.y) << 1); } };
unordered_set<Pt, PtHash> s;
```

### 范围遍历里偷偷修改的陷阱

`for (auto x : m)` 拿到的是**拷贝**，改 x 不影响容器；要改元素用 `auto&` 或 `auto& kv`。凯喵曾想「遍历时改 value」，结果改了副本，容器纹丝不动。

### 容器选择决策清单

末尾给一张「闭眼可用」的清单：默认 vector；需要键查且有序 → map；海量点查 → unordered_map；频繁两端增删 → deque；需要集合语义 → set/unordered_set；队列/栈 → queue/stack。先把访问模式算清楚，再选容器。

## 三视角解析
### 🧑‍💻 程序员视角
`vector` 扩容时把元素搬到新内存，所有旧迭代器、指针、引用立即失效——循环里 `push_back` 后再用之前的迭代器，是典型的 use-after-free。`emplace_back` 省掉的是「临时对象 + 移动」中的临时对象构造，直接在容器内存上原地构造；但若传的是已存在的对象，它照样要拷贝。`list` 的「O(1) 插入」也有前提：你已经持有插入位置的迭代器，而找这个位置本身是 O(n)，加上每个结点独立分配导致的缓存缺失，遍历性能远不如 `vector`——**默认该用 `vector`，除非有明确理由**。

### 🎓 博士生视角
容器的选择本质是「访问模式 × 内存布局」的匹配：`vector` 连续存储、随机访问 O(1)、插入删除 O(n)，缓存友好；`deque` 分段连续，两端 O(1)；`list`/`forward_list` 结点式，任意位置插入 O(1) 但遍历慢。`unordered_map` 的桶数组在负载因子超阈值时 rehash，所有迭代器失效，但引用与指针保持有效（结点不搬）。这些失效规则不是实现细节，而是标准的规定，写库代码时必须按规则假设最坏情况。

### 📚 考研者视角
面试高频：
1. **迭代器失效规则**：`vector` 扩容全失效、`deque` 中间插入全失效、`map`/`set` 只失效被删元素、`unordered_*` rehash 全失效。
2. **`reserve` 与 `resize`**：前者只改容量，后者改元素个数。
3. **`map` 与 `unordered_map` 的取舍**：前者有序 O(log n)、后者平均 O(1) 但最坏 O(n)、内存开销更大。
4. **`vector<bool>` 的坑**：它是特化版本，`operator[]` 返回代理对象而非 `bool&`，不能取地址。

```text
05-container-pitfalls-in-practice.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 真实场景：vector 扩容带来的隐性拷贝  (cpp)
    |
    v
  [02] 迭代器失效的三种现场  (cpp)
    |
    v
  [03] emplace_back 省掉的这一次拷贝  (cpp)
    |
    v
  [04] map 还是 unordered_map 怎么选  (-)
    |
    v
  [05] 用 reserve 消灭扩容抖动  (-)
    |
    v
  [06] 用 shrink_to_fit 归还多余容量  (cpp)
    |
    v
  [07] 自定义 key 时的相等与哈希  (cpp)
    |
    v
  [08] 范围遍历里偷偷修改的陷阱  (-)
    |
    v
  [... 其余 1 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
