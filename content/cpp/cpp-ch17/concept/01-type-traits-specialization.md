# 01 · 类型萃取 type_traits 与模板特化/偏特化

## 一、<type_traits>：编译期的「类型查询与变换」

`<type_traits>` 提供一组编译期常量/类型别名，用于在编译期询问或变换类型。
- **询问（谓词）**：`is_same<T,U>`、`is_integral<T>`、`is_pointer<T>`、`is_destructible<T>` 等，提供 `value`（bool 常量）与 `_v` 便捷别名。
- **变换（元函数）**：`remove_reference<T>`、`add_pointer<T>`、`decay<T>`、`remove_cv<T>` 等，提供 `type` 与 `_t` 便捷别名。

```cpp
static_assert(std::is_same_v<std::remove_reference_t<int&>, int>);
static_assert(std::is_same_v<std::decay_t<int[3]>, int*>);
static_assert(std::is_destructible_v<int>);
```

## 二、模板特化与偏特化

特化允许为特定类型定制实现：
- **全特化**：`template<> struct X<double>{...};` 针对单一具体类型。
- **偏特化**：`template<typename T> struct X<T*>{...};` 针对一类类型模式（如指针）。

### 🧑‍💻 程序员视角
- STL 大量依赖 traits：`std::move` 的实现核心是 `static_cast<remove_reference_t<T>&&>(t)`，先去引用再转右值；`std::decay` 用于 `std::function` 的参数类型归一。
- 工程惯例：写泛型库时优先用标准 traits 而非手写 `typeid`/`dynamic_cast`——前者零开销且编译期完成，后者有运行时成本且依赖 RTTI。
- 偏特化常用于「对指针/容器特判」：`vector<bool>` 就是 `vector` 的偏特化（位压缩存储），是典型的「为特定类型牺牲通用性换空间」的取舍。

### 🎓 博士生视角
- traits 本质是**编译期纯函数**：输入类型、输出类型或 bool 常量，无副作用、可在 `static_assert`/模板参数中求值。其实现依赖 SFINAE 与模板偏特化（如 `is_same` 用 `true_type`/`false_type` 两个偏特化做模式匹配）。
- `decay` 的语义等价于「按值传参后的类型」：`T&`→`T`、`const T`→`T`、数组→指针、函数→函数指针——它模拟了 C++ 值传递的类型退化规则。
- 偏特化在编译器内部形成**偏序（partial ordering）**：更「特化」的版本在重载决议中优先于更「通用」的版本，这是模板匹配的形式化基础。

### 📚 考研者视角
- C++ 方向笔试/面试标准问法：「`std::move` 为什么用 `remove_reference`？」「`decay` 和 `remove_reference` 区别？」「`is_same` 怎么实现？」
- 易错口径：`is_same_v<int, const int>` 是 **false**（cv 限定不同）；`remove_reference_t<int&>` 是 `int` 但 `add_lvalue_reference_t<int>` 是 `int&`。
- 模板特化考点：全特化 vs 偏特化语法区别；**函数模板不支持偏特化**（只允许重载/全特化），这是高频陷阱题。

---

## 三、is_destructible 与「类型是否可销毁」

`is_destructible_v<T>` 在编译期回答「`T` 的对象能否被销毁」（析构函数可访问且未被删除）。
```cpp
struct NoDtor { ~NoDtor() = delete; };
static_assert(std::is_destructible_v<int>);
static_assert(!std::is_destructible_v<NoDtor>);
```

### 🧑‍💻 程序员视角
- 在写泛型容器/智能指针时，常用 `is_destructible` 或 `is_nothrow_destructible` 决定是否需要调用析构、能否 `noexcept`，这是「零开销抽象」的常规手段。
- 真实事故：把删除析构函数的类型塞进 `std::vector`，会在实例化 `~vector` 时触发硬错误；用 `static_assert(is_destructible_v<T>)` 可在最外层提前报错，错误信息更友好。

### 🎓 博士生视角
- `is_destructible` 的实现依赖 SFINAE 探测表达式 `std::declval<T>().~T()` 是否良构；它只关心**可访问性/存在性**，不关心析构是否抛异常（那是 `is_nothrow_destructible` 的职责）。
- 与对象生命周期的形式化模型相关：可销毁性是「RAII 资源管理正确性」的必要前提，标准库容器要求 `value_type` 满足可析构。

### 📚 考研者视角
- 面试标准问法：「如何判断一个类型能否被销毁？」「`is_destructible` 和 `is_nothrow_destructible` 区别？」
- 易错口径：删除析构函数 `= delete` 后 `is_destructible_v` 为 **false**；而仅删除拷贝构造不影响可析构性（二者正交）。

---

## 四、三视角小结

| 主题 | 程序员（工程/坑） | 博士生（机制/原理） | 考研者（考点/口径） |
|---|---|---|---|
| type_traits | 优先用标准 traits 替代 RTTI | 编译期纯函数，靠偏特化实现 | is_same/decay 易错口径 |
| 特化/偏特化 | vector<bool> 位压缩 | 偏序决议 | 函数模板无偏特化 |
| is_destructible | 容器前置 static_assert | declval 探测良构性 | =delete 后为 false |
