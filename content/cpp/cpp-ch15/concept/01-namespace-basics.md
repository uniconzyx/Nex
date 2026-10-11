# 01 · 命名空间基础：作用域、查找与 ADL

## 一、理论根基：命名空间是为了解决什么

C 语言只有「全局 + 文件静态 + 块」三层作用域，项目一大就不可避免**名字冲突**——两个库都定义了 `list`、`max`、`error`。C++ 的 `namespace` 提供**用户可控的命名作用域**，把名字关进一个「名字盒子」，用 `Namespace::name` 限定访问。

- **第一性原理**：命名空间是**编译期**的名字管理工具，不改变链接属性本身（除非匿名），只是给「未限定名字查找（unqualified lookup）」增加一层候选域。
- 它和「类作用域」有本质区别：类作用域是**类型的一部分**（影响成员访问与重载），命名空间作用域只是**名字分组**，不构成类型。

## 二、实现机制：名字查找到底怎么走

C++ 的名字解析分两条腿：

1. **限定查找（qualified lookup）**：`std::vector<int>` 直接锁定 `std` 内，不参与 ADL。
2. **未限定查找（unqualified lookup）**：写 `vector<int>`（无 `std::`），编译器从当前作用域向外逐层找，遇到 `using namespace` 引入的域也会参与；此外还会触发 **ADL（Argument-Dependent Lookup，参数依赖查找）**。

**ADL 的机理**：当函数调用实参里有「用户自定义类型」，编译器会**额外把该类型所在的命名空间也拉进候选集**，即使没有 `using`。这是为了让运算符（`<<`、`==`、`swap`）能「跟着类型走」。

```cpp
namespace geom {
    struct Point { int x, y; };
    void draw(const Point&) { /* ... */ }
}
int main() {
    geom::Point p{1, 2};
    draw(p);   // 未限定，但因为实参 p 的类型在 geom，ADL 把 geom::draw 拉进来 → OK
}
```

> 关键：ADL 是**为运算符与泛型库（如 `std::swap`、流输出）量身定做**的。它让 `using std::swap; swap(a, b);` 在 `a,b` 有特化版本时自动选中特化。

## 三、工程实践：程序员视角的取舍

- **头文件里绝不写 `using namespace std;`（反模式）**，因为它把所有名字**泄漏进每一个包含该头文件的翻译单元**，极易造成冲突与「静默选中错误重载」。参见 pitfalls。
- **`using` 声明（点名引入）**优于 **`using` 指令（整桶引入）**：
  ```cpp
  using std::cout;        // 声明：只引入 cout，精确、可控
  // using namespace std; // 指令：引入整个 std，污染面大
  ```
- **命名空间别名**化简长前缀：`namespace fs = std::filesystem;`。
- **嵌套命名空间**（C++17 可写 `namespace A::B::C {}`，等价于层层嵌套）。

## 四、边界与陷阱

- ADL 的「意外」：当实参类型来自某命名空间，该命名空间的自由函数会**绕过你的本地同名函数**被选中，造成诡异结果（见 pitfalls 第 2 条）。
- `using namespace` 在 `.cpp` 文件内**局部可控**使用尚可，但在头文件中绝对禁止。
- 全局 `using namespace` 在命名空间块内作用域受限，但仍是潜在污染源。

## 五、可运行示例：眼见为实（见 `examples/ex02-adl.md` 对应 ex02）

```cpp
#include <iostream>
namespace lib {
    struct Widget {};
    void inspect(const Widget&) { std::cout << "lib::inspect(Widget)\n"; }
}
void inspect(int) { std::cout << "global::inspect(int)\n"; }

int main() {
    lib::Widget w;
    inspect(w);   // ADL：实参类型在 lib，选中 lib::inspect
}
```

**输出**：`lib::inspect(Widget)`

---

## 三视角解析

### 🧑‍💻 程序员视角
- **头文件里禁止 `using namespace`**：会污染所有包含者，引发难以定位的重载歧义；在 `.cpp` 里也只在函数作用域内用。
- 用 `using std::string;`（声明）而非 `using namespace std;`（指令）——前者只引入需要的名字。
- **ADL 既是便利也是陷阱**：`swap(a,b)` 会找到 `a` 所属命名空间的 `swap`（这是 `std::swap` 两段式惯用法的基础），但也可能命中非预期的重载。

### 🎓 博士生视角
- ADL（参数依赖查找）是**为了运算符与泛型编程而引入的**：让 `operator<<(ostream&, MyType)` 无需限定即可找到，从而使 `cout << myObj` 可用。它是 C++ 名字查找里唯一的「按实参类型扩展搜索集」机制。
- `using` 声明与 `using` 指令的区别本质是**「引入一个名字」vs「改变查找规则」**：后者会把命名空间内**当前与未来**的所有名字都变得可见（包括后续通过 `using` 加入的），语义远比前者宽泛。
- 命名空间是**开放且可嵌套**的，因此不存在「封闭的模块边界」——这正是 C++20 模块要解决的问题（模块是封闭的、可编译的、可导出的）。

### 📚 考研者视角
- 记忆锚点：**`using` 声明引入单个名字、`using` 指令引入整个命名空间**；**ADL 按实参类型查找所属命名空间**。
- 常考辨析：C++ 的 `namespace` 与 Java 的 `package` 不同——**前者不建立文件系统映射，后者建立目录映射**。
- 若考「为什么头文件里不要 `using namespace`」：答**会污染包含者的命名空间，产生重载歧义与意外名字冲突**。

---
