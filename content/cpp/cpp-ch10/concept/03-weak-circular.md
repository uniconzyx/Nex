# 03 · weak_ptr 打破循环、自定义删除器、enable_shared_from_this

## 一、理论根基：为什么 shared_ptr 处理不了循环引用

`shared_ptr` 的释放条件是"强引用计数降到 0"。若存在 **A ↔ B** 的互相持有：
```
A.sp_B → B     B.sp_A → A
```
当外部对 A、B 的最后一个 `shared_ptr` 离开作用域，A 的强计数从 1→0 吗？**不会**——因为 B 还持有一个指向 A 的 `shared_ptr`（强引用），B 的强计数同理被 A 撑着。双方计数互相"钉死"在 ≥1，析构函数**永不调用**，对象与资源**永久泄漏**。图论上这就是一个"强连通分量"：追踪式 GC 能识别不可达环并回收，但引用计数（哪怕是原子的）**无能为力**，必须靠"弱引用"手动打断。

`weak_ptr` 的语义正是"**不增加强引用计数的观察者**"：它指向控制块、能查询对象是否还活着（`expired()` / `lock()`），但**不阻止对象析构**。把环的一侧改为 `weak_ptr`，环就被打破——强计数能正常归零，析构正常发生。

## 二、实现机制：weak_ptr 与控制块的弱计数

`weak_ptr` 与 `shared_ptr` 共享同一个控制块，但只操作 `weak_count`（弱引用计数），**不影响 `strong_count`**：
- `weak_ptr` 从 `shared_ptr` 构造/赋值时，`weak_count++`；自身析构时 `weak_count--`。
- 对象何时 `delete`：当 `strong_count == 0` → 调用删除器销毁对象。
- 控制块何时 `delete`：当 `strong_count == 0 **且** weak_count == 0` → 控制块自身才释放。
- 因此只要有 `weak_ptr` 存活，控制块（含其中的 `weak_count`、删除器）就保留——这也是 `weak_ptr::lock()` 能在对象死后仍知道"已死"的原因。

**提升（promotion）的线程安全**：`weak_ptr::lock()` 内部原子地"若对象未死则强计数 +1 并返回 `shared_ptr`，否则返回空 `shared_ptr`"。这一过程是原子的，不会拿到一个正在析构中的悬空对象——这是 `weak_ptr` 相比"裸指针 + 标志位"的根本安全优势。

## 三、实现机制：自定义删除器（类型擦除的成本差异）

删除器决定"`delete` 时到底调什么"。两种智能指针对删除器的处理策略**截然不同**：

| | unique_ptr | shared_ptr |
|---|---|---|
| 删除器位置 | **编译期类型参数** `unique_ptr<T, D>` | **运行时类型擦除**存入控制块 |
| 对指针类型影响 | 不同删除器 → 不同类型 | 不同删除器 → **同一类型** `shared_ptr<T>` |
| 调用开销 | 内联、无虚函数、零成本 | 一次**函数指针 / std::function 间接调用** |
| 典型用法 | `unique_ptr<FILE, FileCloser>` | `shared_ptr<Res>(new Res, my_deleter)` |

- `unique_ptr`：删除器是类型一部分，编译器在编译期就知道调谁，**可被完全内联**，无运行时间接跳转。代价是"带不同删除器的 `unique_ptr` 是不同类型"，不能混在同一容器。
- `shared_ptr`：删除器被**类型擦除**——无论传 lambda、函数指针还是仿函数，最终 `shared_ptr<T>` 的类型都一样，因而能塞进 `vector<shared_ptr<T>>`。擦除通过控制块里的"删除器 + 分配器"用一小段类型擦除包装（本质一个函数指针 + 可能的内联存储）实现，**每次销毁有一次间接调用**，并占用控制块少量空间。

> 博士视角：类型擦除 = 用一次间接调用 + 一点内存，换取"异构删除器同类型"的灵活性。这是质量-成本的经典权衡，与 `std::function` 对可调用对象的擦除同构。

## 四、实现机制：enable_shared_from_this 与构造期陷阱

