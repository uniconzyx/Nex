# 流程控制与数组

## 流程控制

`if/else`、`switch`（Java 7+ 支持 `String`）、`for`、`while`、`do-while` 与 C 系语法基本一致。

```java
int n = 7;
if (n % 2 == 0) {
    System.out.println("even");
} else {
    System.out.println("odd");
}

for (int i = 1; i <= 5; i++) {
    System.out.println(i);
}
```

`switch` 每个 `case` 后通常需要 `break`，否则会"穿透"到下一个分支。

## 一维数组

数组是固定长度的引用对象，长度通过 `.length` 属性（不是方法）获取。

```java
int[] arr = {3, 1, 4, 1, 5};
int max = arr[0];
for (int k = 1; k < arr.length; k++) {
    if (arr[k] > max) max = arr[k];
}
// 增强 for 遍历
for (int x : arr) {
    System.out.println(x);
}
```

> 数组下标从 0 开始；越界访问抛 `ArrayIndexOutOfBoundsException`。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `switch` 支持 `String` / `enum`（底层先取 hashCode 再 equals）；**增强 for 只能读**，要边遍历边删就用 `Iterator.remove` / `removeIf`。
- 数组是对象：`length` 是**字段**不是方法；工具方法都在 `Arrays`（排序、二分、转 List）。
- 注意 `Arrays.asList` 返回的是定长视图，不能 `add`（会抛 `UnsupportedOperationException`）——这是高频踩坑点。

### 🎓 博士生视角
- Java 数组是**协变**的：`String[]` 是 `Object[]` 的子类型。这是类型系统里的一个著名妥协，代价是必须引入**运行期检查**（`ArrayStoreException`）——即「用运行期开销弥补静态类型系统的宽松」。
- 对比泛型是**不型变**的（`List<String>` 不是 `List<Object>`），两者在可变性设计上的不一致，是 Java 类型系统历史包袱的直接体现。
- `switch` 在字节码中是 `tableswitch`（连续取值，O(1) 跳转表）或 `lookupswitch`（稀疏取值，二分匹配）——这是「用空间换时间」的经典编译优化。

### 📚 考研者视角
- 与 408 **数组（顺序存储）**、二分查找、排序的复杂度分析对应。
- 若考程序设计语言，常考「数组的存储与地址计算」「数组协变是否类型安全」。
- 记忆锚点：**数组协变 + 运行期 ArrayStoreException**；**泛型不型变**。
