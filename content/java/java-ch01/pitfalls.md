# 本章避坑指南

1. **数组长度是属性不是方法** —— 写成 `arr.length()` 会编译报错，正确是 `arr.length`（属性，无括号）。

2. **`==` 比较引用而非内容** —— 对字符串、包装类等对象，`==` 比的是地址；比较内容应使用 `.equals(...)`。例如 `new String("a") == "a"` 为 `false`，而 `.equals` 为 `true`。

3. **整数字面量默认 int，long 必须加 L** —— `long x = 10000000000;` 因右侧是 int 溢出报错，须写成 `10000000000L`；浮点默认 double，声明 float 必须加 `f`：`float f = 3.14f;`。

4. **自动拆箱引发 NPE** —— `Integer` 为 `null` 时参与运算或赋值给 `int` 会抛 `NullPointerException`，基本类型没有此问题；接受外部数据时注意判空。

5. **switch 忘记 break 造成穿透** —— 漏写 `break` 会继续执行后续 `case` 分支，常导致逻辑错误；Java 14+ 可用 `switch` 表达式（带 `->`）避免穿透。
