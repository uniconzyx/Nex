# cpp-ch10 易错点（Pitfalls）

1. **循环引用导致 shared_ptr 泄漏**
   两个对象互相持有 `shared_ptr`，彼此强引用计数永远不为 0，析构不会被触发，内存与资源泄漏。
   ✅ 把其中一侧改为 `weak_ptr`（见 concept/03-weak-circular.md）。

2. **enable_shared_from_this 在构造函数中调用 shared_from_this()**
   尚未被任何 `shared_ptr` 接管时，内部 `weak_ptr` 还是空，`shared_from_this()` 直接抛 `bad_weak_ptr`（std::bad_weak_ptr，C++17 起）。
   ✅ 只在已由 `shared_ptr` 管理的成员函数里（如 `init()`、回调）调用 `shared_from_this()`，绝不在构造函数体里调用。

3. **把 this 直接交给新 shared_ptr（重复控制块 / 双重释放）**
   `std::shared_ptr<Self>(this);` 会为 `*this` 创建**第二个**控制块，与已有的控制块各自独立 → 析构时两次 `delete` 崩溃。
   ✅ 让类继承 `std::enable_shared_from_this<Self>`，统一用 `shared_from_this()` 取共享所有权。

4. **混用 get() 返回的裸指针构造第二个 shared_ptr / unique_ptr**
   `auto q = std::shared_ptr<int>(p.get());` 与 `p` 各自拥有独立控制块，指向同一块内存 → 双重释放。
   ✅ `get()` 只用于"借用"交给不接管所有权的 C API；绝不基于它再构造智能指针。若需共享，复制原 `shared_ptr` 或用 `weak_ptr::lock()`。

5. **用 delete 而非 delete[] 释放 unique_ptr<T[]> 管理的数组**
   `std::unique_ptr<int>` 默认删除器是 `delete`，对数组 UB；且 `operator[]` 不可用。
   ✅ 数组务必用 `std::unique_ptr<T[]>`（删除器自动为 `delete[]`，并提供 `[]` 下标访问），见 examples/ex04。

6. **误以为 weak_ptr 自身持有所有权 / 直接解引用**
   `weak_ptr` 不参与引用计数，不能直接 `*wp` 或 `wp->`。
   ✅ 先 `auto sp = wp.lock();` 提升为 `shared_ptr` 再使用；提升失败（`expired()` 为 true）即对象已析构。

7. **shared_ptr 按值传参会抬高引用计数，带来原子开销**
   大循环里反复按值传递 `shared_ptr` 会频繁执行原子递增/递减，成为性能热点。
   ✅ 只读观察场景传 `const shared_ptr<T>&`；确需延长生命周期才按值传；不可拷贝所有权时优先 `unique_ptr` 移动。

8. **make_shared 与私有构造 / 单独控制块释放的权衡**
   `make_shared` 把对象与控制块合并一次分配，但只要有 `weak_ptr` 存活，控制块（及合并分配）就一直不释放，哪怕对象本身已析构。
   ✅ 需要"对象析构后立刻回收内存"或构造可能抛异常需隔离时，才用 `shared_ptr<T>(new T(...), deleter)` 分开分配。

9. **裸指针交给两个智能指针，双重释放** —— 同一 `new` 结果进两个独立控制块，析构各 delete 一次。✅ 一个裸指针只进一个智能指针；共享用同一 shared_ptr 拷贝。
10. **shared_ptr 循环引用，内存永不释放** —— 环两侧都 shared_ptr，计数永远≥1。✅ 环的一侧改用 `weak_ptr` 打破环。
11. **用 this 直接构造 shared_ptr 自引用炸裂** —— 等于裸 this 进新控制块，与外部不是同一个。✅ 用 `enable_shared_from_this::shared_from_this()`。
12. **shared_ptr 与裸指针混用，生命周期失控** —— `.get()` 返回的指针在 sp 析构后悬垂。✅ `.get()` 只紧邻传给 C 接口，长期共享再拷一个 shared_ptr。
13. **栈对象地址塞进智能指针** —— 析构时 `delete` 栈地址，直接崩。✅ 智能指针只接管堆对象（或自定义 deleter 资源）。
14. **数组用 shared_ptr<T> 而非 shared_ptr<T[]>** —— 析构用 `delete` 而非 `delete[]`，UB。✅ 用 `shared_ptr<T[]>` / `unique_ptr<T[]>` 或 vector。
15. **weak_ptr 没 lock 就直接解引用** —— weak_ptr 不能 `->` 访问。✅ 先 `lock()` 拿 shared_ptr，判空后再用。
