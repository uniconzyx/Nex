# cpp-ch17 易错点（Pitfalls）

1. **SFINAE 只发生在「模板参数替换」阶段** —— 仅当错误出现在模板实参推导/替换过程中（如 `enable_if` 的 `::type` 不存在）时才会被视为「替换失败」而被忽略；替换完成后出现的语义错误仍是硬错误。常见误用：把「运行时才能发现的错误」期望被 SFINAE 吞掉。
   ✅ 约束表达式必须放在能参与替换的位置（返回类型、`std::enable_if_t` 默认模板参数、或函数参数），不要写在函数体里。

2. **enable_if 约束位置/条件写错导致两重载都匹配或都不匹配** —— `enable_if<false>::type` 不存在，该重载即从候选集移除；若两个条件不互斥/不完备，会出现歧义或无候选。
   ✅ 用 `std::enable_if_t<cond>` 放在返回类型或最后一个默认模板参数，并保证条件**互斥且完备**（覆盖所有可能的类型）。

3. **if constexpr 的条件必须是编译期常量，且被裁剪分支仍需语法合法** —— `if constexpr(cond)` 中 `cond` 必须是常量表达式，否则编译失败；被丢弃的分支不会被实例化，但**仍要求语法正确**（只是类型不检查）。
   ✅ 用类型 trait（`is_integral_v` 等）作条件；不要把「另一分支类型非法」的代码放进被裁剪分支后还指望它能通过编译。

4. **std::decay 会退化数组/函数/引用/const，与 remove_reference 不同** —— `decay_t<int&>`→`int`，`decay_t<int[3]>`→`int*`，`decay_t<const int>`→`int`。若只想去引用却用了 `decay`，会把 cv 限定与数组也一起退化掉。
   ✅ 按意图选：仅去引用用 `remove_reference` / `remove_cvref`；「像按值传参一样退化」才用 `decay`。

5. **完美转发丢失值类别：没有用 std::forward<T>(x)** —— `template<typename T> void f(T&& x){ g(x); }` 中 `x` 是具名变量（永远是左值），直接 `g(x)` 会永远以左值转发，右值性丢失。
   ✅ 必须 `g(std::forward<T>(x))` 才能还原 `T` 推导出的原始值类别（引用折叠在此发挥作用）。

6. **把函数模板偏特化当类模板偏特化用** —— C++ **不允许函数模板偏特化**（只允许重载与全特化）；试图写 `template<> void f<Widget>(Widget)` 偏特化会编译报错。
   ✅ 函数用「重载 + `enable_if`」或「转发到类模板偏特化」来模拟偏特化；只有类/结构体支持偏特化。

7. **constexpr 函数并非「一定在编译期执行」** —— `constexpr` 表示「可以在编译期求值」；只有在需要编译期常量的语境（数组大小、`static_assert`、用 `constexpr` 变量接收、模板非类型参数）使用时才会真正编译期求值，普通运行时调用仍是运行时。
   ✅ 想强制编译期求值：用 `constexpr` 变量接收或放进 `static_assert`；C++20 可用 `consteval` 强制编译期。

8. **把 `enable_if` 全塞进返回类型**
   多个重载只在返回类型上有 `enable_if` 差异时，签名差异被埋进返回类型，模板实参推导与重载决议的报错会互相纠缠，错误信息动辄几百行、指向完全无关的行。
   ✅ C++20 用 `requires` / `concept` 表达约束；C++17 及以前把条件放到模板参数默认值（`typename = enable_if_t<...>`），可读性差一个量级。

9. **`constexpr` 函数里的 UB 只在编译期被抓**
   同一个 `constexpr` 函数：常量求值时 UB 会报错，运行期调用时 UB **不检查**（越界读、有符号溢出照样静默出结果），于是「编译过了」被误当成「没问题」。
   ✅ 能只在编译期求值就用 `consteval`；确实要运行期分支时用 `std::is_constant_evaluated()` 分开写；测试开 `-fsanitize=undefined,address`。

10. **判断类型前忘了去掉引用与 cv 限定**
   `template <typename T> void f(T&& v)` 里 `std::is_integral_v<T>` 在传入左值 int 时为 false，因为 `T` 被推导成 `int&`。
   ✅ 判断前先 `std::remove_reference_t<T>` 或直接 `std::decay_t<T>`（同时去引用、cv、数组/函数退化）。

11. **以为 SFINAE 能兜住任意失败**
   SFINAE 只对「立即上下文」里的替换失败生效；函数体内或已实例化类模板深处的失败是硬错误，照样报一堆。
   ✅ 把约束写在签名上（模板默认实参 / 返回类型 / concept），不要在函数体里指望「失败就放弃」。

12. **用普通 if 做按类型分支**
   `if (std::is_integral_v<T>)` 的两个分支都会被实例化，不适用的那支立刻报错。
   ✅ 一律用 `if constexpr`，它在编译期裁剪分支，假分支完全不实例化。

13. **函数模板做偏特化**
   写 `template <typename T> void f(std::vector<T>)` 期望偏特化，实际是重载，且与主模板的优先级常常出乎意料。
   ✅ 函数模板不能偏特化（语言规则）。把逻辑转发到一个类模板上做偏特化，再由一层薄函数调用它。

14. **以为 constexpr 函数一定在编译期执行**
   `constexpr` 只是「允许」编译期求值；传运行期变量时照样运行期算，性能预期落空。
   ✅ 必须编译期就用 `consteval`；需要在两种场景下都可用时，用 `std::is_constant_evaluated()` 分别实现。

15. **漏写 std::forward，右值退化成左值**
   `T&& v` 一旦具名就是左值，`inner(v)` 调用的是拷贝而不是移动，性能静默损失。
   ✅ 完美转发两层都要：参数写 `T&&`，传递写 `std::forward<T>(v)`。发现「临时对象却调了拷贝构造」时先查这里。
