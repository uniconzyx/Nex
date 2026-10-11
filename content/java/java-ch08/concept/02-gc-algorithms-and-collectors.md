# 02 · 垃圾回收：如何判定垃圾、四种引用与七种收集器

## 一、谁才是垃圾：引用计数 vs 可达性分析

| 方法 | 原理 | 致命缺陷 |
|---|---|---|
| **引用计数** | 每个对象记一个引用数，归零即回收 | **循环引用**无法回收（`a.next=b; b.next=a`） |
| **可达性分析** | 从 **GC Roots** 出发遍历，**不可达即可回收** | 需要 STW 保证「对象图不变」 |

**JVM 用可达性分析**。`GC Roots` 六类（背下来）：

1. **虚拟机栈**中局部变量表引用的对象（最常考）
2. **本地方法栈**中 JNI 引用的对象
3. **方法区**中**静态变量**引用的对象
4. **方法区**中**常量**引用的对象（如字符串常量池）
5. **所有被 `synchronized` 持有的对象**（锁对象）
6. JVM **内部引用**（基本类型的 Class、常驻异常对象、系统类加载器）

> 注意：**方法区里「类本身」也会被回收**——条件是「该类所有实例已回收 + 类加载器已回收 + `Class` 对象无引用」，这也是热部署/OSGi 能做到的关键。

## 二、四种引用：回收时机不同

| 引用 | 类 | 回收时机 | 典型用途 |
|---|---|---|---|
| **强引用** | 直接赋值 | **永不回收**（除非不可达） | 普通对象 |
| **软引用** | `SoftReference` | **内存不足时**回收 | 内存敏感缓存（图片缓存） |
| **弱引用** | `WeakReference` | **下次 GC 必回收** | `WeakHashMap`、`ThreadLocal` key |
| **虚引用** | `PhantomReference` | 随时可回收，**只能配合 `ReferenceQueue` 感知回收** | 直接内存（`DirectByteBuffer`）回收通知 |

**关键**：软/弱引用必须配合 `ReferenceQueue` 才知道「对象已被回收」，否则只能靠 `get() == null` 轮询。**`ThreadLocal` 内存泄漏**的根源就是：key 是弱引用（会被回收），value 是强引用（跟着 Entry 一起挂在 Thread 的 `ThreadLocalMap` 上）——**Entry 本身不会被回收，value 就泄漏了**。

## 三、三大 GC 算法

| 算法 | 过程 | 优点 | 缺点 | 用在哪 |
|---|---|---|---|---|
| **标记-清除** | 标记存活 → 清除垃圾 | 无需移动，实现简单 | **产生外部碎片**、分配需空闲链表 | CMS |
| **复制** | 内存一分为二，存活对象整体搬到另一半 | 无碎片、分配只需移动指针（Bump） | **浪费一半空间**、存活多时开销大 | 新生代 Eden↔S |
| **标记-整理** | 标记存活 → 存活对象向一端滑动 → 清理边界外 | 无碎片、不浪费空间 | **移动成本高**、需 STW 较长 | 老年代（Serial Old / Parallel Old） |

**分代假说**（Generational Hypothesis）是这一整套设计的地基：**绝大多数对象朝生夕死**（弱分代假说）+ **越老的对象越难死**（强分代假说）。于是：新生代用**复制**（存活少，成本低），老年代用**标记-清除或标记-整理**。

## 四、七种收集器与停顿模型

```
新生代          老年代            特点
Serial          Serial Old        单线程，STW，客户端模式
ParNew          CMS               JDK 8 的主流组合（CMS 已废弃）
Parallel Scavenge  Parallel Old  吞吐量优先（-XX:+UseParallelGC）
───────────────────────────────────────────────────
G1（Region）     同一收集器管全堆    JDK 9+ 默认，可预测停顿（-XX:MaxGCPauseMillis）
ZGC / Shenandoah  同一收集器管全堆  亚毫秒停顿，染色指针 + 读屏障，TB 级堆
```

**核心取舍是「吞吐量 vs 停顿时间」**（`-XX:GCTimeRatio` vs `-XX:MaxGCPauseMillis`）：

- **Parallel**：最大化 `用户时间 / (用户时间 + GC 时间)`，适合**离线批处理**。
- **CMS**：以最短 STW 为目标，用**并发标记**（`初始标记 STW → 并发标记 → 重新标记 STW → 并发清除`），代价是**碎片 + 浮动垃圾 + Concurrent Mode Failure**。
- **G1**：把堆切成**等大 Region**（`-XX:G1HeapRegionSize`），按**回收收益排序**优先回收垃圾最多的 Region（Garbage-First），用 **Remembered Set** 记录跨 Region 引用，用 **SATB**（原始快照）解决并发标记的三色漏标。有 `Young GC` / `Mixed GC` / `Full GC` 三类。
- **ZGC**：**染色指针**（把标记位存在指针的高 4 位）+ **读屏障**（读引用时自愈），使标记/移动/重定位**全部并发**，停顿只与 **GC Roots 数量**相关（与堆大小无关），做到 **< 1ms**。

## 五、三色标记与「漏标」问题

并发标记时对象分三色：**白**（未访问，候选垃圾）、**灰**（已访问但其引用未扫描完）、**黑**（已访问且引用扫描完）。

**漏标的两个必要条件**（同时满足才漏）：
1. **黑对象新增了指向白对象的引用**；
2. **该白对象到灰对象的路径全部断了**（原本能从灰可达）。

