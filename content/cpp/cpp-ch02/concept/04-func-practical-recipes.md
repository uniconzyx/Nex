# §4 cpp-ch02 实战手记：凯喵带你把函数与 lambda 用「翻车」

> 前三节把函数声明、重载、默认参数、lambda 讲透了。这一节凯喵把函数最容易「悬垂 / 歧义 / 多重定义」的 12 个现场摆出来——每个都是链接错误和运行时灵异事件的源头。

### 现场一：f(NULL) 选中 f(int)，空指针歧义

凯喵重载了 `f(int)` 和 `f(char*)`，调用 `f(NULL)` 却进了 `f(int)`。`NULL` 是整数常量 `0`，不是指针类型。C++11 起一律用 `nullptr`，它是独立的 `std::nullptr_t`，只会匹配指针重载。

```cpp
void f(int); void f(char*);
f(NULL);       // ❌ 调用 f(int)，不是你想要的空指针
f(nullptr);    // ✅ 明确匹配 f(char*)
```

### 现场二：[=] 在成员函数里捕获的是 this，不是对象副本

凯喵在成员函数里写 `[=]{ use(member); }` 以为按值捕获了整个对象，结果对象销毁后 lambda 调用崩溃。`[=]` 捕获成员时捕获的是 `this` 指针，不是对象副本；对象没了 `this` 悬垂。C++20 要求显式写 `[=, this]`，且要注意生命周期。

```cpp
struct Widget {
    int n = 0;
    auto bad() { return [=]{ return n; }; }      // ❌ 捕获 this，悬垂风险
    auto good() { int v = n; return [v]{ return v; }; }  // ✅ 按值拷出
};
```

### 现场三：循环里按引用捕获循环变量，闭包全看到退出值

凯喵 `for (int i...) fns.push_back([&i]{ return i; })`，所有闭包共享同一个 `i`，最后全返回循环退出值。要每个闭包一份，按值捕获 `[i]`。

```cpp
std::vector<std::function<int()>> fns;
for (int i = 0; i < 3; ++i)
    fns.push_back([i]{ return i; });   // ✅ 按值，每个一份
// fns.push_back([&i]{ return i; });   // ❌ 共享，全返回 3
```

### 现场四：mutable 改的是闭包内副本，外部变量纹丝不动

凯喵写 `[=]() mutable { ++x; }` 想改外部 `x`，结果外部没变。`mutable` 只是允许修改**闭包捕获的副本**，外部原变量不受影响。要改外部必须**引用捕获** `[&x]`。

```cpp
int x = 0;
auto f = [=]() mutable { ++x; };   // 改的是副本
f(); /* x 仍是 0 */
auto g = [&x]() { ++x; };          // ✅ 引用捕获，改外部
g(); /* x 变 1 */
```

### 现场五：头文件里定义非 inline 函数，multiple definition

凯喵在 `util.h` 里写了普通函数 `int add(int a,int b){...}`，被两个 .cpp 包含，链接报 `multiple definition`。头文件只放声明；要放定义就用 `inline`（或模板，模板隐式 inline）。

```cpp
// util.h
inline int add(int a, int b) { return a + b; }   // ✅ inline 允许多翻译单元
// int add(int a,int b){return a+b;}              // ❌ 重复定义
```

### 现场六：默认参数只能写在声明一处，调用处再写就重定义

凯喵在函数声明和定义里都写了默认参数，链接报重定义。默认参数**只应出现在声明**（通常是头文件），定义里不能重复。调用方可选填，但默认值以声明为准。

```cpp
// header
int pow(int base, int exp = 2);     // ✅ 默认参数在声明
// impl
int pow(int base, int exp) {        // ❌ 不要再写 =2
    int r = 1; for (; exp; --exp) r *= base; return r;
}
```

### 现场七：重载决议被隐式转换带偏，调到意外版本

凯喵重载 `f(short)` 和 `f(double)`，传 `int` 却进了 `f(double)`——因为 `int→short` 是窄化（需用户转换）、`int→double` 是拓宽（标准转换），编译器选更优的 double。小心「字面量 + 重载」的组合。

```cpp
void f(short); void f(double);
f(42);        // ❌ 42 是 int，窄化到 short 不如拓宽到 double，选 f(double)
f((short)42); // ✅ 显式指定
```

### 现场八：返回局部变量的引用/指针，悬垂

凯喵 `const int& r = max(a, b);` 若 `max` 返回局部引用，调用完对象就销毁，`r` 悬垂。函数返回引用/指针时，必须保证所指对象生命周期长于调用者（全局、静态、传入的引用、或 `static`）。

