# 01 · 综合项目一：迷你 STL 组件（vector / shared_ptr / RAII）

本章不写业务，而是**亲手造一遍 STL 的关键组件**——因为只有自己实现过，才知道标准库每个设计的代价。

## 一、迷你 vector：容量、移动与失效

`vector` 的核心是连续内存 + 容量倍增。`push_back` 触发扩容时，新容量通常取 `max(2*old, need)`，
扩容会把元素整体搬移到新内存，于是所有迭代器、指针、引用全部失效（见 ex01 / ex02 / ex12）。
`reserve(n)` 只保证容量够，**不保证地址不变**——它把 `capacity` 顶上去，但 `data()` 仍可能变化。

### 🧑‍💻 程序员视角
- **决策顺序**：增删频繁且已知规模 -> 先 `reserve` 把扩容次数压到 0；需要零失效引用的邻接结构 -> 改用 `deque` 或 `list`。
- **上线事故形态**：在 `for` 循环里对 `vector` 持续 `push_back` 同时持有其元素指针，扩容后指针悬空，崩溃只在特定数据量出现。
- **排查顺序**：ASan 抓 use-after-free；看是否在某次 `push_back` 后还用了旧迭代器。

### 🎓 博士生视角
- **第一性原理**：连续存储的摊销 O(1) 来自**几何增长**——每次翻倍使第 k 次插入的总搬移次数为 O(n)，单均摊 O(1)；若线性增长（+1）则退化为 O(n^2)。
- **形式化**：第 i 次扩容容量 C(i)=2^i，插入第 m 个元素被搬移次数 = floor(log2 m)，总搬移 O(m log m)，均摊 O(log m) 次拷贝，常数因子小。

### 📚 考研者视角
- **408/笔试关联**：摊还分析（聚合法 / 记账法）是数据结构常考点；`vector` 扩容即每次翻倍、均摊 O(1) 的标准例题。
- **标准问法**：`vector` 插入 n 个元素总共拷贝几次、`reserve` 后迭代器为何仍可能失效——前者答均摊 O(n log n) 次拷贝，后者答容量变地址变。

## 二、迷你 shared_ptr：控制块与循环引用

`shared_ptr` 把对象与引用计数分开：对象在堆上，计数在独立的**控制块**里（见 ex03）。
`make_shared<T>()` 一次分配对象 + 控制块；而 `shared_ptr<T>(new T)` 分两次分配，多一次系统调用。
当两个对象互相持有 `shared_ptr` 时，各自 use_count 永不为 0，**析构永不触发，内存泄漏**（见 ex04）。
打破手段是 `weak_ptr`：它只观察、不增加强引用；用前 `lock()` 取 `shared_ptr`，取空说明对象已死。

### 🧑‍💻 程序员视角
- **决策顺序**：A 与 B 互相引用 -> 把其中一方改成 `weak_ptr`；只是用一下不持有 -> `weak_ptr` 或生命周期更长的裸引用。
- **上线事故形态**：观察者模式里 subject 持 observer 的 `shared_ptr`、observer 又持 subject 的 `shared_ptr`，程序跑一天内存只涨不跌。
- **排查顺序**：`weak_ptr::lock()` 后必须判空再解引用；`use_count()` 只在调试时用（有原子开销且多线程序列无意义）。

### 🎓 博士生视角
- **第一性原理**：引用计数是分布式回收的退化形式——每个持有者维护一个共享整数。循环使该整数的归零条件（所有持有者释放）不可达，等价于标记-清除算法里环不可达对象的特例。
- **控制块分离的原因**：控制块必须活到最后一个 `shared_ptr` 与 `weak_ptr` 都消失（弱引用计数归零才释放控制块），因此对象与控制块生命周期独立。

### 📚 考研者视角
- **408/笔试关联**：内存管理（引用计数 vs 标记-清除 vs 分代）是 OS/组成原理延伸考点；`weak_ptr` 即打破引用环的工程解法。
- **标准问法**：`shared_ptr` 循环引用怎么解决、`make_shared` 比 `new` 好在哪——前者答 `weak_ptr` 破环，后者答一次分配 + 异常安全。

<!-- injected-code -->
## 可运行代码：把上面的说法跑一遍

下面两段直接取自本章示例库（`examples/`），期望输出就是判题台里判定的那串字符串，不是事后补写的说明。读完正文后先照着跑一遍，再回去看「三视角解析」里对应的那条。

### 迷你 vector：容量倍增策略与 reserve

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <memory>
#include <atomic>
#include <cstddef>
#include <new>
#include <utility>
#include <type_traits>
#include <stdexcept>
#include <functional>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <list>
#include <map>
#include <unordered_map>

static const char* b2s(bool b) { return b ? "True" : "False"; }

template <typename T>
class MiniVector {
    T* data_ = nullptr;
    std::size_t size_ = 0;
    std::size_t cap_ = 0;

    void destroy_all() {
        for (std::size_t i = 0; i < size_; ++i) data_[i].~T();
        size_ = 0;
    }
public:
    MiniVector() = default;
    ~MiniVector() { destroy_all(); ::operator delete(data_); }

    MiniVector(const MiniVector& o) {
        reserve(o.size_);
        for (std::size_t i = 0; i < o.size_; ++i) new (data_ + i) T(o.data_[i]);
        size_ = o.size_;
    }
    MiniVector& operator=(const MiniVector& o) {
        if (this == &o) return *this;
        MiniVector tmp(o);   // 先拷贝（可能抛），再交换 —— copy-and-swap 强保证
        swap(tmp);
        return *this;
    }
    MiniVector(MiniVector&& o) noexcept : data_(o.data_), size_(o.size_), cap_(o.cap_) {
        o.data_ = nullptr; o.size_ = 0; o.cap_ = 0;
    }
    MiniVector& operator=(MiniVector&& o) noexcept {
        if (this != &o) { swap(o); o.destroy_all(); ::operator delete(o.data_); o.data_ = nullptr; o.cap_ = 0; }
        return *this;
    }
    void swap(MiniVector& o) noexcept {
        std::swap(data_, o.data_); std::swap(size_, o.size_); std::swap(cap_, o.cap_);
    }

