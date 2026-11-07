# §4 cpp-ch10 实战手记：凯喵带你把智能指针用「漏」

> 前三节把 RAII、unique_ptr、shared_ptr、weak_ptr 与循环引用讲透了。这一节凯喵把智能指针最容易「内存泄漏 / 双重释放 / 悬垂 / 循环」的 12 个现场搬出来——每个都是 C++ 内存事故的源头。

### 现场一：裸指针交给两个智能指针，双重释放

凯喵 `int* p = new int; std::shared_ptr<int> a(p); std::shared_ptr<int> b(p);` 两个独立控制块，析构时各 delete 一次，double free 崩溃。一个裸指针只能交给**一个**智能指针；要共享用同一个 `shared_ptr` 拷贝。

```cpp
auto sp = std::make_shared<int>(1);   // ✅ 一个控制块
auto sp2 = sp;                        // ✅ 拷贝共享，引用计数 +1
// std::shared_ptr<int> a(p), b(p);   // ❌ 两个控制块，双重释放
```

### 现场二：shared_ptr 循环引用，内存永远不释放

凯喵让 A 持有 `shared_ptr<B>`、B 持有 `shared_ptr<A>`，引用计数永远 ≥1，析构时互相等对方先释放，内存泄漏。环里的一侧改用 **`weak_ptr`** 打破循环。

```cpp
struct B;
struct A { std::shared_ptr<B> b; ~A(){/* 不打印也行 */} };
struct B { std::weak_ptr<A> a; };     // ✅ weak_ptr 不增加计数，打破环
auto a = std::make_shared<A>();
auto b = std::make_shared<B>();
a->b = b; b->a = a;                   // 析构时正常释放
```

### 现场三：用 this 直接构造 shared_ptr，自引用炸裂

凯喵在成员函数里 `return std::shared_ptr<Self>(this);`，等于把这个裸 this 交给新控制块，和外部的 `shared_ptr` 不是同一个，双重释放。要让对象自身成为 shared_ptr 用 **`std::enable_shared_from_this`**。

```cpp
struct Self : std::enable_shared_from_this<Self> {
    std::shared_ptr<Self> get() { return shared_from_this(); }  // ✅ 共享同一控制块
};
// return std::shared_ptr<Self>(this);   // ❌ 新控制块，双重释放
```

### 现场四：unique_ptr 当值返回会拷贝，编译失败

凯喵 `std::unique_ptr<T> p = make();` 想返回 unique_ptr 却编译不过——unique_ptr **不可拷贝**，只能移动。返回用 `return std::move(p)` 或让函数返回类型就是 `unique_ptr`（NRVO/移动自动发生）。

```cpp
std::unique_ptr<Res> make() {
    auto p = std::make_unique<Res>();
    return p;                  // ✅ 移动语义，自动转移所有权
}
std::unique_ptr<Res> q = make();
```

### 现场五：shared_ptr 和裸指针混用，生命周期失控

凯喵 `shared_ptr<T> sp = ...; T* raw = sp.get();` 之后用 raw 访问，sp 提前析构后 raw 悬垂。`.get()` 只用于**临时**传给 C 接口，别长期持有；要共享所有权就再拷贝一个 `shared_ptr`。

```cpp
void c_api(const T*);
c_api(sp.get());              // ✅ 紧邻调用，sp 还活着
// T* raw = sp.get(); use_later(raw);  // ❌ sp 可能已析构
```

### 现场六：make_shared 与私有构造 / 单独控制块释放的权衡

凯喵无脑 `make_shared`，但只要有 `weak_ptr` 存活，控制块（及合并分配）就一直不释放，哪怕对象本身已析构。需要「对象析构后立刻回收内存」或构造可能抛异常需隔离时，才用 `shared_ptr<T>(new T(...), deleter)` 分开分配。

```cpp
// 普通场景直接 make_shared（一次分配，快）
auto p = std::make_shared<Big>();
// 需要 weak_ptr 频繁过期且内存敏感时，分开分配
auto q = std::shared_ptr<Big>(new Big, std::default_delete<Big>());
```

