# 03 · finally 与 return 的执行顺序陷阱、异常链

## 一、理论根基：finally 的语义是「无论怎样都执行」

`finally` 的设计意图是「清理代码必须运行」，与是否抛异常、是否 return 无关。但它的执行时机与返回值的交互，**是 Java 语义里最容易写错、也最常被追问的细节**。

## 二、实现机制：字节码层面的顺序

方法返回前，JVM 保证 finally 块一定执行。关键陷阱在「finally 里也有 return」：

```java
static int tricky() { try { return 1; } finally { return 2; } }   // 返回 2
```
字节码逻辑：try 先计算出返回值 `1` 并暂存到局部变量，准备返回；但进入 finally 后 finally 自身的 `return 2` **重新设置返回值**，最终方法返回 2。即 **finally 的 return 会覆盖 try/ catch 的 return**。若 finally 没有 return，只是修改了某个局部变量：

```java
static int withValue() { int x = 10; try { return x; } finally { x = 20; } }  // 返回 10
```
try 已将 `x` 的当前值（10）暂存，finally 改的是另一份引用/副本，不影响已确定的返回值——所以返回 10。结论：**不要在 finally 里写 return，也不要在 finally 里改即将返回的变量并指望生效**。

正常清理（无 return）时，finally 在 return 表达式求值之后、方法真正退出之前执行，这正是「关闭资源」的安全时机。

见 `examples/ex03-finally-return.json`：两个方法的真实输出分别为 `2` 与 `10`。

## 三、异常链（cause）：保留根因

早期 Java 抛异常常丢失根因（「caused by」缺失）。`Throwable` 提供 `initCause(Throwable)` 与带 `cause` 参数的构造器，形成**异常链**：高层业务异常 `ServiceException` 包装底层 `IllegalStateException`，调用者通过 `getCause()` 一路回溯根因。这是诊断分布式/多层系统的关键。

```java
throw new ServiceException("failed to load user", rootCause);
// rootCause.getMessage() 给出真正的底层错误
```

见 `examples/ex04-exception-chain.json`：`cause=java.lang.IllegalStateException: db connection lost` 被完整保留。

## 四、suppressed 与 cause 的配合

- **cause**：异常「为什么发生」（根因链），纵向。
- **suppressed**：异常「发生时还有哪些附属异常被压制」（如关闭资源的失败），横向。
二者共同保证「一次失败能还原完整现场」，是成熟异常设计的标志。

## 五、工程实践

- 清理逻辑放 finally 或 TWR（优先 TWR）；绝不在 finally 写 return。
- 捕获底层异常时，用自定义业务异常包装并传入 cause，而非吞掉或只打印。
- 用日志框架记录完整链路（`log.error("...", e)` 会自动打印 cause 与 suppressed）。

## 六、边界与陷阱

1. **finally 的 return 会吞掉 try 中的异常**：若 try 抛异常而 finally 有 return，异常被静默丢弃（不再抛出）——极隐蔽的 bug。
2. **finally 抛异常会掩盖 try 异常**：此时 try 的异常变成 suppressed（仅 TWR 有此保护；裸 try/finally 中 finally 异常会直接抛出并掩盖 try 异常）。
3. **不要用异常做控制流**（见 concept 02 性能成本）。

## 七、可运行代码

- `examples/ex03-finally-return.json`：finally 覆盖 return 与值不变的实证。
- `examples/ex04-exception-chain.json`：异常链 cause 的保留。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **绝不要在 `finally` 里写 `return`**：它会覆盖 `try` 里的返回值（也覆盖异常），是最隐蔽的一类 bug。
- `finally` 只做资源清理；业务逻辑放外面。
- 自定义异常务必带上 `cause`（`super(msg, cause)`），否则排障时只有最外层错误，看不到根因。

### 🎓 博士生视角
- 执行序：`try` 的 `return` 会**先求值返回表达式并暂存**，然后执行 `finally`，最后才真正返回。因此 `finally` 里修改局部变量**不会**影响已求值的返回值，但 `finally` 里的 `return`（或抛异常）会**覆盖**整个返回过程。这是「控制流展平」时最容易出错的地方。
- 异常链（`initCause` / 构造器传 `cause`）保留了「A 因为 B、B 因为 C」的**因果链**，是分布式系统与框架排障的核心信息；丢失 cause 等于丢失根因。
- 异常的性能成本主要在**栈快照**：`Throwable` 构造时调用 `fillInStackTrace()` 遍历调用栈。JDK 7+ 提供 `writableStackTrace=false` 用于「预分配、无栈信息」的高频异常（如控制流用的异常）。
- 从语言设计看，`finally` 是「结构化的清理钩子」，与 C++ 的析构、Python 的 `with`、Go 的 `defer` 目的相同，但各自绑定在不同的语言机制上（作用域 / 对象生命周期 / 函数返回）。

### 📚 考研者视角
- 与**编译原理**的「控制流分析与展平」对应：`try/catch/finally` 在字节码中通过**异常表（exception table）**描述「哪段代码的哪个区间由哪个处理器接管」，这正是控制流图的显式化。
- 常考概念题：「`finally` 与 `return` 的执行顺序」「异常链的作用」。
- 记忆锚点：**`finally` 里的 `return` 会覆盖 `try` 的返回值**；**异常必须保留 cause**。
