# 02 · constexpr 编译期计算 与 if constexpr 分支裁剪

## 一、constexpr：把计算搬进编译期

`constexpr` 函数/变量表示「可以在编译期求值」。编译期计算带来：零运行时开销、可用于需要编译期常量的语境（数组大小、`static_assert`、模板非类型参数）。

```cpp
constexpr int fib(int n) {
    return n <= 1 ? n : fib(n - 1) + fib(n - 2);
}
static_assert(fib(10) == 55);   // 证明计算发生在编译期
```

## 二、if constexpr：模板内的编译期分支

`if constexpr(cond)` 中 `cond` 必须是编译期 bool 常量；**不满足的分支不会被实例化**，因此可以对不适用类型写「看似非法实则被裁剪」的代码。

```cpp
template <typename T>
void log(T v) {
    if constexpr (std::is_pointer_v<T>)
        std::cout << *v;     // 仅当 T 是指针才实例化
    else
        std::cout << v;
}
```

### 🧑‍💻 程序员视角
- 用 `constexpr` 替代宏与「初始化期才算出」的全局变量：编译期算出查表/常量，二进制里直接是结果，启动更快、可被优化进立即数。
- `if constexpr` 是替代「大量模板特化/ overload 集」的利器：以前要用 3 个特化才能区分的处理，现在一个函数模板 + `if constexpr` 搞定，代码量骤减、可读性提升。
- 注意：`constexpr` 函数也**可以**在运行时调用（只要参数不是编译期常量），不要误以为它会强制编译期；要强制请用 `consteval`（C++20）或 `static_assert`。

### 🎓 博士生视角
- `constexpr` 求值属于**常量表达式解释器**：编译器在翻译期执行受限的 C++ 子集（不允许未定义行为、不能有未初始化读取等），其结果直接写入目标代码的常量区。
- `if constexpr` 的「不实例化」意味着被裁剪分支内的类型错误、未定义名字都不会触发，这本质上是**编译期选择性展开**；而普通 `if` 会对所有分支实例化，对非适用类型直接报错。
- `static_assert` 是编译期断言，可消费任意常量表达式；它不生成任何运行时指令，纯粹是「类型/值层面的契约」。

### 📚 考研者视角
- 面试标准问法：「`constexpr` 和 `const` 区别？」「`if constexpr` 与普通 `if` 在模板中区别？」「怎么证明函数真的在编译期执行？」
- 易错口径：`const` 只保证运行时不修改，`constexpr` 保证编译期可知；`constexpr` 变量**隐含** `const` 但反之不成立。
- 证明编译期执行的标准做法：`static_assert(f(10) == X)` 或 `int arr[f(5)];`（需要编译期常量作数组大小）。

---

## 三、static_assert 与编译期契约

`static_assert(常量表达式, 可选消息)` 在编译期检查；C++17 起消息可省。它常用于给模板加「前置约束」，把难懂的实例化错误转成人话。

### 🧑‍💻 程序员视角
- 在模板入口写 `static_assert(std::is_integral_v<T>, "T must be integral")`，比实例化深处几百行报错友好得多；现代应优先用 `concept`（C++20）做这件事。
- 跨平台代码常用 `static_assert(sizeof(int) == 4)` 锁定 ABI 假设，防止在陌生平台上静默出错。

### 🎓 博士生视角
- `static_assert` 不进入目标代码，是纯编译期谓词；它和 `if constexpr` 共享「常量表达式」求值管道，二者都是模板元编程「从类型走向值」的桥梁。
- 与 `requires` 子句（concept）相比，`static_assert` 是「事后断言」，而 `requires` 是「参与重载决议的约束」，前者报错位置更靠后、粒度更粗。

### 📚 考研者视角
- 笔试常考：`static_assert` 与 `assert` 区别——前者编译期、零运行时成本、失败则编不过；后者运行时、可关闭。
- 易错口径：C++17 起 `static_assert(expr)` 可以不带消息字符串；旧标准 `static_assert(expr, msg)` 必须带消息。

---

## 四、三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| constexpr | 替代宏/全局初始化 | 常量表达式解释器 | constexpr vs const |
| if constexpr | 替代多特化 | 编译期选择性实例化 | 与普通 if 区别 |
| static_assert | 模板前置约束 | 纯编译期谓词 | 与 assert 区别 |
