# 02 · try-with-resources 与 AutoCloseable：字节码展开、异常抑制与性能成本

## 一、理论根基：资源的「获取即释放」契约

任何持有外部资源（文件、连接、锁）的对象都面临一个问题：**无论成功还是异常，都必须释放**。手写 `try/finally` 容易在多个资源、且关闭本身也抛异常时写出既丑陋又丢异常的代码。`AutoCloseable` 把「释放」抽象成一个方法 `void close() throws Exception`，`try-with-resources`（TWR）把它与「作用域结束自动调用」绑定。

## 二、实现机制：编译器如何展开 TWR

对以下代码：
```java
try (R1 r1 = new R1(); R2 r2 = new R2()) { r1.use(); }
```
编译器在字节码里大致展开为：把每个资源提升为**隐式 final 局部变量**，try 块正常或异常退出时，**按声明逆序**调用 `close()`。逆序的原因是资源间常有依赖（如先关外层流再关内层流）。异常处理的精妙之处在于**抑制（suppressed）**：

- 若 try 主体抛异常 `A`，而某个 `close()` 又抛异常 `B`，**`A` 被作为主异常抛出**，`B` 不会覆盖它，而是通过 `A.addSuppressed(B)` 挂在 `A` 上，可用 `A.getSuppressed()` 取得。这避免了「关闭异常把真正的业务异常吞掉」。
- 若多个 `close()` 都抛异常，第一个 `close` 的异常作为 suppressed 挂到主异常，其余依次挂载。

见 `examples/ex08-suppressed.json`：主体抛 `work failed`，关闭抛 `close failed`，后者进入 `getSuppressed()`。逆序关闭见 `examples/ex02-try-with-resources.json`（A 先于 B 打开，关闭时 B 先关、A 后关）。

## 三、异常的性能成本：fillInStackTrace 的栈快照

`Throwable` 构造时会调用 **`fillInStackTrace()`**：遍历当前线程的整个调用栈、把每一帧拷贝进一个 `StackTraceElement[]`。这意味着**抛一次异常 ≈ 一次重量级栈遍历**，比一次普通方法调用慢几个数量级（可达微秒级、且不可被 JIT 内联优化得像分支那样轻）。经验法则：

- **异常只用于「异常路径」**，绝不作为正常控制流（如用异常退出双层循环、用异常做参数校验返回）——在高频路径上这会成为性能杀手。
- 若确定不需要栈轨迹，可重写 `fillInStackTrace()` 返回 `this`（快速异常），但会损失调试信息。
- 现代 JVM 对「热异常」有一定优化（如共享栈帧），但代价仍显著高于分支判断。

## 四、工程实践

- 所有可关闭资源（流、连接、Channel、`Statement`）一律用 TWR，不要用裸 `try/finally`。
- 资源初始化本身抛异常（如文件不存在）时，TWR 不会调用 `close`（因为对象没拿到），直接抛初始化异常，符合直觉。
- 禁止在 `close()` 中再抛受检异常掩盖问题；必要时用 suppressed 机制保留。

## 五、边界与陷阱

1. **`close()` 不能抛受检异常却想报告**：`AutoCloseable.close()` 声明 `throws Exception`，TWR 已能处理，无需额外包装。
2. **TWR 变量是隐式 final**：不能在块内重新赋值资源变量。
3. **多个资源顺序敏感**：依赖顺序写错会抛 `NullPointerException` 于关闭阶段，难以排查。

## 六、可运行代码

- `examples/ex02-try-with-resources.json`：多资源逆序关闭。
- `examples/ex08-suppressed.json`：主异常与 suppressed 异常的保留。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 对象实现 `AutoCloseable` 就该用 try-with-resources；多资源用分号分隔，**关闭顺序是声明的逆序**（栈式）。
- 别再手写 `finally { if (r != null) r.close(); }`：既啰嗦又容易漏判空，而且会**吞掉主异常**。
- 需要访问关闭时抛出的异常，用 `getSuppressed()` 取——它不会覆盖主异常。

### 🎓 博士生视角
- 编译器把 try-with-resources 展开为 `try { ... } finally { res.close(); }` 的等价形式，但做了关键增强：若 `close()` 抛异常而 try 块中已有异常在传播，则 close 的异常被**抑制（suppressed）**并附加到主异常上。
- 这解决的正是经典陷阱：`finally` 里的 `close()` 抛异常会**覆盖**掉 `try` 中的原始异常，导致根因丢失。抑制机制让「根因 + 后续失败」同时可见，这体现了「**在不破坏主错误信息的前提下追加**」的异常设计原则。
- 资源关闭顺序是**逆序**（后申请的先释放），这与栈的 LIFO、RAII 的析构顺序一致——依赖关系上「后创建的可能依赖先创建的」，因此必须后创建的先销毁。
- 与 C++ RAII 对比：Java 把「确定性的资源释放」从语言级（析构器）搬到了语法级（try-with-resources），因此必须显式书写作用域，而 C++ 靠对象生命周期自动完成。

### 📚 考研者视角
- 与 408 **资源管理与死锁预防**（有序申请、逆序释放是从「循环等待」条件入手的经典手段）在思想上一致。
- 若考程序设计语言，常考「RAII 与 finally 的对比」「资源泄漏的成因」。
- 记忆锚点：**try-with-resources 逆序关闭 + 异常被 suppressed**（不覆盖主异常）。
