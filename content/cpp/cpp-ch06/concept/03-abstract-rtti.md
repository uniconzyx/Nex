# 03 · 抽象类、RTTI 与多重/虚继承：运行时查表与 this 修正

## 一、纯虚函数与抽象类：接口隔离的契约

**纯虚函数** `virtual void f() = 0;` 表示「此函数在本类无实现，强制派生类提供」。含至少一个纯虚函数的类成为**抽象类**：

- **不能实例化**（`Shape s;` 编译错误）——因为它有「未填的槽位」，构造出的对象 vtable 该槽为空，调用即 UB。
- 抽象类的价值是**定义接口契约**（shape 能 `area()`、能 `draw()`），把「调用方依赖的抽象」与「实现方的具体类型」解耦——这是依赖倒置（DIP）的落地。

```cpp
struct Shape {                       // 抽象类
    virtual double area() const = 0; // 纯虚：必须被覆盖
    virtual void draw() const = 0;
    virtual ~Shape() = default;      // 仍要 virtual 析构（ch06 pitfalls 第 2 条）
};
```

> 即使纯虚函数，C++ 也允许提供**定义**（用于让派生类「显式调用基类版本」），只是不能实例化。纯虚析构函数**必须**有定义——因为派生类析构结束时要调用它。

## 二、RTTI：dynamic_cast 与 typeid 的运行时查表

C++ 的运行时类型信息（RTTI）依赖 vtable 中额外存放的 `std::type_info` 与（多继承时）`offset_to_top`：

- **`typeid(expr)`**：返回 `const type_info&`。若 expr 是**多态类型**（含虚函数），结果取运行时真实类型；否则取静态类型。
- **`dynamic_cast<T*>(p)`**：运行时判断「`*p` 是否 `T` 或其派生」：
  - **指针版本**：失败返回 `nullptr`（安全，可判空）。
  - **引用版本**：失败抛 `std::bad_cast`（引用不能表示「空」）。
  - **前提**：基类**至少有一个虚函数**。若无虚函数，`dynamic_cast` 指针版本**编译通过但运行返回 null**（无 type_info 可查），引用版本**直接编译失败**。

```
dynamic_cast<Derived*>(base_ptr) 的运行期动作：
  取 base_ptr 指向对象的 vtable → 读取 type_info / 继承链
     ├─ 找到 Derived 在链上 → 计算 this 调整偏移 → 返回修正后的 Derived*
     └─ 找不到            → 返回 nullptr（指针）/ 抛 bad_cast（引用）
```

> **程序员视角**：向下转型本身常是「设计味道」（caller 比接口更懂具体类型）。更优解往往是「把行为上移成虚函数」，彻底消除转型。

## 三、多重继承：多个 vptr 与 this 修正

```cpp
struct A { virtual void fa(); int a; };
struct B { virtual void fb(); int b; };
struct C : A, B { virtual void fc(); int c; };
```

内存布局（示意）：

```
  C 对象:
  +------------------+  <- 偏移 0
  | A 子对象:        |
  |   vptr_A         |  → A vtable
  |   a              |
  +------------------+  <- 偏移 16 (假设 8+4 对齐=16)
  | B 子对象:        |
  |   vptr_B         |  → B vtable
  |   b              |
  +------------------+  <- 偏移 32
  | C 自己: c        |
  +------------------+
```

关键事实：
1. **两个基类子对象各有一个 vptr**（C 的 vtable 实际被拆成「主 vtable（挂在 A 子对象）+ 次 vtable（挂在 B 子对象）」）。
2. `A*` 与 `C*` 值相同（偏移 0）；但 `B*` 指向偏移 16 处，**≠ `C*` 的值**——这就是「this 指针调整」的物理来源（见 02 第三、四节 thunk）。
3. 若 `C` 重写 `A::fa`，主 vtable 对应槽被覆盖；若 `C` 重写 `B::fb`，次 vtable 对应槽被覆盖。

## 四、菱形继承与虚继承：消除重复基类子对象

经典菱形：`D : B, C` 且 `B, C : A`——`D` 里会有**两份 `A` 子对象**，带来二义性（pitfalls 第 4 条）。解决：**虚继承** `class B : virtual A`。

