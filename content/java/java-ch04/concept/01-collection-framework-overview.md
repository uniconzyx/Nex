# 01 · 集合框架总览：接口层次、迭代器与泛型集合的类型安全

## 一、理论根基：为什么需要统一的集合抽象

在 Java 之前，开发者用数组、自定义链表、哈希表散落各处，互不相通。`java.util` 集合框架的第一性原理是：**用一组相互继承的接口（而非具体类）来抽象「数据的容器语义」**，让算法（如排序、查找）与具体实现解耦——这正是「面向接口编程」与「算法复用」在语言标准库层面的落地。

体系用两条互不相干的顶级接口切开：
- **`Collection<E>`**：一维「元素集合」，子接口分 `List`（有序可重复）、`Set`（不可重复）、`Queue`/`Deque`（队列/双端队列）。
- **`Map<K,V>`**：键值对，不属于 `Collection`（但它的值视图 `values()`、键集 `keySet()` 是 `Collection`）。

> 设计哲学：接口定义「能做什么」，实现类定义「怎么做、代价多少」。学习集合框架，**先记接口契约，再记实现的复杂度与适用场景**，而不是背 API。

## 二、实现机制：接口如何落到具体类

```
Collection
 ├─ List      → ArrayList（动态数组） / LinkedList（双向链表） / Vector（线程安全但已过时）
 ├─ Set       → HashSet（哈希） / LinkedHashSet（哈希+插入序） / TreeSet（红黑树有序）
 └─ Queue/Deque → PriorityQueue（堆） / ArrayDeque（循环数组双端队列）
Map
 ├─ HashMap / LinkedHashMap / TreeMap / WeakHashMap
 └─ 并发：ConcurrentHashMap / ConcurrentSkipListMap
```

**迭代器（Iterator）是统一遍历协议**：每个 `Collection` 都通过 `iterator()` 暴露一个 `Iterator`，for-each 语法糖正是调用它（`Iterable` 接口）。`Iterator` 的关键方法：
- `hasNext()` / `next()`：遍历；`next()` 内部会检查结构性修改。
- `remove()`：安全删除当前元素（同步 `expectedModCount`）。

**fail-fast 的字段基础**：`ArrayList`/`HashMap` 等维护一个 `modCount`（修改计数）。迭代器创建时记录 `expectedModCount = modCount`，每次 `next()` 先比对，不一致即抛 `ConcurrentModificationException`。这不是线程安全机制，而是「在单线程误改时尽早报错」的调试辅助（详见 concept 05）。

## 三、工程实践：泛型集合带来的编译期类型安全

Java 5 引入泛型后，集合从「装 `Object`、取出要强转」变成了 `List<String>` 这类**参数化类型**。编译器在编译期插入检查与强转（擦除后仍插入 `checkcast`），从而：
- 杜绝了把 `Integer` 误当 `String` 取用的 `ClassCastException`（运行期 → 编译期）。
- 让 API 意图自文档化：`Map<String, List<Integer>>` 一眼可知结构。

`Collections` 工具类提供：排序 `sort`、二分 `binarySearch`、频率 `frequency`、不可变视图 `unmodifiableXxx`、线程安全包装 `synchronizedXxx`。注意 `unmodifiableXxx` 只是「视图不可改」，底层集合仍可改；`synchronizedXxx` 给每个方法加锁，迭代仍需手动同步。

## 四、边界与陷阱

1. **`Arrays.asList(...)` 返回的是固定大小的 `List`**（底层是数组），调用 `add/remove` 会抛 `UnsupportedOperationException`。
2. **`Collection` 与 `Map` 不能相互转型**：`Map` 没有实现 `Collection`，要用 `entrySet()`/`keySet()`/`values()` 桥接。
3. **泛型不可协变**：`List<Integer>` 不是 `List<Number>` 的子类型（语言层面保证类型安全，避免「往 `List<Integer>` 里塞 `Double`」）。
4. **`for-each` 内不能增删集合**（会触发 fail-fast），必须用迭代器或 `removeIf`。

## 五、可运行代码

框架层面的「接口 → 多实现」与迭代器遍历，见 `examples/ex10-collections-utils.json`（工具类）、`examples/ex07-fail-fast.json`（迭代器与 fail-fast）。`examples/ex09-deque-arraydeque.json` 展示 `Deque` 同时充当栈与队列的统一抽象。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **面向接口编程**：声明用 `List` / `Set` / `Map`，构造时才选具体实现，便于替换。
- 注意 **`Map` 不属于 `Collection`**（它是独立的顶层接口），这个层次关系在面试里经常被考。
- 遍历统一用迭代器/增强 for；要按序遍历有序容器（`LinkedHashMap`、`TreeMap`）时别用 `HashMap`。

### 🎓 博士生视角
- 接口层次：`Iterable` → `Collection` → `List`/`Set`/`Queue`，`Map` 独立。**迭代器模式**把「遍历方式」与「容器内部表示」解耦，使同一套遍历代码适配所有容器。
- 泛型提供**编译期类型安全**，但运行期被**擦除**：因此不能 `new T[]`、不能用类型参数做 `instanceof`、`List<String>` 与 `List<Integer>` 在运行期是同一个类。这是为了与 1.5 之前的原始类型代码保持二进制兼容所付的代价。
- 从抽象层次看，这套框架是「同一抽象（集合）的多种实现（策略）」的教科书案例，与数据结构的 ADT 定义完全对应。

### 📚 考研者视角
- **408 数据结构**：集合框架的每个实现都对应一种数据结构（动态数组、双向链表、哈希表、红黑树、堆）——可以把它当作「数据结构在标准库中的落地」来对照记忆。
- 记忆锚点：**`Map` 不是 `Collection`**；**泛型只存在于编译期（擦除）**。
