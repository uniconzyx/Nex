# 本章避坑指南

1. **方法重写 ≠ 方法重载** —— override 是运行期动态分派（依据对象实际类型），overload 是编译期按实参静态类型选定。把"想重写却写成重载（参数类型不同）"会静默失效（`examples/ex08-override-contract.json` 配合 `@Override` 可抓错）。

2. **字段没有多态（字段隐藏 hides）** —— 子类声明与父类同名字段只是隐藏父类字段，父类引用访问到的永远是父类那份字段；想做行为多态必须用方法（`examples/ex07-field-no-polymorphism.json` 实证）。

3. **子类构造器未调用父类构造器** —— 父类没有无参构造器时，子类构造器必须显式 `super(实参)` 且为第一条语句，否则编译失败；隐式 `super()` 只在父类有无参构造器时可用。

4. **接口 default 方法冲突** —— 一个类实现多个接口且它们有同签名 `default` 方法，必须显式重写并指定 `A.super.foo()` / `B.super.foo()`，否则编译报错（`examples/ex06-interface-default-conflict.json`）。

5. **构造器里调用可重写方法** —— 动态分派会调到子类覆写版，但此时子类字段尚未初始化（仍是默认值 0/null），导致读到错误值甚至 NPE；应只调用 `private`/`final` 方法或 `super` 方法。

6. **向下转型未用 instanceof** —— `Animal a = new Dog(); Cat c = (Cat) a;` 会在运行期抛 `ClassCastException`；安全做法先 `if (a instanceof Cat c)` 再使用（`examples/ex09-upcast-downcast-instanceof.json`）。
