# §5 java-ch03 实战手记：凯喵带你把 OOP 用「翻车」

> 前四节把继承、多态、重写、抽象类/接口、final/Object 方法讲透了。这一节凯喵把多态最容易「调不到 / 编译不过 / 运行炸」的 12 个现场摆出来——每个都是面试和上线双杀点。

### 现场一：重写签名差一个参数，变成了重载

凯喵写 `public String toString(Object o)` 想重写 `Object.toString()`，结果压根没覆盖、还以为生效了。重写要求**方法名、参数列表、返回类型（协变）完全一致**；多一个参数就是重载，和多态无关。加 `@Override` 让编译器替你抓。

```java
class A {
    // ❌ 带参，是重载不是重写
    // public String toString(Object o) { return ""; }
    @Override public String toString() { return "A"; }  // ✅ 精确匹配
}
```

### 现场二：父类 private 方法被同名方法「重写」的错觉

凯喵看到子类写了和父类 `private` 同名的方法，以为覆盖了它。错：`private` 不参与继承，子类只是新定义一个方法；父类内部调用仍然走父类那一份。要扩展点用 `protected`（或 `protected abstract`），不想被扩展就 `final`。

```java
class Base {
    private void hook() { System.out.println("base"); }
    public void run() { hook(); }   // 永远调 Base.hook，不是子类那份
}
class Sub extends Base {
    // 这只是 Sub 自己的新方法，Base.run 调不到它
    public void hook() { System.out.println("sub"); }
}
```

### 现场三：静态方法不能被重写，调用看编译期类型

凯喵在父类 `static void f()`、子类也写 `static void f()`，用 `Base b = new Sub(); b.f()` 期望走子类。错：静态方法**编译期绑定**到声明类型 `Base`，不走虚表。要多态必须用实例方法。

```java
Base b = new Sub();
b.staticMethod();   // ❌ 调的是 Base.staticMethod，编译期定死
b.instanceMethod();// ✅ 走 Sub 的重写（虚派发）
```

### 现场四：字段不多态，子类同名字段只是隐藏

凯喵在父类和子类都写了 `int x`，用 `Base b = new Sub()` 访问 `b.x` 拿到的是父类的 x。Java 的字段**不参与多态**（没有虚字段），`b.x` 看声明类型。多态只发生在方法上。需要用方法（`getX()`）才能拿到子类的覆盖值。

```java
class Base { int x = 1; }
class Sub extends Base { int x = 2; }
Base b = new Sub();
System.out.println(b.x);   // 1（字段看声明类型，不多态）
System.out.println(((Sub)b).x); // 2
```

### 现场五：抽象类不能实例化，却常被当普通类 new

凯喵写 `Shape s = new Shape();` 编译不过——`abstract class` 不允许直接实例化，只能 `new 具体子类`。抽象类用于「抽取共性 + 强制子类实现抽象方法」；若想放工具方法用 `static`，想多继承行为用接口。

```java
abstract class Shape { abstract double area(); }
// Shape s = new Shape();      // ❌ 编译错误
Shape s = new Circle(1.0);   // ✅ 用具体子类
```

### 现场六：接口默认方法冲突，忘了显式重写

凯喵让一个类同时实现两个接口，俩都有 `default void foo()`，编译直接报冲突。必须**在该类里显式重写 `foo()`**（可用 `InterfaceA.super.foo()` 选一个）。

```java
interface A { default void foo(){ System.out.println("A"); } }
interface B { default void foo(){ System.out.println("B"); } }
class C implements A, B {
    @Override public void foo() { A.super.foo(); }  // ✅ 显式选一个
}
```

### 现场七：equals 不重写 hashCode，HashMap 找不到

凯喵重写了 `equals` 却忘了 `hashCode`，把对象当 key 存进 HashMap 再 get 拿不到。契约：**equals 相等则 hashCode 必须相等**；只重写 equals 会让两个相等对象落进不同桶。两者必须一起重写。

```java
class P {
    int x;
    @Override public boolean equals(Object o){ return o instanceof P p && p.x==x; }
    @Override public int hashCode(){ return Integer.hashCode(x); }  // ✅ 配套
}
```

### 现场八：equals 里用 getClass() 还是 instanceof 没想清

凯喵在 `equals` 里用 `getClass() != o.getClass()` 判定，结果 `P` 和 `P` 的子类永远 unequal，破坏了「equals 应对称」的约定。若允许跨子类相等用 `instanceof`；若要求严格同类型用 `getClass()`——选定一种并写进注释。

```java
// instanceof：允许子类对象与父类等（对称）
if (!(o instanceof P p)) return false;
// getClass：严格要求同一运行时类
if (o == null || o.getClass() != getClass()) return false;
```

