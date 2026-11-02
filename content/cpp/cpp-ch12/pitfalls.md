# cpp-ch12 易错点（Pitfalls）

1. **`auto` 丢失引用/const 导致意外拷贝**
   `auto a = getVec();` 拿到的是**副本**而非引用；若想避免大拷贝或要改原对象，应写 `auto&` / `const auto&`。`decltype(auto)` 才能完整保留表达式的引用与 const。
   ✅ 只读大对象用 `const auto&`，要改原对象用 `auto&`，转发返回值用 `decltype(auto)`。

2. **`std::move` 之后继续使用源对象的值**
   `std::move(x)` 只是把 `x` 当右值，**真正的资源转移发生在移动构造/赋值里**，移动后 `x` 处于「有效但未指定状态」。再读 `x.someField()` 可能得到空/垃圾。
   ✅ 移动后只允许「重新赋值 / 析构 / 判空」；不要依赖其值。

3. **移动构造未标 `noexcept` 导致 `vector` 扩容退化成拷贝**
   `std::vector` 重分配时，只有移动构造是 `noexcept` 才敢用移动；否则为保证强异常安全**回退到拷贝构造**，性能翻倍损失。
   ✅ 写移动构造/移动赋值一律加 `noexcept`（只要内部不抛）。

4. **在范围 for 中修改容器导致迭代器失效**
   范围 for 等价于「`begin`…`end` 的迭代器循环」，`__end` 只求值一次；循环内对 `vector` 做 `push_back`/`erase`/`insert` 会让 `++__begin`/解引用成为 UB。
   ✅ 删除用显式迭代器循环 + `it = v.erase(it)` 推进；新增用 `push_back` 后重新取迭代器。

5. **`emplace_back` 传入已存在的对象反而多一次拷贝**
   `emplace_back(existingObj)` 用 `existingObj` **拷贝构造**新元素（ forwarding 把它当左值），并没有「移动」效果，还多了一次构造。
   ✅ 要搬走已有对象用 `push_back(std::move(existingObj))`；`emplace_back` 只用于「直接传构造参数原地造」。

6. **`auto&&` 的误解**
   `auto&&` 是转发引用（不是「万能引用」的别名），它**既能绑左值也能绑右值**：`auto&& x = 左值`→`T&`，`auto&& x = 临时`→`T&&`（并延长临时生命）。常见误用是以为 `auto&&` 一定产生右值引用。
   ✅ 写泛型转发/要在循环里延长临时生命时用 `auto&&`，理解它落入左值时就是左值引用。

7. **`std::string_view` 悬垂**
   `string_view` 不拥有内存，返回局部 `string` 的视图、或绑定到临时 `string` 后再用，都是 UB（悬垂）。
   ✅ 仅在被引用字符串「确定比视图活得久」时用 `string_view`；需长期持有就转 `std::string`。

8. **返回值误用 `std::move` 抑制 RVO**
   `return std::move(local);` 把局部变量变成右值，反而**阻止命名返回值优化（NRVO）**，还多一次移动。
   ✅ 直接 `return local;`，让编译器优先 RVO，失败再走移动。
9. **`auto` 按值默默拷贝大对象** —— `auto x = bigVec;` 拷贝整个容器。正确写法：遍历大对象用 `const auto&`/`auto&`，只读不拷贝。
10. **移动后误读对象内容** —— 移动后对象处于「有效但未指定状态」，读它可能非你预期。正确写法：移动后只重新赋值/析构，不假设其值为空或原值。
11. **`emplace` 意外命中 `initializer_list`** —— `v.emplace_back({1,2})` 可能匹配 `initializer_list` 构造，行为偏离预期。正确写法：歧义时显式构造再传，或用 `v.push_back(T{1,2})`。
12. **结构化绑定的值类别陷阱** —— `auto [a,b] = ...` 按值拷贝；要改原值用 `auto& [a,b]`。正确写法：需修改元素绑定到引用。
13. **`optional` 解引用前未判空** —— `*opt` 在 `nullopt` 时是 UB。正确写法：先 `if (opt)` 或 `opt.has_value()` 再解引用，或用 `opt.value_or(def)`。
14. **范围 for 用 `auto` 改的是副本** —— `for (auto x : vec) x=0;` 原容器不变。正确写法：要改元素用 `auto& x`。
15. **误以为 `std::move` 真的移动了** —— `move` 只是把表达式变成右值，真正移动发生在接收端。正确写法：确保下一步有能吃掉右值的移动构造/赋值，否则它啥也没干。
