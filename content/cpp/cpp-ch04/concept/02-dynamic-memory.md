# 动态内存：new / delete

栈上的对象在离开作用域自动销毁；**堆（自由存储）**上的对象需手动 `new` / `delete` 管理生命周期。

## 要点

- 单对象：`int* p = new int(7);` … `delete p;`
- 数组：`int* a = new int[3];` … `delete[] a;`（**必须** `delete[]`，否则 UB）
- `new` / `delete` 与 `new[]` / `delete[]` **严格匹配**
- 异常安全：若 `new` 后、`delete` 前抛异常，会泄漏 → 优先用智能指针（`std::unique_ptr`）
- 释放后置 `nullptr` 可避免"重复 delete"的二次释放（但更好的是用智能指针彻底消除手动管理）

```cpp
int* p = new int(7);
// ... 使用 p
delete p;
p = nullptr;   // 避免悬垂后再误用
```

---

## 三视角解析

### 🧑‍💻 程序员视角
- `new` 配 `delete`、`new[]` 配 `delete[]`，**不能混用**（数组版会漏掉元素数量 cookie，行为未定义）。
- 生产代码优先用智能指针或容器，裸 `new`/`delete` 只应出现在极少数需要精细控制的底层代码。
- `new` 失败默认抛 `std::bad_alloc`（异常安全路径），要「不抛」版本可用 `new (std::nothrow)`。

### 🎓 博士生视角
- `new` 是**两步操作**：`operator new` 分配原始内存 → 在该内存上**placement new 构造对象**；`delete` 也是两步：调析构函数 → `operator delete` 释放内存。这与 `malloc`/`free` 有本质区别——后者只管内存，不懂构造与析构。
- `new T[n]` 需要在某处记录**元素个数**（数组 cookie），以便 `delete[]` 能正确调用 n 次析构——这正是「`new[]` 必须配 `delete[]`」的技术原因。
- `operator new`/`operator delete` 可以被**重载**（包括类级），这是内存池、调试分配器与自定义分配策略的接口；标准库容器的分配器（Allocator）抽象同源于此。
- 从语言设计看，把「分配」与「构造」分离，才让 `std::vector` 能做到「预留容量但不构造元素」（`capacity` 与 `size` 的区分）。

### 📚 考研者视角
- 与 408 的**动态存储管理**（空闲链表、分配算法、内存回收）直接对应。
- 常考概念题：「`new`/`delete` 与 `malloc`/`free` 的区别」（构造析构、返回类型、失败行为、是否可重载）。
- 记忆锚点：**`new` = 分配 + 构造，`delete` = 析构 + 释放**；**`new[]` 必须配 `delete[]`**。
