# 04 · 两阶段编译、依赖名与包含模型：模板为何"难报错"又"必须放头文件"

## 一、理论根基：模板为什么是"两阶段"编译

普通函数编译一次即可；模板**不能**一次性编译成机器码，因为类型 `T` 未知。**标准规定模板分两阶段处理（two-phase translation，[temp.res] / [temp.inst]）**：

- **阶段一（解析 / 定义期）**：模板**首次见到定义**时（通常在包含它的翻译单元里），编译器对模板做"与 `T` 无关"的检查：
  - 语法检查、非依赖（non-dependent）名字的绑定、非依赖结构的语义检查。
  - 此时 `T` 还是一个"未确定的模板参数"，编译器**无法**确认 `T` 上是否真有某个成员。
- **阶段二（实例化 / 使用期）**：当以具体实参 `Stack<int>` 使用模板时，编译器用 `int` 替换 `T`，再对**依赖（dependent）**部分做完整检查并生成代码。

这两阶段的分离，是模板一系列"反直觉"行为的根因：错误有时在你"写完模板"时很晚才报（实例化处才暴露），有时又在不相关处报。

## 二、实现机制：依赖名（Dependent Name）与两个关键字

**依赖名 = 名称的含义依赖于模板参数 `T`**。例如 `T::value_type`、`p->foo()`、`T x` 中 `x` 的类型。因为阶段一不知道 `T` 是什么，编译器**默认假设依赖名不是类型、不是模板**，从而：

### `typename`：告诉编译器"这是类型"
```cpp
template <typename T>
void f() {
    typename T::value_type x;   // 必须写 typename：T::value_type 是依赖名，默认被当作"值"
}
```
不写 `typename` 时，编译器按"变量/成员"解析 `T::value_type`，随后若它其实是类型就语法报错。**规则：任何"嵌套依赖类型名"前加 `typename`。**

### `template`：告诉编译器"后面的 < 是模板参数列表"
```cpp
template <typename T>
void g(T& c) {
    c.template push_back(1);    // 必须写 template：push_back 是依赖名的成员模板，< 默认被当作小于号
}
```
若 `c` 的类型依赖 `T`，且 `push_back` 本身是成员模板，则 `c.push_back<...>` 里的 `<` 会被误读为"小于"。加 `template` 关键字消歧。

> 经验法则：当你在模板里写 `X::Y` 且 `X` 依赖模板参数 → 加 `typename`；写 `obj.mem<...` 且 `obj` 类型依赖模板参数 → 加 `template`。

## 三、实现机制：名称查找的两阶段（Dependent vs Non-dependent）

- **非依赖名字**：在阶段一就按常规规则（普通查找 + ADL 受限）绑定。例如模板里直接调用的全局 `log()` 若非依赖，阶段一即确定。
- **依赖名字**：在阶段二、实例化点按"**普通查找（定义处可见的） + ADL（实参相关查找）**"联合解析。这解释了模板里运算符/函数调用常走 **ADL（Argument-Dependent Lookup）**：`std::cout << obj` 能找到 `operator<<` 是因为 `std::ostream` 所在的 `std` 命名空间被实参带入。

经典坑：`std::swap(a, b)` 在模板里若直接 `using std::swap; swap(a,b);` 才能两阶段都正确落到用户特化（参见 concept 01 的重载决议）。

## 四、工程实践：包含模型（为什么模板实现放头文件）

由 §一 可知：**实例化需要模板的完整定义**。模板通常在头文件中给出完整定义（**包含模型**），调用方 `#include` 后即可在自身翻译单元内实例化。这与普通函数"声明在 .h、定义在 .cpp"相反：

- 若把 `template<class T> void f()` 的定义放进 `f.cpp`，只有 `f.cpp` 自己能实例化；别的 .cpp 包含声明后想用 `f<int>` 时**链接失败**（`undefined reference` to `f<int>`）。
- 变通：**显式实例化导出**：在 `f.cpp` 末尾写 `template void f<int>(int);` 等，强制生成指定实例，头文件只留声明。代价是失去了泛型透明性、需手工列举所有实参组合，工程上少用。

## 五、与 Java 泛型 / 类型擦除的本质区别（程序员视角）

| 维度 | C++ 模板 | Java 泛型（类型擦除） |
|---|---|---|
| 编译产物 | 每个实参组合生成**独立真实代码** | 运行时只有**一份擦除后的 `Object`/边界代码** |
| 类型信息（运行时） | 保留，可做 `typeid`、偏特化 | 被擦除，无法 `instanceof List<Integer>` |
| 性能 | 零抽象开销，可内联、可 NTTP 优化 | 有桥方法、强制转换、装箱开销 |
| 基本类型 | 直接支持 `vector<int>` | 必须装箱 `List<Integer>`（无 `List<int>`） |
| 错误信息 | 实例化失败时报冗长模板栈 | 编译期类型检查，但运行时无类型 |
| 特化 | 一等公民（全/偏特化） | **不支持特化**，靠通配与边界 |

