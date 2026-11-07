# §4 cpp-ch11 实战手记：凯喵带你把异常用「崩」

> 前三节把 try/catch、异常安全、noexcept、assert 讲透了。这一节凯喵把 C++ 异常最容易「泄漏 / 吞掉 / 不抛不报」的 12 个现场摆出来——每个都是资源泄漏和 UB 的入口。

### 现场一：异常对象用 throw new MyErr() 抛指针

凯喵 `throw new MyErr();` 后必须 `catch (MyErr*)` 且调用方负责 `delete`，极易泄漏，且与标准体系（`catch (const std::exception&)`）不兼容。正确：抛**值或引用指向的栈对象**，如 `throw std::runtime_error("...")`，`catch` 用 `const` 引用接。

```cpp
// ❌ 抛指针，谁 delete？
throw new std::runtime_error("x");
// ✅ 抛值，catch 用 const 引用
throw std::runtime_error("x");
catch (const std::runtime_error& e) { }
```

### 现场二：catch 按值接，对象被 slicing

凯喵 `catch (std::exception e)` 按值接，派生类特有的信息在拷贝时被「切片」丢掉。一律用 **`catch (const std::exception& e)`** 引用接，保留动态类型和多态。

```cpp
try { throw Derived(); }
catch (const Base& e) { e.what(); }   // ✅ 引用保留派生类型
// catch (Base e) { }                  // ❌ 切片，丢失派生信息
```

### 现场三：catch 顺序写反，窄的永远进不去

凯喵先 `catch (std::exception)` 再 `catch (std::runtime_error)`，后者成了死代码——基类在前会把派生类一并接走。catch 必须**从最派生到最基类**排，否则派生分支永远触发不到。

```cpp
try { /* ... */ }
catch (const std::runtime_error& e) { }  // ✅ 先窄
catch (const std::exception& e) { }      // ✅ 再宽
```

### 现场四：在析构函数里抛异常，程序直接 terminate

凯喵在析构函数里 `throw`，结果栈展开途中又抛异常，C++ 标准规定此时**直接 `std::terminate`**，进程崩溃。析构函数要么吞掉异常（捕获后记日志），要么标 `noexcept(false)` 但绝对不在栈展开时抛。

```cpp
~Guard() {
    try { cleanup(); }
    catch (...) { /* 记录日志，绝不向外抛 */ }
}
```

### 现场五：没用 RAII，异常跳过释放导致泄漏

凯喵 `lock(); do_work(); unlock();`，`do_work()` 一抛异常，`unlock()` 被跳过，锁永远不释放。资源获取即初始化（RAII）：把资源放进对象，构造拿、析构放，异常安全自动清理。

```cpp
struct LockGuard {
    LockGuard(Mutex& m): m_(m) { m_.lock(); }
    ~LockGuard() { m_.unlock(); }   // ✅ 异常也释放
    Mutex& m_;
};
```

### 现场六：noexcept 函数里抛异常，直接 terminate

凯喵给函数标了 `noexcept` 却在里面 `throw`，一旦抛出直接 `terminate`。`noexcept` 是承诺「绝不抛」，移动构造/移动赋值标了它 STL 才敢用移动优化；不确定就别标，或确保内部不抛。

```cpp
void f() noexcept { throw 1; }   // ❌ 抛即 terminate
void g() { throw 1; }            // ✅ 不标 noexcept
```

### 现场七：用 assert 做运行期参数校验，release 下失效

凯喵 `assert(ptr != nullptr);` 当参数校验，结果 release 编译（NDEBUG）后 assert 整段消失，空指针一路裸奔。assert 只查**内部不变式**；对外参数校验用显式 `if (!p) throw`。

```cpp
assert(invariant_holds());        // ✅ 内部不变式，release 可被优化掉
if (user_ptr == nullptr) throw std::invalid_argument("null");  // ✅ 运行期校验
```

### 现场八：catch (...) 吞掉一切却不知啥错

凯喵 `catch (...) { return -1; }` 把异常吃了，排错时完全不知道发生了什么。至少打印/记录，或重新抛出（`throw;`）交给上层；别静默吞。

```cpp
catch (...) {
    log("unknown error");   // ✅ 至少留痕
    throw;                  // 或重新抛给上层
}
```

### 现场九：在构造函数里抛异常，对象部分构造难清理

凯喵构造函数里中途抛异常，已分配的资源没释放（因为析构不会被调——对象没构造成功）。构造函数要么成功要么抛，资源分配用 RAII 成员（成员析构会自动清理已构造的部分）。

```cpp
struct Widget {
    std::unique_ptr<Res> a = std::make_unique<Res>();  // ✅ 成员 RAII，异常时自动释放
    Widget() { maybe_throw(); }
};
```

### 现场十：异常说明（dynamic exception specification）已废弃

凯喵写 `void f() throw(int);` 想声明只抛 int，这是 C++11 起**已移除**的特性，现代应改用 `noexcept` 或什么都不写。动态异常规格既难用又会因不符而意外 terminate。

```cpp
void f() noexcept;   // ✅ 现代写法
// void f() throw(int);  // ❌ 已废弃
```

### 现场十一：跨 ABI / 跨语言边界抛异常，直接崩

凯喵从 C 接口回调里抛 C++ 异常，或动态库边界抛自定义类型，对方无法 catch，栈损坏。异常**不要跨 ABI / C 边界**；接口层捕获后转错误码返回。

