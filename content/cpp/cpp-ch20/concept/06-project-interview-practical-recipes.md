# 综合项目与面试冲刺实战手记：凯喵带人做完 mini-STL 后总结的十二个现场

> 这是 C++ 学习线的收官章。前面把语法、OOP、STL、模板、并发都过了一遍，这一章要把零散能力**收口成可交付的工程**：自己造一遍容器、写一个并发项目、按规范组织代码、并在面试里把这些讲清楚。这篇手记用十二个现场记录"从会写到能交付"的差距。

## 开场：会写代码和能交付代码之间的三道坎

凯喵带过不少人做 mini-STL，发现卡点非常一致，都是三道：

**第一道 · 正确性坎**——不考虑异常安全、不考虑自引用、不考虑迭代器失效，测试用简单类型全过，换成 `std::string` 就崩。

**第二道 · 工程坎**——单文件能跑，拆成多文件就链接错误；不会写 CMake、不会配 sanitizer、不知道怎么测。

**第三道 · 表达坎**——自己做的东西讲不清设计取舍，面试官一问"为什么这么写"就答"书上这么写的"。

下面十二个现场就是这三道坎的具体形态。

### 现场一：手写 vector 的 `push_back` 没有异常安全

```cpp
template <typename T>
void Vector<T>::push_back(const T& v) {
    if (size_ == cap_) {
        T* p = allocator_.allocate(cap_ ? cap_ * 2 : 1);
        for (size_t i = 0; i < size_; ++i) p[i] = std::move(data_[i]);  // ← 可能抛异常
        allocator_.deallocate(data_, cap_);
        data_ = p;
        cap_ = cap_ ? cap_ * 2 : 1;
    }
    new (data_ + size_) T(v);      // ← 这一步抛异常，容器状态已破坏
    ++size_;
}
```

两处问题：移动过程中抛异常会留下"部分移动"的源容器；构造新元素失败时 `size_` 没增加但内存已分配。

**基本异常安全保证**的写法是「先完成所有可能抛异常的操作，再做不抛的指针交换」：

```cpp
template <typename T>
void Vector<T>::push_back(const T& v) {
    if (size_ == cap_) {
        size_t new_cap = cap_ ? cap_ * 2 : 1;
        T* p = allocator_.allocate(new_cap);
        size_t built = 0;
        try {
            for (; built < size_; ++built)
                new (p + built) T(std::move_if_noexcept(data_[built]));
        } catch (...) {
            for (size_t i = 0; i < built; ++i) p[i].~T();
            allocator_.deallocate(p, new_cap);
            throw;
        }
        for (size_t i = 0; i < size_; ++i) data_[i].~T();
        allocator_.deallocate(data_, cap_);
        data_ = p;
        cap_ = new_cap;
    }
    new (data_ + size_) T(v);
    ++size_;
}
```

关键三点：`move_if_noexcept`（移动可能抛时退回拷贝，保证源对象不被破坏）、失败时逐个析构已构造的对象、成功后统一替换。

### 现场二：`emplace_back` 用了完美转发，但仍多一次构造

```cpp
// 常见错误：忘了 std::forward，右值退化成左值 → 调拷贝构造
template <typename... Args>
void emplace_back(Args&&... args) {
    new (data_ + size_) T(args...);            // ❌
}

// 正确：两层都要 forward
template <typename... Args>
void emplace_back(Args&&... args) {
    new (data_ + size_) T(std::forward<Args>(args)...);   // ✅
}
```

`Args&&` 是万能引用，但**一旦具名就是左值**。这条规则在模板里被违反的频率极高，症状是"性能静默变差"——编译器不报错，只是悄悄调了拷贝。

验证手段：给类型加计数器的拷贝/移动构造，用 `emplace_back` 传临时对象，看移动次数。

### 现场三：迭代器失效规则记混，扩容后还用旧指针

```cpp
std::vector<int> v{1, 2, 3};
auto it = v.begin();
v.push_back(4);          // 可能扩容 → it 失效
*it = 9;                 // UB，可能崩溃也可能"看起来没事"
```

各容器的失效规则必须记准：

```text
vector    扩容时全部失效；不扩容时插入点之后失效
deque     两端插入只失效迭代器不失效引用；中间插入全部失效
list/map  只有被删除元素的迭代器失效，其余不受影响
unordered 插入可能 rehash → 全部迭代器失效
```

