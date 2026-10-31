# 本章避坑指南

1. **数组长度是属性不是方法** —— 写成 `arr.length()` 会编译报错，正确是 `arr.length`（属性，无括号）。
2. **`==` 比较引用而非内容** —— 对字符串、包装类等对象，`==` 比的是地址；比较内容应使用 `.equals(...)`。例如 `new String("a") == "a"` 为 `false`，而 `.equals` 为 `true`。
3. **整数字面量默认 int，long 必须加 L** —— `long x = 10000000000;` 因右侧是 int 溢出报错，须写成 `10000000000L`；浮点默认 double，声明 float 必须加 `f`：`float f = 3.14f;`。
4. **自动拆箱引发 NPE** —— `Integer` 为 `null` 时参与运算或赋值给 `int` 会抛 `NullPointerException`，基本类型没有此问题；接受外部数据时注意判空。
5. **`switch` 忘记 `break` 造成穿透** —— 漏写 `break` 会继续执行后续 `case` 分支，常导致逻辑错误；Java 14+ 可用 `switch` 表达式（带 `->`）避免穿透。
6. **`byte`/`short` 参与运算先升 `int`** —— `short s = 1; s = s + 1;` 编译报错（右侧是 `int`）。写 `s += 1` 或强转 `(short)(s + 1)`。
7. **`char` 参与算术变成 `int`** —— `char c = 'a' + 1;` 编译报错，必须 `(char)('a' + 1)`。`char` 是 16 位无符号整数，不是字符串。
8. **`Integer` 的 `==` 在小整数上"恰好正确"** —— `Integer a = 127, b = 127; a == b` 为 `true`（缓存），128 就为 `false`。比较值一律用 `equals`，别记缓存范围。
9. **金额用 `double`** —— `0.1 + 0.2 != 0.3`，累加误差在财务场景不可接受。用 `BigDecimal`，且构造必须传字符串：`new BigDecimal("0.1")`。
10. **`Arrays.asList` 返回定长列表** —— 对它 `add`/`remove` 抛 `UnsupportedOperationException`。要可变就 `new ArrayList<>(Arrays.asList(...))`。
11. **增强 for 里删元素** —— 抛 `ConcurrentModificationException`。用 `Iterator.remove()` 或 `removeIf()`。
12. **数组赋值是共享引用** —— `int[] a = b;` 之后改 `a` 会改到 `b`；需要独立副本用 `Arrays.copyOf` 或 `clone()`。
13. **`main` 签名写错** —— `public void main(String[] args)`（缺 `static`）能编译，但运行时报"找不到主方法"。签名必须 `public static void main(String[] args)`。
14. **`java Main.class`** —— 参数是类名不是文件名，正确写法 `java Main`。
15. **`Arrays.binarySearch` 未排序** —— 返回值无意义（可能是负数但不代表"该插在哪"）。先 `Arrays.sort` 再查。
