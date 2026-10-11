# cpp-ch11 易错点（Pitfalls）

1. **在析构函数里抛异常 —— 可能导致 `std::terminate`**
   若析构在**栈展开期间**被调用（即已有一个异常正在传播），此时析构再抛异常，运行时会立即 `std::terminate`。即使不在展开期，析构抛异常也会让调用方被迫处理"清理失败"，非常危险。
   ✅ 析构函数一律标 `noexcept`（默认即如此），内部任何可能失败的操作要**吞掉并记录日志**，绝不向外 `throw`。

2. **`catch` 按值捕获导致切片（slicing）**
   `catch (std::exception e)` 会把派生异常对象**按基类值拷贝**，派生部分被切掉，`e.what()` 可能丢失派生类的重写，甚至行为变化。
   ✅ 永远 `catch (const std::exception& e)`（引用捕获，零拷贝、保留动态类型）。

3. **`catch(...)` 或空 `catch` 静默吞掉异常**
   ```cpp
   try { risky(); } catch (...) {}   // 异常消失了，问题被掩盖，事后极难排查
   ```
   ✅ 至少要记录日志再决定；若确实要忽略，写明注释说明"此异常已知且安全"。更常见的是捕获后做清理再 `throw;` 重抛。

4. **`noexcept` 函数内仍抛异常 → 直接 `std::terminate`**
   标了 `noexcept` 是给编译器的**契约**：一旦内部 `throw`（含调用了会抛的函数且未捕获），进程直接终止，不会展开恢复。
   ```cpp
   void boom() noexcept { throw 1; }   // 调用即 terminate！
   ```
   ✅ 只在"确实绝不抛"时标 `noexcept`；标准库特殊成员函数在满足条件时自动 noexcept，勿破坏。移动构造/赋值几乎总应 `noexcept`（见 concept 03）。

5. **异常穿越 C 接口 / `extern "C"` / 跨模块边界**
   C 函数（如 `qsort` 的比较回调、pthread 的入口）不知道 C++ 异常；异常从 C 帧"漏过去"会**绕过 C++ 栈展开**，导致对象不析构、资源泄漏，甚至直接 `std::terminate`。
   ✅ 在调用 C 接口前**捕获所有异常并转为错误码/返回状态**；跨 `.so`/`.dll` 抛异常也要谨慎（不同模块可能用不同 unwind 运行时）。

6. **`catch` 顺序写反：基类在前、派生类在后**
   匹配按**第一个**可转换的子句进行；基类写在前面会把所有派生异常"吃掉"。
   ```cpp
   catch (const std::exception&) { ... }   // 写在前面
   catch (const std::runtime_error&) { ... } // 永远到不了！
   ```
   ✅ 派生类 `catch` 必须写在基类 `catch` **之前**。

7. **用 `assert` 代替错误处理（Release 下失效）**
   `assert(p != nullptr)` 在定义 `NDEBUG`（Release）后被**整体删除**，等于没有任何检查；若 `p` 真为空，Release 下直接 UB。
   ✅ 用户/外部可触发的错误用**异常或错误码**处理；`assert` 只用于"开发期捕捉本不该发生的程序员错误"。

8. **异常对象用 `throw new MyErr()`（抛指针）**
   抛指针后必须 `catch (MyErr*)` 且调用方负责 `delete`，极易泄漏，且与标准体系（`catch (const std::exception&)`）不兼容。
   ✅ 抛**值或引用指向的栈对象**（如 `throw std::runtime_error("...")`），`catch` 用 `const` 引用接。
