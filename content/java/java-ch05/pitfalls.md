# 本章避坑指南

1. **finally 里写 return** —— finally 的 return 会覆盖 try/catch 的 return，甚至静默吞掉 try 中抛出的异常（`examples/ex03-finally-return.json` 实证：tricky() 返回 2 而非 1）。正确：finally 只做清理，绝不 return，也不要改即将返回的变量。

2. **用异常做普通控制流** —— 抛异常要 `fillInStackTrace` 遍历整个调用栈，比分支慢几个数量级。在高频路径用异常做「提前退出/参数校验返回」会成为性能杀手。正确：用返回值、Optional、或显式状态判断表达正常控制流。

3. **丢失异常根因** —— 捕获底层异常后只打印或重新 `throw new RuntimeException(msg)` 而不传 cause，导致排查时看不到真正的底层错误。正确：用带 cause 的构造器包装（`examples/ex04-exception-chain.json`），保留 `getCause()` 链路。

4. **裸 try/finally 中 finally 抛异常掩盖主异常** —— 与 TWR 不同，裸 try/finally 里若 finally 抛异常，try 中的异常会被直接丢弃。正确：优先用 try-with-resources（它把关闭异常放入 suppressed），或手动 `addSuppressed`。

5. **泛型擦除导致的「运行时类型丢失」误判** —— 以为 `List<String>` 与 `List<Integer>` 是不同类型，或在泛型里 `new T[]` / `instanceof T`。运行时二者是同一 `Class`（`examples/ex06-generic-erasure.json` 实证）。正确：靠类型令牌或超类型令牌恢复信息，避开擦除限制。

6. **PECS 用反导致无法读写** —— 对「只生产」的集合用 `? super`（无法可靠读）、对「只消费」的集合用 `? extends`（无法写入），编译即失败（`examples/ex05-pecs.json` 详解）。正确：生产者 extends、消费者 super。

7. **滥用 @SuppressWarnings("unchecked")** —— 包住大段代码会掩盖真正危险的未受检强转。正确：在最小作用域、且确有把握时局部抑制，并加注释说明安全理由（`examples/ex07-suppress-warnings.json`）。

8. **误以为桥接方法可被普通代码调用** —— 泛型子类重写的桥接方法（`setData(Object)`）由编译器合成、仅供多态转发，普通代码不应直接依赖；反射遍历方法时需用 `isBridge()` 过滤（`examples/ex09-bridge-method.json` 实证）。

9. **`catch (Exception e)` 吞掉一切** —— 把 `RuntimeException`、`Error`（含 `OutOfMemoryError`）全兜住，连 NPE 都被静默吞，排错无门且掩盖真 bug。应只 catch 能合理处理的异常，其他的让它上抛。

10. **构造函数里抛异常却没释放半初始化资源** —— 构造失败对象未完全建立，若持有文件/连接等需释放的资源，要在 `finally` 或 try-with-resources 里释放，否则泄漏且难以定位。

11. **`finally` 里的异常覆盖 try 异常** —— try 抛 A、finally 也抛 B，A 会被 B 屏蔽而丢失，根因难查。finally 只做清理且不抛；多异常要保留用 `Throwable.addSuppressed`。

12. **泛型方法类型推断不如预期** —— `List<String> x = foo()` 当 `foo` 缺乏上下文时推断不出 `String`；需要显式 `<String>foo()` 或借助目标类型。不要假设编译器总能猜对。

13. **数组与泛型不兼容** —— 不能 `new T[]`、不能 `List<String>[]`，数组是协变且运行时擦除后类型不安全；用 `ArrayList` 或 `Array.newInstance` + 强转替代。

14. **`instanceof` 对泛型类型无效** —— `obj instanceof List<String>` 编译不过（运行时类型擦除），只能 `instanceof List`；元素具体类型要另行检查，否则会有堆污染告警。

15. **异常被用于正常控制流** —— 用异常做「找不到就跳」的分支，性能（栈轨迹构建）与可读性双输。用返回值/`Optional` 表达「可能不存在」，异常只留给真正的意外。
