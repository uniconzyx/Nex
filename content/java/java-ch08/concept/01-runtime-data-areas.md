# 01 · 运行时数据区与对象内存布局：栈、堆、方法区各放什么

## 一、五块运行时数据区

JVM 规范把内存划分为五块，**线程私有 / 共享**是理解一切的起点：

| 区域 | 线程 | 存放内容 | 生命周期 | 可能异常 |
|---|---|---|---|---|
| **程序计数器 PC** | 私有 | 当前线程执行的字节码行号（native 方法时为 `undefined`） | 随线程 | 唯一**无** OOM 的区域 |
| **虚拟机栈** | 私有 | 栈帧：局部变量表、操作数栈、动态链接、方法返回地址 | 随线程 | `StackOverflowError`（深度超限）、`OutOfMemoryError`（扩展失败） |
| **本地方法栈** | 私有 | native 方法调用 | 随线程 | 同上 |
| **堆** | **共享** | 对象实例、数组 | 随 JVM | `OutOfMemoryError: Java heap space` |
| **方法区** | **共享** | 类元信息、常量、静态变量、即时编译代码缓存 | 随 JVM | `OutOfMemoryError: Metaspace`（JDK 8+ 元空间在**本地内存**） |

**KD 记忆**：**「两栈一计数私有，堆与方法区共享」**。JDK 8 起**永久代被元空间取代**，字符串常量池从方法区移到**堆**——这是 JDK 7 就开始的迁移的收尾。

### 栈帧四件套
- **局部变量表**：以 **Slot**（32 位）为单位，`long`/`double` 占 2 Slot。实例方法的 slot 0 是 `this`。
- **操作数栈**：字节码的计算工作区，最大深度在编译期算好写进 `Code` 属性。
- **动态链接**：指向运行时常量池中该方法的**符号引用**，运行时解析为直接引用。
- **方法返回地址**：正常返回时 PC 的恢复值；异常返回则靠**异常表**查找 handler。

> **`i++` 与 `++i` 的字节码差异**就在操作数栈上：`i++` 先 `iload` 后 `iinc`（栈里是旧值），`++i` 先 `iinc` 后 `iload`（栈里是新值）。

## 二、堆的分代结构

```
                 ┌──────────── Young ────────────┐   ┌─── Old ───┐
   [ Eden 8 ] [ Survivor0 1 ] [ Survivor1 1 ]        [ Tenured ]
             ↑ Minor GC 复制算法在 S0/S1 间来回复制
```

- **默认比例** `-XX:NewRatio=2`（老年代 : 新生代 = 2:1），`-XX:SurvivorRatio=8`（Eden : 单个 Survivor = 8:1）。
- **对象分配路径**：先尝试 **TLAB**（线程本地分配缓冲，堆内私有小块）→ 分配不下再 CAS 在 Eden 分配 → Eden 满触发 **Minor GC**。
- **大对象**（`-XX:PretenureSizeThreshold`）直接在老年代分配，避免在 Eden/S 间反复复制。
- **晋升年龄** `-XX:MaxTenuringThreshold=15`：对象每熬过一次 Minor GC 年龄 +1；**同龄对象超 Survivor 一半**时按「动态年龄判定」提前晋升。

## 三、对象的内存布局

64 位 HotSpot，**开启指针压缩**（`-XX:+UseCompressedOops`，堆 < 32G 时默认开）后的固定开销：

| 组成 | 大小 | 说明 |
|---|---|---|
| **Mark Word** | 8 B | 哈希码 / GC 年龄 / 锁标志位（无锁→偏向→轻量级→重量级） |
| **Klass Pointer** | **4 B** | 指向方法区类元数据（压缩后）；未压缩 8 B |
| **数组长度** | 4 B | **仅数组对象**有 |
| **实例数据** | 视字段 | 按 `long/double → int/float → short/char → byte/boolean` 排列，尽量填满 8 B |
| **对齐填充** | 0~7 B | 补齐到 **8 B 的整数倍** |

**心算三个**：
- `new Object()`：8（Mark）+ 4（Klass）+ 4（padding）= **16 B**
- `new int[10]`：8 + 4 + 4（length）+ 40（10×4）= 56 → 对齐 **56 B**
- 含 `int a; long b; int c;` 的对象：8 + 4 + 8 + 8 + 4 = 32 → 对齐 **32 B**（字段重排后 `long` 前置）

## 四、逃逸分析与分配优化

JIT 在 C2 阶段做**逃逸分析**（Escape Analysis）：若对象**不逃逸**（只在本方法内使用且不被外部引用），则可做：

- **栈上分配**：对象随栈帧消亡，**不进堆、不劳烦 GC**。
- **标量替换**：把对象**拆成若干局部变量**（如 `Point p` → `int x, int y`），是最主要的收益来源。
- **锁消除**：对不可能被并发访问的对象，抹掉 `synchronized`。

