# 本章避坑指南

1. **finally 里写 return** —— finally 的 return 会覆盖 try/catch 的 return，甚至静默吞掉 try 中抛出的异常（`examples/ex03-finally-return.json` 实证：tricky() 返回 2 而非 1）。正确：finally 只做清理，绝不 return，也不要改即将返回的变量。

2. **用异常做普通控制流** —— 抛异常要 `fillInStackTrace` 遍历整个调用栈，比分支慢几个数量级。在高频路径用异常做「提前退出/参数校验返回」会成为性能杀手。正确：用返回值、Optional、或显式状态判断表达正常控制流。

3. **丢失异常根因** —— 捕获底层异常后只打印或重新 `throw new RuntimeException(msg)` 而不传 cause，导致排查时看不到真正的底层错误。正确：用带 cause 的构造器包装（`examples/ex04-exception-chain.json`），保留 `getCause()` 链路。

4. **裸 try/finally 中 finally 抛异常掩盖主异常** —— 与 TWR 不同，裸 try/finally 里若 finally 抛异常，try 中的异常会被直接丢弃。正确：优先用 try-with-resources（它把关闭异常放入 suppressed），或手动 `addSuppressed`。

5. **泛型擦除导致的「运行时类型丢失」误判** —— 以为 `List<String>` 与 `List<Integer>` 是不同类型，或在泛型里 `new T[]` / `instanceof T`。运行时二者是同一 `Class`（`examples/ex06-generic-erasure.json` 实证）。正确：靠类型令牌或超类型令牌恢复信息，避开擦除限制。

6. **PECS 用反导致无法读写** —— 对「只生产」的集合用 `? super`（无法可靠读）、对「只消费」的集合用 `? extends`（无法写入），编译即失败（`examples/ex05-pecs.json` 详解）。正确：生产者 extends、消费者 super。

7. **滥用 @SuppressWarnings("unchecked")** —— 包住大段代码会掩盖真正危险的未受检强转。正确：在最小作用域、且确有把握时局部抑制，并加注释说明安全理由（`examples/ex07-suppress-warnings.json`）。

8. **误以为桥接方法可被普通代码调用** —— 泛型子类重写的桥接方法（`setData(Object)`）由编译器合成、仅供多态转发，普通代码不应直接依赖；反射遍历方法时需用 `isBridge()` 过滤（`examples/ex09-bridge-method.json` 实证）。
