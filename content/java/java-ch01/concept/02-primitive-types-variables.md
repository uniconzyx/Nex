# 八种基本类型、变量与类型转换

Java 只有八种基本类型，其余都是引用类型（对象）。

这个设计选择值得先说清楚：基本类型**按值存储、不进堆、没有对象头开销**，是 Java 在"纯面向对象"与"性能"之间留的一道后门。代价是它们不能参与泛型（必须装箱）、不能为 `null`（因此没有"缺失值"的表达），以及拆装箱带来的隐式开销。

## 一、八种基本类型与它们的固定位宽

| 类型 | 位宽 | 范围 / 默认值 | 说明 |
|------|------|--------|------|
| `byte` | 8 | −128 ~ 127 / 0 | 整数，常用于字节流 |
| `short` | 16 | −32768 ~ 32767 / 0 | 整数，很少用 |
| `int` | 32 | ±21 亿 / 0 | **默认整数字面量类型** |
| `long` | 64 | 很大 / 0L | 字面量需加 `L` |
| `float` | 32 | IEEE 754 单精度 / 0.0f | 字面量需加 `f` |
| `double` | 64 | IEEE 754 双精度 / 0.0d | **默认浮点字面量类型** |
| `char` | 16 | 0 ~ 65535 / '\u0000' | **无符号** UTF-16 码元 |
| `boolean` | — | true / false | 规范未规定位宽 |

两点容易忽略：

- **Java 没有无符号整数类型**（除 `char`）。需要处理无符号值用 `Integer.parseUnsignedInt`、`Long.toUnsignedString` 等工具方法。
- **`boolean` 的位宽由实现决定**，规范只保证能表示 true/false。别假定它是 1 位或 1 字节。

## 二、变量、常量与作用域

```java
int count = 10;            // 变量
final double PI = 3.14159; // 常量：只能赋值一次
```

`final` 修饰基本类型表示"值不可变"；修饰引用表示"引用不可重新指向"（**对象内容仍可变**）——这是 `final List` 仍能 `add` 的原因，常被误解。

Java 的局部变量**必须显式初始化**才能使用，编译器会做**确定赋值分析**（definite assignment）。这与 C/C++ 的"未初始化局部变量是垃圾值"完全不同，是 Java 消除一整类 UB 的体现。

## 三、类型转换：拓宽安全，收窄丢精度

### 拓宽（widening）：自动，安全

`byte → short → int → long → float → double`，以及 `char → int → long → float → double`。方向单调，不会丢信息（`int → float` 例外：超过 2²⁴ 的整数会丢低位）。

### 收窄（narrowing）：必须强转，可能丢高位

```java
double d = 10.0 / 4;   // 2.5
int i = (int) d;       // 2，直接截断小数
int big = 300;
byte b = (byte) big;   // 44（300 - 256），截断高位
```

注意 `(int)` 是**向零截断**，不是四舍五入。要四舍五入用 `Math.round(d)`（返回 `long`）。

### 二元运算的自动提升

三条规则，全部与"结果类型"有关：

1. 若任一操作数是 `double` → 结果是 `double`；`float` 次之；`long` 再次。
2. 否则（都是整型且不含 `long`）→ **两边都提升为 `int`**。
3. 因此 `byte + byte` 的结果是 `int`，`byte b = b1 + b2;` 编译报错，必须强转。

```text
二元数值提升的方向（结果类型）

  double ← float ← long ← int ← {byte, short, char}
                                     ↑
                        三者参与运算一律先升为 int
```

这条规则解释了新手最常见的编译错误：`short s = 1; s = s + 1;` 报"可能丢失精度"——因为 `s + 1` 是 `int`。写成 `s += 1`（复合赋值自带隐式收窄）就合法。

## 四、`char` 是 UTF-16 码元，不是字符

`char` 是 16 位**无符号**整数，表示一个 UTF-16 码元。基本平面的字符（BMP，含绝大多数中日韩汉字）一个 `char` 够用；**补充平面**（不少 emoji、部分生僻字）需要**两个 `char` 组成的代理对**。

因此 `String.length()` 返回的是**码元数**，不是字符数：

```java
String s = "𝄞";               // U+1D11E，占两个 char
s.length();                    // 2
s.codePointCount(0, s.length()); // 1 ← 真正的字符数
```

这个区别在做文本截断、光标位置、字数统计时是致命的：按 `length()` 截断可能把代理对切成两半，得到非法字符串。

## 五、包装类与缓存：`==` 的陷阱区

每个基本类型都有包装类（`Integer`、`Long`、`Double`、`Character`…）。自动装箱（`Integer x = 1;`）与拆箱（`int y = x;`）由编译器插入 `valueOf`/`intValue` 调用。

关键事实：**`Integer.valueOf` 对 −128~127 有缓存**（`IntegerCache`，上界可用 `-XX:AutoBoxCacheMax` 调），因此：

```java
Integer a = 127, b = 127;
a == b;             // true —— 同一个缓存对象
Integer c = 128, d = 128;
c == d;             // false —— 超出缓存，两个不同对象
```

结论不是"记住 127 这个数"，而是**包装类比较值一律用 `equals`**。用 `==` 比包装类是 bug，与缓存范围无关。