```
非虚继承（两份 A，二义）：          虚继承（共享一份 A）：
        A                                  A (虚基类，仅一份)
       / \                                / \
      B   C                              B   C   (均 virtual 继承 A)
       \ /                                \ /
        D                                   D
   D 内：B 的 A + C 的 A（重复）        D 内：仅一个共享 A 子对象
```

虚继承的实现成本更高：虚基类子对象被放到**对象末尾（或独立区域）**，派生类通过 vtable 里的 `virtual base offset` 间接定位它，访问 `a` 需要一次额外间接。因此**非必要时别用菱形/虚继承**——多数场景用「组合」或「接口（纯抽象）多继承」替代。

> **工程准则**：多重继承只建议「一个实现基类 + 多个纯抽象接口」；实体菱形继承几乎总是设计信号，应重构。

## 五、边界与陷阱

- `dynamic_cast` 对非多态类型静默返回 null（指针）/ 编译失败（引用）——最常见的「转型失败查不出原因」。
- 虚继承下构造函数责任上移：最派生类要**直接**调用虚基类构造函数，中间的 `B/C` 对 `A` 的构造会被忽略，否则易漏初始化。
- RTTI 可整体关闭（`-fno-rtti`）以减小体积/提升启动，关闭后 `dynamic_cast`/`typeid` 不可用。

## 六、可运行示例：dynamic_cast 成功与失败

```cpp
#include <iostream>
struct Base { virtual ~Base() = default; };
struct Derived : Base { void hello() const { std::cout << "Derived::hello\n"; } };
struct Other   : Base {};

int main() {
    Derived d;
    Base* p1 = &d;
    if (auto* dp = dynamic_cast<Derived*>(p1)) dp->hello();   // 成功

    Other o;
    Base* p2 = &o;
    if (auto* dp = dynamic_cast<Derived*>(p2))
        std::cout << "should not reach\n";
    else
        std::cout << "cast failed: null\n";
}
```

**输出**：
```
Derived::hello
cast failed: null
```

> 观察点：① `p1` 实际指向 `Derived`，转型成功并调用；② `p2` 指向 `Other`，转型失败返回 **nullptr**（指针版本安全降级），程序可控。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 纯虚函数（`= 0`）定义接口；含纯虚函数的类不能实例化。C++11 起可以有 `override` 提示与纯虚函数**带默认实现**（但仍须派生类重写）。
- `dynamic_cast` 需要**多态类型**（至少有一个虚函数）才能在运行时检查。
- 优先用虚函数做分派，`dynamic_cast` 只作兜底（大量 `if (dynamic_cast<A*>(p))` 是设计需要重构的信号）。

### 🎓 博士生视角
- `dynamic_cast` 在运行时做类型检查：对单一继承通常可以通过 `type_info` 比较或 vtable 相关结构完成；在**多重/虚继承**下，源指针可能指向某个基类子对象，必须先遍历/查表确定完整对象，再做地址修正——因此代价显著高于 `static_cast`（编译期完成）。
- `typeid` 返回 `std::type_info`（含名字与比较能力）；`typeid(*p)` 对多态类型是**运行时**求值（动态类型），而 `typeid(p)` 是静态类型。
- RTTI 可以被编译选项关掉（`-fno-rtti`），此时 `dynamic_cast` 与 `typeid` 不可用——这是许多嵌入式/游戏项目的常见配置，代价是失去运行时类型检查。
- 从设计角度看，抽象类把「接口」与「实现」分离，是**依赖倒置**的语言级支持；而 `dynamic_cast` 属于「运行期类型分支」，与「用多态替代类型分支」的设计原则相冲突。

### 📚 考研者视角
- 与「运行时类型检查」、以及动态类型语言的类型分发形成对比。
- 常考概念题：「纯虚函数与抽象类」「`dynamic_cast` 与 `static_cast` 的区别」「RTTI 的代价」。
- 记忆锚点：**`dynamic_cast` 需要多态类型（有虚函数）**；**虚继承下的 `dynamic_cast` 代价更高**。