注意：这些是**JIT 的优化结果，不是 JVM 规范要求**，`-XX:-DoEscapeAnalysis` 可关闭，`-XX:+PrintEscapeAnalysis` 可观察。**面试别把「栈上分配」说成必然发生**。

## 五、可运行代码：观察运行时数据区

```java
import java.lang.management.*;
import java.util.*;

public class Main {
    public static void main(String[] args) {
        // 1) 堆 / 非堆内存池：名称由所选收集器决定（默认 G1）
        System.out.println("=== memory pools ===");
        List<String> heap = new ArrayList<>(), nonHeap = new ArrayList<>();
        for (MemoryPoolMXBean p : ManagementFactory.getMemoryPoolMXBeans()) {
            (p.getType() == MemoryType.HEAP ? heap : nonHeap).add(p.getName());
        }
        Collections.sort(heap); Collections.sort(nonHeap);
        System.out.println("heap     : " + heap);
        System.out.println("non-heap : " + nonHeap);

        // 2) 收集器名称
        System.out.println("=== collectors ===");
        for (GarbageCollectorMXBean g : ManagementFactory.getGarbageCollectorMXBeans())
            System.out.println("  " + g.getName());

        // 3) 栈深度：递归到 StackOverflowError（深度机器相关，只输出布尔判据）
        System.out.println("=== stack ===");
        System.out.println("StackOverflowError caught: " + overflows(0));

        // 4) 对象大小公式验证（不依赖 instrumentation，用字段数推导）
        System.out.println("=== layout (formula, 64bit + compressed oops) ===");
        System.out.println("Object      : 8 mark + 4 klass + 4 pad = 16");
        System.out.println("int[10]     : 8 + 4 + 4 + 40 = 56");
    }

    static boolean overflows(int d) {
        try { return overflows(d + 1) > d; }
        catch (StackOverflowError e) { return true; }
    }
}
```

## 三视角解析

### 🧑‍💻 程序员视角
- **排查顺序**：`jps -l` 找 pid → `jcmd <pid> GC.heap_info` 看堆占用 → `jmap -histo:live <pid> | head -30` 看对象 Top → `jmap -dump` 落盘给 MAT 看**支配树**。不要一上来就 dump（大堆会把磁盘打满、STW 数秒）。
- **栈深是工程参数**：`-Xss` 默认 512K~1M，深度递归/正则回溯会先撞栈。写解析器时**优先改成显式栈**，别指望调大 `-Xss`。
- **对象大小影响缓存命中率**：字段顺序 JVM 会重排，但**别为了省 4 字节而牺牲可读性**；真要紧凑就用**基本类型数组**替代对象数组（`int[]` 比 `Integer[]` 省一半以上且无指针跳转）。
- **TLAB 与伪共享**：高并发计数时 `LongAdder` 优于 `AtomicLong`，本质就是**分散到不同缓存行**减少伪共享。

### 🎓 博士生视角
- 运行时数据区是**抽象规范**，HotSpot 的落地是：堆 = 分代 + TLAB；方法区 = 元空间（本地内存，`MetaspaceSize`/`MaxMetaspaceSize`）+ 代码缓存。
- **PC 无 OOM** 的原因：它只存一个 `returnAddress`/行号，大小由指令集与字节码格式固定，不随规模增长。
- **指针压缩的地址算术**：对象地址按 8 字节对齐，于是可用 `base + (compressed << 3)` 表示，32 位可寻址 `4G × 8 = 32G`——这就是「堆超 32G 压缩失效」的数论根据。若开了 `-XX:ObjectAlignmentInBytes=16` 还能把上限推到 64G（以牺牲 16B 对齐的空间浪费为代价）。
- **标量替换的可证明前提**是「对象不逃逸 + 字段可静态定名」，因此**反射/`hashCode()` 未覆写/传给未知方法**都会阻断优化——这也是「无脑 `toString()` 打日志拖慢热路径」的底层原因。
- Mark Word 的**锁状态复用同一 64 位字**：无锁态存 `hashCode(31) + age(4) + biased_lock(1) + tag(2)`；加锁后位含义整体改写为指向 `ObjectMonitor` 的指针——**锁升级本质是「同一个字在不同状态下复用」**。

### 📚 考研者视角
- 直接对应 **408 操作系统「内存管理」与「程序的链接与装入」**：JVM 的**虚拟机栈 ≈ 用户栈**、**堆 ≈ 动态存储区**、**方法区 ≈ 代码段 + 数据段的合并抽象**。
- 常考点：**栈是线程私有、堆是进程（JVM）共享**——与 OS 里「栈私有、堆共享」**口径完全一致**，可用 OS 知识直接迁移。
- 408 会考**堆的分配算法**（首次适应 / 最佳适应 / 最坏适应 / 邻近适应）与**碎片问题**；JVM 的 TLAB/CAS 分配对应「分配策略」，而 GC 的标记-整理对应「紧凑化消除外部碎片」。
- 记忆锚点：**「PC 不 OOM、栈会溢出、堆会满、元空间会涨」**；**对象头 8B + 类指针 4B（压缩）+ 8B 对齐**。
