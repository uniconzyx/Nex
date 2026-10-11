# 本章避坑指南

1. **把"对象参数传递"说成引用传递** —— Java 只有值传递，传递的是引用的副本；方法内重指形参不影响外部，但改对象状态可见。正确：理解"引用的副本"语义（`examples/ex07-pass-by-value-reference.json` 实证）。

2. **用 `==` 比较对象内容** —— `==` 对引用比地址。比较内容必须用 `equals`；`new String("a") == "a"` 为 `false`，而 `.equals` 才为 `true`。

3. **重写 `equals` 却忘了重写 `hashCode`** —— 放进 `HashMap`/`HashSet` 后"找不到"，因为两个相等对象落到不同桶（`examples/ex10-equals-hashcode-contract.json` 实证）。务必成对重写。

4. **字段不加 `private`、setter 不校验** —— 等于没封装，任何非法值都能进，破坏不变式。正确：字段 `private` + setter 内校验（`examples/ex05-encapsulation-getter-setter.json`）。

5. **构造器里调用可被重写的方法** —— 动态分派会调用子类覆写版，而此时子类字段尚未初始化，得到错误/部分值（详见 ch03 陷阱）。

6. **误用 `record` 访问器名与可变性** —— record 字段是 `final`、访问器名为 `x()` 而非 `getX()`；框架若按 `getXxx` 找会失败（`examples/ex08-record-java17.json`）。需要可变请用普通类。
