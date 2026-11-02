# §4 java-ch01 实战手记：凯喵带你把 Java 基础用「翻车」

> 前三节把 Hello World、基本类型、变量、控制流、数组讲透了。这一节凯喵把新手最容易「编译不过 / 静默出错 / 溢出」的 12 个现场搬出来——每个都是入门必踩的坑。

### 现场一：main 签名写错，运行时找不到主方法

凯喵写 `public void main(String[] args)`（缺 `static`）能编译，但运行时报「找不到主方法」。JVM 规范要求签名必须是 `public static void main(String[] args)`，少一个修饰符都不认。

```java
public class Main {
    public static void main(String[] args) {   // ✅ 一个都不能少
        System.out.println("hi");
    }
}
```

### 现场二：把文件名和 public 类名写不一致，编译失败

凯喵把 `public class Hello` 存进 `World.java`，编译器直接报错「类名与文件名不符」。一个 `.java` 文件里若有 `public class`，文件名必须和它**完全一致**（含大小写）。

```java
// 文件必须命名为 Hello.java
public class Hello { public static void main(String[] a){} }
```

### 现场三：整数溢出不报错，结果变负数

凯喵 `int n = 2_000_000_000; System.out.println(n * 2);` 输出 `-294967296`。`int` 约 ±21 亿，乘法溢出后回绕成负数，且**不抛异常**。大数运算用 `long` 或 `Math.multiplyExact`（溢出抛异常）。

```java
long a = 2_000_000_000L;          // ✅ 加 L 变 long
System.out.println(a * 2);        // 4000000000
// 或 Math.multiplyExact 溢出即抛 ArithmeticException
```

### 现场四：== 比较包装类型比的是地址

凯喵 `Integer a = 200, b = 200; System.out.println(a == b);` 输出 false。自动装箱只缓存 -128~127，超出范围是不同对象，`==` 比地址。比较值一律用 `equals`，或先拆箱。

```java
Integer a = 200, b = 200;
System.out.println(a.equals(b));     // ✅ true
System.out.println(a.intValue() == b.intValue());  // ✅ 拆箱比
```

### 现场五：浮点数直接判相等，永远不等

凯喵 `if (0.1 + 0.2 == 0.3)` 得到 false——二进制浮点有精度误差，`0.1+0.2` 实际是 `0.30000000000000004`。比较浮点用**误差范围**（abs 差 < 1e-9）。

```java
double d = 0.1 + 0.2;
if (Math.abs(d - 0.3) < 1e-9) {     // ✅ 误差范围内判等
    System.out.println("equal");
}
```

### 现场六：数组下标越界，运行时崩

凯喵 `int[] a = new int[3]; a[3] = 1;` 直接 `ArrayIndexOutOfBoundsException`。合法下标是 `0 ~ length-1`，循环条件写 `i < a.length` 别写 `<=`。

```java
int[] a = new int[3];
for (int i = 0; i < a.length; i++) {   // ✅ 0..2
    a[i] = i;
}
```

### 现场七：foreach 遍历时修改集合，抛异常

凯喵 `for (int x : list) if (x < 0) list.remove(x);` 抛 `ConcurrentModificationException`。foreach 底层是迭代器，结构性修改会破坏其一致性。用 `Iterator.remove()` 或 `removeIf`。

```java
list.removeIf(x -> x < 0);          // ✅ 安全移除
// 或 Iterator 显式 remove
```

### 现场八：字符串用 == 比较内容，永远不对

凯喵 `if (s1 == s2)` 判断两个字符串相等，常得到 false。`==` 比地址，`String` 是对象，比内容用 `equals`；注意先判 null 防 NPE，或用 `Objects.equals`。

```java
String s1 = new String("a"), s2 = new String("a");
System.out.println(s1.equals(s2));          // ✅ true
System.out.println(Objects.equals(s1, s2)); // ✅ 自带 null 安全
```