`std::enable_shared_from_this<T>` 在 `T` 内部嵌入一个 `weak_ptr<T>` 成员。规则（[util.smartptr.enab]）：
- 当**第一个** `shared_ptr<T>` 接管该对象时，它会把内部那个 `weak_ptr` 初始化为指向自己（指向同一控制块）。
- 此后成员函数里调用 `shared_from_this()` 就能把这个 `weak_ptr` **提升**为安全的 `shared_ptr`，从而"拿到指向自己的共享所有权"而不制造第二个控制块。
- **未定义行为**：在对象还**未被任何 `shared_ptr` 接管**时（尤其是**构造函数体内**）调用 `shared_from_this()`，内部 `weak_ptr` 尚为空，标准规定此时行为是 UB（C++17 起明确抛 `std::bad_weak_ptr`）。因为构造函数里 `this` 还没有控制块——不可能凭空造出共享所有权。

## 五、可运行示例：循环引用 vs 打破、enable_shared_from_this

```cpp
#include <iostream>
#include <memory>

struct A; struct B;
struct A { std::shared_ptr<B> b; ~A(){ std::cout << "~A\n"; } };
struct B { std::weak_ptr<A>   a; ~B(){ std::cout << "~B\n"; } };   // 弱引用打破环

struct Node : std::enable_shared_from_this<Node> {
    void report() {
        auto self = shared_from_this();          // 安全地获取指向自身的 shared_ptr
        std::cout << "self.use_count=" << self.use_count() << '\n';
    }
    ~Node(){ std::cout << "~Node\n"; }
};

int main() {
    // 1) 打破循环：仅 A 强持有 B，B 弱持有 A
    auto a = std::make_shared<A>();
    auto b = std::make_shared<B>();
    a->b = b; b->a = a;
    std::cout << "count a=" << a.use_count() << " b=" << b.use_count() << '\n';
    // 作用域结束 → 强计数归零 → ~A ~B 都会打印（对比 concept 演示里循环引用不打印）

    // 2) enable_shared_from_this
    std::cout << "--- shared_from_this ---\n";
    auto n = std::make_shared<Node>();
    n->report();
}
```

**输出**：
```
count a=1 b=2
~A
~B
--- shared_from_this ---
self.use_count=2
~Node
```
> 观察点：① 把 B 侧改成 `weak_ptr` 后，析构**正常发生**（`~A` `~B` 都打印），证明循环被打破；② `shared_from_this()` 返回的 `self` 与原 `n` 共享控制块，`use_count` 变 2。

## 六、边界与陷阱

- 用 `shared_ptr(this)` 制造第二个控制块 → 双重释放（见 pitfalls 第 3 条）。
- `weak_ptr` 不能直接解引用，必须先 `lock()` 并检查非空。
- 自定义删除器若抛异常，会触发 `std::terminate`（析构路径中抛异常），删除器内部须自带错误处理。
- 数组用 `unique_ptr<T[]>`，不要误用 `unique_ptr<T>`（见 pitfalls 第 5 条与 examples/ex04）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **循环引用 = 强计数永不归零 = 内存泄漏**。打破方法：把「反向/回指」的一方改为 `weak_ptr`（如父持有子用 `shared_ptr`，子指父用 `weak_ptr`）。
- `weak_ptr` 使用前必须 `lock()` 提升为 `shared_ptr` 并判空——因为对象可能已析构；**不要「先判 expired 再 lock」**（中间存在竞态）。
- `enable_shared_from_this` 让成员函数拿到 `shared_ptr` 形式的 `this`；**绝不能在构造函数里调用 `shared_from_this()`**（控制块尚未建立，抛 `bad_weak_ptr`）。

### 🎓 博士生视角
- 弱引用计数的存在让控制块**在强计数归零后仍存活**，直到所有 `weak_ptr` 也消失——这解决了「如何在对象死后安全地探测它死没死」的问题。
- 循环引用是**引用计数 GC 的固有缺陷**，标准解法有三类：弱引用打破环、环收集器（trial deletion，如 CPython 的 gc 模块）、显式所有权树（不允许交叉强引用）。
- `enable_shared_from_this` 的工作原理是基类里存一个 `weak_ptr`，由 `shared_ptr` 构造时回填——所以「先有 shared_ptr，后有 shared_from_this」是硬约束。

### 📚 考研者视角
- 记忆锚点：**循环引用是引用计数的死穴**；对照理解为「引用计数 vs 标记清除」两种 GC 策略的取舍（前者实时但漏环，后者可回收环但需暂停扫描）。
- 若考操作系统/内存管理：可与「硬链接计数为 0 才删 inode」对照——**引用计数的语义都是「最后一个所有者负责释放」**。
- 常见简答：**为什么需要弱引用？** 答：为了「观察而不拥有」，从而打破强引用的环。

---
