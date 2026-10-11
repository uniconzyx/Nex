# 03 · 范围 for 与 `emplace`：遍历、迭代器失效与原地构造

## 一、范围 for 的展开（编译器到底做了什么）

`for (auto x : range)` 不是新语法糖的魔法，标准规定它**等价于**如下迭代器循环（[stmt.ranged]）：

```cpp
{
    auto && __range = range;                 // 绑定整个 range（延长临时生命）
    for (auto __begin = begin(__range),
              __end   = end(__range);        // 只求值一次！__end 在循环外固定
         __begin != __end; ++__begin) {
        auto x = *__begin;                   // 每次解引用，按值拷贝给 x
        // 循环体
    }
}
```

关键事实：**`__end` 只在循环开始前求值一次**（不是每次判断都重算）。这带来两个推论：

1. 若 `range` 是临时对象（如 `for (auto x : getVec())`），`__range` 是 `auto&&` 引用，**延长了临时对象的生命**到整个循环结束——这是安全的（C++11 起修复了早期草案的悬垂问题）。
2. 循环体内若 `range` 是 `vector`，正常情况下 `__end` 不变；但**一旦改变了容器的元素数量（增删），迭代器可能失效**。

## 二、迭代器失效（范围 for 的致命陷阱）

范围 for 本质是「`begin`…`end` 的迭代器遍历」。对 `vector`/`string`/`deque`：

| 操作 | 对迭代器/引用/指针的影响 |
|---|---|
| `push_back` 触发扩容 | **全部**迭代器、引用、指针失效 |
| `push_back` 未扩容 | 仅尾后迭代器失效 |
| `erase(it)` | `it` 及之后所有迭代器失效 |
| `insert(it, ...)` 触发扩容 | 全部失效 |

**在范围 for 里对 `vector` 做 `erase`/`push_back` 是 UB**：因为底层迭代器已被 `__begin` 持有，增删后它失效，下一次 `++__begin`/解引用是未定义行为。

```cpp
for (auto& x : v) {
    if (x == 0) v.erase(...);   // ❌ 迭代器失效，UB
}
```

正确做法：**改用显式迭代器循环，用 `erase` 的返回值推进**（见 ex07），或先收集下标、循环结束后再删。

## 三、`emplace_back` vs `push_back`：构造次数差异

`push_back` 的参数是一个**已构造好的元素**（左值或右值）：

- `v.push_back(Widget("a"));`：`Widget("a")` 先在调用处构造一个临时对象（**1 次构造**），再把临时对象**移动/拷贝**进容器（**1 次移动或拷贝**）。共 2 次。
- `v.emplace_back("a");`：`emplace_back` 接收**构造函数参数包**，直接在容器预留的内存里**原地构造** Widget（**1 次构造**），无需先造临时再搬。共 1 次。

```
push_back(临时):   [调用处构造临时] --> (移动/拷贝) --> [容器内存]
emplace_back(args):                     [容器内存中原地构造]   ← 少一次移动/拷贝
```

实测（ex08）：`push_back(Widget("a"))` 打印 `ctor a` + `copy a`（临时→容器，因未定义移动构造而走拷贝）；`emplace_back("b")` 只打印 `ctor b`（原地构造），随后因扩容再 `copy a` 一次。即便都有移动构造，`emplace_back` 仍省去「构造临时 + 移动」中的临时构造。

## 四、转发引用参数的陷阱（`emplace`/`make_unique` 的坑）

`emplace_back` 的参数类型是**转发引用（forwarding reference）** `T&&... args`，内部用 `std::forward<Args>(args)...` 完美转发。陷阱：

- **传入已存在的左值对象**：`emplace_back(existingObj)` 会用 `existingObj` 去**拷贝构造**一个元素——这「看起来像移动，其实是多一次拷贝」，并没有省。要搬已有的对象，仍应 `push_back(std::move(existingObj))`。
- **`emplace` 接受初始化列表时**：`emplace_back({1,2})` 可能推导失败（花括号不总是能 forwarding），此时 `push_back({1,2})` 反而更顺手。
- **`explicit` 构造**：`emplace_back(args)` 走直接初始化，能调用 `explicit` 构造函数；而 `push_back(T(args))` 需要一次隐式/显式转换路径，有时 `emplace` 才是唯一写法。

## 五、工程实践

- 遍历只读：优先范围 for（`for (const auto& x : v)`）。
- 遍历要改元素：`for (auto& x : v)`（注意别在循环里增删）。
- 向尾部加元素：优先 `emplace_back(args...)`；要移动一个已有对象用 `push_back(std::move(obj))`。
- 中途删除：用迭代器 + `erase` 返回值，或倒序遍历 + `pop_back`。

## 六、可运行示例（见 examples/ex06.json、ex07.json、ex08.json）

- `ex06`：范围 for 按值只读 vs 按 `int&` 修改元素。
- `ex07`：`vector` 中正确删除偶数元素（用 `erase` 返回迭代器推进，无失效）。
- `ex08`：`push_back(临时)` 与 `emplace_back` 的构造次数对比。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **范围 for 中修改容器 = 迭代器失效**：`for (auto& x : v) v.push_back(...)` 是典型 UB，因为 `v` 可能扩容导致迭代器失效。
- **遍历时别拷贝大对象**：`for (auto x : v)` 会逐个拷贝，应写 `for (const auto& x : v)`。
- `emplace_back` 直接原地构造，省一次移动；但传**已存在的对象**时反而多一次（构造 + 移动），此时 `push_back` 更合适。

### 🎓 博士生视角
- 范围 for 的展开是固定模式：`auto __begin = begin(range); auto __end = end(range); for (; __begin != __end; ++__begin) { T x = *__begin; ... }` ——**在循环开始时就求值 end()**，所以循环中增删元素会导致越界或漏遍历。
- `emplace_back` 用**完美转发**把参数包直接传给构造函数，在 vector 的**未初始化内存**上 placement-new；`push_back` 则要求先有对象再移动进去。
- `emplace_back` 的**转发引用陷阱**：`v.emplace_back(v[0])` 可能因扩容导致 `v[0]` 引用失效而构造出垃圾值——根源是「实参在扩容前求值、但内存在扩容后使用」的顺序矛盾。

### 📚 考研者视角
- 记忆锚点：**范围 for 会在循环开始时固化 end()**，因此循环内增删元素不安全。
- 常考对比：`emplace_back`（原地构造，省一次移动）vs `push_back`（先构造再移动）。
- 若考 C++ 与 Java 的迭代器：Java 的增强 for 基于 `Iterator` 且**有 fail-fast（modCount 检测）**，会立刻抛 `ConcurrentModificationException`；C++ 无此保护，是**未定义行为**（更危险）。

---
