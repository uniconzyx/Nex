# 本章避坑指南

1. **只重写 equals 不重写 hashCode** —— 放进 `HashMap`/`HashSet` 后「找不到」。两个逻辑相等的键产生不同哈希码、落到不同桶，`get`/`contains` 失效（`examples/ex08-generic-key-equals-hashcode.json` 实证）。正确：用同一组字段成对重写 `equals`/`hashCode`，优先 `record` 或 `Objects.hash`。

2. **用可变对象做 HashMap 的键** —— 放入后修改参与 `hashCode` 的字段，桶位随之改变，再 `get` 按新哈希找桶，旧对象「凭空消失」。正确：键必须不可变（String/Integer/record 或 final 字段）。

3. **for-each 遍历时调用 `list.remove(...)`** —— 结构性修改令 `modCount` 与迭代器的 `expectedModCount` 不一致，下次 `next()` 抛 `ConcurrentModificationException`（`examples/ex07-fail-fast.json` 实证）。正确：用 `iterator.remove()` 或 `removeIf`。

4. **误以为 LinkedList 比 ArrayList 快** —— 链表随机访问 `get(i)` 是 O(n) 且节点分散、缓存不友好，实测遍历比 ArrayList 慢数十倍（`examples/ex02-list-traversal-perf.json` 实证）。正确：默认用 `ArrayList`；只在「已知节点处 O(1) 增删且几乎不随机访问」时用 LinkedList。

5. **把 `Arrays.asList(...)` / `List.of(...)` 当可变列表用** —— 二者返回的是固定大小/不可变列表，调用 `add`/`remove` 抛 `UnsupportedOperationException`。正确：需要可变列表用 `new ArrayList<>(List.of(...))` 拷贝一份。

6. **依赖 HashSet/HashMap 的迭代顺序** —— 哈希集合的迭代顺序受 hash 种子随机化影响，跨版本/运行不保证一致。正确：需要有序用 `LinkedHashSet`（插入序）或 `TreeMap/TreeSet`（排序）。

7. **认为 fail-fast 等于线程安全** —— `ConcurrentModificationException` 只是单线程误改时的调试辅助，存在竞态「遗漏更新」，无法保证一定能检测到。正确：多线程场景用 `ConcurrentHashMap`/`CopyOnWriteArrayList` 等并发容器，而非依赖 fail-fast。

8. **对 `Arrays.asList(...)` 的结果做 `add` / `remove`**
   它返回的是 `Arrays` 内部的固定大小视图，`add` / `remove` 抛 `UnsupportedOperationException`；`set` 却是允许的，于是「有时候能改有时候不能改」更让人迷惑。
   ✅ `new ArrayList<>(Arrays.asList(...))` 要可变；要不可变就用 `List.of(...)`（Java 9+），语义明确且拒绝一切修改。

9. **遍历集合时直接 `list.remove(x)` → `ConcurrentModificationException`**
   foreach 底层是迭代器，结构性修改会让 `modCount` 与迭代器持有的 `expectedModCount` 不一致，下一次 `next()` 即抛异常（单线程也会抛，名字有误导性）。
   ✅ 用 `Iterator.remove()`；或用 `list.removeIf(pred)`；或先收集待删元素再 `removeAll`。

10. **`Integer` 自动装箱缓存误当全局相等** —— 只缓存 -128~127，超出范围是不同对象，`==` 比地址必 false；在集合里用 `==` 比对元素会漏判。✅ 比较值一律用 `equals`，别依赖缓存区间。
11. **`Collections.sort` 后忘了它原地改原列表** —— `sort` 是原地排序（返回 void 或仍是原引用），有人接了返回值又用原引用，误以为得到新列表。✅ 要不可变副本先 `new ArrayList<>(...)` 再 sort。
12. **把 `subList` 当独立 List 修改导致原列表异常** —— subList 是视图，对原列表结构性修改后再用 subList 抛 `ConcurrentModificationException`。✅ 需要独立副本用 `new ArrayList<>(list.subList(a,b))`。
13. **`PriorityQueue` 的 iterator 不保证有序** —— 只有 `poll` 出队才维持堆序，直接遍历打印是堆内部数组顺序，看着像「没排序」。✅ 要全排序用 `List.sort`，别信迭代器顺序。
14. **把 `HashMap` 当线程安全用** —— 并发 `put` 可能丢数据或死循环（旧版本扩容时），靠「偶尔没出问题」蒙混。✅ 并发场景用 `ConcurrentHashMap`，别裸用 `HashMap`。
15. **`removeIf` / `replaceAll` 在多线程并发下仍不安全** —— 它们基于 `Iterator.remove` 只保证单线程遍历安全，多线程并发改同一集合照样崩。✅ 多线程改用并发容器或在外部加锁。
