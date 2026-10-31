# 流程控制与数组

Java 的流程控制与 C 系语法基本一致，但有几处**语义不同**的地方值得单独记住：`switch` 支持字符串与枚举、数组是对象（有 `length` 字段、有默认值、会做越界检查）、增强 for 是只读的。这些差异决定了"照着 C 的直觉写 Java"会在哪里出错。

## 一、`if` 与布尔条件：没有"真值"概念

Java 的条件表达式**必须是 `boolean`**，不存在 C 的"非零即真"：

```java
int n = 1;
// if (n) { }          // 编译错误
if (n != 0) { }        // 必须显式比较
```

这消除了一整类错误：`if (x = 1)`（赋值当比较）在 Java 里因为类型不匹配而直接编译失败。C/C++ 里 `-Wall` 才告警的问题，在 Java 里是编译期硬错误。

## 二、`switch`：从穿透到表达式

经典 `switch` 的规则：

- 支持 `byte`/`short`/`char`/`int`、对应的包装类、`String`（Java 7+）、`enum`。
- **不支持 `long`、`float`、`double`、`boolean`**。
- 漏写 `break` 会**穿透（fall through）**到下一个分支——有时是刻意利用（多个 case 共用逻辑），更多时候是 bug。

```java
switch (day) {
    case 1: case 2: case 3:
        System.out.println("工作日");  // 有意穿透：三个 case 共用一个分支
        break;
    default:
        System.out.println("其他");
}
```

### `switch` 表达式（Java 14+）

新语法用 `->` 消除穿透，并且**可以作为表达式返回值**：

```java
String type = switch (day) {
    case 1, 2, 3 -> "工作日";
    case 6, 7    -> "周末";
    default      -> "未知";
};
```

`yield` 用于多语句分支里返回值。`->` 形式不会穿透，也不需要 `break`——这是 Java 近十年最实用的一处语法改进。

### 字节码层面：`tableswitch` vs `lookupswitch`

- case 值**连续密集** → `tableswitch`：直接按索引跳转，O(1)。
- case 值**稀疏** → `lookupswitch`：二分查找键值，O(log n)。

这是"用空间换时间"的经典编译优化，也解释了为什么"密集 case 更快"不是玄学。`String` 的 `switch` 会先对 `hashCode` 做 `switch`，再在分支里用 `equals` 校验（防哈希碰撞）。

## 三、四种循环的适用场景

| 形式 | 适用 | 注意 |
|---|---|---|
| `for (init; cond; step)` | 需要索引、需要控制步长 | 循环变量作用域限于循环内 |
| `while` | 条件先判断，次数未知 | 条件可能一次都不成立 |
| `do-while` | 至少执行一次 | 结尾必须分号 |
| `for (T x : coll)` | 只读遍历 | **不能改集合结构**，也拿不到索引 |

增强 for 是**只读**的：想边遍历边删，用 `Iterator.remove()` 或 `Collection.removeIf()`。直接在增强 for 里 `list.remove(x)` 会抛 `ConcurrentModificationException`（快速失败机制）。

## 四、数组是对象

`int[] arr` 的类型是"引用数组对象的引用"，因此：

- **有 `length` 字段**（不是方法，不能写 `arr.length()`）。
- **元素有默认值**（`0`/`false`/`null`），因为数组创建时被零初始化。
- **越界抛 `ArrayIndexOutOfBoundsException`**（不是 UB，不是静默读垃圾）。
- **可以赋 `null`**，因此访问前可能需要判空。

```java
int[] arr = new int[3];      // {0, 0, 0}
int[] lit = {3, 1, 4, 1, 5}; // 字面量初始化，长度由元素个数决定
int[][] grid = new int[2][3];// 二维：数组的数组
```

### 二维数组是"数组的数组"，可以是不规则矩形

```java
int[][] jag = new int[3][];
jag[0] = new int[1];
jag[1] = new int[2];      // 每行长度可以不同
```

这与 C 的连续二维数组在内存布局上**完全不同**：C 的 `int a[3][4]` 是一整块连续内存，Java 的 `int[][]` 是"一个数组，元素是指向其他数组的引用"。因此 Java 二维数组的访问多一次间接寻址，缓存局部性更差。

```text
int[][] 的内存结构（Java）

  grid ──► [ ref0, ref1, ref2 ]      外层数组（长度 3）
              │     │     │
              ▼     ▼     ▼
            [0,0] [0,1] [0,2]        三个独立的内层数组
                  [1,0] [1,1]
```

## 五、`Arrays` 工具类与它的坑

- `Arrays.sort(arr)`：对基本类型用**双轴快排**（Dual-Pivot Quicksort），对对象数组用 **TimSort**（稳定，最坏 O(n log n)）。
- `Arrays.binarySearch(arr, key)`：**必须先排序**，否则结果未定义。
- `Arrays.fill(arr, v)` / `Arrays.copyOf(arr, n)` / `Arrays.equals(a, b)`：常用工具。
- `Arrays.asList(...)`：返回**定长视图**，`add`/`remove` 抛 `UnsupportedOperationException`——它背后是原数组，不是 `ArrayList`。要可变就用 `new ArrayList<>(Arrays.asList(...))`。

