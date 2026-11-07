# §6 java-ch04 实战手记：凯喵带你把集合框架用「出事」

> 前面五节把 List / Map / Set / Queue 的原理拆透了。这一节不复习原理，凯喵直接把线上最容易炸的 12 个现场搬出来，边踩坑边改。读的时候别觉得自己「都懂」——集合的坑往往就在「以为懂了」的地方。

### 现场一：ArrayList 扩容不是「翻倍」，是 1.5 倍

凯喵第一次看 `ArrayList.grow()` 源码时被自己骗了：直觉里数组扩容都是翻倍，结果 JDK 写的是 `int newCapacity = oldCapacity + (oldCapacity >> 1)`。右移一位就是除以 2，所以 10 → 15 → 22 → 33。为什么是 1.5 而不是 2？翻倍会让尾部浪费接近一半空间；1.5 倍在「空间浪费」和「扩容次数」之间取了折中。

```java
// JDK ArrayList.grow() 简化版
private int newCapacity(int minCapacity) {
    int oldCapacity = elementData.length;
    int grow = oldCapacity >> 1;            // 1.5 倍 = 老 + 老/2
    int newCapacity = oldCapacity + grow;
    if (newCapacity - minCapacity < 0)      // 还是不够就直接顶到 minCapacity
        newCapacity = minCapacity;
    return newCapacity;
}
System.out.println(10 >> 1);  // 5  -> 10+5=15
```

### 现场二：foreach 里 remove，单线程也会炸

凯喵曾在一个单线程批处理里写 `for (String s : list) if (s.isEmpty()) list.remove(s);`，本地跑得好好的，一上压测就 `ConcurrentModificationException`。原因：foreach 其实是 `Iterator`，每次 `next()` 都会比对 `modCount` 和自己的 `expectedModCount`。你直接 `list.remove` 改了 modCount，下一次 `next()` 立刻发现「票不对」，抛异常。名字带 Concurrent 纯属误导。

```java
List<String> list = new ArrayList<>(Arrays.asList("a", "", "b"));
// ❌ 错误：foreach 内结构性修改
for (String s : list) {
    if (s.isEmpty()) list.remove(s);   // 抛 ConcurrentModificationException
}
// ✅ 正确：用 Iterator.remove 或者 removeIf
list.removeIf(String::isEmpty);
```

### 现场三：LinkedList 当队列用，别用 get(i)

凯喵见过有人拿 `LinkedList` 做「随机访问」然后 complain 慢。LinkedList 的 `get(i)` 是 O(n) 从头遍历；它真正擅长的是**头尾增删 O(1)**。如果你要的是队列/栈语义，请用 `offer` / `poll` / `peek`，而不是 `get`。

```java
Deque<String> dq = new LinkedList<>();
dq.offerLast("task1");   // 入队尾 O(1)
dq.offerFirst("urgent"); // 入队首 O(1)
String head = dq.pollFirst();  // 出队首 O(1)
// ❌ dq.get(5000) 在 10 万元素里是 O(n) 灾难
```

### 现场四：HashMap 的键必须是「不可变」且守契约

凯喵带新人时最爱问：用 `new Point(x, y)` 当 HashMap 的 key，存进去后再改 x，还能 get 出来吗？答案是大概率 get 不到——因为 hashCode 变了，定位到的桶已经不是当初那个。所以**键必须不可变**（用 `String`、`Integer`，或自己写 `final` 字段的类），并且 `equals` 和 `hashCode` 必须同时正确重写。

```java
class BadKey {
    int x;
    BadKey(int x) { this.x = x; }
    public int hashCode() { return x; }
}
Map<BadKey, String> m = new HashMap<>();
BadKey k = new BadKey(1);
m.put(k, "v");
k.x = 2;                       // 改了 key 的可变字段
System.out.println(m.get(k)); // null —— hashCode 变了，桶找错
```

### 现场五：HashSet 去重靠的是 hashCode + equals，不是 ==

凯喵排查过一个「为啥两个内容一样的对象没去重」的 bug：同事只重写了 `equals` 忘了 `hashCode`，结果两个相等对象落进不同桶，HashSet 当成了两个。记住铁律：**equals 相等 → hashCode 必须相等；但 hashCode 相等 ≠ equals 相等**（哈希冲突允许）。