**本质区别**：C++ 模板是"**生成代码**"（图灵完备的编译期元编程），Java 泛型是"**编译期类型约束 + 运行时擦除**"（仅保证类型安全，不生成多份代码）。所以 C++ 模板能做 `std::vector<bool>` 位压缩特化、能做编译期计算，而 Java 做不到；但 Java 泛型二进制兼容更好、编译更快、错误信息更短。

## 六、工程实践：模板的代码膨胀与编译期成本

- **代码膨胀（code bloat）**：每个不同的实参组合生成独立代码，`std::vector<int>`/`std::vector<double>` 是两份机器码；大型模板库会显著增大二进制与延长链接。
  - 缓解：**抽出非模板公共逻辑**（如把 `vector` 的内存管理下沉到一个 `void*` 底层实现，再由薄模板层包装）；或**类型擦除**（`std::function`、`any`）。
- **编译时间**：模板在多个翻译单元各自实例化相同类型 → 重复工作（PCH、外部模板 `extern template`、模块 C++20 缓解）。
- **头文件暴露**：包含模型使模板定义暴露给所有用户，改动重建面广；C++20 **模块（module）**是根治方向（见 ch15）。

## 七、可运行示例：眼见为实

```cpp
#include <iostream>
#include <type_traits>

// 依赖名 + typename / template 关键字的真实用法
template <typename T>
void inspect() {
    // T::value_type 是嵌套依赖类型名 → 必须 typename
    using value_type = typename T::value_type;
    std::cout << "value_type size=" << sizeof(value_type) << '\n';
}

template <typename C>
void emplace_back(C& c, typename C::value_type v) {   // 第二参数类型依赖 C
    c.push_back(v);
}

int main() {
    static_assert(std::is_same<typename std::vector<int>::value_type, int>::value,
                  "vector<int>::value_type 必须是 int");
    inspect<std::vector<int>>();            // 实例化：阶段二解析依赖名

    std::vector<int> v;
    emplace_back(v, 7);                     // 依赖名在实例化点解析
    std::cout << "v[0]=" << v[0] << '\n';
}
```

**输出**：
```
value_type size=4
v[0]=7
```

> 关键结论：① `typename T::value_type` 的 `typename` 不是风格，而是**两阶段编译的硬性要求**（告诉编译器这个依赖名是类型）；② 模板真正的"全量检查"发生在**实例化点**（main 里 `inspect<std::vector<int>>()` 才触发），这正是"模板错误常延迟报到"的底层原因，也是它必须放头文件的根本原因（包含模型）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`typename` 与 `template` 消歧**是模板代码的两大高频书写负担：`typename T::value_type`（告诉编译器这是类型）、`x.template f<U>()`（告诉编译器这是模板）。
- 依赖名查找分两阶段，所以「先定义后使用」在模板里更严格；老代码用 `.h + .tpp` 或显式实例化来绕过。
- 编译时间优化：**显式实例化（explicit instantiation）**把实例化集中到一个 .cpp，其他 TU 只保留声明，能明显缩短增量编译。

### 🎓 博士生视角
- 两阶段查找（two-phase lookup）源于**模板定义点与实例化点分离**：非依赖名在**定义点**绑定（用定义处可见的重载集），依赖名在**实例化点**绑定（用 ADL + 实例化处可见的声明）。C++ 在此引入了 `-fno-ms-compatibility` 才严格实现的规则，MSVC 早期长期不遵守。
- 包含模型（inclusion model）是**语言复杂度换工程简单性**的设计：模板定义必须在每个使用它的 TU 可见，代价是重复解析与代码膨胀；C++20 模块正是为了打破这一模型。
- 从编译理论看，这是「**名字解析需要上下文**」的经典矛盾：模板把解析推迟到实例化，无法在定义时完全定型。

### 📚 考研者视角
- 考研层面只需掌握**「模板代码为什么通常写在头文件」**这一结论及其因果链（实例化需要定义可见 → 编译单元各自实例化 → 代码膨胀）。
- 记忆锚点：**两阶段查找 = 非依赖名早绑定（定义点）、依赖名晚绑定（实例化点）**。
- 若考编译原理：这与**「宏展开 vs 模板实例化」**的对比常一起出现——宏是文本替换无类型检查，模板是语法树级替换有完整类型检查。

---