```cpp
extern "C" int api() {
    try { do_cpp(); return 0; }
    catch (...) { return -1; }   // ✅ 边界内消化，转错误码
}
```

### 现场十二：异常成本高就全盘禁用，反而更难维护

凯喵因「异常慢」在全局禁用异常，结果错误码层层 return 检查，漏一处就静默失败。异常在**不抛的路径几乎免费**，只在抛出时贵。用异常表达真正「意外」，普通错误仍可用 `std::optional` / 错误码。

```cpp
// 意外失败用异常
if (!open_file()) throw std::runtime_error("open failed");
// 可预期的空结果用 optional
std::optional<int> find(int k);
```

> 凯喵总结：C++ 异常的坑九成是「抛指针」「slicing」「catch 顺序」「析构抛异常」「noexcept 翻车」。记住抛值接引用、RAII 保平安、析构不抛。把这 12 个现场刻进手感，资源泄漏少一半。

### 现场之外：凯喵的异常五条军规
写 C++ 异常处理，凯喵给自己立了五条军规。第一，抛值接引用：throw 栈对象，catch 用 const 引用，既避免指针泄漏又避免值拷贝的 slicing。第二，析构函数绝对不向外抛，栈展开途中再抛就是 terminate，有风险的操作在析构里吞掉并记日志。第三，资源一律 RAII，锁、文件、连接都交给带析构的对象，异常跳过代码路径也能自动清理。第四，noexcept 是写给人看的承诺，标了就保证不抛，移动构造这类关键函数标了 STL 才会用移动优化。第五，跨 ABI 和 C 边界绝不抛，接口层把异常转成错误码再出去。五条守住，异常就从「灾难」变成「可控的失败」。

### 现场拾遗：异常不是用来吞的
再补一句心态：异常存在的意义是让程序在「做不到」的时候诚实地停下来，而不是悄悄带着错误继续跑。新人最容易犯的错是 catch 之后什么都不做，或者只打一行日志就继续，结果错误被埋进调用链的更深处，最后在完全不相干的地方炸出来，排查时一头雾水。要么在当前层能处理就处理，要么加上下文信息后继续往上抛，千万别无声吞掉。诚实失败比假装成功可靠得多。

### 一句话收尾
凯喵最后提醒：C++ 给了你四种错误处理路径——异常、错误码、optional、断言——不是为了让你随便挑，而是让你按「这件事是不是意外」来选。真正意外、上层才能决定怎么处理的用异常；可预期、调用方应当检查结果的用 optional 或错误码；仅限内部不变式用断言。选错了，代码要么噪音满天飞，要么 silently 带着错继续跑。分清楚「意外」和「预期」，异常处理才算真正用对。

## 三视角解析
### 🧑‍💻 程序员视角
`throw new MyErr()` 抛的是指针，捕获方必须 `delete`，一旦中途再次抛出就泄漏——标准做法是抛值、按 `const&` 捕获。按值捕获会切片：`catch (Base e)` 把派生异常切成基类，丢失派生信息。`catch` 顺序必须「派生在前、基类在后」，否则窄的永远进不去。析构函数里抛异常更危险：栈展开过程中再抛，直接 `std::terminate`，正确做法是把析构里的操作包在 `try/catch` 里吞掉或提供显式的 `close()`。

### 🎓 博士生视角
异常机制依赖「栈展开」（stack unwinding）：抛出后沿调用栈逐层销毁局部对象（调用析构），直到匹配的 `catch`。这带来两个约束：析构函数不能抛（否则展开中再抛导致 terminate）、异常安全需要 RAII 保证（资源在析构中释放，展开时自动清理）。异常安全的四级保证（no-throw、strong、basic、none）是评价接口质量的标准，`std::vector::push_back` 提供的是 strong 保证——失败时容器状态不变，实现靠「先构造新内存、成功后再交换」。

### 📚 考研者视角
面试常考：
1. **异常安全的三个级别**：基本保证（不泄漏、对象有效）、强保证（失败则回滚）、不抛保证（`noexcept`）。
2. **为什么析构函数默认 `noexcept`**：C++11 起析构默认不抛，抛出即 terminate。
3. **`noexcept` 的性能意义**：`vector` 扩容时优先移动而非拷贝，前提是移动构造为 `noexcept`。
4. **异常 vs 错误码**：异常适合「不可恢复且需跨层传播」的错误，热路径与嵌入式常禁用异常。

```text
04-exception-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：异常对象用 throw new MyErr() 抛指针  (cpp)
    |
    v
  [02] 现场二：catch 按值接，对象被 slicing  (cpp)
    |
    v
  [03] 现场三：catch 顺序写反，窄的永远进不去  (cpp)
    |
    v
  [04] 现场四：在析构函数里抛异常，程序直接 terminate  (cpp)
    |
    v
  [05] 现场五：没用 RAII，异常跳过释放导致泄漏  (cpp)
    |
    v
  [06] 现场六：noexcept 函数里抛异常，直接 terminate  (cpp)
    |
    v
  [07] 现场七：用 assert 做运行期参数校验，release 下失效  (cpp)
    |
    v
  [08] 现场八：catch (...) 吞掉一切却不知啥错  (cpp)
    |
    v
  [... 其余 7 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
