# 04 · 内存问题排查与 JVM 调优实战

## 一、四类 OOM 与各自的第一反应

| 错误 | 直接原因 | 第一反应 |
|---|---|---|
| `Java heap space` | 堆不够 / 对象泄漏 | `jmap -histo:live` 看对象 Top、dump 给 MAT 看支配树 |
| `Metaspace` | 类太多（动态代理/CGLIB/热部署反复重建） | `jcmd <pid> VM.metaspace` 看已用类数；查 `-XX:MaxMetaspaceSize` |
| `GC overhead limit exceeded` | 98% 时间在 GC，回收不到 2% 堆 | 本质是**堆太小或真的泄漏**，加堆只是拖时间 |
| `Unable to create new native thread` | 线程数撞上限 | 查是否线程池未复用/未 `shutdown`；`ulimit -u`、`-Xss` |
| `Direct buffer memory` | 直接内存（`ByteBuffer.allocateDirect`）耗尽 | `-XX:MaxDirectMemorySize`；`Netty` 泄漏检测 `-Dio.netty.leakDetection.level=paranoid` |

**栈溢出**（`StackOverflowError`）与堆 OOM 是两回事：前者是**栈帧太深**（递归/正则回溯/深 JSON 嵌套），解法是**改算法/降嵌套**，不是加内存。

## 二、工具链：从「看现象」到「定位对象」

```bash
jps -l                          # 找 pid 与主类
jcmd <pid> VM.flags             # 当前生效的所有参数（含默认值）
jcmd <pid> GC.heap_info         # 各分代/Region 容量与使用量
jcmd <pid> Thread.print         # = jstack，看线程栈与死锁
jstat -gcutil <pid> 1000        # 每秒一次：E/S0/S1/O/M 使用率 + GC 次数/耗时
jmap -histo:live <pid> | head   # 活对象的类直方图（注意会触发一次 Full GC）
jmap -dump:live,format=b,file=heap.hprof <pid>
jinfo -flag MaxHeapSize <pid>   # 查单个参数
```

**MAT 三板斧**：**Dominator Tree**（谁在支配内存）→ **Leak Suspects**（自动报告）→ **Path to GC Roots**（为什么回收不掉）。

**Arthas 常用**：`dashboard`（实时面板）、`thread -n 5`（最忙线程）、`heapdump`、`trace Class method`（方法级耗时）、`watch`、`jad`（反编译确认线上版本）、`sc -d Class`（看类来自哪个 jar/加载器）。

## 三、调参基线（可直接抄的起点）

```bash
java -Xms4g -Xmx4g \                    # 1) 堆固定，避免动态扩缩抖动
     -XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m \
     -XX:+UseG1GC \                     # 2) JDK 9+ 默认，显式写出便于审计
     -XX:MaxGCPauseMillis=200 \         # 3) 目标停顿（软目标，不是硬保证）
     -XX:+ParallelRefProcEnabled \      # 4) 并行处理引用（有大量软/弱引用时收益明显）
     -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/data/dump \
     -Xlog:gc*:file=/data/logs/gc.log:time,uptime,level,tags:filecount=10,filesize=50M \
     -jar app.jar
```

**参数含义与理由（面试要能逐条讲）**：
- `-Xms == -Xmx`：避免堆在运行期反复伸缩（**伸缩本身要 STW**，还会引起 GC 次数波动）。
- `MaxGCPauseMillis` 是**软目标**：G1 通过调整**新生代大小**与**混合回收的 Region 数**来逼近，设得过小会导致**新生代过小 ⇒ Young GC 频率暴涨**（吞吐骤降）。
- **不要设 `-Xmn`**：G1 下固定新生代会**削弱**其自适应能力；且 G1 不再用「固定 Eden/Survivor」的物理划分。
- **不要设 `SurvivorRatio`**：G1 的 Survivor 数量自适应（`-XX:G1HeapRegionSize` 才重要）。
- **`-XX:+UseStringDeduplication`**：G1 专有，对「大量重复长字符串」有效（如日志字段），但它**只在 Young GC 期间**做，且会消耗 CPU。

## 四、四个经典故障案例与定位路径

1. **堆 OOM，但 Top 对象是 `byte[]` 且量大** → 多半是**大文件/大响应体一次性读入**或**直接内存未释放**。检查有没有 `InputStream.readAllBytes()`、有没有把 `ResponseEntity<byte[]>` 缓存住。
2. **`Metaspace` OOM，类数持续增长** → 动态代理无限生成（`CGLIB` 每次 `Enhancer.create` 都产生新类）或**热部署反复建类**。修法是**缓存代理类**（用 `ClassLoader` 维度隔离）或限制部署频率。
3. **`GC overhead limit exceeded` + Full GC 后堆仍满** → **真泄漏**。用 `jmap -dump:live` 后 MAT 的支配树找**到底是哪个 Map / List 在增长**。
4. **响应时间周期性毛刺（P99 突刺）** → 观察 GC 日志与 `jstat` 的 **`FGC` 次数**：若 Full GC 周期性发生，检查是否有 `System.gc()`（`-XX:+DisableExplicitGC` 可屏蔽）、`RMI`/`NIO` 的 DirectMemory 触发、以及 `Metaspace` 扩容。

## 五、可运行代码：用 ManagementFactory 读 GC 计数与内存池