```java
class User {
    String id;
    User(String id) { this.id = id; }
    @Override public boolean equals(Object o) {
        return o instanceof User u && id.equals(u.id);
    }
    // ❌ 漏了 hashCode -> HashSet 不去重
    @Override public int hashCode() { return id.hashCode(); }  // ✅ 补上
}
```

### 现场六：TreeMap/TreeSet 要求键可比较

用 `TreeMap` 当缓存，塞进去一个没实现 `Comparable` 的对象，第一次 `put` 就 `ClassCastException`。凯喵的教训：如果你不确定键会不会比较，老老实实用 `HashMap`；要排序就用 `Comparator` 显式传进去，别指望对象自己会排。

```java
Map<String, Integer> tm = new TreeMap<>();        // 键是 String，天然 Comparable
tm.put("banana", 3); tm.put("apple", 1);
System.out.println(tm.keySet()); // [apple, banana] 已排序

// 自定义键排序：传 Comparator
Map<Event, Long> byTime = new TreeMap<>(
    Comparator.comparingLong(e -> e.ts));
```

### 现场七：PriorityQueue 不是「自动排序的 List」

凯喵面试必考：PriorityQueue 的 `poll()` 永远返回最小（或最大）元素，但 `iterator()` 遍历它**不保证有序**，只有出队才维护堆。想拿「前 K 小」就反复 `poll` K 次；想全排序就别用它，用 `List.sort`。

```java
PriorityQueue<Integer> pq = new PriorityQueue<>();
pq.addAll(Arrays.asList(5, 1, 3, 2, 4));
while (!pq.isEmpty()) System.out.print(pq.poll()); // 12345 出队有序
// ❌ 但 System.out.println(pq) 打印的是堆内部数组，顺序乱
```

### 现场八：Arrays.asList 返回的是固定大小视图

凯喵踩过最阴的坑：`List<String> l = Arrays.asList("a","b"); l.add("c");` 直接 `UnsupportedOperationException`。因为 `Arrays.asList` 返回的是数组的**固定大小包装**，只支持 `set` 不支持 `add`/`remove`。要可变就 `new ArrayList<>(...)`，要不可变就用 `List.of(...)`（Java 9+）。

```java
List<String> fixed = Arrays.asList("a", "b");
fixed.set(0, "x");                 // ✅ 允许
// fixed.add("c");                 // ❌ UnsupportedOperationException
List<String> mutable = new ArrayList<>(fixed);  // ✅ 真可变
List<String> immutable = List.of("a", "b");     // ✅ 真不可变
```

### 现场九：subList 是「视图」，改原列表会失效

`list.subList(0, 3)` 返回的不是一个新 List，而是原 List 的一段**视图**。你对原 List 做了结构性修改（add/remove），再碰 subList 就会 `ConcurrentModificationException`。凯喵建议：要独立副本就 `new ArrayList<>(list.subList(...))`。

```java
List<Integer> src = new ArrayList<>(Arrays.asList(1,2,3,4,5));
List<Integer> view = src.subList(0, 3);  // 视图
src.add(99);                             // 结构性修改原列表
// view.get(0);                          // ❌ 抛 ConcurrentModificationException
List<Integer> copy = new ArrayList<>(src.subList(0, 3)); // ✅ 拷出独立副本
```

### 现场十：Vector / Hashtable 基本别用了

凯喵见过老项目满屏 `Vector` 和 `Hashtable`。这俩给每个方法都加 `synchronized`，并发读多写少时性能极差，而且「方法级同步」挡不住复合操作（比如 `if (!map.containsKey(k)) map.put(k, v)` 仍非原子）。要线程安全请选 `ConcurrentHashMap`；要偶尔同步用 `Collections.synchronizedList`。

```java
// ❌ 老古董，全方法 synchronized
Vector<Integer> v = new Vector<>();
// ✅ 现代替代
List<Integer> sync = Collections.synchronizedList(new ArrayList<>());
Map<String, Integer> chm = new ConcurrentHashMap<>();
```