对策：
- **增量更新（Incremental Update）**：记录「黑 → 白」的新增引用，重新标记阶段以**黑对象为根**重扫。**CMS 用这个**。
- **原始快照（SATB）**：记录「灰 → 白」的**删除**引用，以**旧快照**为准扫描。**G1 / Shenandoah 用这个**。

## 六、可运行代码：三色标记算法

```java
import java.util.*;

public class Main {
    static final int WHITE = 0, GREY = 1, BLACK = 2;

    record Node(String name) {}

    static int marked = 0;

    /** 从 roots 出发做三色标记，返回不可达（白）节点名。 */
    static List<String> mark(Map<String, List<String>> graph, List<String> roots) {
        Map<String, Integer> color = new HashMap<>();
        for (String k : graph.keySet()) color.put(k, WHITE);
        Deque<String> grey = new ArrayDeque<>();
        for (String r : roots) { color.put(r, GREY); grey.add(r); }
        while (!grey.isEmpty()) {
            String cur = grey.poll();
            System.out.println("  visit grey=" + cur + " -> black");
            for (String nxt : graph.getOrDefault(cur, List.of())) {
                if (color.get(nxt) == WHITE) { color.put(nxt, GREY); grey.add(nxt); }
            }
            color.put(cur, BLACK);
            marked++;
        }
        List<String> white = new ArrayList<>();
        for (Map.Entry<String, Integer> e : color.entrySet())
            if (e.getValue() == WHITE) white.add(e.getKey());
        Collections.sort(white);
        return white;
    }

    public static void main(String[] args) {
        // 对象图：A -> B -> D ; A -> C ; E、F 自成一个环（引用计数回收不掉，可达性分析能）
        Map<String, List<String>> g = new LinkedHashMap<>();
        g.put("A", List.of("B", "C"));
        g.put("B", List.of("D"));
        g.put("C", List.of());
        g.put("D", List.of());
        g.put("E", List.of("F"));
        g.put("F", List.of("E"));

        System.out.println("GC Roots = [A]");
        List<String> dead = mark(g, List.of("A"));
        System.out.println("marked(black) = " + marked);
        System.out.println("unreachable   = " + dead);
        System.out.println("cyclic E<->F collected by tracing: " + dead.containsAll(List.of("E", "F")));
    }
}
```

## 三视角解析

### 🧑‍💻 程序员视角
- **不要调 `System.gc()`**：它只是「建议」，且默认 Full GC，会让 STW 从毫秒级跳到秒级。真要观察 GC，用 `-Xlog:gc*:file=gc.log:time,uptime,level,tags`。
- **选型决策树**：堆 < 4G 且要低延迟 → G1（默认即可）；堆 4~16G 且延迟敏感 → G1 调 `MaxGCPauseMillis`；堆 > 16G 或要求 < 10ms → ZGC；离线吞吐优先 → Parallel。
- **`ThreadLocal` 必须 `remove()`**（尤其线程池场景）：线程复用 ⇒ `ThreadLocalMap` 不释放 ⇒ value 泄漏。规范写法是 `try { ... } finally { tl.remove(); }`。
- **软引用做缓存要小心**：它在内存压力下被清理，可能造成**缓存雪崩式回源**；生产上更常用 Caffeine（W-TinyLFU 淘汰）这类**容量受限**的方案，而不是依赖 GC 时机。
- **`-XX:+HeapDumpOnOutOfMemoryError` 一定要开**，配合 `-XX:HeapDumpPath`，否则现场只剩日志没有堆。

### 🎓 博士生视角
- 可达性分析的**正确性依赖「对象图在标记期间不变」**，因此并发标记必须与用户线程协调——这直接推出**三色标记 + 写屏障**这一整套机制。**读屏障**（ZGC）在**读**时自愈，**写屏障**（G1 SATB / CMS 增量更新）在**写**时记录。
- **SATB 的代价**是「浮动垃圾」：快照外的死对象活过一次 GC；**增量更新的代价**是「重新标记必须重扫黑对象的引用」⇒ 重新标记阶段更长。这就是 **CMS 的 `Remark` 慢、G1 的浮动垃圾多** 的根因。
- **ZGC 停顿与堆大小解耦**的证明要点：染色指针把标记信息放进指针本身，读屏障在**每次引用读**时做「标记/重定位」补偿，于是移动对象不需要改所有引用（不需要 STW 修指针）——**把「更新引用的 O(堆) 工作」摊到 O(访问) 的用户线程上**。
- **分代假说不是定理**而是经验规律；有研究指出在**大内存 + 长生命周期对象为主**的负载下，分代反而有害（跨代引用需要卡表），这也催化了 ZGC 的**非分代→分代**演进（JDK 21 的分代 ZGC 正是重新引入分代）。

### 📚 考研者视角
- 直接对应 **408 操作系统的存储管理**：**可达性分析 ≈ 内存回收的「引用可达」判据**，**标记-清除 ≈ 非紧凑分配**，**标记-整理 ≈ 紧凑（compact）**，**复制 ≈ 双空间/对换**。
- 408 高频考「**外部碎片与内部碎片**」：标记-清除产生**外部碎片**；固定分区产生**内部碎片**。JVM 的 CMS 与 G1 之争，本质就是这两种碎片的工程取舍。
- 常考「**内存回收的时机**」：408 讲「当内存不足时进行回收」→ 对应 JVM 的 **Minor GC 由 Eden 分配失败触发**。
- 记忆锚点：**「引用计数怕环、可达性分析靠根、复制不碎片但费空间、整理不费空间但要移动」**；**软引用『内存不足才回收』、弱引用『下次 GC 就回收』、虚引用『只为感知回收』**。
