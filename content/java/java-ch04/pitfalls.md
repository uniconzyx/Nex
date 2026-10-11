# 本章避坑指南

1. **只重写 equals 不重写 hashCode** —— 放进 `HashMap`/`HashSet` 后「找不到」。两个逻辑相等的键产生不同哈希码、落到不同桶，`get`/`contains` 失效（`examples/ex08-generic-key-equals-hashcode.json` 实证）。正确：用同一组字段成对重写 `equals`/`hashCode`，优先 `record` 或 `Objects.hash`。

2. **用可变对象做 HashMap 的键** —— 放入后修改参与 `hashCode` 的字段，桶位随之改变，再 `get` 按新哈希找桶，旧对象「凭空消失」。正确：键必须不可变（String/Integer/record 或 final 字段）。

3. **for-each 遍历时调用 `list.remove(...)`** —— 结构性修改令 `modCount` 与迭代器的 `expectedModCount` 不一致，下次 `next()` 抛 `ConcurrentModificationException`（`examples/ex07-fail-fast.json` 实证）。正确：用 `iterator.remove()` 或 `removeIf`。

4. **误以为 LinkedList 比 ArrayList 快** —— 链表随机访问 `get(i)` 是 O(n) 且节点分散、缓存不友好，实测遍历比 ArrayList 慢数十倍（`examples/ex02-list-traversal-perf.json` 实证）。正确：默认用 `ArrayList`；只在「已知节点处 O(1) 增删且几乎不随机访问」时用 LinkedList。

5. **把 `Arrays.asList(...)` / `List.of(...)` 当可变列表用** —— 二者返回的是固定大小/不可变列表，调用 `add`/`remove` 抛 `UnsupportedOperationException`。正确：需要可变列表用 `new ArrayList<>(List.of(...))` 拷贝一份。

6. **依赖 HashSet/HashMap 的迭代顺序** —— 哈希集合的迭代顺序受 hash 种子随机化影响，跨版本/运行不保证一致。正确：需要有序用 `LinkedHashSet`（插入序）或 `TreeMap/TreeSet`（排序）。

7. **认为 fail-fast 等于线程安全** —— `ConcurrentModificationException` 只是单线程误改时的调试辅助，存在竞态「遗漏更新」，无法保证一定能检测到。正确：多线程场景用 `ConcurrentHashMap`/`CopyOnWriteArrayList` 等并发容器，而非依赖 fail-fast。
