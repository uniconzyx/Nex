# 03 · 抽象类 vs 接口：语义差异与字节码真相

## 一、理论根基：两者回答不同的问题

- **抽象类（abstract class）**："是什么"（is-a）的部分实现。可含抽象方法（无体，强制子类补完）、具体方法、实例字段、构造器。代表一组**紧密相关子类型的共享基类**。
- **接口（interface）**："能做什么"（capability）的契约。Java 8 起允许 `default` 方法（带实现）、`static` 方法，Java 9 起允许 `private` 方法；字段隐式为 `public static final` 常量；**无构造器、无实例字段**。一个类可 `implements` 多个接口（类型的多重继承），但只能 `extends` 一个类。

关键区别：**类携带状态（字段），接口（传统上）不携带状态**。这正是 Java 允许"类单继承、接口多实现"的根本原因——多继承状态会导致菱形歧义（同一份基类字段该有几份？），而多重继承无状态的契约是安全的。

## 二、实现机制：invokevirtual vs invokeinterface

这是最硬核、也最常被忽略的差异，可直接从字节码证伪：

- **抽象类的方法调用 → `invokevirtual`**：抽象类终究是类，其（具体）方法通过 vtable 分派，与普通类一致。`examples/ex10-abstract-vs-interface.json` 中 `Abs.hello()` 的调用编译为 `invokevirtual`。
- **接口的 `default`/普通方法调用 → `invokeinterface`**：因为实现接口的类是任意的，JVM 必须在运行期查找对象的 **itable（接口方法表）** 来定位实现。可见 `javap -c` 中 `Greet.hi()` 的调用是 `invokeinterface`。

> 一个常被误解的点：把方法放进抽象类或接口，在**可读性/设计语义**上完全不同，在**运行期性能**上也略有差异（`invokeinterface` 比 `invokevirtual` 多一步接口表查找）。但这远不如"语义正确性"重要。

- **default 方法冲突解决**：当一个类 `implements A, B` 且两者都有同签名 `default foo()`，编译**报错**，必须在该类中显式重写并指定 `A.super.foo()` 或 `B.super.foo()`。这是刻意设计——把"菱形问题"的歧义解决**上推到编译期显式决策**，而不是像 C++ 那样靠复杂的继承规则隐式解决（见 `examples/ex06-interface-default-conflict.json`）。
- 抽象类仍可被实例化？**不可以**——含抽象方法或显式 `abstract` 的类不能 `new`，但**可以有构造器**（供子类 `super()` 调用）。

## 三、工程实践

- **用接口定义能力/契约**：`Comparable`、`Runnable`、`Serializable` 这类"很多不相关类都能具备"的行为。
- **用抽象类做共享基类**：当子类型紧密相关、且要复用**状态与具体方法**（模板方法、公共字段）时，如 `AbstractList`、`HttpServlet`。
- **经典组合**："接口 + 薄抽象基类"模式（如 `List` 接口 + `AbstractList` 抽象类），既保证多实现灵活、又减少样板。
- **default 方法的正确用途**：为已发布的接口**向后兼容地追加方法**，而非用来堆砌继承层级。滥用 default 会把接口变成"退化抽象类"。

## 四、边界与陷阱

1. **default 冲突必须显式解决**：多接口同签名 default 不写 `X.super.method()` 直接编译失败。
2. 接口字段是 `public static final` 常量——**不能有实例字段**，需要状态请用抽象类或组合。
3. 抽象类可以被继承并实现接口，二者不互斥：`class Impl extends Abs implements Greet`。
4. 把 `default` 方法当"多继承实现"用会迅速失控——它不支持字段、不支持 `super.super`，语义远弱于类继承。
5. 接口里的 `static` 方法属于接口本身，不能被实现类继承/重写，调用的语法是 `Interface.staticMethod()`。

## 五、可运行代码

见 `examples/ex04-abstract-class.json`（抽象类 + 抽象方法）、`examples/ex05-interface-default.json`（default 方法）、`examples/ex06-interface-default-conflict.json`（多接口冲突解决）、`examples/ex10-abstract-vs-interface.json`（`invokevirtual` vs `invokeinterface` 实证，配合 `javap -c` 观察）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 判据：**需要共享状态（字段）与实现 → 抽象类；只描述能力与契约、期望多实现 → 接口**。
- Java 8 之后接口可以有 `default` / `static` 方法，因此「接口不能有实现」已过时；但接口仍**不能有实例字段**。
- 实现多个接口时若 `default` 方法冲突，**必须显式重写**并 `Interface.super.method()` 指定用哪个。

### 🎓 博士生视角
- 语义分工：接口表达**类型/能力**（can-do，多实现），抽象类还承担**实现复用**（is-a，共享状态与骨架）。这是「契约」与「模板」的分离。
- `default` 方法的引入是为**接口演进而非功能扩张**：给已有接口加方法时，用 `default` 避免破坏所有实现类（二进制兼容）。代价是引入了「菱形继承」的变体，需要显式覆盖来消歧。
- 字节码层面二者都是类文件，只是访问标志位不同（接口有 `ACC_INTERFACE | ACC_ABSTRACT`）；接口的实例字段必须同时是 `static final` 常量。
- 与 C++ 的纯虚类对比：C++ 没有单独的接口概念，靠「只有纯虚函数的抽象类」模拟，代价是无法真正多继承实现。

### 📚 考研者视角
- 与**软件工程**的「接口隔离原则」「依赖倒置原则」直接对应，是简答题素材。
- 若考程序设计语言，常考「抽象类与接口的区别」（字段、构造器、多继承、默认方法）。
- 记忆锚点：**抽象类 = is-a + 复用（可有状态），接口 = can-do + 契约（无实例字段）**；**default 冲突必须显式重写**。
