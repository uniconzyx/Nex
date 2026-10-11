# 02 · unique_ptr 独占 vs shared_ptr 引用计数：控制块、原子与开销

## 一、理论根基：两种"所有权语义"的数学区别

智能指针本质是**把"谁负责 delete"这件事编码进类型系统**：

- **`unique_ptr<T>` = 独占所有权（排他）**：同一时刻**只有一个** `unique_ptr` 指向对象。语义等价于"线性类型（linear type）"——资源不能被复制，只能被**移动（move）**。因此它**禁止拷贝构造/拷贝赋值**，只提供移动构造/移动赋值。
- **`shared_ptr<T>` = 共享所有权（引用计数）**：任意多个 `shared_ptr` 可指向同一对象，最后一个销毁时才 `delete`。需要运行时记录"当前有几个持有者"。

> 博士视角：独占语义可以由编译器在编译期静态验证（所有权唯一），**零运行时成本**；共享语义必须引入运行时状态（计数器），必然有动态分配 + 原子操作成本。能用 `unique_ptr` 就别用 `shared_ptr`——前者免费，后者付费。

## 二、实现机制：unique_ptr 为何"零开销"

`unique_ptr` 只是一个**带删除器的裸指针包装**，典型布局：
```
unique_ptr<T, D> { T* ptr; /* D 若无状态则被空基类优化(EBCO)消除 */ }
```
- 默认删除器 `default_delete<T>` 是**空类型**，C++ 的**空基类优化（EBBO）**让它的尺寸为 0。于是 `sizeof(unique_ptr<T>) == sizeof(T*)`，**与裸指针同大、零额外内存**。
- 删除器是**编译期类型参数** `<D>`，调用删除器就是一次普通函数调用（可被内联），**没有类型擦除、没有虚函数、没有堆分配**。
- 移动只是"转移指针 + 置空原指针"，一条 `mov` 指令量级。这就是为什么 `unique_ptr` 常作为**工厂函数返回值**（转移所有权而不付费）。

## 三、实现机制：shared_ptr 的控制块与原子引用计数

`shared_ptr` 的内存布局远比 `unique_ptr` 复杂。它内部持有**两个指针**或一个指针 + 控制块：
```
shared_ptr<T> { T* ptr;  control_block* cb; }
control_block {
    atomic<long> strong_count;   // 强引用（shared_ptr）计数
    atomic<long> weak_count;     // 弱引用（weak_ptr + 自身）计数
    deleter;                     // 类型擦除后的删除器
    allocator;                   // 控制块自身的分配器
    T*          object_ptr;       // 有时与 cb 合并（make_shared）
}
```

**关键点（博士视角）**：
1. **引用计数在哪？在"控制块"里，不在 `shared_ptr` 对象里**。`shared_ptr` 之间靠"指向同一个控制块"来共享状态。拷贝一个 `shared_ptr` = 拷贝指针 + 原子递增 `strong_count`。
2. **为何需要原子操作？** 多个线程可能同时拷贝/析构同一个 `shared_ptr`（即使对象本身只读）。`strong_count`/`weak_count` 的增减必须是 `std::atomic` 的 **RMW（read-modify-write）**，典型底层是 `lock xadd` 这样的总线锁指令。
3. **开销有多大？** 每次拷贝/析构一次原子递增/递减（通常 ~10–20 ns，单核；竞争时更贵，且跨核会触发缓存行在 CPU 间来回弹）；控制块本身一次**堆分配**（2 个计数器 + 删除器 + 可能的对象）。
4. **控制块何时创建？** 第一次由 `shared_ptr` 接管对象时创建（如 `make_shared` 或 `shared_ptr(new T)`）。之后所有拷贝共享它；`weak_ptr` 也指向同一控制块，只增 `weak_count`。