```cpp
// ❌ 返回局部引用
// int& bad() { int x; return x; }
// ✅ 返回传入引用之一
int& pick(int& a, int& b) { return a > b ? a : b; }
```

### 现场九：递归没基准情形，栈溢出

凯喵写阶乘忘了 `n==0` 返回 1，调用炸成 `stack overflow`。任何递归必须有**收敛到基准**的路径，否则无限自调用吃光栈。尾递归在 C++ 通常不保证优化，别依赖。

```cpp
int fact(int n) {
    if (n <= 1) return 1;     // ✅ 基准情形
    return n * fact(n - 1);
}
```

### 现场十：函数指针类型不匹配，赋值编译不过

凯喵 `void(*fp)(int) = &print;` 想接一个 `void print(double)` 的函数，编译失败。函数指针类型要**完全匹配**参数与返回；想统一回调可用 `std::function` + lambda 适配。

```cpp
void print(int);
void (*fp)(int) = print;                 // ✅ 类型匹配
// fp = [](double d){};                  // ❌ 类型不对
std::function<void(int)> f = [](double d){};  // ✅ function 可适配
```

### 现场十一：lambda 作为模板参数没指明返回类型，auto 推导歧义

凯喵写 `[](auto a, auto b){ return a > b ? a : b; }` 在三元表达式两分支类型不同时（如 int vs double），返回类型推导冲突。显式写返回类型 `-> double` 或用 `std::common_type`。

```cpp
auto m = [](auto a, auto b) -> double { return a > b ? a : b; };  // ✅ 显式返回
```

### 现场十二：默认参数表达式在每次调用都重算，带副作用要小心

凯喵 `void f(int x = g())` 以为 `g()` 只在编译期算一次，结果每次调用都重新执行 `g()`。默认参数是**运行时**在调用点求值的，带副作用或昂贵计算会被反复触发。

```cpp
int counter = 0;
int g() { return ++counter; }
void f(int x = g()) {}    // ❌ 每次调用 f() 都 ++counter
```

> 凯喵总结：函数与 lambda 的坑九成在「悬垂」「歧义」「链接重复」。记住 `nullptr` 替代 `NULL`、`[&]` 循环变量是雷、`inline` 救头文件、默认参数只在声明写。把这 12 个现场刻进手感，链接错误少一半。

### 现场之外：凯喵的三条铁律
写函数最容易犯的错不是语法，而是「生命周期」和「类型匹配」想当然。凯喵给自己定下三条：第一，任何返回引用或指针的函数，先问一句「所指对象到底能活多久」；第二，重载与默认参数宁显式不省略，别让编译器替你做主；第三，lambda 捕获列表把「捕获的是什么、生命周期多长」写清楚再编译。把这三句话贴在显示器边上，大半链接错误和悬垂崩溃都能在落笔时避开。

## 三视角解析
### 🧑‍💻 程序员视角
`f(NULL)` 选中 `f(int)` 而不是 `f(char*)`，因为 `NULL` 在多数实现里就是 `0`，整型字面量的匹配优先级更高——要传空指针必须写 `nullptr`。lambda 的两个高频坑：在成员函数里写 `[=]` 捕获的是 `this` 指针而非对象副本，对象销毁后闭包就成了悬垂；在循环里按引用捕获循环变量，所有闭包看到的是同一个变量的最终值，要按值捕获或每次循环重建闭包。`mutable` 只允许修改闭包内的副本，对原始变量没有任何影响，这一点经常被误解成「可以改外部变量」。

### 🎓 博士生视角
lambda 的本质是编译器生成的函数对象：捕获列表决定它的数据成员，`operator()` 默认是 `const`，因此要修改捕获的副本必须加 `mutable`。`[=]` 在成员函数中捕获 `this` 是标准的规定（C++20 起可用 `[=, this]` 显式表达），这使闭包的生命周期与对象绑定，异步场景必须用 `shared_from_this` 或值捕获来延长。从类型系统看，每个 lambda 都有独一无二的闭包类型，只能通过 `auto` 或 `std::function`（类型擦除）持有，后者会带来一次间接调用与可能的堆分配。

### 📚 考研者视角
面试常考：
1. **重载决议顺序**：精确匹配 → 提升转换 → 标准转换 → 用户定义转换。`f(NULL)` 的歧义正是这条链的体现。
2. **lambda 的捕获方式**：值捕获在定义时拷贝、引用捕获共享变量；`[&]` 与 `[=]` 的默认捕获规则，以及 C++20 的 `[=, this]` 变化。
3. **`std::function` 的开销**：类型擦除 + 可能的堆分配，热路径上应优先用模板参数或函数指针。
4. **函数对象 vs 函数指针**：前者可内联、可携带状态，后者不能。
