# §4 cpp-ch01 实战手记：凯喵带你把 C++ 基础用「炸」

> 前三节把类型、引用、auto、string、vector 讲透了。这一节凯喵把 C++ 基础最容易「未定义行为 / 悬垂 / 静默截断」的 12 个现场搬出来——每个都是 debug 到凌晨的代价。

### 现场一：引用绑定到临时对象，离开作用域变悬垂

凯喵写 `const std::string& s = getTemp();` 以为引用延长了临时对象生命。延长只在「引用**直接**绑定临时对象」时成立；若函数返回的是**引用**，临时对象早已销毁，`s` 悬垂。要安全就按值接。

```cpp
std::string getTemp();          // 返回对象
const std::string& f();         // 返回引用
const std::string s1 = getTemp();   // ✅ 拷贝/移动，安全
// const std::string& s2 = f();   // ❌ 悬垂，f 返回的临时已死
```

### 现场二：auto 退化掉引用和 const，副本悄悄产生

凯喵写 `for (auto x : vec)` 想改元素，结果原 vector 纹丝不动——`auto` 按值拷贝。要改元素用 `auto&`；只读大对象用 `const auto&`；要移动用 `auto&&`。auto 不会自动保留引用，必须自己写 `&`。

```cpp
std::vector<int> v = {1,2,3};
for (auto x : v) x = 0;        // ❌ 改的是副本
for (auto& x : v) x = 0;      // ✅ 改的是原元素
for (const auto& x : v) { /* 只读，避免拷贝 */ }
```

### 现场三：有符号与无符号混比，-1 秒变超大正数

凯喵写 `int i = -1; if (i < v.size()) ...`，结果条件为 false。`size()` 返回无符号 `size_t`，`-1` 被转成极大值 `4294967295`，比较直接翻转。混用有/无符号是 UB 温床，统一用 `size_t` 或范围 for。

```cpp
std::vector<int> v(5);
// for (int i = 0; i < v.size(); ++i)  // ❌ 类型不匹配隐患
for (size_t i = 0; i < v.size(); ++i) { }  // ✅ 同类型
for (int x : v) { }                          // ✅ 范围 for 最稳
```

### 现场四：reserve 当成 resize 用，v[0] 直接越界 UB

凯喵 `v.reserve(10)` 后直接 `v[0] = 1`，程序崩溃。`reserve` 只扩**容量**不变**大小**，`size()` 仍是 0，下标访问越界是未定义行为。要长度用 `resize`，要容量用 `reserve`。

```cpp
std::vector<int> v;
v.reserve(10);                 // capacity=10, size=0
// v[0] = 1;                   // ❌ 越界 UB
v.resize(10);                  // ✅ size=10，可下标
v.push_back(1);                // ✅ 或 push_back 增长
```

### 现场五：c_str() 指针跨修改使用，悬垂

凯喵 `const char* p = s.c_str(); s += "x"; printf(p);`，打印出垃圾。`c_str()` 返回的指针在 `s` 被修改（可能扩容搬迁）后失效。C 接口调用要在同一表达式或紧邻作用域内完成，别长期持有。

```cpp
std::string s = "hi";
const char* p = s.c_str();
// s += "!";                   // ❌ 之后 p 可能悬垂
printf("%s\n", s.c_str());     // ✅ 紧邻调用
```

### 现场六：const T& 绑定函数返回的引用不延长生命周期

凯喵 `const std::string& s = factory_ref();`，`factory_ref` 返回引用，临时对象在 return 语句结束即销毁，`s` 悬垂。生命周期延长规则只认「引用直接绑定临时」，经过一层返回值就失效。

```cpp
const std::string& factory_ref();
// const std::string& s = factory_ref();  // ❌ 悬垂
std::string s = factory_ref();            // ✅ 拷贝出来
```

### 现场七：列表初始化才挡窄化，= 初始化静默截断

凯喵 `int x = 3.14;` 以为会报错，结果 x 静默变成 3。用 `=` 的初始化允许窄化（丢精度）；用 `{}` 的列表初始化**禁止窄化**，编译期就抓出来，默认用 `{}` 更安全。

```cpp
int a = 3.14;     // ❌ 静默截断为 3
int b{3.14};      // ✅ 编译报错，挡住窄化
std::vector<int> v{1,2,3};   // ✅ 推荐初始化风格
```

### 现场八：string 拼接用 + 连 char 而不是 string，类型错乱

凯喵 `std::string s = "x" + 'c';` 编译不过——`"x"` 是 `const char[2]`，`'c'` 是 `char`，两边都不是 `std::string`，`+` 不认识。至少一侧是 `std::string` 才能拼接。

```cpp
std::string s = std::string("x") + 'c';   // ✅ 左操作数是 string
s += 'c';                                  // ✅ += 重载可用
// std::string t = "x" + 'c';              // ❌ 无 string 参与
```

### 现场九：迭代器失效，erase 后还用旧迭代器

凯喵边遍历边 `erase`，用旧迭代器继续走，直接崩。`vector` 的 `erase` 会让被删位置之后的迭代器全部失效。正确写法：`it = v.erase(it)` 用返回值续上；或反向遍历。

```cpp
for (auto it = v.begin(); it != v.end(); ) {
    if (*it % 2 == 0) it = v.erase(it);   // ✅ 用返回值续上
    else ++it;
}
```

### 现场十：vector 扩容搬迁，旧指针/引用全废

凯喵持有一个 `&v[0]` 的引用，之后 `push_back` 触发扩容，vector 搬到新内存，引用指向旧地址。扩容后所有指向元素的指针/引用/迭代器失效。需要稳定地址用 `std::list` / `std::deque` / 存索引而非引用。

```cpp
std::vector<int> v{1,2,3};
int& r = v[0];
v.push_back(4);     // 可能扩容，r 悬垂
// 改存下标安全：size_t idx = 0; ... v[idx] ...
```

### 现场十一：用 NULL 而非 nullptr，重载歧义

凯喵写 `f(NULL)` 想传空指针，却调到了 `f(int)` 重载。`NULL` 是整数 0，`nullptr` 才是真正的指针字面量。C++11 起一律用 `nullptr`，类型安全无歧义。

```cpp
void f(int); void f(char*);
f(NULL);     // ❌ 可能选 f(int)
f(nullptr);  // ✅ 明确选 f(char*)
```

### 现场十二：未初始化局部变量，读到随机垃圾

凯喵 `int x; if (cond) x = 1; cout << x;` 有时输出巨大随机数。局部非静态变量**不默认初始化**，走未初始化分支就是 UB。定义即初始化（用 `{}` 还能顺带挡窄化）。

```cpp
int x{};          // ✅ 值初始化为 0
// int x;         // ❌ 未初始化，读它是 UB
```

> 凯喵总结：C++ 基础的坑九成是「未定义行为」——悬垂引用、混用有/无符号、reserve/resize 混淆、迭代器失效、窄化静默截断。把这 12 个现场刻进编译习惯，debug 时间砍半。