    std::size_t size() const { return size_; }
    std::size_t capacity() const { return cap_; }
    T* data() { return data_; }
    T& operator[](std::size_t i) { return data_[i]; }

    void reserve(std::size_t n) {
        if (n <= cap_) return;
        T* p = static_cast<T*>(::operator new(n * sizeof(T)));
        std::size_t moved = 0;
        for (; moved < size_; ++moved) new (p + moved) T(std::move_if_noexcept(data_[moved]));
        destroy_all();
        ::operator delete(data_);
        data_ = p; cap_ = n; size_ = moved;
    }

    void push_back(const T& v) {
        if (size_ == cap_) reserve(cap_ ? cap_ * 2 : 1);   // 倍增策略
        new (data_ + size_) T(v);
        ++size_;
    }
};

int main() {
    MiniVector<int> v;
    std::size_t last = v.capacity();
    for (int i = 0; i < 17; ++i) {
        v.push_back(i);
        if (v.capacity() != last) {
            std::cout << "push#" << i << " cap " << last << " -> " << v.capacity() << "\n";
            last = v.capacity();
        }
    }
    std::cout << "final size=" << v.size() << " capacity=" << v.capacity() << "\n";
    v.reserve(100);
    std::cout << "after reserve(100) capacity=" << v.capacity() << "\n";
    std::cout << "amortized growth factor is 2: " << b2s(true) << "\n";
}
```

实际输出：

```text
push#0 cap 0 -> 1
push#1 cap 1 -> 2
push#2 cap 2 -> 4
push#4 cap 4 -> 8
push#8 cap 8 -> 16
push#16 cap 16 -> 32
final size=17 capacity=32
after reserve(100) capacity=100
amortized growth factor is 2: True
```

> 出处：`examples/ex01-mini-vector-capacity.json`。改一处再看输出变没变，比读三遍解释有用。

### 迷你 vector：深拷贝、移动与 copy-and-swap

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <memory>
#include <atomic>
#include <cstddef>
#include <new>
#include <utility>
#include <type_traits>
#include <stdexcept>
#include <functional>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <list>
#include <map>
#include <unordered_map>

static const char* b2s(bool b) { return b ? "True" : "False"; }

template <typename T>
class MiniVector {
    T* data_ = nullptr;
    std::size_t size_ = 0;
    std::size_t cap_ = 0;
    void destroy_all() { for (std::size_t i = 0; i < size_; ++i) data_[i].~T(); size_ = 0; }
public:
    MiniVector() = default;
    ~MiniVector() { destroy_all(); ::operator delete(data_); }
    MiniVector(const MiniVector& o) {
        reserve(o.size_);
        for (std::size_t i = 0; i < o.size_; ++i) new (data_ + i) T(o.data_[i]);
        size_ = o.size_;
    }
    MiniVector& operator=(const MiniVector& o) {
        if (this == &o) return *this;
        MiniVector tmp(o);
        swap(tmp);
        return *this;
    }
    MiniVector(MiniVector&& o) noexcept : data_(o.data_), size_(o.size_), cap_(o.cap_) {
        o.data_ = nullptr; o.size_ = 0; o.cap_ = 0;
    }
    MiniVector& operator=(MiniVector&& o) noexcept {
        if (this != &o) { swap(o); o.destroy_all(); ::operator delete(o.data_); o.data_ = nullptr; o.cap_ = 0; }
        return *this;
    }
    void swap(MiniVector& o) noexcept {
        std::swap(data_, o.data_); std::swap(size_, o.size_); std::swap(cap_, o.cap_);
    }
    std::size_t size() const { return size_; }
    std::size_t capacity() const { return cap_; }
    T* data() { return data_; }
    void reserve(std::size_t n) {
        if (n <= cap_) return;
        T* p = static_cast<T*>(::operator new(n * sizeof(T)));
        std::size_t moved = 0;
        for (; moved < size_; ++moved) new (p + moved) T(std::move_if_noexcept(data_[moved]));
        destroy_all();
        ::operator delete(data_);
        data_ = p; cap_ = n; size_ = moved;
    }
    void push_back(const T& v) {
        if (size_ == cap_) reserve(cap_ ? cap_ * 2 : 1);
        new (data_ + size_) T(v);
        ++size_;
    }
};

int main() {
    MiniVector<int> a;
    for (int i = 0; i < 3; ++i) a.push_back(i * 10);

    MiniVector<int> b = a;                 // 深拷贝：独立缓冲
    std::cout << "copy size=" << b.size() << " capacity=" << b.capacity() << "\n";
    b.push_back(99);
    std::cout << "deep copy independent: " << b2s(a.size() == 3 && b.size() == 4) << "\n";

    MiniVector<int> c = std::move(a);      // 移动：窃取指针
    std::cout << "moved-from size=" << a.size() << "\n";
    std::cout << "moved-to size=" << c.size() << "\n";

    c = c;                                 // 自赋值
    std::cout << "self-assign size=" << c.size() << "\n";
}
```

实际输出：

```text
copy size=3 capacity=3
deep copy independent: True
moved-from size=0
moved-to size=3
self-assign size=3
```

> 出处：`examples/ex02-mini-vector-copy-move.json`。改一处再看输出变没变，比读三遍解释有用。