凯喵的实用规则：**任何可能改变大小的操作之后，不要复用之前保存的迭代器/指针/引用**。需要稳定引用就用 `list`/`map`，或在操作前 `reserve`。

### 现场四：循环里 `erase` 之后 `++it`

```cpp
for (auto it = v.begin(); it != v.end(); ++it) {
    if (*it % 2 == 0) v.erase(it);      // ❌ erase 后 it 已失效
}

// ✅ 用返回值续接
for (auto it = v.begin(); it != v.end(); ) {
    it = (*it % 2 == 0) ? v.erase(it) : it + 1;
}

// ✅ C++20 直接用
std::erase_if(v, [](int x) { return x % 2 == 0; });
```

这个坑在 `map`/`set` 上更隐蔽：`m.erase(it++)` 是"先传旧值再自增"的经典写法，能工作但可读性差，现代代码直接用 `it = m.erase(it)`。

### 现场五：自己写的智能指针 `shared_ptr` 有两份控制块

```cpp
// 错误：用同一个裸指针构造两次
Foo* raw = new Foo();
std::shared_ptr<Foo> a(raw);
std::shared_ptr<Foo> b(raw);      // ❌ 两个独立控制块，析构两次 → double free
```

正确做法：要么一次构造再拷贝，要么用 `enable_shared_from_this`：

```cpp
std::shared_ptr<Foo> a = std::make_shared<Foo>();
std::shared_ptr<Foo> b = a;                       // ✅ 共享同一控制块

// 类内部需要返回 shared_ptr 时
class Foo : public std::enable_shared_from_this<Foo> {
public:
    std::shared_ptr<Foo> self() { return shared_from_this(); }
};
```

这条坑我在 mini-STL 项目里见到过三次，每次都是"看起来能跑，特定路径下 double free"。`make_shared` 还能把对象和控制块一次分配，少一次内存分配、缓存更友好。

### 现场六：循环引用导致内存泄漏，`weak_ptr` 忘了用

```cpp
struct Node {
    std::shared_ptr<Node> next;
    std::shared_ptr<Node> prev;      // ❌ 双向链表用两个 shared_ptr → 引用计数永不归零
};
```

`a.next = b; b.prev = a;` 之后，`a` 和 `b` 的引用计数都是 2，出作用域各减 1 变成 1，永远不释放。

修法：**环里至少有一端用 `weak_ptr`**：

```cpp
struct Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;        // ✅
};
```

判断标准很简单：**画一下所有权图，只要有环就必须打断**。父子关系用 `shared_ptr` 向下、`weak_ptr` 向上；观察者用 `weak_ptr`；缓存用 `weak_ptr`（让对象能被回收）。

### 现场七：CMake 只会 `add_executable`，多模块就崩

单文件项目 `g++ main.cpp` 够了，一拆模块就需要真正的构建系统：

```cmake
cmake_minimum_required(VERSION 3.20)
project(mini_stl CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)        # 生成 compile_commands.json，clangd 要用

add_library(mini_stl INTERFACE)
target_include_directories(mini_stl INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(tests tests/main.cpp)
target_link_libraries(tests PRIVATE mini_stl)

# sanitizer 作为可选项，方便本地排查
option(ENABLE_ASAN "build with address sanitizer" OFF)
if (ENABLE_ASAN)
    target_compile_options(tests PRIVATE -fsanitize=address,undefined -g)
    target_link_options(tests PRIVATE -fsanitize=address,undefined)
endif()
```

三个要点：**头文件库用 INTERFACE**（不产生编译单元）；**导出 compile_commands.json**（编辑器体验的关键）；**sanitizer 做成选项**（默认关，排查时开）。

### 现场八：从不跑 sanitizer，UB 全靠运气

C++ 的未定义行为有个特点：**在开发机上"看起来正常"**。指针越界可能读到相邻内存的旧值，正好是对的；未初始化变量可能恰好是 0。

必开的三个工具：

```bash
# AddressSanitizer：越界、double free、use-after-free、内存泄漏
g++ -fsanitize=address -g main.cpp -o app && ./app

# UndefinedBehaviorSanitizer：整数溢出、空指针解引用、类型双关
g++ -fsanitize=undefined -g main.cpp -o app && ./app

# ThreadSanitizer：数据竞争（并发项目必开）
g++ -fsanitize=thread -g main.cpp -o app -pthread && ./app
```