`Arrays.toString(arr)` 也别忘：直接 `System.out.println(arr)` 打印的是 `[I@1b6d3586` 这种类型+哈希，不是内容。

## 六、边界与陷阱

- **`arr.length()` 编译错误**：`length` 是字段。
- **`ArrayIndexOutOfBoundsException`**：Java 会检查，但仍要避免越界（`for (i <= arr.length)` 是经典错）。
- **增强 for 中修改集合**：抛 `ConcurrentModificationException`。
- **`Arrays.asList` 定长**：见上。
- **`int[] a = b;` 是共享引用**：改 `a` 影响 `b`，拷贝要 `Arrays.copyOf` 或 `clone()`。
- **数组协变 = 运行期检查**：`Object[] o = new String[1]; o[0] = 1;` 编译通过，运行期抛 `ArrayStoreException`。
- **`switch` 漏 `break`**：静默穿透，是逻辑 bug 的高发区。
- **`switch` 不支持 `long`/`double`**：编译报错，别硬试。

## 七、可运行示例：数组、协变与增强 for 的边界

```java
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        int[] arr = {3, 1, 4, 1, 5};
        Arrays.sort(arr);
        System.out.println(Arrays.toString(arr));            // [1, 1, 3, 4, 5]
        System.out.println("idx4 = " + Arrays.binarySearch(arr, 4));

        int[] copy = Arrays.copyOf(arr, arr.length);
        copy[0] = 99;
        System.out.println("shared = " + (arr == copy) + " arr0 = " + arr[0]);

        int[][] jag = new int[2][];
        jag[0] = new int[] {1, 2};
        jag[1] = new int[] {3};
        System.out.println("rows = " + jag.length + " row0 = " + jag[0].length);

        List<Integer> fixed = Arrays.asList(1, 2, 3);
        try { fixed.add(4); } catch (UnsupportedOperationException e) {
            System.out.println("asList is fixed-size");
        }
        List<Integer> growable = new ArrayList<>(fixed);
        growable.add(4);
        System.out.println("growable = " + growable);

        Object[] covariant = new String[1];
        try { covariant[0] = 42; } catch (ArrayStoreException e) {
            System.out.println("covariance checked at runtime");
        }
    }
}
```

最后一段是"数组协变要付运行期代价"的实证：编译期放行，运行期抛 `ArrayStoreException`。`growable` 那段则是 `Arrays.asList` 陷阱的标准绕法。

## 三视角解析

### 🧑‍💻 程序员视角
- `switch` 支持 `String` / `enum`（底层先取 hashCode 再 equals）；**增强 for 只能读**，要边遍历边删就用 `Iterator.remove` / `removeIf`。
- 数组是对象：`length` 是**字段**不是方法；工具方法都在 `Arrays`（排序、二分、转 List）。
- 注意 `Arrays.asList` 返回的是定长视图，不能 `add`（会抛 `UnsupportedOperationException`）——这是高频踩坑点。
- Java 14+ 优先用 `switch` 表达式（`->`），从语法上消除穿透，还能直接返回值。

### 🎓 博士生视角
- Java 数组是**协变**的：`String[]` 是 `Object[]` 的子类型。这是类型系统里的一个著名妥协，代价是必须引入**运行期检查**（`ArrayStoreException`）——即「用运行期开销弥补静态类型系统的宽松」。
- 对比泛型是**不型变**的（`List<String>` 不是 `List<Object>`），两者在可变性设计上的不一致，是 Java 类型系统历史包袱的直接体现。
- `switch` 在字节码中是 `tableswitch`（连续取值，O(1) 跳转表）或 `lookupswitch`（稀疏取值，二分匹配）——这是「用空间换时间」的经典编译优化。
- 增强 for 的快速失败（fail-fast）基于 `modCount` 版本号：迭代器每次 `next()` 校验它是否变化，变化即抛 `ConcurrentModificationException`。它是**错误检测机制，不是并发安全机制**（不保证多线程下一定检测到）。
- Java 的二维数组是"数组的数组"，因此不是连续内存，也没有 C 那种 `a[i][j] = *(*(a+i)+j)` 的指针算术；这既是安全性的代价（多一层引用、多一次跳转），也是灵活性的来源（允许不规则行长度）。

### 📚 考研者视角
- 与 408 **数组（顺序存储）**、二分查找、排序的复杂度分析对应。
- 常考计算：二维数组按行优先存储的地址计算 `LOC(i,j) = base + (i*n + j)*size`；注意这是 C 的模型，Java 的"数组的数组"不适用这条公式。
- 若考程序设计语言，常考「数组的存储与地址计算」「数组协变是否类型安全」。
- 记忆锚点：**数组协变 + 运行期 ArrayStoreException**；**泛型不型变**；**`length` 是字段**；**`Arrays.asList` 定长**。
