# cpp-ch16 易错点（Pitfalls）

1. **忘记 join/detach 导致 terminate**
   `std::thread` 析构时若仍 `joinable()`（既没 join 也没 detach），标准规定调用 `std::terminate()` 直接崩溃。常见诱因：线程对象在作用域末尾析构前忘了处理。
   ✅ 启动线程后立刻规划生命周期：要么 `join`，要么 `detach`（并确保引用对象活得够久）；或直接用 `std::jthread`（析构自动 join）。

2. **按值捕获/传引用导致悬垂**
   `std::thread t([&]{ use(local); });` 或把局部变量引用传进线程，若线程晚于 `local` 析构才运行，访问已销毁对象是 UB；`async` 的 lambda 同理。
   ✅ 用 `std::ref` 时需确保生命周期覆盖线程；更稳妥是**按值捕获**或 `std::move` 所有权（如 `shared_ptr`）。

3. **死锁：两把锁顺序不一致**
   线程 A 先锁 m1 再锁 m2，线程 B 先锁 m2 再锁 m1，形成循环等待，双双卡死。
   ✅ 所有线程按**同一顺序**加锁；或用 `std::lock(m1, m2)` / `std::scoped_lock`（一次性安全获取多锁，标准保证不死锁）。

4. **`volatile` 误当同步原语**
   `volatile` 只禁止编译器优化重排/缓存到寄存器，**不提供线程间原子性与 happens-before**，不能替代 `atomic`/`mutex`。在 C++ 里 `volatile` 不等于 Java 的 `volatile`。
   ✅ 多线程共享变量一律用 `std::atomic` 或 mutex 保护；`volatile` 只用于内存映射 IO 等场景。

5. **condition_variable 未用谓词导致虚假唤醒 bug**
   `cv.wait(lk);` 醒来后不验证条件就继续，一旦遭遇**虚假唤醒**或「被 notify 但条件仍未真」，就读到未就绪状态 → 逻辑错乱。
   ✅ 永远用带谓词的 `cv.wait(lk, pred)`，或 `while(!pred) cv.wait(lk);`。

6. **数据竞争：未加保护地 `++` 共享计数**
   `counter++` 是「读-改-写」三步，非原子；多线程并发会丢失更新，结果不确定（每次运行可能不同）。
   ✅ 用 `std::atomic<int>` 的 `fetch_add`，或用 `mutex` 保护临界区。

7. **`std::async` 默认策略的意外同步执行**
   `std::async(task)` 默认策略是 `async | deferred`，实现**可能选择 deferred**——`get()` 时就在**调用线程同步执行**，根本没有并行。依赖并行提速的代码会「看起来没并发」。
   ✅ 需要真并行时显式写 `std::async(std::launch::async, task)`。
