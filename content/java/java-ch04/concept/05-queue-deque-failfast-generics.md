# 05 · Queue/Deque、fail-fast（modCount）与泛型集合的擦除影响

## 一、Queue 与 Deque：双端抽象与 ArrayDeque

`Queue` 定义 FIFO 语义（`offer`/`poll`/`peek`），`Deque`（双端队列）在此基础上加 `addFirst/removeLast` 等，既能当队列又能当栈。**`ArrayDeque` 是用循环数组实现的双端队列**，两端增删均摊 O(1)，且无链表节点的堆分配开销，因此**全面优于 `LinkedList` 与遗留的 `Stack`**——官方建议用 `ArrayDeque` 替代 `Stack`（见 `examples/ex09-deque-arraydeque.json`：同一 `Deque` 既能 `push/pop`（栈 LIFO）又能 `offer/poll`（队列 FIFO））。

## 二、实现机制：fail-fast 与 modCount

`ArrayList`/`HashMap`/`LinkedList` 等都维护一个 `protected transient int modCount`（修改计数器）。`add/remove/clear` 等**结构性修改**会令 `modCount++`；`set`（仅改值）不算。

迭代器在 `iterator()` 创建时记录 `expectedModCount = modCount`。每次调用 `next()`：
```java
if (modCount != expectedModCount) throw new ConcurrentModificationException();
```
这就是 **fail-fast（快速失败）**：一旦发现「在迭代期间集合被结构性修改（且不是通过本迭代器的 `remove()`）」，立刻报错，避免在不一致状态下继续产生难排查的错乱结果。

**关键点**：
- fail-fast **不是线程安全机制**，它只在「单线程中错误地边遍历边改」或「多线程无同步修改」时尽早暴露问题，无法保证一定能检测到（存在「遗漏更新」的竞态，详见 JDK 文档）。
- 安全遍历增删的正确写法：① 用 `iterator.remove()`（它会同步 `expectedModCount`）；② Java 8+ 用 `Collection.removeIf(Predicate)`；③ 收集待删集合后 `removeAll`；④ 并发场景用 `CopyOnWriteArrayList` 或 `ConcurrentHashMap`。

见 `examples/ex07-fail-fast.json`：for-each 内用 `list.remove(...)` 触发 `ConcurrentModificationException`；而把删除交给迭代器则可安全进行。

## 三、泛型集合与类型擦除对集合的影响

泛型集合（`List<String>`）在编译期保证类型安全（取出无需强转、误插编译报错）。但**类型擦除**意味着运行时：
- `List<String>` 与 `List<Integer>` 是**同一个 `Class` 对象**（`ArrayList.class`），运行时无法区分元素类型。
- 集合内部实际存的是 `Object`（擦除到上限），`checkcast` 在取出的边界处插入。
- 因此集合「天然」允许通过原始类型/反射绕过类型检查（如 `examples/ex06-...` 在 ch05 演示的：原始类型 `List raw` 可 `add(123)` 进一个声明为 `List<String>` 的列表，运行时才在取出时抛 `ClassCastException`）。这印证了「泛型只防编译期、不防运行期反射/原始类型」的本质。

## 四、工程实践

- 栈/队列优先 `ArrayDeque`；需要线程安全的队列用 `ConcurrentLinkedQueue`/`ArrayBlockingQueue` 等 JUC 实现。
- 遍历中删除务必用迭代器或 `removeIf`，不要手写在 for-each 里 `list.remove`。
- 不要对集合使用原始类型（raw type），否则失去泛型安全检查；`@SuppressWarnings("unchecked")` 只在确有把握时局部使用（ch05 详述）。

## 五、可运行代码

- `examples/ex09-deque-arraydeque.json`：`ArrayDeque` 作栈与队列。
- `examples/ex07-fail-fast.json`：modCount 触发的 fail-fast。
- `examples/ex10-collections-utils.json`：`Collections.sort/binarySearch/frequency/unmodifiableList`。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 用 **`ArrayDeque`** 替代 `Stack`（`Stack` 是遗留类、继承 `Vector`、方法全同步，性能差）；`Deque` 可同时当栈和队列用。
- 迭代中删除元素用 `Iterator.remove()` 或 `removeIf()`，不要直接调容器的 `remove`（会触发 `ConcurrentModificationException`）。
- 想在多线程下遍历安全，用 `ConcurrentHashMap` / `CopyOnWriteArrayList` 这类**弱一致迭代器**容器。

### 🎓 博士生视角
- **fail-fast 靠 `modCount`**：容器维护修改计数，迭代器创建时保存快照 `expectedModCount`，每次 `next()` 校验二者是否一致。它是「**尽力而为的检测**」——不保证一定触发（并发修改可能恰好不被发现），所以**不能当作并发正确性保证**，只能用来尽早暴露 bug。
- `Deque` 的两端操作在设计上都是 O(1)，`ArrayDeque` 用**环形数组**实现（与循环队列同一套下标回绕技巧），因此比 `LinkedList` 更快也更省内存。
- 泛型擦除的后果在这里再次显现：`Set<String>` 与 `Set<Integer>` 运行期是同一类型，因此**不能靠泛型做运行期校验**；反射可以绕过编译期检查（`set` 里混入异类元素直到取出时才 `ClassCastException`）。

### 📚 考研者视角
- **408 直接对应**：**队列与双端队列**的存储与操作、**循环队列**的下标回绕与判空判满。
- 常考：用两个栈实现队列、用队列实现栈，以及循环队列的 `(rear - front + m) % m` 计算。
- 记忆锚点：**fail-fast 靠 `modCount`，是尽力而为的检测**；**`ArrayDeque` 优于 `Stack`**。