### 现场九：final 的三种用法混着用

凯喵以为 `final` 只修饰常量，结果给方法加 `final` 想「禁止继承」却没效果，给类加 `final` 又报「不能继承」。记清：`final 类`不可继承、`final 方法`不可重写、`final 变量`不可重赋值（引用类型只保证引用不变）。

```java
final class Lock { }            // ❌ 不能被继承
class A { public final void f(){} }  // 子类不能重写 f
final int[] a = {1,2}; a[0]=9;  // ✅ 引用不可变但元素可变
```

### 现场十：clone 是浅拷贝，改副本影响原对象

凯喵用 `Object.clone()` 复制一个含 `List` 字段的对象，改副本的列表，原对象也变了。默认 `clone` 是**浅拷贝**：引用字段指向同一对象。要深拷贝需自己递归 clone 每个引用字段，或改用拷贝构造器 / 序列化。

```java
class Box implements Cloneable {
    List<Integer> items = new ArrayList<>();
    @Override protected Box clone() throws CloneNotSupportedException {
        Box b = (Box) super.clone();
        b.items = new ArrayList<>(this.items);  // ✅ 深拷贝列表
        return b;
    }
}
```

### 现场十一：包装类缓存区间外 == 比较翻车

凯喵写 `new Integer(200) == new Integer(200)` 得到 false，心想「值一样为啥不等」。两个 `new` 是不同对象，`==` 比地址；即便自动装箱，`Integer` 也只缓存 -128~127，超出范围是新对象。比较值一律用 `equals`。

```java
System.out.println(new Integer(200) == new Integer(200)); // false
System.out.println(Integer.valueOf(200).equals(200));    // true ✅
```

### 现场十二：toString 忘了覆盖，打印出一串哈希

凯喵打印一个自定义对象，出来 `com.x.User@1b6d3586`，调试时一脸懵。没重写 `toString()` 就走 `Object` 默认实现（类名@哈希）。调试友好的 Bean 一律重写 `toString`，把关键字段打出来。

```java
@Override public String toString() {
    return "User{id=" + id + ", name='" + name + "'}";  // ✅ 调试一目了然
}
```

> 凯喵总结：OOP 的坑几乎都在「重写契约」「字段不多态」「静态不虚派发」「equals/hashCode 绑定」。把这 12 个现场刻进手感，多态不再是玄学。

## 三视角解析
### 🧑‍💻 程序员视角
重写签名差一个参数就变成重载，`@Override` 注解能在编译期抓住这类错误——**所有重写都该加它**。父类的 `private` 方法不参与继承，子类写同名方法是「新方法」而非重写。静态方法按编译期类型绑定，通过实例调用也不构成重写。字段更不参与多态：子类同名字段只是隐藏，通过父类引用访问到的仍是父类字段。

### 🎓 博士生视角
Java 的方法分派规则是「重载看编译期类型、重写看运行期类型」：前者由静态类型在编译期选定签名，后者由对象实际类型在运行期经虚方法表（vtable）确定。字段与静态方法都走静态绑定，因为它们不进入虚方法表。这一分层设计使「多态」只作用于实例方法，避免了字段访问的歧义；代价是「父类引用看到的字段」与「子类对象实际持有的字段」可能不同，这是面试官最爱问的细节。

### 📚 考研者视角
笔试必考：
1. **重载与重写**：前者同签名规则（参数列表不同）、编译期决定；后者同签名、运行期决定。返回值协变允许，参数不允许。
2. **访问权限不能收紧**：重写时子类方法的可见性必须 ≥ 父类。
3. **抽象类与接口**：抽象类可有构造器与状态，接口只能有常量与默认/静态方法（Java 8+）。
4. **多态的三个必要条件**：继承、重写、父类引用指向子类对象。

```text
05-oop-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：重写签名差一个参数，变成了重载  (java)
    |
    v
  [02] 现场二：父类 private 方法被同名方法「重写」的错觉  (java)
    |
    v
  [03] 现场三：静态方法不能被重写，调用看编译期类型  (java)
    |
    v
  [04] 现场四：字段不多态，子类同名字段只是隐藏  (java)
    |
    v
  [05] 现场五：抽象类不能实例化，却常被当普通类 new  (java)
    |
    v
  [06] 现场六：接口默认方法冲突，忘了显式重写  (java)
    |
    v
  [07] 现场七：equals 不重写 hashCode，HashMap 找不到  (java)
    |
    v
  [08] 现场八：equals 里用 getClass() 还是 instanceof 没想清  (java)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
