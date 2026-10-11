# 01 · 异常体系总览：Throwable 的二分与受检/非受检

## 一、理论根基：异常是一种「错误信号的控制流」

大多数语言把错误当返回值或特殊值处理；Java 把「发生了什么」建模为一个**对象层次**，并通过编译器强制区分「必须处理」与「可选择处理」，从而把错误处理的纪律前移到编译期。`Throwable` 是唯一能被 `throw` 抛出的根类型，其下分两支：

```
Throwable
 ├─ Error          （非受检）严重系统错误：OutOfMemoryError / StackOverflowError
 └─ Exception
     ├─ RuntimeException 及其子类（非受检）：NullPointerException / IllegalArgumentException ...
     └─ 其余 Exception      （受检）：IOException / SQLException ...
```

## 二、实现机制：编译期的「受检」检查

**受检异常（checked）**指 `RuntimeException` 与 `Error` 之外的所有 `Exception`。编译器规则：一个方法若可能抛出受检异常（或调用了声明受检异常的方法），则调用方**必须**二选一——`try/catch` 捕获，或在本方法签名用 `throws` 继续上抛，否则编译失败。`Throwable`、`Error`、`RuntimeException` 及其子类则是**非受检（unchecked）**，编译器不强制处理。

> 这本质上是语言在「可恢复的外部故障（如文件不存在）」与「编程错误（如空指针）」之间做的分类：前者调用方「应当知情并恢复」，后者是 bug、不该被强制 catch 掩盖。

## 三、受检异常的调用方契约与函数式接口的冲突

受检异常的设计初衷很美，但与 **lambda / 函数式接口** 正面冲突：`Runnable.run()`、`Callable.call()`（仅 `call` 允许）、`Comparator.compare()` 等接口方法**签名没有 `throws`**，于是一个内部抛受检异常的表达式无法放进 lambda——编译器直接拒绝。例如：

```java
// 编译错误：Stream 的 map 接受 Function，其 apply 不声明受检异常
files.stream().map(f -> Files.readAllLines(f)).toList(); // IOException 无法抛出
```

业界解法：① 用 `RuntimeException` 包装（如 `UncheckedIOException`）；② 用「 sneaky throw」技巧把受检异常当非受检抛出；③ 直接定义**非受检的业务异常**继承 `RuntimeException`。这也是《Effective Java》与现代框架（Spring 等）倾向「对绝大多数业务异常使用非受检异常」的原因：**异常类型表达的是语义而非强制处理义务**。

## 四、工程实践

- 自定义业务异常：需要被框架统一拦截的非受检异常继承 `RuntimeException`；需要强制调用方处理的才继承 `Exception`（受检）。
- 不要用异常做普通控制流（见 concept 02 的性能成本）。
- 捕获要具体：优先捕获最具体的异常，避免 `catch (Exception e)` 一刀切吞掉 `Error` 与线程中断 `InterruptedException`。

## 五、边界与陷阱

1. **`catch` 顺序**：子类异常必须写在父类之前，否则编译报错（不可达代码）。
2. **`Throwable` 不是都能恢复**：`Error` 通常不应捕获（JVM 可能已处于不稳定状态）。
3. **`InterruptedException` 被吞**：捕获后应 `Thread.currentThread().interrupt()` 恢复中断状态，否则破坏中断协议。

## 六、可运行代码

`examples/ex01-checked-vs-unchecked.json`：受检 `IOException` 必须 try/catch（或 throws），非受检 `IllegalArgumentException` 无需声明即可抛出。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 受检异常必须 `try/catch` 或写进 `throws`；能不改签名就别滥用受检异常（尤其在 lambda 里，`Function` 不允许抛受检异常，用起来很别扭）。
- 三条纪律：**不要吞异常**（至少记日志）、**不要用异常做正常控制流**、**自定义异常要带 cause**。
- `catch` 顺序必须**从具体到宽泛**，否则宽泛的会先接住导致编译报错（不可达 catch）。

### 🎓 博士生视角
- 体系：`Throwable` → `Error` / `Exception`；`Error`（如 `OutOfMemoryError`、`StackOverflowError`）表示 JVM 层面的严重问题，**通常不应捕获**；`Exception` 再分受检（必须处理）与非受检（`RuntimeException`，可不处理）。
- 受检异常是 Java 独有的**类型系统层面的契约**——方法签名即契约的一部分。它的代价在于与函数式接口、`Stream`、lambda 的组合很差（这些接口没有 `throws` 声明），这也是后来 API 设计普遍倾向非受检异常的原因。
- 异常的开销主要在 `fillInStackTrace()` 的**栈快照**（遍历并记录调用栈），而不是「抛出」这一动作本身；高频路径上可以用预分配异常或关闭栈记录来缓解。

### 📚 考研者视角
- 与**软件工程**的「异常处理策略」「错误处理设计」对应，是简答题素材。
- 若考程序设计语言，常考「受检异常与运行时异常的区别」「异常与错误码的取舍」。
- 记忆锚点：**`Error` 不捕获、受检必须处理**；**受检异常与函数式接口天然冲突**。