**make_shared 的一次分配优势**：
- `std::shared_ptr<T>(new T)`：**两次分配**——`new T`（对象）+ 控制块分配。
- `std::make_shared<T>()`：**一次分配**——把对象与控制块在**同一块连续内存**里一起分配，只一次 `new`，缓存局部性更好，且异常安全（避免 `f(shared_ptr(new T), g())` 参数求值顺序导致泄漏）。
- 代价：对象内存与控制块绑定，只要有 `weak_ptr` 存活，连对象内存都不会释放（见 pitfalls 第 8 条）。

**shared_ptr 的别名构造（alias constructor）**：
`shared_ptr<U> alias(sp, &sp->member);` 创建一个指向 `sp` 内部成员的 `shared_ptr`，但**共享 `sp` 的控制块与所有权**。即别名指针的 `use_count` 与 `sp` 相同，且它保活的是整个 `sp` 对象而非成员。这是实现"返回容器某元素的智能指针视图"的安全手段。

## 四、工程实践：选择矩阵

| 场景 | 推荐 |
|---|---|
| 工厂返回值、唯一拥有者、成员独占资源 | `unique_ptr`（免费、明确） |
| 需要共享、生命周期跨作用域、观察者需延长生命 | `shared_ptr` |
| 仅观察、可能悬空、要打破循环 | `weak_ptr` |
| 仅临时借给不接管所有权的 C API | 裸指针 `get()`（红线见 pitfalls） |

**与 GC 语言对比**：`shared_ptr` 的引用计数是**手动 GC 的一种**，回收确定但**不处理循环**（需 `weak_ptr` 手工打断），且原子计数有可观测的成本；Java/Go 的追踪式 GC 能自动回收循环，但带来停顿与吞吐损耗。两者各有权衡，没有银弹。

## 五、可运行示例：计数变化与别名构造

```cpp
#include <iostream>
#include <memory>

struct Holder { int value = 7; };

int main() {
    auto holder = std::make_shared<Holder>();
    std::shared_ptr<int> alias(holder, &holder->value);   // 别名构造
    std::cout << *alias << '\n';
    std::cout << "alias.use_count="  << alias.use_count()  << '\n';
    std::cout << "holder.use_count=" << holder.use_count() << '\n';
}
```

**输出**：
```
7
alias.use_count=2
holder.use_count=2
```
> 观察点：别名指针与原始 `shared_ptr` **共享同一个控制块**，所以两侧 `use_count` 都是 2；它们共同保活的是整个 `holder` 对象。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **默认用 `unique_ptr`**：零开销（与裸指针同大小）、独占语义清晰；需要共享所有权时才升级到 `shared_ptr`。
- **`make_shared` 优于 `shared_ptr<T>(new T)`**：一次分配同时放下对象和控制块，少一次分配、少一次指针跳转，且异常安全。
- `shared_ptr` 传参优先按 `const shared_ptr<T>&` 或裸引用（不增加计数）；只在**需要延续生命周期**时才按值拷贝。

### 🎓 博士生视角
- 控制块含**强引用计数、弱引用计数、删除器、分配器**；强计数归零时析构对象，弱计数归零时释放控制块。计数的增减是**原子操作**（通常 `lock` 前缀 / `fetch_add`），这构成 shared_ptr 的主要开销来源。
- `unique_ptr` 的删除器是**类型的一部分**（编译期确定、无存储开销）；`shared_ptr` 的删除器**类型擦除**（存在控制块里、有间接调用开销）——这是两者零开销与否的分水岭。
- 从所有权语义看，`unique_ptr` 表达**仿射类型（affine）**（至多一个所有者、可转移不可复制），`shared_ptr` 表达**引用计数所有权**（易形成环）。

### 📚 考研者视角
- 408 不直接考智能指针，但**「引用计数」**是内存管理经典考点（可与文件系统的硬链接计数、操作系统的页框引用计数对照）。
- 记忆锚点：**`shared_ptr` 的计数是原子的（线程安全），但所指对象不是线程安全的**；**`unique_ptr` 与裸指针同尺寸（无额外开销）**。
- 若考 OS：**引用计数无法处理循环引用**——这是它与「可达性分析（GC）」的根本差别。

---