## 六、浮点：`double` 不能表示金额

`0.1` 在二进制下是无限循环小数，`double` 只能存近似值。于是：

```java
0.1 + 0.2 == 0.3;                  // false
new BigDecimal(0.1);               // 0.1000000000000000055511151231257827...
new BigDecimal("0.1");             // 0.1 ← 正确写法
```

金额必须用 `BigDecimal`，且**必须用字符串构造**（或 `BigDecimal.valueOf(0.1)`，它走 `Double.toString` 再解析）。除法还要指定 `scale` 与 `RoundingMode`，否则 `1/3` 会抛 `ArithmeticException`。

## 七、边界与陷阱

- **整数字面量默认 `int`**：`long x = 10000000000;` 编译报错，必须 `10000000000L`。
- **`float` 字面量必须加 `f`**：`float f = 3.14;` 报错（`double` 不能隐式收窄）。
- **`byte`/`short` 运算升为 `int`**：`s = s + 1` 编译错误，用 `s += 1` 或强转。
- **`char` 参与运算变成 `int`**：`char c = 'a' + 1;` 需要强转 `(char)`。
- **自动拆箱 NPE**：`Integer x = null; int y = x;` 抛 `NullPointerException`，且堆栈里看不到业务代码行。
- **`==` 比包装类**：见上，用小整数时"恰好正确"，掩盖 bug。
- **`Integer.MIN_VALUE` 取绝对值溢出**：`Math.abs(Integer.MIN_VALUE)` 仍是负数。

## 八、可运行示例：一次看清溢出、缓存与浮点误差

```java
public class Main {
    public static void main(String[] args) {
        int max = Integer.MAX_VALUE;
        System.out.println("overflow = " + (max + 1));          // -2147483648（回绕）

        System.out.println("div = " + (10 / 4) + " / " + (10.0 / 4));
        System.out.println("trunc = " + (int) -2.7);            // -2（向零截断）

        Integer a = 127, b = 127, c = 128, d = 128;
        System.out.println("cached = " + (a == b) + " uncached = " + (c == d));
        System.out.println("equals = " + c.equals(d));

        System.out.println("fp = " + (0.1 + 0.2));              // 0.30000000000000004
        System.out.println("char_add = " + (char) ('a' + 1));   // b

        String s = "𝄞";
        System.out.println("len = " + s.length() + " cp = " + s.codePointCount(0, s.length()));
    }
}
```

六行输出覆盖了本章全部要点：`int` 溢出回绕（不是异常，是模运算）、整除与浮点除的差别、强转向零截断、包装类缓存边界、浮点误差、`char` 运算升为 `int`、以及码元数 ≠ 字符数。

## 三视角解析

### 🧑‍💻 程序员视角
- 八种基本类型记不住时按类分：4 种整数（`byte/short/int/long`）、2 种浮点（`float/double`）、`char`、`boolean`。
- **包装类的 `==` 在 −128~127 之外是比地址**，所以比较值一律用 `equals` 或先拆箱。
- **金额绝不用 `double`**，用 `BigDecimal`（构造要用字符串，`new BigDecimal(0.1)` 本身就不精确）。
- 局部变量必须初始化，这是 Java 相对 C/C++ 的一大优势；别用 `int x = 0;` 掩盖"忘了赋值"的逻辑错误。

### 🎓 博士生视角
- Java 的基本类型**位宽是语言规范固定的**（`int` 恒为 32 位），因此跨平台行为一致；这点与 C 的 `int` 随平台变化形成鲜明对比，是 Java 可移植性设计的一部分。
- `char` 是 **16 位 UTF-16 码元**而非完整字符：补充平面（如不少 emoji）需要**两个 char（代理对）**表示，这导致 `String.length()` 不等于「字符数」——`length()` 数的是码元。正确做法是用 `codePointCount`。
- `double` 是 IEEE 754 双精度：无法精确表示 0.1（二进制无限循环），因此累加会有误差；`BigDecimal` 用十进制表示规避了这一点。
- 整数溢出在 Java 中是**静默回绕**（定义良好的模 2ⁿ 运算），不是 UB 也不抛异常——这与 C 的有符号溢出（UB）属于两种完全不同的处理哲学；Java 8 起可用 `Math.addExact` 主动抛 `ArithmeticException`。
- 确定赋值分析（definite assignment）是编译期的数据流分析：编译器证明每个局部变量在使用前必被赋值，从而**在语言层面消除了"读未初始化内存"**这一类整型 UB。

### 📚 考研者视角
- **408 计组交叉**：定点表示与**补码**、浮点的 IEEE 754 格式（符号位/阶码/尾数）、数据类型位宽与溢出。
- 常考计算：给定字节数求可表示范围、补码加减与溢出判断、float 的位模式拆解。
- 常考辨析：自动类型转换（拓宽）与强制类型转换（收窄）的规则；`int` 与 `float` 互转时的精度损失。
- 记忆锚点：**Java 基本类型位宽固定**；**`char` 是 UTF-16 码元，`length()` 不等于字符数**；**`byte`/`short` 运算先升 `int`**。
