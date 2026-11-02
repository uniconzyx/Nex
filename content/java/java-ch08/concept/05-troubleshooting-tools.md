# java-ch08 · 内存问题排查与工具链

> 承接 `01-运行时数据区`、`02-GC 算法与收集器`、`03-类加载`、`04-调优与排查`。本节把「线上真出问题怎么定位」落到具体命令与判断逻辑上——这是面试和值班都高频考的部分。

## 1. 本节定位

前面讲的是机制，本节讲的是**出事时怎么用工具把机制对应到现场**。没有这一层，参数背得再熟也救不了一次 OOM。

### 2. 堆 OOM 的定位：jmap + MAT

`jmap -histo:live <pid>` 列出存活对象按类占用（含 `live` 会触发 Full GC，低峰期用）；`jmap -dump:format=b,file=heap.hprof <pid>` 导出堆转储，用 MAT（Eclipse Memory Analyzer）按 `Retained Heap` 排序找泄漏源头。注意别在业务高峰随手 `jmap -histo:live`，它会 STW 数秒。

### 3. 元空间 OOM 与类卸载

`Metaspace` 放类元数据，动态代理 / 热部署场景下若 `ClassLoader` 泄漏（被静态缓存或 `ThreadLocal` 持有），类无法卸载，元空间一路涨到 `OutOfMemoryError: Metaspace`。排查看哪个自定义 `ClassLoader` 的 retained heap 异常大，修法是清掉持有它的静态缓存与线程引用。

### 4. 线程泄漏与死锁：jstack

`jstack <pid>` 导出线程栈，搜 `BLOCKED` / `WAITING` 与 `Found one Java-level deadlock` 直接定位死锁双方持有的锁；线程数异常多时检查线程池是否未设上限或被反复创建。

### 5. Arthas 在线诊断

Arthas 能在不重启的情况下 `watch`/`trace` 方法耗时、`jad` 反编译线上类确认生效版本、`ognl` 读运行时字段，适合「不能停机又要查」的场景。它证明了线上类的真实字节码，避免「我以为部署的是这个版本」的误判。

### 6. GC 日志与停顿分析

开启 `-Xlog:gc*:file=gc.log:time` 后，用工具（GCeasy / 自带分析）看「停顿次数、最长 STW、晋升失败」。G1 下频繁 `Mixed GC` 或 `to-space exhausted` 往往指向 `MaxGCPauseMillis` 过紧或 Region 设置不当。

### 7. 容器环境的内存视图（RSS vs -Xmx）

容器内「反复重启但 Java 日志干净」通常是被内核 `OOMKilled`（SIGKILL，无 Java 栈）。看 `RSS` 是否逼近容器 limit，而 `-Xmx` 只是堆上限——元空间、直接内存、线程栈、JVM 自身都算在容器内存里，必须给它们留余量。

### 8. 一套可落地的 JVM 启动参数模板

```
-Xms4g -Xmx4g                 # 堆上下限一致，避免运行期扩容抖动
-XX:MaxMetaspaceSize=512m     # 给元空间封顶，防无限涨
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200      # G1 调这个，不要硬设 -Xmn
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/data/heap.hprof
```

理由：固定堆减少扩容停顿；G1 用停顿目标驱动而非固定新生代；OOM 自动留证便于事后定位。参数没有银弹，必须结合 GC 日志迭代。

## 三视角解析
### 🧑‍💻 程序员视角
堆 OOM 的第一步不是加内存，而是 `-XX:+HeapDumpOnOutOfMemoryError` 拿到 dump，再用 MAT 看「谁持有了最大的对象图」——多数情况是一个静态集合只增不减。元空间 OOM 通常是动态生成类过多（CGLIB 代理、热部署），要限制 `-XX:MaxMetaspaceSize` 并排查类加载器泄漏。线程死锁用 `jstack` 一次就能看到「Found one Java-level deadlock」，比猜快一百倍；线上不方便重启时用 Arthas 的 `watch`/`trace` 直接观测方法入参与耗时。

### 🎓 博士生视角
JVM 内存分区的排查工具是一一对应的：堆用 `jmap`/MAT，元空间用 `jstat -gc` 看 `MC/MU`，线程用 `jstack`，GC 用 `-Xlog:gc*` 或 GCViewer。这些工具的共同前提是「先分类、再定位」——OOM 有「堆溢出、元空间溢出、直接内存溢出、栈溢出、GC overhead limit」多种，盲目加 `-Xmx` 只会把问题推迟。Arthas 这类在线诊断工具的价值在于「不停机观测」，其原理是字节码增强（instrument），代价是轻微性能损耗与类加载器污染风险。

### 📚 考研者视角
面试与实战：
1. **OOM 的类型与定位**：`Java heap space`、`Metaspace`、`Direct buffer memory`、`unable to create new native thread`。
2. **常用命令**：`jps`、`jstat`、`jmap`、`jstack`、`jinfo` 各自的作用。
3. **GC 日志分析**：`Young GC` 频率高说明新生代小或对象晋升快；`Full GC` 频繁要查大对象与内存泄漏。
4. **CPU 100% 排查**：`top -Hp` 找线程 → `printf %x` 转十六进制 → `jstack` 搜 nid。
