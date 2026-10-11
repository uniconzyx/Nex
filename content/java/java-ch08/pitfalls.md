# java-ch08 · 陷阱清单：JVM 面试与线上排查最容易错的十件事

1. **把「准备阶段」当成「初始化阶段」** —— 准备阶段只给静态变量**赋零值**：`static int a = 10;` 在这一步是 `a = 0`，赋 10 要等**初始化**执行 `<clinit>()`。但 `static final int A = 10;`（编译期常量）在准备阶段就已直接是 10。**这是类加载题最高频的送分/送命点**。

2. **说「`Class.forName` 与 `loadClass` 等价」** —— `Class.forName(String)` 默认**初始化**（`initialize=true`），`ClassLoader.loadClass(String)` 默认**只加载不初始化**。JDBC 老代码 `Class.forName("com.mysql.cj.jdbc.Driver")` 就是靠前者触发静态块注册驱动；换成 `loadClass` 驱动不会注册。

3. **以为「对象一定分配在堆上」** —— 逃逸分析 + 标量替换可以让**不逃逸对象拆成局部变量**甚至栈上分配，**完全不走堆**。但这是 **JIT 优化结果、不是规范保证**，`-XX:-DoEscapeAnalysis` 可关闭。答题时务必加「在满足逃逸分析前提下、由 JIT 决定」。

4. **用引用计数来解释 JVM 的回收** —— JVM 用**可达性分析**，不是引用计数。引用计数的致命伤是**循环引用**（`a.next=b; b.next=a`）永远不归零。可以用一个 E↔F 互指的用例自己在代码里验证：可达性分析能回收，引用计数不能。

5. **认为「软引用会被及时回收做缓存」** —— 软引用只在**内存不足**时回收，时机由 GC 决定、不可控；依赖它做缓存会导致**回收后集中回源**（缓存雪崩）。生产缓存用**容量受限**的方案（Caffeine / Redis），不用 GC 时机。

6. **`ThreadLocal` 用完不 `remove()`** —— Entry 的 key 是弱引用会被回收，但 **value 是强引用且 Entry 挂在 `ThreadLocalMap` 上**，线程复用时 value 泄漏，且 value 若持有 `Class` 会连带**阻止类卸载**（Metaspace 一路涨）。线程池场景**必须** `try/finally` 里 `remove()`。

7. **把 `-Xmn` 和 `SurvivorRatio` 套到 G1 上** —— G1 用 **Region** 划分，新生代大小**自适应**（由 `MaxGCPauseMillis` 驱动）；硬设 `-Xmn` 会削弱自适应能力。G1 真正该调的是 `-XX:MaxGCPauseMillis` 与 `-XX:G1HeapRegionSize`。

8. **在生产随手 `jmap -histo:live` 或 `jmap -dump`** —— 二者都会**触发 Full GC**（`live` 语义），大堆下 STW 数秒，直接把服务打挂。要么用不带 `live` 的 `-histo`（含垃圾但不动 GC），要么在低峰期操作。

9. **把容器 `OOMKilled` 当成 Java 的 `OutOfMemoryError`** —— `OutOfMemoryError` 由 JVM **主动抛出**（可捕获、可 dump、有日志）；容器内存超限是内核 **SIGKILL**（进程当场死，**没有任何 Java 日志**）。看到「容器反复重启但日志干净」要立刻查 **RSS vs `-Xmx` 的差值**：元空间 + 直接内存 + 线程栈 + JVM 自身都算在容器内存里。

10. **以为「打破双亲委派」是 bug** —— 它是**刻意设计**：SPI 用**线程上下文类加载器**解决「接口在核心库、实现在应用库」的依赖倒置；Tomcat 用**每 WebApp 一个加载器 + 先自己后委派**实现应用隔离；OSGi 用网状委派实现模块热替换。答题时要说出**为什么要打破**，而不是只背「可以重写 `loadClass`」。

11. **混淆 `ClassNotFoundException` 与 `NoClassDefFoundError`** —— 前者是**受检异常**，`Class.forName`/`loadClass` 在**加载阶段**找不到类时抛出；后者是 **`Error`**，在**链接或初始化阶段**找不到（典型：编译通过但运行缺依赖、静态块抛异常导致后续初始化失败）。**一个能被 `catch (Exception)` 抓到，一个不能**。

12. **只看堆不看「类加载器」定位内存泄漏** —— 热部署/动态代理场景下，泄漏往往表现为**某个自定义 `ClassLoader` 及其加载的整片类无法回收**。MAT 里要看 **`ClassLoader` 的 retained heap**，而不是只看对象数 Top；修法通常是**清理静态缓存 + 保证没有线程/`ThreadLocal` 持有该加载器**。
