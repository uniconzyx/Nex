# 05 · 通配符 PECS、自限定类型、泛型方法与 @SuppressWarnings

## 一、理论根基：泛型不可协变与通配符的补偿

`List<Integer>` 不是 `List<Number>` 的子类型（若允许，就能往 `List<Integer>` 塞 `Double`，破坏类型安全）。但很多 API 想表达「接受某种类型的任意子/超类型集合」——通配符 `? extends T` / `? super T` 正是为此而生，并用 **PECS**（Producer Extends, Consumer Super）规则约束其用法。

## 二、实现机制：PECS 的读写权限

- **`? extends T`（上界，生产者）**：集合「生产」T（只往外读）。可安全读出 `T`，但**不能写入**（除了 `null`）：因为你不知道具体是 `T` 的哪个子类型，`list.add(new Sub())` 可能类型不符。典型：`List<? extends Number>` 能 `get` 出 `Number`，不能 `add` 任何非 null 元素。
- **`? super T`（下界，消费者）**：集合「消费」T（只往里写）。可安全写入 `T` 及其子类型，但读出的只能当 `Object`（不知道具体超类型）。典型：`List<? super Integer>` 能 `add(Integer)`，但取出只能当 `Object`。

记忆口诀：**Producer（读）用 extends，Consumer（写）用 super**。标准库范例 `Collections.copy(dst, src)`：`dst` 是 `? super T`（消费目标），`src` 是 `? extends T`（生产源）。

见 `examples/ex05-pecs.json`：`sum(List<? extends Number>)` 从集合读、`addIntegers(List<? super Integer>)` 向集合写，二者都用对边界。

## 三、泛型方法

泛型方法把类型参数声明在返回类型之前（`static <T> T foo(...)`），调用时由实参推断。`<T>` 让方法独立于类的类型参数、高度可复用。注意类型推断受上界约束；推断失败时可用显式实参 `<Integer>foo(...)`。

## 四、自限定类型（Self-Bounded Generic）

一种高阶技巧：`class SelfBounded<T extends SelfBounded<T>>`——类型参数 T 必须是以自身为参数的该类型。它用在**仿函数式（fluent）API 与 CRTP 式编译期约束**上：基类的方法能返回「具体的子类类型」而非父类，从而链式调用后仍保留子类的精确类型。例如在类型安全的构建器/DSL 中保证 `copy().special()` 可用（若返回父类则 `special()` 不可见）。见 `examples/ex10-self-bounded.json`：`c.copy()` 返回 `Concrete` 而非 `SelfBounded`，故能继续调用 `special()`。

## 五、@SuppressWarnings：克制使用

泛型与遗留代码交互时常产生「未受检（unchecked）」警告（如原始类型强转 `(List<String>) raw`）。`@SuppressWarnings("unchecked")` 用于**在确有把握的最小作用域**抑制该警告，避免用 `@SuppressWarnings` 包住整个类掩盖真实隐患。原则是：窄作用域、加注释说明为何安全。

## 六、工程实践

- 方法签名里「只进不出」用 `? super`，「只出不进」用 `? extends`；需要既读又写则放弃通配符用精确类型（或受限时用有界类型参数 `<T extends Number>`）。
- 优先泛型方法而非强制类型转换；用 `Objects.requireNonNull` 等工具替代手写校验。
- `PECS` 是《Effective Java》第 31 条的核心，面试高频。

## 七、边界与陷阱

1. **`List<?>` 不等于 `List<Object>`**：`List<?>` 是「未知类型的列表」，既不能 add（除 null）也不能可靠 get（只能 Object）；它常用于「只关心集合结构、不碰元素」的场景。
2. **`? extends` 不能写、`? super` 不能可靠读**，误用会编译失败而非运行时错——这是好事，把 bug 挡在编译期。
3. **不要滥用 `@SuppressWarnings`**：包住大段代码会掩盖真正危险的未受检操作。

## 八、可运行代码

- `examples/ex05-pecs.json`：PECS 读写权限实证。
- `examples/ex07-suppress-warnings.json`：`@SuppressWarnings("unchecked")` 抑制原始类型强转警告。
- `examples/ex10-self-bounded.json`：自限定类型返回具体子类，支持 fluent 链式调用。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 记死 **PECS**：**Producer Extends, Consumer Super**。只读来源用 `? extends T`，只写目标用 `? super T`，既读又写就别用通配符。
- `? extends T` 的容器**不能放入元素**（除了 `null`），因为编译器不知道具体是哪个子类型。
- 需要「返回 this 的自身类型」的 API（如 `Builder`、`Enum`）用自限定类型，代价是声明看起来绕。

### 🎓 博士生视角
- Java 泛型是**不型变（invariant）**的：`List<String>` 不是 `List<Object>` 的子类型。这不是保守，而是**必要的**——若允许，就能往 `List<Object>` 里塞整数，破坏原 `List<String>` 的类型安全。
- 通配符正是为了在**方法参数位置**引入可控的**协变读（`? extends`）与逆变写（`? super`）**，从而在保持类型安全的前提下提高 API 的灵活性。PECS 是可变性（variance）理论在实践中的落地口诀。
- 自限定类型（`class Enum<E extends Enum<E>>`）用 F-bounded 多态表达「子类型必须返回自身类型」，这是「在缺少 `Self` 类型机制的语言里模拟 self type」的经典手法。
- 与 C# 对比：C# 支持声明处可变性（`out T` / `in T`），把 variance 标注在类型参数声明上；Java 采用使用处通配符。两种设计各有表达力与可读性的取舍。

### 📚 考研者视角
- 与**类型系统**中的**协变（covariance）/ 逆变（contravariance）/ 不变（invariance）**直接对应，是类型论的核心概念。
- 常考概念题：「为什么 `List<String>` 不能赋给 `List<Object>`」「PECS 原则」。
- 记忆锚点：**PECS**；**`? extends` 只能取不能存（除 null）**；**Java 泛型默认不型变**。
