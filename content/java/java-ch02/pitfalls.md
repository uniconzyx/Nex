# 本章避坑指南

1. **把"对象参数传递"说成引用传递** —— Java 只有值传递，传递的是引用的副本；方法内重指形参不影响外部，但改对象状态可见。正确：理解"引用的副本"语义（`examples/ex07-pass-by-value-reference.json` 实证）。

2. **用 `==` 比较对象内容** —— `==` 对引用比地址。比较内容必须用 `equals`；`new String("a") == "a"` 为 `false`，而 `.equals` 才为 `true`。

3. **重写 `equals` 却忘了重写 `hashCode`** —— 放进 `HashMap`/`HashSet` 后"找不到"，因为两个相等对象落到不同桶（`examples/ex10-equals-hashcode-contract.json` 实证）。务必成对重写。

4. **字段不加 `private`、setter 不校验** —— 等于没封装，任何非法值都能进，破坏不变式。正确：字段 `private` + setter 内校验（`examples/ex05-encapsulation-getter-setter.json`）。

5. **构造器里调用可被重写的方法** —— 动态分派会调用子类覆写版，而此时子类字段尚未初始化，得到错误/部分值（详见 ch03 陷阱）。

6. **误用 `record` 访问器名与可变性** —— record 字段是 `final`、访问器名为 `x()` 而非 `getX()`；框架若按 `getXxx` 找会失败（`examples/ex08-record-java17.json`）。需要可变请用普通类。

7. **重写 `equals` 却不重写 `hashCode`**
   两个「相等」的对象 hash 不同，就会被放进 `HashMap` / `HashSet` 的**不同桶**：`contains` 返回 false，同一个逻辑 key 还能被存成两份，删也删不掉。
   ✅ 成对重写；`hashCode` 用 `Objects.hash(...)`，且参与 `equals` 的字段必须与 `hashCode` 完全一致；能用 `record` 就让编译器生成。

8. **`equals` 的参数写成具体类型而不是 `Object`**
   ```java
   public boolean equals(MyType o) { ... }   // 这是重载，不是重写
   ```
   编译器不会报错，但集合内部调用的是 `Object.equals(Object)`，于是永远走引用比较——「明明重写了却不生效」。
   ✅ 参数必须写 `Object`，并加 `@Override` 让编译器替你抓这类签名错误（`@Override` 是最便宜的防线）。

9. **在构造器里调用可被重写的方法**
   父类构造器先执行，此时子类字段还全是默认值（`0` / `null`）。如果构造器调用了一个被子类重写过的方法，子类版本会读到**尚未初始化**的状态，表现为莫名其妙的 NPE 或「配置没生效」。
   ✅ 构造器只调用 `private` / `final` 方法；需要扩展点就让子类显式调 `init()`。
