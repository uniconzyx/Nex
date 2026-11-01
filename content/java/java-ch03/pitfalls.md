# 本章避坑指南

1. **方法重写 ≠ 方法重载** —— override 是运行期动态分派（依据对象实际类型），overload 是编译期按实参静态类型选定。把"想重写却写成重载（参数类型不同）"会静默失效（`examples/ex08-override-contract.json` 配合 `@Override` 可抓错）。

2. **字段没有多态（字段隐藏 hides）** —— 子类声明与父类同名字段只是隐藏父类字段，父类引用访问到的永远是父类那份字段；想做行为多态必须用方法（`examples/ex07-field-no-polymorphism.json` 实证）。

3. **子类构造器未调用父类构造器** —— 父类没有无参构造器时，子类构造器必须显式 `super(实参)` 且为第一条语句，否则编译失败；隐式 `super()` 只在父类有无参构造器时可用。

4. **接口 default 方法冲突** —— 一个类实现多个接口且它们有同签名 `default` 方法，必须显式重写并指定 `A.super.foo()` / `B.super.foo()`，否则编译报错（`examples/ex06-interface-default-conflict.json`）。

5. **构造器里调用可重写方法** —— 动态分派会调到子类覆写版，但此时子类字段尚未初始化（仍是默认值 0/null），导致读到错误值甚至 NPE；应只调用 `private`/`final` 方法或 `super` 方法。

6. **向下转型未用 instanceof** —— `Animal a = new Dog(); Cat c = (Cat) a;` 会在运行期抛 `ClassCastException`；安全做法先 `if (a instanceof Cat c)` 再使用（`examples/ex09-upcast-downcast-instanceof.json`）。

7. **以为 `static` 方法能被「重写」**
   子类写同名 `static` 方法只是**隐藏（hiding）**，不是多态：调用哪个版本由**编译期声明类型**决定，与运行时对象无关。`A a = new B(); a.f();` 永远调 `A.f()`。
   ✅ 需要多态就用实例方法；工具类的 `static` 方法不要指望被覆盖，也无法通过接口抽象。

8. **以为字段访问是多态的**
   ```java
   class A { int x = 1; }
   class B extends A { int x = 2; }
   A a = new B();
   System.out.println(a.x);      // 1，不是 2
   ```
   字段访问在编译期按声明类型绑定，父子同名字段是**两个独立字段**（各自占内存），不是覆盖。
   ✅ 字段一律 `private`，对外用 getter——方法才会多态。

9. **父类 `private` 方法被同名方法「重写」的错觉**
   `private` 方法不参与继承，子类写同名方法只是新定义一个方法；父类内部调用仍然走父类那一份。看代码像模板方法模式，运行时却完全不按预期分流。
   ✅ 需要扩展点用 `protected`（或 `protected abstract`）；不想被扩展就 `final`，并在命名上避开父类的私有实现名。