凯喵的习惯是**每个新项目第一天就把这三个开关接进 CMake**，因为等到出问题时再加，往往已经积累了几十个 UB，一次跑出几百条告警，根本改不动。

### 现场九：并发项目只用 `mutex`，不知道 `atomic` 和内存序

保护一个计数器用 `mutex` 能跑，但性能比 `atomic` 差一个数量级。更关键的是**不知道什么时候能不用锁**。

```cpp
// 只保护单个变量的读写 → atomic 够
std::atomic<long> counter{0};
counter.fetch_add(1, std::memory_order_relaxed);   // 纯计数不需要同步语义

// 保护「多个变量的一致性」→ 必须用锁
struct Snapshot { long a, b; };
std::mutex m;
Snapshot read() {
    std::lock_guard<std::mutex> lk(m);
    return {a_, b_};        // a_ 和 b_ 必须是同一时刻的值
}
```

判断标准：**「一个变量」用 atomic，「一组变量的不变量」用锁**。`memory_order_relaxed` 只保证原子性、不保证顺序，纯计数场景够用；需要"写完 A 别人能看见 B"时才用 `release`/`acquire`。

### 现场十：不知道代码规范从哪来，风格全靠个人喜好

面试官看作品时会在意"这份代码像不像团队协作的产物"。最低标准：

```text
命名     类型 CamelCase / 函数 camelCase 或 snake_case（选一种，全程一致）
常量     k 前缀或全大写，选一种
成员     trailing underscore（size_）或 m_ 前缀
头文件   #pragma once 或 include guard，选一种
包含顺序 对应头文件 → 标准库 → 第三方 → 本项目（每组空行分隔）
```

比风格更重要的是**两条硬规则**：

```text
1. 所有头文件必须自包含（单独 include 就能编译，不依赖包含顺序）
2. 所有 .cpp 第一行包含自己的头文件（保证声明与定义一致）
```

第二条能在编译期抓到大量签名不一致的问题，成本几乎为零。

### 现场十一：面试讲项目只会讲"我实现了什么"

被问"介绍一下你的 mini-STL"，回答"我实现了 vector、list、map、智能指针"，然后就没话了。面试官想听的完全不是这个。

有效的讲法是**按"问题 → 取舍 → 验证"三段**：

```text
问题：为什么值得自己写一遍？
  vector 的扩容策略直接决定 push_back 的摊还复杂度；
  我想搞清楚「为什么是 1.5 倍或 2 倍」「异常安全保证怎么落地」。

取舍：做过的三个决定
  1. 扩容用 2 倍：空间换摊还 O(1)；如果内存紧张会选 1.5 倍（更省但拷贝次数多）
  2. push_back 用 move_if_noexcept：移动可能抛时退回拷贝，保基本异常安全
  3. 迭代器用裸指针：vector 连续存储，裸指针天然满足随机访问迭代器要求，
     不需要额外封装（对比 list 必须自定义节点迭代器）

验证：怎么知道它是对的
  写了 200+ 单元测试；用 ASan/UBSan 跑零告警；
  用一个「拷贝/移动计数器」类型验证 emplace_back 只移动一次；
  和 std::vector 对比 10^7 次 push_back 的耗时差异。
```

三段里"取舍"和"验证"是加分项，因为它们展示的是**判断力**，而不是记忆力。

### 现场十二：系统设计题上来就画架构图，不先问约束

"设计一个线程池"——很多人立刻开始画：任务队列、工作线程、条件变量。

但面试官真正想看的是你先问约束：

```text
1. 任务是 CPU 密集还是 IO 密集？（决定线程数策略）
2. 队列要有界还是无界？（有界要处理拒绝策略）
3. 需要支持优先级/延迟任务吗？（决定队列结构）
4. 关闭时要等任务跑完还是立刻中断？
5. 需要动态调整线程数吗？（决定是否有管理线程）
```

问完再画，方案会自然收敛。而且这些问题的答案直接决定实现细节：CPU 密集型线程数 ≈ 核数；IO 密集型要大得多；有界队列必须定义满时行为（阻塞 / 拒绝 / 丢弃最旧）；优雅关闭需要 `stop` 标志 + 通知所有线程 + `join`。

凯喵的经验：**面试里的系统设计，70% 的分数在提问阶段**。因为真实工程里，需求不清就开工才是最贵的错误。

