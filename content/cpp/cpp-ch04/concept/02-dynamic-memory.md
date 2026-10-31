# 动态内存：new / delete

栈上的对象在离开作用域自动销毁；**堆（自由存储）**上的对象需手动 `new` / `delete` 管理生命周期。

这一章的真正主题不是"怎么用 `new`"，而是**为什么现代 C++ 几乎不该直接用它**。理解了 `new` 的两步本质与异常安全陷阱，`unique_ptr` 的存在理由就不言自明。

## 一、`new` 是两件事，`delete` 也是

```cpp
int* p = new int(7);
```

这一行做了**两步**：

1. `operator new(sizeof(int))` —— 分配原始内存（可能失败抛 `bad_alloc`）。
2. **placement new** —— 在那块内存上构造对象（对 `int` 是写入 7，对类类型是调构造函数）。

`delete p;` 同样是两步：**先调析构函数**，再 `operator delete` 释放内存。顺序不能反——析构函数要访问对象成员，内存必须还在。

这是 `new`/`delete` 与 `malloc`/`free` 的本质区别：后两者**只懂内存，不懂对象**。`malloc` 出来的内存里没有"对象"，`free` 也不会调析构。

```text
new / delete 的分步结构

  new T(args)
    ① operator new(sizeof(T))  ──► 原始内存（未构造）
    ② placement new T(args)    ──► 构造函数执行，对象诞生

  delete p
    ① p->~T()                  ──► 析构函数执行，对象死亡
    ② operator delete(p)       ──► 内存归还
```

正因为这两步可以拆开，`std::vector` 才能做到"预留容量但不构造元素"：它用 `operator new` 拿内存，用 placement new 逐个构造，`size()` 与 `capacity()` 的差异本质上就是"已构造"与"已分配"的差异。

## 二、`new[]` / `delete[]` 与数组 cookie

```cpp
int* a = new int[3];
delete[] a;      // 正确
delete a;        // UB：漏了 []
```

为什么必须配对？因为 `delete[]` 需要知道**要调多少次析构**。对于有析构函数的类型，`new T[n]` 通常在返回指针的**前面**多分配几个字节存元素个数（数组 cookie），`delete[]` 读到它才能正确地析构 n 次。用 `delete` 会按单对象处理：少调 n−1 次析构，且释放的地址与分配时不一致 → 堆损坏。

`int`/`double` 这类平凡析构类型，编译器可能省掉 cookie，于是"混用有时不崩"——这更危险，因为它让 bug 潜伏到换成类类型时才爆发。

## 三、异常安全：为什么裸 `new` 一定会漏

```cpp
void f() {
    Resource* r = new Resource();
    may_throw();          // 若此处抛异常…
    delete r;             // …这一行永远不执行 → 泄漏
}
```

C++ 没有 `finally`，所以"手动配对"在异常路径上必然失效。这不是程序员粗心，而是**语言没有提供自动清理机制**（除了析构函数）。RAII 正是为此而生：

```cpp
void f() {
    auto r = std::make_unique<Resource>();   // 无论正常返回还是抛异常，都会析构
    may_throw();
}
```

`unique_ptr` 的析构函数在栈展开时被调用，于是 `delete` 自动化。这就是"用对象的生命周期管理资源"的核心思想，也是 C++ 最重要的惯用法。

## 四、`operator new` 可以重载：内存池的入口

`operator new` / `operator delete` 是可替换的（全局或类级）。这让内存池、调试分配器、对齐分配成为可能：

```cpp
void* operator new(std::size_t n);          // 全局替换
struct Pooled { static void* operator new(std::size_t n); };  // 类级
```

标准库容器的 `Allocator` 抽象与之一脉相承：把"如何拿内存"从"如何使用内存"里分离出来，于是 `vector` 可以换分配策略而不改算法。

## 五、什么情况下仍然可以用 `new`

- **placement new**：在已有内存上构造对象（`std::optional`、`vector` 的内部实现、嵌入式固定缓冲）。
- **需要在构造函数外延迟构造**（配合 `std::aligned_storage` 或 `union`）。
- **与 C API 交互**且明确知道谁释放（此时通常用 `malloc` 更合适）。
- **重载分配器**的底层实现本身。

除此之外，应用层代码应该**一次 `new` 都不写**——`make_unique` / `make_shared` / 容器足够覆盖所有场景。