### 现场七：把栈对象地址塞进智能指针，析构时 double free

凯喵 `int x; std::shared_ptr<int> p(&x);` 智能指针析构时会 `delete &x`，而 x 在栈上根本不能 delete，直接崩。智能指针只接管**堆上 new 出来的**对象（或自定义 deleter 管理的资源）。

```cpp
// ❌ 栈对象不能交给智能指针
int x; std::shared_ptr<int> p(&x);
// ✅ 只接管堆对象
auto p = std::make_shared<int>(0);
```

### 现场八：数组用 shared_ptr<T> 而非 shared_ptr<T[]>，delete 错配

凯喵 `std::shared_ptr<int> p(new int[10]);` 析构时用 `delete` 而非 `delete[]`，未定义行为。数组要用 `std::shared_ptr<T[]>`（C++17+）或干脆用 `std::vector` / `unique_ptr<T[]>`。

```cpp
std::shared_ptr<int[]> arr(new int[10]);   // ✅ 数组特化，正确 delete[]
std::unique_ptr<int[]> u(new int[10]);     // ✅ 更轻量
```

### 现场九：weak_ptr 没 lock 就用，悬垂访问

凯喵 `weak_ptr<T> w; w->foo();` 直接调用，weak_ptr 不能解引用。必须先 `lock()` 拿到 `shared_ptr`，判空后再用——锁失败说明目标已析构。

```cpp
if (auto sp = w.lock()) {        // ✅ lock 成功才有对象
    sp->foo();
}                                  // 失败说明已析构，安全跳过
```

### 现场十：自定义 deleter 类型不一致，shared_ptr 不可赋值

凯喵两个 `shared_ptr` 用了不同签名的 deleter，互相赋值编译失败——`shared_ptr<T, Deleter>` 的删除器是类型的一部分。需要不同类型间转换就统一 deleter 类型，或用默认 deleter。

```cpp
auto a = std::shared_ptr<Res>(new Res, [](Res* p){ delete p; });
auto b = std::shared_ptr<Res>(new Res);   // 不同 deleter 类型，不能互赋
```

### 现场十一：把智能指针当函数参数传值，意外延长生命周期

凯喵函数参数写 `void f(std::shared_ptr<T> p)`（按值），调用处拷贝一次，引用计数 +1，对象在函数返回前不释放——可能比预期活得更久，还隐藏所有权。只读观察用 `const T&` 或 `const shared_ptr<T>&`，要共享所有权才按值。

```cpp
void observe(const T& o);                 // ✅ 只读，不碰所有权
void take(std::shared_ptr<T> p);          // ✅ 真要接管所有权才按值
```

### 现场十二：用 auto 推断 shared_ptr 结果，类型被吃掉

凯喵 `auto p = std::make_shared<Derived>(); std::shared_ptr<Base> b = p;` 没问题，但若中间用 `auto` 接了 `weak_ptr::lock()` 返回又强转，容易混。明确类型边界，别让 auto 把所有权语义藏起来。

```cpp
std::shared_ptr<Base> b = std::make_shared<Derived>();  // ✅ 显式基类指针，多态清晰
// auto x = b;  // x 是 shared_ptr<Base>，语义 OK 但隐式，关键处写全类型
```

> 凯喵总结：智能指针的坑九成是「多控制块双重释放」「循环引用泄漏」「混用裸指针」「this 自引用」。记住一个裸指针只进一个智能指针、环里用 weak_ptr、返回用 move。把这 12 个现场刻进手感，内存泄漏少一大半。