## 三视角解析
### 🧑‍💻 程序员视角
手写 `vector` 的 `push_back` 最容易漏掉「扩容后旧元素要移动而非拷贝」以及「异常安全」——新内存分配成功后，移动构造若抛异常，旧数据必须仍然可用。迭代器失效规则在 mini-STL 里必须写进文档：`push_back` 可能导致全部失效，`erase` 只失效被删位置之后的。面试时被问「你这个 vector 和标准库差在哪」，能答出「异常安全、`emplace` 的完美转发、`reserve` 的倍增策略」就足够有说服力。

### 🎓 博士生视角
手写容器是理解「抽象代价」的最好方式：`vector` 的三指针模型（begin/end/cap）把「大小与容量」的区分编码进指针差，`push_back` 的均摊 O(1) 靠倍增扩容保证。异常安全在这里不是锦上添花——`push_back` 的强保证要求「先在新内存构造成功，再交换指针」，否则扩容中途失败会丢失数据。面试官真正想听的是「你知道标准库为什么这么设计」，而不是「你能背出 API」。

### 📚 考研者视角
面试冲刺要点：
1. **手写 vector**：三指针 + 倍增扩容 + `push_back` 的异常安全，是最高频的手写题。
2. **手写 string**：SSO、拷贝交换（copy-and-swap）实现强异常安全。
3. **手写 shared_ptr**：控制块 + 原子计数 + 删除器。
4. **常见追问**：「为什么 `reserve` 要倍增而不是 +1」「`shrink_to_fit` 为什么不一定生效」。

## 收尾：凯喵的收口三清单

从"会写"到"能交付"，做三件事就够：

**正确性清单**——异常安全（基本/强保证）、迭代器失效规则、`shared_ptr` 控制块唯一、不要有循环引用、跑 ASan/UBSan/TSan 零告警。

**工程清单**——多文件 + CMake + 头文件自包含 + `compile_commands.json` + 单元测试 + 一个可复现的构建脚本。

**表达清单**——每个技术决定能说出"为什么这么选、不选另一个的理由"；每个结论能给出"怎么验证的"；每个设计能先说清约束再画方案。

最后说一句总结性的话。C++ 这门语言学到最后，你会发现真正的门槛不在语法——语法一年就能学完——而在**对"资源与不变量"的敏感度**：这段代码在异常时会不会泄漏、这个指针在扩容后还有效吗、这个锁保护的不变量是什么、这个移动之后源对象还能用吗。

这种敏感度没法靠背规则获得，只能靠**亲手实现一遍**：写过一次带异常安全的 `push_back`，你以后看任何容器的文档都会自动去找"异常安全保证"那一栏；写过一次循环引用的泄漏，你以后看到 `shared_ptr` 就会先画所有权图。这也是为什么这一章把"自己造 STL"放在收官位置——它不是为了炫技，而是为了让你在**别人的代码出错之前，先在自己的代码里把所有坑踩一遍**。

### 补充：作品集不是"代码堆"，而是三个可复述的故事

最后补一条关于作品集的经验。很多人把 GitHub 上的 repos 当成作品集，链接一放就完了。但面试官不会去翻你的 commit 历史，他只会问"讲讲你做的项目"。

真正有效的作品集是**三个可复述的故事**，每个都能在九十秒内讲完，且都包含上面说的"问题 → 取舍 → 验证"三段结构：

```text
故事一（深度）：mini-STL 里的异常安全
  这是最能体现 C++ 功底的一个，因为它逼你面对「分配失败怎么办」这种真实问题

故事二（广度）：并发任务池
  体现你能把锁、条件变量、原子量组合成一个可用的东西，而不是只会背概念

故事三（工程）：一次线上问题的完整排查
  从现象、到定位工具（gdb / perf / sanitizer）、到根因、到修复与回归验证
  这个故事的价值在于证明你「能独立负责一件事」
```

三个故事要覆盖三种能力：**底层功底、系统设计、问题定位**。它们比十个 CRUD 项目更能说明水平，因为面试官需要判断的不是"你会不会写代码"——那是笔试的事——而是"遇到没见过的难题时你能不能啃下来"。

凯喵还建议给每个项目写一份 README，只写三件事：这个项目解决了什么问题、有哪些关键设计决策、怎么验证它是对的。这份 README 在面试前重读一遍，比临时回忆有效得多，因为它把"当时为什么这么想"保留了下来——而那恰恰是面试官最想听的部分。