## 六、边界与陷阱

- **`new[]` 配 `delete`**：UB，且可能悄悄不崩，等换成类类型才爆。
- **`delete` 两次**：double free，堆损坏。置 `nullptr` 只能防"同一个指针变量"，防不住副本。
- **`new` 后提前 return**：泄漏。用 RAII。
- **构造中途抛异常**：`new T(...)` 若构造函数抛异常，`operator new` 分配的内存会被自动释放（标准保证），但**构造函数里已获取的其他资源不会**——所以构造函数里也要用 RAII 成员。
- **`new (std::nothrow)`**：失败返回 `nullptr`，不抛异常。仅在内核/嵌入式等不支持异常的场合有意义。
- **`delete` 基类指针而基类析构非虚**：只调基类析构，派生部分泄漏（见 cpp-ch06）。

## 七、可运行示例：观察构造/析构与 cookie 的痕迹

```cpp
#include <cstddef>
#include <iostream>
#include <memory>

struct Tracked {
    int v;
    explicit Tracked(int x) : v(x) { std::cout << "ctor " << v << "\n"; }
    ~Tracked() { std::cout << "dtor " << v << "\n"; }
};

int main() {
    Tracked* one = new Tracked(1);
    delete one;                                  // ctor 1 / dtor 1

    Tracked* arr = new Tracked[3]{Tracked(10), Tracked(11), Tracked(12)};
    delete[] arr;                                // 每个元素各析构一次（共 3 次 dtor）

    {
        auto up = std::make_unique<Tracked>(99); // 异常安全：栈展开时自动 delete
        std::cout << "inside=" << up->v << "\n";
    }                                            // 此处 dtor 99

    std::cout << "raw_size=" << sizeof(Tracked) << "\n";
}
```

比较 `delete one` 与 `delete[] arr` 的输出行数，就能看出"数组析构必须知道元素个数"这件事。`make_unique` 那段演示 RAII：作用域结束时 `dtor 99` 自动出现，全程没有手写 `delete`。

## 三视角解析

### 🧑‍💻 程序员视角
- `new` 配 `delete`、`new[]` 配 `delete[]`，**不能混用**（数组版会漏掉元素数量 cookie，行为未定义）。
- 生产代码优先用智能指针或容器，裸 `new`/`delete` 只应出现在极少数需要精细控制的底层代码。
- `new` 失败默认抛 `std::bad_alloc`（异常安全路径），要「不抛」版本可用 `new (std::nothrow)`。
- 判据很简单：**只要你能想到"这里抛异常会怎样"，就该用 `unique_ptr`**。

### 🎓 博士生视角
- `new` 是**两步操作**：`operator new` 分配原始内存 → 在该内存上**placement new 构造对象**；`delete` 也是两步：调析构函数 → `operator delete` 释放内存。这与 `malloc`/`free` 有本质区别——后者只管内存，不懂构造与析构。
- `new T[n]` 需要在某处记录**元素个数**（数组 cookie），以便 `delete[]` 能正确调用 n 次析构——这正是「`new[]` 必须配 `delete[]`」的技术原因。
- `operator new`/`operator delete` 可以被**重载**（包括类级），这是内存池、调试分配器与自定义分配策略的接口；标准库容器的分配器（Allocator）抽象同源于此。
- 从语言设计看，把「分配」与「构造」分离，才让 `std::vector` 能做到「预留容量但不构造元素」（`capacity` 与 `size` 的区分）。
- 标准保证：若构造函数抛异常，已分配的原始内存会被自动释放（`operator delete` 被调用），但已构造完成的部分成员按逆序析构——这就是"构造函数抛异常不会泄漏，但成员必须自己 RAII"的精确表述。

### 📚 考研者视角
- 与 408 的**动态存储管理**（空闲链表、分配算法、内存回收）直接对应。
- 常考概念题：「`new`/`delete` 与 `malloc`/`free` 的区别」（构造析构、返回类型、失败行为、是否可重载）。
- 常考辨析：`new[]`/`delete[]` 与 `new`/`delete` 的配对规则；内存泄漏与悬垂指针的区别。
- 记忆锚点：**`new` = 分配 + 构造，`delete` = 析构 + 释放**；**`new[]` 必须配 `delete[]`**。