```java
import java.lang.management.*;
import java.util.*;

public class Main {
    static Comparator<MemoryPoolMXBean> byName = Comparator.comparing(MemoryPoolMXBean::getName);

    public static void main(String[] args) {
        MemoryMXBean mem = ManagementFactory.getMemoryMXBean();

        System.out.println("=== heap memory (bytes, machine dependent) ===");
        MemoryUsage h = mem.getHeapMemoryUsage();
        System.out.println("committed > 0 : " + (h.getCommitted() > 0));
        System.out.println("max > 0       : " + (h.getMax() > 0));
        System.out.println("used <= committed : " + (h.getUsed() <= h.getCommitted()));

        System.out.println("=== pools sorted by name ===");
        List<MemoryPoolMXBean> pools = new ArrayList<>(ManagementFactory.getMemoryPoolMXBeans());
        pools.sort(byName);
        for (MemoryPoolMXBean p : pools) System.out.println("  " + p.getName() + " [" + p.getType() + "]");

        System.out.println("=== collectors (counts are machine dependent, names are not) ===");
        List<String> names = new ArrayList<>();
        for (GarbageCollectorMXBean g : ManagementFactory.getGarbageCollectorMXBeans())
            names.add(g.getName());
        Collections.sort(names);
        for (String n : names) System.out.println("  " + n);

        System.out.println("=== heap pool count ===");
        int heapPools = 0;
        for (MemoryPoolMXBean p : pools) if (p.getType() == MemoryType.HEAP) heapPools++;
        System.out.println("heap pools = " + heapPools + " (Eden/Survivor/Old for generational GC)");

        System.out.println("=== runtime ===");
        Runtime rt = Runtime.getRuntime();
        System.out.println("availableProcessors >= 1 : " + (rt.availableProcessors() >= 1));
        System.out.println("freeMemory <= totalMemory : " + (rt.freeMemory() <= rt.totalMemory()));
    }
}
```

## 三视角解析

### 🧑‍💻 程序员视角
- **排查顺序固定成肌肉记忆**：`jps` → `jcmd GC.heap_info` → `jstat -gcutil 1s` → `jstack`（卡顿）或 `jmap -histo:live`（内存）。**先看是否真 GC 问题，再看对象**，不要一上来 dump（大堆 dump 会让服务停数秒）。
- **不要在生产随便 `jmap -histo:live`**：它会触发 **Full GC**。要么用 `-histo`（不带 `live`，不触 GC 但含垃圾），要么在低峰期做。
- **日志比工具更重要**：`-Xlog:gc*` 常开（滚动 + 限额），因为**故障现场的堆往往抓不到**（OOM 时进程已被 kill 或 dump 未开）。
- **K8s 里的坑**：容器内存限制与 JVM 堆是两套账，`-Xmx` 必须留出**元空间 + 直接内存 + 线程栈 + JVM 自身**的空间，否则会被 **OOMKilled**（内核杀，不是 Java 抛 `OutOfMemoryError`，日志里什么都看不到）。JDK 10+ 有 `-XX:+UseContainerSupport`（默认开）能让 JVM 感知 cgroup 限额。

### 🎓 博士生视角
- **`MaxGCPauseMillis` 的可满足性**：G1 用「预测模型」（基于历史 Region 回收耗时）挑选本次回收的 Region 集合，这是一个**在线背包问题**的近似解——目标停顿越小，可选的 Region 越少，于是**回收吞吐下降、Full GC 风险上升**。所以「低延迟」与「吞吐」在 G1 内部也是同一根弹簧的两端。
- **`GC overhead limit exceeded` 的判据**是 JVM 的启发式：**过去一段时间内 GC 时间占比 > 98% 且回收的堆 < 2%**。它是**症状而非病因**——加堆只能延后爆发，根因是**活跃对象集随时间单调增长**（真泄漏）。
- **`OutOfMemoryError` 与 OOMKilled 的语义差别**：前者是 JVM **主动**抛出的可捕获错误（还能打日志、还能 dump）；后者是内核 `cgroup` 的 **SIGKILL**（进程无机会响应）。**可观测性设计上必须区分这两条路径**，否则线上只会看到「容器重启、无日志」。
- **ZGC 的 `-XX:MaxGCPauseMillis` 语义不同**：它不再需要「按目标停顿挑 Region」，停顿基本恒定在亚毫秒，因此这个参数对 ZGC 影响很小——**参数的可迁移性取决于收集器的算法模型**，不能跨收集器照抄。

### 📚 考研者视角
- 直接对应 **408 操作系统的「虚拟存储与页面置换」**：`jstat -gcutil` 的 **GC 次数与耗时 ≈ 缺页次数与缺页处理时间**；**Minor GC ≈ 局部性良好的页替换**；**Full GC ≈ 系统抖动（thrashing）**。
- 408 高频考「**抖动（thrashing）**」的定义与解法（工作集模型 / 降低多道程序度）；JVM 的 `GC overhead limit exceeded` 就是**抖动在 GC 领域的同构现象**——两者都是「把时间都花在换出换入上，真正干活的比例趋近于零」。**这个类比写在答题纸上很加分**。
- 常考「**内存不足的处理**」：408 讲「淘汰页面 / 拒绝服务 / 交换进程」；JVM 对应「GC 回收 / 抛 OOM」。**注意 JVM 没有『拒绝分配』这一档，只有 OOM**。
- 记忆锚点：**「堆满 OOM、栈深溢出、元空间涨类、直接内存用量外」**；**「先看 GC 日志，再 jstat 定时，最后才 dump」**。
