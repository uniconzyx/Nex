# 03 · SFINAE / enable_if 与 C++20 concept

## 一、SFINAE：替换失败不是错误

SFINAE（Substitution Failure Is Not An Error）指：在模板实参替换过程中发生的失败**不视为硬错误**，而是简单地把该模板从重载候选集中移除。利用这一点，可以「按类型特征挑选重载」。

`std::enable_if<Cond, T>::type` 在 `Cond` 为真时提供 `type=T`，为假时无 `type` 成员，触发替换失败→该重载被剔除。

```cpp
template <typename T>
std::enable_if_t<std::is_integral_v<T>, int> dispatch(T) { return 1; }
template <typename T>
std::enable_if_t<!std::is_integral_v<T>, int> dispatch(T) { return 2; }
```

## 二、C++20 concept：可读的约束

`concept` 把「类型必须满足的一组要求」命名并复用；`requires` 子句直接表达约束，重载决议时约束不满足的版本被丢弃——意图比 SFINAE 清晰得多。

```cpp
template <typename T>
concept Integral = std::is_integral_v<T>;
template <typename T> requires Integral<T> int f(T) { return 1; }
template <typename T> requires (!Integral<T>) int f(T) { return 2; }
```

### 🧑‍💻 程序员视角
- SFINAE 实战：写「只对可迭代类型启用 `print`」「只对数值类型启用 `mean`」的泛型函数，避免对 `std::string` 误调用。
- 最大痛点：SFINAE 报错信息像天书（几百行模板回溯），且 `enable_if` 语法冗长、条件易写错。
- 因此 C++20 强烈推荐 `concept`：约束可读、错误信息直接说「不满足 Integral」，且能组合（`Integral && !FloatingPoint`）。老代码无法升 C++20 时再退回 SFINAE。

### 🎓 博士生视角
- SFINAE 本质：模板替换是一个「可能失败的模式匹配」过程，失败时编译器回退到「尝试其他候选」，而非中止——这是重载决议的**软失败**机制。
- `enable_if` 是 SFINAE 的「人工触发」手段：通过让 `::type` 在条件为假时消失，人为制造替换失败。它依赖「替换发生在返回类型/默认模板参数」这一时机。
- `concept` 在语言层把「约束」提升为一等公民：约束参与**偏序与重载决议**，且可推导、可组合，是 SFINAE 的形式化封装，并非新机制而是更好的语法糖衣。

### 📚 考研者视角
- 面试标准问法：「什么是 SFINAE？」「`enable_if` 怎么用来约束模板？」「concept 解决了 SFINAE 的什么问题？」
- 易错口径：SFINAE 只发生在**替换阶段**，函数体内的错误不是 SFINAE；两个 `enable_if` 条件必须**互斥且完备**，否则歧义或全失败。
- 高频对比题：`enable_if` vs `concept`——后者可读性更好、错误信息更友好、可组合，是 C++20 推荐写法。

---

## 三、requires 表达式与约束组合

`requires` 既能做**简单约束**（`requires Integral<T>`），也能做**复合约束**（`requires { {expr} -> concept; }`），检查某个表达式是否良构、返回类型是否满足 concept。

### 🧑‍💻 程序员视角
- 实际项目里常用标准库 concept：`std::integral`、`std::floating_point`、`std::range`、`std::invocable`，少自己造轮子。
- 约束放 `template<Integral T>` 还是 `requires Integral<T>` 都行；返回类型位置写 `requires` 还能和 `auto` 配合做缩写函数模板（`void f(Integral auto x)`）。

### 🎓 博士生视角
- `requires` 表达式在编译期检查「语法良构性 + 类型关系」，它把「鸭子类型」正式化为可被编译器验证的契约，是 concept 表达力的核心。
- 约束满足关系构成**偏序**：更具体的 concept 在重载决议中优先，这与模板偏特化的偏序一致，是统一的设计哲学。

### 📚 考研者视角
- 标准问法：「`requires` 表达式能检查什么？」「标准库提供了哪些常用 concept？」
- 易错口径：`concept` 是 C++20 特性，需 `-std=c++20`；老标准（如面试常考的 C++11/14/17 代码）只能用 SFINAE/enable_if 实现等价约束。

---

## 四、三视角小结

| 主题 | 程序员 | 博士生 | 考研者 |
|---|---|---|---|
| SFINAE | 按 trait 选重载 | 替换软失败 | 替换阶段才生效 |
| enable_if | 条件易写错 | 人工触发替换失败 | 条件互斥且完备 |
| concept | 可读/可组合 | 约束一等公民 | C++20 特性 |
