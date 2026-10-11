# 04 · 泛型擦除与桥接方法（bridge method）

## 一、理论根基：为什么 Java 选了「擦除」而非「具化」

Java 5 引入泛型时，已有大量字节码与库（如 `ArrayList` 在 1.4 是 `Object` 容器）。为了**二进制向后兼容**（旧 class 文件仍能运行、泛型代码与非泛型代码互操作），Java 选择了**擦除法（type erasure）**：泛型类型参数只在**编译期**做类型检查与强转插入，编译后的字节码中类型参数被「擦除」为它的上界（无界时 `Object`），**不生成新的类**。

## 二、实现机制：擦除带来的直接限制

因为运行时没有类型参数信息：
- **`List<String>.class` 与 `List<Integer>.class` 是同一个 `Class` 对象**（`java.util.ArrayList`），无法在运行时区分元素类型。见 `examples/ex06-generic-erasure.json`：`strings.getClass() == ints.getClass()` 为 `true`。
- **不能 `new T[]` / 不能 `new T()`**：编译器不知道 T 具体是什么。
- **不能 `instanceof T`**：运行时 T 不存在。
- **不能重载仅泛型参数不同的方法**：`void f(List<String>)` 与 `void f(List<Integer>)` 擦除后签名相同，非法。
- 原始类型（raw type）`List raw` 可绕过检查：`raw.add(123)` 能塞进声明为 `List<String>` 的列表，直到取出时才抛 `ClassCastException`——证明泛型只防编译期。

## 三、实现机制：桥接方法为何存在

擦除破坏了**多态覆盖**。考虑：
```java
class Node<T>        { void setData(T data) { this.data = data; } }
class IntNode extends Node<Integer> { void setData(Integer data) { super.setData(data); } }
```
擦除后，父类方法变成 `setData(Object)`；子类 `setData(Integer)` 与 `setData(Object)` **签名不同**，依 Java 语义它**不构成对父类的覆盖**——但语义上它应该是覆盖（否则 `Node<Integer> n = new IntNode(); n.setData(42)` 会调用父类的 `setData(Object)`，绕过子类的类型化逻辑）。

为维持多态，编译器在 `IntNode` 中**生成一个合成方法（synthetic bridge）**：
```java
// 编译器生成，带 bridge 标志
public void setData(Object data) { this.setData((Integer) data); }
```
它把 `Object` 强转成 `Integer` 再转发到真正的 `setData(Integer)`。反射可见：`Method.isBridge()` 为 `true`，`getParameterTypes()` 为 `Object`。见 `examples/ex09-bridge-method.json`：同一子类 `IntNode` 存在两个 `setData`——参数 `Integer`（非桥）与参数 `Object`（桥）。

## 四、工程实践

- 用**类型令牌**（`Class<T>`）在运行时恢复一点类型信息；用「超类型令牌」`TypeToken`（Guava）绕过擦除获取泛型。
- 设计 API 时记住不可协变：方法参数想「接受任意 Number 子类型」要用 `? extends Number`（PECS，见 concept 05）。
- 不要对集合使用原始类型（`List` 而非 `List<String>`），否则丢失编译期检查；必要时用 `@SuppressWarnings("unchecked")` 局部抑制（concept 05）。

## 五、边界与陷阱

1. **桥接方法可能被反射误判**：用 `getDeclaredMethods()` 遍历时会出现「重复的」方法，需 `isBridge()` 过滤。
2. **擦除导致数组协变与泛型不协变的割裂**：`String[]` 是 `Object[]` 子类型（数组协变，运行期才检查），但 `List<String>` 不是 `List<Object>` 子类型（编译期就拒绝）——二者不一致，易混淆。
3. **基本类型不能作为类型参数**：`List<int>` 非法，必须 `List<Integer>`（装箱有开销）。

## 六、可运行代码

- `examples/ex06-generic-erasure.json`：`List<String>` 与 `List<Integer>` 运行时同类型。
- `examples/ex09-bridge-method.json`：桥接方法的反射实证。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 运行期拿不到泛型实参：`new ArrayList<String>().getClass() == new ArrayList<Integer>().getClass()` 结果为 `true`。
- 因此**不能 `new T[]`**、不能用类型参数做 `instanceof`；需要类型信息就显式传 `Class<T>`（如 `new T[size]` 的替代方案是 `(T[]) Array.newInstance(clazz, size)`）。
- 反序列化/反射场景拿不到泛型时，用「类型令牌」或选择器方法弥补。

### 🎓 博士生视角
- 擦除意味着 `List<String>` 与 `List<Integer>` 运行期是同一个类，泛型信息只保留在**签名（Signature）属性**里供编译器与反射读取。这是为**迁移兼容**付出的代价：1.5 引入泛型时，已有大量使用原始类型的代码与类库，擦除保证了二进制兼容。
- **桥接方法（bridge method）** 是「擦除 + 多态」的黏合剂：当子类特化父类的泛型方法时，擦除后父类方法的签名与子类不一致，编译器便生成一个带 `ACC_BRIDGE | ACC_SYNTHETIC` 的方法把调用转发到特化版本，从而让重写仍然生效。
- 后果之一是不能基于泛型实参做**重载**（`f(List<String>)` 与 `f(List<Integer>)` 擦除后签名相同，编译报错）——这是「编译期检查 + 运行期无信息」这一设计的直接限制。
- 与 C++ 模板对比：C++ 为每组实参生成**独立代码**（代码膨胀但保留类型信息、支持特化与编译期计算）；Java 擦除只生成一份（体积小但丢失类型能力）。这是「编译期多态」两条路线的根本分歧。

### 📚 考研者视角
- 与编译原理的**类型检查、单态化（monomorphization）** 对应：C++ 模板走单态化，Java 泛型走擦除 + 类型检查。
- 常考概念题：「泛型擦除的影响」「为什么 Java 泛型不能是基本类型」（`List<int>` 非法，需要 `List<Integer>`，因为擦除后要用 `Object`）。
- 记忆锚点：**擦除 = 编译期类型检查 + 运行期无类型信息**；**桥接方法保证泛型重写可用**。