### 现场之外：凯喵的智能指针四句口诀
用智能指针，凯喵把经验编成四句口诀。第一句，一个裸指针只许进一个智能指针，要共享就拷贝同一个 shared_ptr，绝不让两个独立控制块指向同一块内存。第二句，环里必有一侧是 weak_ptr，否则引用计数永远降不到零，内存悄悄泄漏。第三句，返回动态对象用 unique_ptr 或 move 出去的 shared_ptr，所有权转移清清楚楚，别靠裸指针传所有权。第四句，.get() 拿到的裸指针只供紧邻的 C 接口临时使用，别长期持有，否则智能指针一析构它就悬垂。四句口诀背熟，C++ 的内存安全基本就稳了。

### 现场拾遗：先想所有权，再写代码
最后一句话：用智能指针之前，先想清楚这块内存的「所有权」归谁。是独享就 unique_ptr，是共享就 shared_ptr，是临时观察就 raw 或 weak_ptr。很多内存 bug 的根源不是语法用错，而是一开始就没想清谁该负责释放。把所有权当设计的一部分，而不是写完再补的 cleanup，代码自然就干净，泄漏和双重释放也失去了生长的土壤。

### 一句话收尾
凯喵最后提醒：智能指针再智能，也只是把「谁负责 delete」这件事自动化了，它替不了你对所有权的思考。一个函数到底是接管、共享还是只是借看一眼，这个判断得你来下，然后才选 unique、shared 还是 raw/weak。把智能指针当成「不用想就能写对内存」的银弹，恰恰会栽在最隐蔽的循环引用和悬垂上。工具帮你执行，决策还得你自己做。

## 三视角解析
### 🧑‍💻 程序员视角
同一个裸指针交给两个 `shared_ptr` 会各自建一个控制块，引用计数各算各的，最后双重释放——必须用 `make_shared` 或从已有的 `shared_ptr` 拷贝。循环引用是另一类泄漏：A 持有 B 的 `shared_ptr`、B 持有 A 的，计数永远不归零，解法是把其中一条边改成 `weak_ptr`。`shared_ptr<T>(this)` 也会造出第二个控制块，正确写法是继承 `enable_shared_from_this` 并调用 `shared_from_this()`。

### 🎓 博士生视角
`shared_ptr` 是「引用计数 + 控制块」的实现：控制块存强引用数、弱引用数、删除器与分配器，强引用归零时析构对象，弱引用归零时释放控制块。原子计数的增减带内存序开销，因此高频拷贝 `shared_ptr` 在多线程下会成为争用点。`unique_ptr` 是零开销抽象——大小与裸指针相同、移动即指针转移、无引用计数。设计上应默认 `unique_ptr`，只有在确实需要共享所有权时才升级为 `shared_ptr`，这是所有权语义最小化的原则。

### 📚 考研者视角
面试必问：
1. **三种智能指针的语义**：`unique_ptr` 独占、`shared_ptr` 共享、`weak_ptr` 观察不持有。
2. **`make_shared` 的优势**：一次分配同时容纳对象与控制块，缓存更友好、异常安全。
3. **循环引用与破解**：画出双向引用的计数变化，说明 `weak_ptr` 如何打破环。
4. **`shared_ptr` 的线程安全性**：引用计数操作原子，但「同一个 shared_ptr 对象」的读写不是线程安全的。

```text
04-smartptr-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：裸指针交给两个智能指针，双重释放  (cpp)
    |
    v
  [02] 现场二：shared_ptr 循环引用，内存永远不释放  (cpp)
    |
    v
  [03] 现场三：用 this 直接构造 shared_ptr，自引用炸裂  (cpp)
    |
    v
  [04] 现场四：unique_ptr 当值返回会拷贝，编译失败  (cpp)
    |
    v
  [05] 现场五：shared_ptr 和裸指针混用，生命周期失控  (cpp)
    |
    v
  [06] 现场六：make_shared 与私有构造 / 单独控制块释放的权衡  (cpp)
    |
    v
  [07] 现场七：把栈对象地址塞进智能指针，析构时 double free  (cpp)
    |
    v
  [08] 现场八：数组用 shared_ptr<T> 而非 shared_ptr<T[]>，delete 错配  (cpp)
    |
    v
  [... 其余 7 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
