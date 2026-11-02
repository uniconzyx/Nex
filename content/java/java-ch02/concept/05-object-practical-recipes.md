# §5 java-ch02 实战手记：凯喵带你把对象模型用「翻车」

> 前四节把对象内存布局、封装、构造器、equals/hashCode 讲透了。这一节凯喵把对象最容易「NPE / 串号 / 哈希丢失 / 浅拷贝陷阱」的 12 个现场搬出来——每个都是线上灵异事件的元凶。

### 现场一：构造器里调用可被重写的方法，读到未初始化字段

凯喵在父类构造器里调了一个被子类重写的方法，结果子类版本读到的全是默认值（`0` / `null`），配置「没生效」。父类构造器先执行，此时子类字段尚未初始化。构造器只调 `private`/`final` 方法，或让子类显式调 `init()`。

```java
class Base {
    int x;
    Base() { init(); }            // ❌ 调用虚方法
    void init() {}
}
class Sub extends Base {
    Sub() { x = 10; }
    @Override void init() { System.out.println(x); }  // 打印 0，而非 10
}
```

### 现场二：== 比较对象比的是地址，不是内容

凯喵 `new String("a") == new String("a")` 得到 false，以为「内容一样为啥不等」。`==` 对引用类型比的是**地址**；要比值必须用 `equals`。基本类型 `==` 比值，包装类型 `==` 比地址，别混。

```java
String a = new String("x"), b = new String("x");
System.out.println(a == b);        // false（不同对象）
System.out.println(a.equals(b));   // true（内容相等）✅
```

### 现场三：equals 写了 hashCode 没写，HashMap 找不到 key

凯喵重写了 `equals` 却漏了 `hashCode`，把对象塞进 HashMap 再 get 拿不到。契约：**equals 相等则 hashCode 必须相等**；只写 equals 会让相等对象落进不同桶。IDE 一键生成两者，永远一起生成。

```java
class User {
    String id;
    @Override public boolean equals(Object o){ return o instanceof User u && id.equals(u.id); }
    @Override public int hashCode(){ return id.hashCode(); }  // ✅ 必须配套
}
```

### 现场四：可变对象当 HashMap 的 key，改完就找不到

凯喵用 `List` 当 key，存进去后改了 list 内容，再 get 返回 null。key 的 hashCode 变了，定位到的桶不再是当初那个。Map 的 key 必须是**不可变**对象（String、Integer、或字段全 final 的自定义类）。

```java
Map<List<Integer>, String> m = new HashMap<>();
List<Integer> k = List.of(1, 2);
m.put(k, "v");
k.set(0, 9);                  // ❌ 改了 key
System.out.println(m.get(k)); // null —— hashCode 已变
```

### 现场五：字段没封装，外部直接改破坏不变量

凯喵把 `balance` 设成 `public`，外部 `acc.balance = -100;` 直接把余额改负，业务约束形同虚设。字段一律 `private`，通过 `getXXX` / `setXXX` 暴露，在 setter 里校验，保证对象始终合法。

```java
class Account {
    private int balance;
    public void deposit(int n) {           // ✅ 唯一修改入口
        if (n < 0) throw new IllegalArgumentException();
        balance += n;
    }
}
```

### 现场六：this 在内部类/lambda 里指向谁要想清

凯喵在匿名内部类里用 `this`，以为指外部类，其实指**内部类自己**。要引用外部实例用 `OuterClass.this`。lambda 里 `this` 指包围它的实例（lambda 不引入新作用域），这点又和匿名类不同，容易混。

```java
class Outer {
    int x = 1;
    void m() {
        Runnable r = new Runnable() {
            int x = 2;
            public void run() {
                System.out.println(this.x);          // 2（内部类自己的 x）
                System.out.println(Outer.this.x);    // 1（外部实例）✅
            }
        };
    }
}
```

### 现场七：构造器没写 this(...) / super(...)，默认调无参父类构造器

凯喵子类构造器没显式调 `super(...)`，父类又没有无参构造器，编译直接失败。子类构造器**第一行**必须调用本类其他构造器 `this(...)` 或父类构造器 `super(...)`，否则默认 `super()`（无参）。

```java
class Base { Base(int x) {} }
class Sub extends Base {
    Sub() { super(0); }   // ✅ 必须显式调父类有参构造
}
```

### 现场八：重写 equals 参数写 Object 却漏 @Override，变成重载

凯喵写 `public boolean equals(User u)` 想重写，漏了 `Object` 参数和 `@Override`，结果这是**重载**不是重写，`HashSet.contains` 仍走 `Object.equals`（比地址），查找失败。参数必须是 `Object`，并加 `@Override`。

```java
@Override public boolean equals(Object o) {     // ✅ 参数写 Object + @Override
    return o instanceof User u && id.equals(u.id);
}
// public boolean equals(User u) { ... }        // ❌ 重载，多态不生效
```

### 现场九：clone 默认浅拷贝，改副本动原对象

凯喵 `obj.clone()` 复制了一个含 `List` 字段的对象，改副本的列表原对象也变。`Object.clone()` 是**浅拷贝**，引用字段指向同一对象。要深拷贝就递归 clone 每个引用字段，或写拷贝构造器。

```java
class Box implements Cloneable {
    List<Integer> items = new ArrayList<>();
    @Override protected Box clone() throws CloneNotSupportedException {
        Box b = (Box) super.clone();
        b.items = new ArrayList<>(this.items);  // ✅ 深拷贝
        return b;
    }
}
```

### 现场十：静态字段被所有实例共享，误当实例状态

凯喵在类里写 `static int counter`，以为每个对象各一份，结果所有实例的计数互相影响。`static` 属于**类**而非实例，所有对象共享同一份。实例状态用普通字段，类级常量/工具才用 static。

```java
class Counter {
    static int n = 0;          // ❌ 所有实例共享
    int local = 0;             // ✅ 每实例一份
}
```

### 现场十一：用可变静态集合做缓存，线程不安全还内存泄漏

凯喵用 `static Map` 当全局缓存，并发写入丢数据、key 只塞不删最终 OOM。`static` 集合生命周期等同于类加载，必须配并发容器 + 容量/过期策略（如 `ConcurrentHashMap` + `WeakReference` 或 Caffeine）。

```java
// ❌ 裸 static Map 并发写丢数据、无上限
// ✅ 用 Caffeine / ConcurrentHashMap + 清理策略
```

### 现场十二：toString 没重写，打印出一串 @哈希

凯喵打印自定义对象，出来 `com.x.User@1b6d3586`，排查时全靠猜。没重写 `toString()` 就走 `Object` 默认（类名@哈希）。调试友好的 Bean 一律重写 `toString`，把关键字段打出来。

```java
@Override public String toString() {
    return "User{id=" + id + ", name='" + name + "'}";  // ✅ 一目了然
}
```

> 凯喵总结：对象模型的坑九成在「构造器调虚方法」「== vs equals」「equals/hashCode 绑定」「可变 key」「static 共享」。把这 12 个现场刻进手感，线上灵异事件少一半。

### 现场之外：凯喵的对象三问
每次新写一个类，凯喵都会先问自己三个问题，能挡掉八成对象模型的坑：第一，这个类会被当成 Map 的 key 吗？会就让它不可变并正确实现 equals/hashCode。第二，这个字段会被多线程碰到吗？会就把状态收进方法内部、别留 public 可变成员。第三，构造器里有没有无意调用了会被子类重写的方法？有就立刻改成 private 或 final。三问过完再写，代码少返工、上线少背锅。