### 现场十一：泛型不能装基本类型，用包装类

凯喵新人写 `List<int>` 编译不过，问为什么。因为泛型类型擦除后盒子里放的是 `Object`，而 `int` 不是 `Object`。必须用 `Integer`。代价是装箱拆箱有微小开销，但换来类型安全——别为了省这点性能退回 `List` 裸类型（会失去编译期检查）。

```java
// List<int> bad;            // ❌ 编译错误
List<Integer> good = new ArrayList<>();
good.add(1);                // 自动装箱 int -> Integer
int x = good.get(0);        // 自动拆箱
```

### 现场十二：遍历 + ConcurrentHashMap 的弱一致性迭代器

最后凯喵提醒：`ConcurrentHashMap` 的迭代器是**弱一致性**的——遍历途中别的线程改了 map，你可能看不到新条目，也可能看到被删的，但**绝不会抛异常**。这点和 `HashMap` 在遍历中修改就炸完全相反，用之前心里要有数。

```java
ConcurrentHashMap<String, Integer> m = new ConcurrentHashMap<>();
m.put("a", 1);
for (Map.Entry<String, Integer> e : m.entrySet()) {
    m.put("b", 2);          // 遍历中修改，不抛异常（弱一致性）
    System.out.println(e.getKey());
}
```

> 凯喵总结：集合框架的坑 90% 来自「把视图当副本」「把遍历当锁」「把可变对象当键」。把这 12 个现场刻进肌肉记忆，面试和上线都少挨两顿批。

## 三视角解析
### 🧑‍💻 程序员视角
`ArrayList` 扩容是 `oldCapacity + (oldCapacity >> 1)`，即 1.5 倍而不是翻倍——频繁添加时预估容量 `new ArrayList<>(n)` 能省掉多次复制。`foreach` 里 `remove` 会抛 `ConcurrentModificationException`：迭代器维护 `modCount`，结构性修改与预期不符就快速失败；正确做法是 `iterator.remove()` 或 `removeIf`。`LinkedList` 当队列用没问题，但 `get(i)` 是 O(n)，循环 `get` 会退化成 O(n²)。

### 🎓 博士生视角
集合框架的设计是「接口分层 + 实现可选」：`Collection` 下分 `List`/`Set`/`Queue`，`Map` 独立成支。`ArrayList` 用连续数组，随机访问 O(1)、中间插入 O(n)；`LinkedList` 用双向链表，头尾操作 O(1)、随机访问 O(n)；`HashMap` 用「数组 + 链表/红黑树」，Java 8 起链表长度超过 8 且桶数 ≥ 64 时树化，把最坏 O(n) 降到 O(log n)。这些选择背后都是「访问模式决定数据结构」的同一原则。

### 📚 考研者视角
笔试高频：
1. **各集合的底层结构**：`ArrayList`（数组）、`LinkedList`（双向链表）、`HashMap`（数组+链表+红黑树）、`TreeMap`（红黑树）。
2. **`HashMap` 的扩容**：负载因子 0.75、容量为 2 的幂、扩容后元素「要么原位、要么原位+旧容量」。
3. **`ConcurrentModificationException`**：快速失败机制与 `modCount`。
4. **`ArrayList` 与 `LinkedList` 的选型**：随机访问多选前者，头尾增删多选后者。

```text
06-collection-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：ArrayList 扩容不是「翻倍」，是 1.5 倍  (java)
    |
    v
  [02] 现场二：foreach 里 remove，单线程也会炸  (java)
    |
    v
  [03] 现场三：LinkedList 当队列用，别用 get(i)  (java)
    |
    v
  [04] 现场四：HashMap 的键必须是「不可变」且守契约  (java)
    |
    v
  [05] 现场五：HashSet 去重靠的是 hashCode + equals，不是 ==  (java)
    |
    v
  [06] 现场六：TreeMap/TreeSet 要求键可比较  (java)
    |
    v
  [07] 现场七：PriorityQueue 不是「自动排序的 List」  (java)
    |
    v
  [08] 现场八：Arrays.asList 返回的是固定大小视图  (java)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
