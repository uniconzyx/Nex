# 04 · equals 与 hashCode 契约：等价关系与散列分布

## 一、理论根基：等价关系是数学约束

`Object.equals` 的默认实现就是 `==`（比地址）。要让"逻辑相等"的对象被当作相等，必须重写 `equals`，且必须满足**等价关系（equivalence relation）**：
- **自反**：`x.equals(x) == true`
- **对称**：`x.equals(y) == y.equals(x)`
- **传递**：`x.equals(y) && y.equals(z)` ⇒ `x.equals(z)`
- **一致**：对象未修改期间，多次调用结果相同
- 对 `null` 返回 `false`（即 `x.equals(null) == false`）

`hashCode` 的契约：**相等的对象必须有相等的哈希码**（`x.equals(y)` ⇒ `x.hashCode() == y.hashCode()`）。注意反过来不要求（哈希冲突允许，但相等必须同码）。

## 二、实现机制：为什么两者必须同时重写

`hashCode` 用于基于散列的集合（`HashMap`/`HashSet`/`Hashtable`）。`HashMap.get(key)` 先算 `key.hashCode()` 定位桶，再用 `equals` 在桶内比对。若只重写 `equals` 不重写 `hashCode`：
- 两个逻辑相等的对象产生**不同的哈希码** → 落在不同桶 → `map.get(新对象)` 找不到旧对象 → 看似"丢了数据"（见 ex10 的 `BadUser`：`bad get: null`）。
- 反之只重写 `hashCode` 不重写 `equals`：同码但 `equals` 仍比地址，散列集合照样认不出相等。

JVM 层面：`Object.hashCode()` 默认返回 **identity hash code**（与 `System.identityHashCode` 同源，通常基于对象地址扰动），所以未重写的对象"每个实例码都不同"。

## 三、工程实践

- 用 `java.util.Objects` 工具：`Objects.equals(a,b)` 自动处理 `null` 安全；`Objects.hash(a,b,c)` 生成组合哈希；`Objects.requireNonNull` 做参数校验。
- 重写范式（Java 7+）：
  ```java
  @Override public boolean equals(Object o){
      if (this == o) return true;
      if (!(o instanceof Person p)) return false;  // 顺带 null 安全
      return age == p.age && Objects.equals(name, p.name);
  }
  @Override public int hashCode(){ return Objects.hash(name, age); }
  ```
- 哈希组合：用 31 做乘法因子（`31*x+y`）是经典做法（`Objects.hash` 内部即用 `(31 * h + x)`），31 是奇素数、且 `31*i == (i<<5)-i` 利于 JIT 优化。
- 优先用 `record`：编译器自动生成满足契约的 `equals/hashCode`（基于全部组件）。

## 四、边界与陷阱

1. **必须成对重写**：漏写 `hashCode` 是散列集合 bug 的头号来源（ex10 实证）。
2. **可变对象做 key 是定时炸弹**：把对象放入 `HashSet` 后修改了参与 `hashCode` 的字段，再 `contains` 就找不到了（桶位置变了）。
3. **`equals` 里不要依赖可变字段**，否则一致性被破坏。
4. **`equals` 参数必须是 `Object`**：写成 `equals(Person p)` 只是重载不是重写，`@Override` 会直接编译报错帮你抓这个错。
5. 浮点字段比较要用 `Float.compare/Double.compare` 而非 `==`（NaN/-0.0 语义）。

## 五、可运行代码

见 `examples/ex09-equals-default-vs-override.json`（默认 vs 重写）、`examples/ex10-equals-hashcode-contract.json`（契约缺失的后果）、`examples/ex11-identity-equals.json`（`==` vs `equals`）、`examples/ex12-nullsafe-equals.json`（null 安全写法）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **重写 `equals` 必须重写 `hashCode`**，否则对象放进 `HashMap`/`HashSet` 会「找不到」。
- 现代写法：用 `record`（自动生成）或 IDE/Lombok 生成；手写容易漏字段或写错 `instanceof` 判断。
- 用**不可变对象**做键；可变对象做键，一旦被修改就再也查不回来（哈希桶位置变了）。

### 🎓 博士生视角
- `equals` 必须满足五条性质：**自反、对称、传递、一致、与 null 比较返回 false**——这正好是数学中**等价关系**的定义（一致性额外要求「多次调用结果不变」）。`hashCode` 的契约是「`equals` 相等 ⇒ `hashCode` 相等」（**单向蕴含**，反向不成立）。
- 契约的数学意义是：`equals` 把对象划分成**等价类**，`hashCode` 必须是「等价类上的函数」——同一等价类必须映到同一哈希值，否则哈希表无法定位。这就是为什么改了 `equals` 就必须同步 `hashCode`。
- 违反传递性（经典场景：父类与子类混用 `equals`）会导致集合行为诡异，这是「组合优于继承」在 `equals` 设计上的直接体现。
- 可变对象作为键会破坏哈希表的**不变量**（键的哈希值应当稳定），所以「键不可变」是哈希容器正确性的前提，而非性能建议。

### 📚 考研者视角
- **408 数据结构交叉**：哈希表的**冲突处理**、装填因子、平均查找长度（ASL）；「为什么需要 hashCode」正对应「为什么需要哈希函数」。
- **离散数学交叉**：等价关系的三条性质（自反、对称、传递）是必考概念，此处正是一个真实应用。
- 记忆锚点：**`equals` 五性质 + `hashCode` 单向蕴含**；**可变对象不能当键**。
