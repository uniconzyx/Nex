# 04 · final 与 Object 基类：不可变语义与语言根基

## 一、理论根基：final 是"约束即契约"

`final` 在 Java 里是"只能一次"的语义约束，但**作用于不同目标含义不同**：

- **final 类**：不能被继承。动机一是**安全/不可变保证**（如 `String`、`Integer` 都是 final，杜绝子类篡改行为），二是给 JIT 更强的**去虚拟化与内联**优化线索。
- **final 方法**：不能被子类重写 → 编译为静态绑定（`invokespecial`/`final` 虚调用被去虚拟化），性能更好，但牺牲扩展性。
- **final 变量**：只能赋值一次（"常量"）。**关键误区**：`final` 修饰的是**引用**，不是对象——`final List<T> l = ...;` 只保证 `l` 不再指向别的对象，列表内容仍可增删改。真正的不可变需要对象自身不可变（见 ch02 的 record / 不可变类）。

## 二、实现机制与 Object 核心方法

所有类都隐式继承 `java.lang.Object`，它的几个方法是整个对象模型的地基：

- `getClass()`：返回运行期 `Class` 对象（`final native`），是多态判断与反射的入口；`a.getClass() == b.getClass()` 比 `instanceof` 更严格（不含子类）。
- `equals()` / `hashCode()`：见 ch02 concept 04 的契约详述。
- `toString()`：默认实现 `getClass().getName() + "@" + Integer.toHexString(hashCode())`，几乎总是应重写以便调试。注意 `System.out.println(obj)` 会自动调用它。
- `clone()`：`protected`，默认**浅拷贝**（只复制字段值，引用字段仍指向同一对象）。要求类实现标记接口 `Cloneable` 否则抛 `CloneNotSupportedException`——这是个设计糟糕的 API（标记接口无方法、浅拷贝易踩坑）。Effective Java 第 13 条建议：**优先用拷贝构造器或静态工厂，而非 clone**。
- `finalize()`：Java 9 起 `@Deprecated`，切勿用于释放资源；改用 `Cleaner` / `PhantomReference` 或 `try-with-resources`。
- `wait()/notify()/notifyAll()`：定义在 Object 上，因为**每个对象都自带一个监视器锁（monitor）**，线程协调（等待/通知）天然依附于锁对象。这是"为什么它们不在 Thread 上"的根本原因。

## 三、工程实践

- 公开给外部的类若设计为不可变，果断 `final`；需要被扩展则开放继承但把"不应被覆写"的方法标 `final`。
- 永远重写 `toString()`（尤其在 DTO、领域对象上），日志与调试收益巨大。
- 需要"复制对象"时优先实现 `new Foo(other)` 拷贝构造器；避免 `Cloneable` 的浅拷贝陷阱。
- 资源释放一律交给 `try-with-resources`（实现 `AutoCloseable`），别依赖 `finalize`。

## 四、边界与陷阱

1. **final 引用 ≠ final 对象**：引用不可变，对象内部可变（如 `final List` 仍可 `add`）。
2. **clone 是浅拷贝**：含引用字段时要手动深拷贝，否则两个对象共享子对象。
3. `finalize` 调用时机不确定甚至不调用，**绝不能**用于必须及时释放的资源。
4. 重写 `equals` 时 `getClass()` 与 `instanceof` 二选一要一致：用 `getClass()` 则要求同类型（不含子类）才相等；用 `instanceof` 则允许子类相等（需保证对称性）——混用会破坏等价关系。

## 五、可运行代码

见 `examples/ex11-final.json`（final 常量/方法/类语义）、`examples/ex02-override-tostring.json`（重写 toString），以及 ch02 的 `examples/ex09~ex12`（equals/hashCode 契约实证）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 写不可变类四步：`final class` + 全部字段 `private final` + 不提供 setter + **对可变成员做防御性拷贝**（传入和取出都要拷）。
- 集合要对外暴露时用 `List.copyOf` / `Collections.unmodifiableList`。
- `clone()` 设计有缺陷（`Cloneable` 只是标记接口、默认是浅拷贝），优先用拷贝构造器或静态工厂。

### 🎓 博士生视角
- `final` 有三重语义：**变量不可重赋值、方法不可重写、类不可继承**——同一个关键字承担了三个维度的「封闭」。
- 最值得记住的是 `final` 的**内存语义**：JMM 保证「正确构造的对象」其 `final` 字段在构造完成后对其他线程可见（无需同步）。这是**不可变对象天然线程安全**的语言级基础，也是「安全发布」的标准手段。
- `Object` 是所有类的根基（无显式父类时隐式继承），提供 `equals` / `hashCode` / `toString` / `getClass` / `clone` / `finalize` 与 `wait`/`notify` 系列——其中 `wait`/`notify` 直接绑定到对象头的 monitor，是「对象即锁」的语言根源。
- `finalize` 已被标记废弃（JDK 9+ 弃用、后续版本移除），原因是非确定性执行与性能问题——这是「自动回收资源」这一想法的失败案例，也促成了 `Cleaner` / try-with-resources 的推广。

### 📚 考研者视角
- 与**并发编程的内存可见性**交叉：「`final` 字段为什么能安全发布」是并发专题的经典问题。
- 若考程序设计语言，可考「不可变对象的意义」「为什么 `clone` 设计不佳」。
- 记忆锚点：**`final` 字段 + 正确构造 = 安全发布**；**`Cloneable` 是标记接口，`clone` 默认浅拷贝**。