### 现场九：局部变量不初始化就使用，编译不过

凯喵 `int x; System.out.println(x);` 编译报错——局部变量**不默认初始化**，必须用过就必须先赋值。成员变量才会被默认初始化（0 / null / false）。

```java
int x = 0;          // ✅ 定义即初始化
System.out.println(x);
```

### 现场十：switch 漏写 break，case 穿透

凯喵 `switch` 每个 case 忘写 `break`，结果匹配到一个 case 后把后面所有 case 都执行了（fall-through）。除非故意贯穿，否则每个 case 结尾加 `break`；Java 14+ 可用 `switch` 表达式避免。

```java
switch (day) {
    case 1: System.out.println("一"); break;   // ✅ break 防穿透
    case 2: System.out.println("二"); break;
    default: System.out.println("?");
}
```

### 现场十一：除零对整数抛异常，对浮点给 Infinity

凯喵 `int r = 1 / 0;` 抛 `ArithmeticException`，但 `double r = 1.0 / 0;` 得到 `Infinity` 不抛。整数除法前先判除数非零；浮点除零会得到特殊值，比较时要用 `Double.isFinite`。

```java
if (denom != 0) result = num / denom;   // ✅ 整数除法先判零
double d = num / 0.0;
if (Double.isFinite(d)) { ... }          // ✅ 浮点先判有限
```

### 现场十二：增强 for 遍历数组时改数组长度，概念混淆

凯喵以为在 foreach 里能增删数组元素，结果编译都过不了——数组**长度固定**，没有 add/remove；要动态增删用 `ArrayList`。集合和数组的 API 别混。

```java
// 数组长度固定，要动态用 List
List<Integer> list = new ArrayList<>(Arrays.asList(1,2,3));
list.add(4);                  // ✅ List 可动态增删
```

> 凯喵总结：Java 基础的坑九成是「签名/文件名」「== vs equals」「整数溢出」「浮点精度」「数组越界」。把这 12 个现场刻进肌肉记忆，入门少掉几根头发。

### 现场之外：凯喵的基础三件事
每次教新人写 Java，凯喵都让他们先把三件事刻进手感。第一件事，分清楚「基本类型」和「包装类型」：int 是值、Integer 是对象，== 对前者比值、对后者比地址，比较内容永远用 equals，这件事想错一次就会在函数里传串错值。第二件事，整数运算前先想清楚会不会溢出，金额、计数、ID 这类一旦超 int 范围就用 long，乘法用 Math.multiplyExact 兜底。第三件事，浮点永远别直接判等，误差范围内比较才是正道。这三件事看似琐碎，却是 Java 代码里最高频的隐藏 Bug 来源，比任何高级特性都值得先练熟。

### 现场拾遗：编译器是你的第一道防线
再补一个心态：Java 编译器很严格，报错不是来烦你的，是替你把一半低级错误挡在运行前。新人常犯的「能编译就说明对了」是错的，编译过只是语法对，逻辑和边界还是要自己想清楚。但反过来，凡是编译器能替你查的——@Override、final、显式类型、不要的未使用变量——都让它查，别用各种方式绕过警告。把编译器当搭档而不是对手，入门阶段能少踩无数坑。

### 一句话收尾
凯喵最后提醒：Java 基础这些规则看起来零碎，但它们的共同底色只有一句话——「类型系统和内存模型是认真的，别跟它对着干」。整数有范围、对象比的是地址、浮点有误差、数组有边界，这些都是语言在设计时就定死的物理规律。接受它们、顺着它们写，代码就稳；总想「差不多就行」，Bug 就在这些差不多里生根。把基础当规律而不是约定，你会比很多写了几年的人都稳。

### 收个尾
说到底，基础章节的价值不在 memorize，而在形成一种「下笔前先想边界」的直觉。等你写到泛型、集合、并发那一章，会发现今天这些坑全都会换身衣服重新出现。地基稳了，上面的楼才盖得高。
