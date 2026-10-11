# 02 · 格式化控制：操纵符、浮点精度与对齐

## 一、理论根基：格式化是「状态 + 一次性修饰符」的混合模型

iostream 的格式控制有两类：

1. **持久状态**（`setf`/`unsetf` 控制的格式标志，如 `boolalpha`、`showpos`）：设置后一直生效，直到再次改变。
2. **一次性操纵符（manipulator）**：作用于紧接着的下一个 IO 操作，过后恢复。典型如 `setw(n)`——**只影响下一次字段宽度**，这是新手常误解的点。

> 第一性原理：`setw` 是「一次性」而非「持久」，因为宽度是一次性布局需求；而 `setprecision` 是「持久」的，因为它描述的是浮点表示的语义。把二者混为一谈是格式化 bug 的常见来源。

## 二、实现机制：locale 与 facet 的代价

默认 locale（通常是 `"C"` 或系统本地化）里包含 `numpunct`、`ctype` 等 **facet**（方面）。每次格式化一个数字，都要经过 facet 的虚函数调用做「千位分隔符」「小数点字符」等处理。这正是 iostream 慢于 `printf` 的另一处原因——`printf` 的 `%d` 几乎直接格式化。

- `std::fixed` + `std::setprecision(n)`：固定小数点后 n 位（定点表示）。
- `std::scientific` + `setprecision(n)`：科学计数法，小数点后 n 位。
- **默认（不指定 fixed/scientific）**：`setprecision(n)` 表示**有效数字**位数（总位数），且默认 `float` 只打印 6 位有效数字——这正是「浮点默认精度丢失」假象的根源（不是真的丢，是显示位数不够）。

## 三、工程实践：对齐表格与浮点

常用操纵符（需 `#include <iomanip>`）：

| 操纵符 | 作用 |
|---|---|
| `setw(n)` | 下一次字段最小宽度（一次性） |
| `setfill(c)` | 不足宽度时的填充字符（持久） |
| `left` / `right` / `internal` | 对齐方式（持久） |
| `setprecision(n)` | 浮点精度（持久，含义随 fixed/scientific 变） |
| `fixed` / `scientific` | 定点 / 科学计数（持久） |
| `boolalpha` | 把 `bool` 输出为 `true`/`false`（持久） |

构造对齐报表的惯用法：
```cpp
std::cout << std::left << std::setfill('.') << std::setw(12) << "Name"
          << std::right << std::setw(8) << std::fixed << std::setprecision(2) << 3.14159 << '\n';
// 输出：Name........    3.14
```

## 四、边界与陷阱

1. **`setw` 只管下一个输出**，链式写多个字段时每个都要单独 `setw`。
2. **浮点默认 6 位有效数字**：`std::cout << 0.123456789;` 只显示 `0.123457`，容易被误判为精度丢失。
3. `setprecision` 与 `fixed` 的组合语义完全不同，务必成对设置。
4. `std::endl` 会 `flush`，在循环中高频使用会严重拖慢 IO——用 `'\n'` 代替。

## 五、可运行示例：浮点与对齐

```cpp
#include <iostream>
#include <iomanip>
int main() {
    double pi = 3.14159265358979;
    std::cout << "默认: " << pi << '\n';                  // 6 位有效数字
    std::cout << "定点2位: " << std::fixed << std::setprecision(2) << pi << '\n';
    std::cout << "科学3位: " << std::scientific << std::setprecision(3) << pi << '\n';

    std::cout << std::defaultfloat;                       // 恢复默认
    std::cout << std::left << std::setfill('#') << std::setw(8) << "apple"
              << std::right << std::setw(6) << 42 << '\n';
}
```

**输出**：
```
默认: 3.14159
定点2位: 3.14
科学3位: 3.142e+00
apple###    42
```
> 观察点：① 默认只给 6 位有效数字；② `fixed`+`setprecision(2)` 才真正保留两位小数；③ `setw` 一次性、`setfill` 持久；④ `left`/`right` 决定填充方向。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **格式化是「有状态」的**：`setw` 只影响**下一次**输出，而 `fixed`/`setprecision`/`setfill` 会**持续生效**直到被改回——忘记恢复是常见 bug。
- 输出对齐表格：`setw(10) << left << setfill('.')`；恢复默认用 `resetter` 或手动 `std::defaultfloat`、`setfill(' ')`。
- 浮点默认是 `defaultfloat`（6 位有效数字），要固定小数位必须 `fixed << setprecision(n)`（注意此时 `setprecision` 含义变为**小数位数**）。

### 🎓 博士生视角
- 操纵符（manipulator）本质是**函数指针**：`operator<<(ostream&, ostream&(*)(ostream&))`，所以 `std::endl` 能「顺带」刷新缓冲区（它做了 `flush` 而 `'\n'` 不做）。
- `setprecision` 的语义**随 floatfield 而变**：`defaultfloat` 下是有效数字、`fixed/scientific` 下是小数位——同一 API 两种语义，是历史遗留的设计债。
- `std::format`（C++20）用 `{}` 占位 + 编译期格式检查取代状态机式操纵符，本质是**把格式化从「流状态」改为「纯函数」**，消除了状态泄漏。

### 📚 考研者视角
- 记忆锚点：**`setw` 是一次性、`setprecision/setfill/fixed` 是持续性的**。
- 常考细节：**`std::endl` 会 flush，`'\n'` 不会**——因此循环中大量输出应优先用 `'\n'`（性能差异显著）。
- 与 C 的 `printf` 对照：`%f` 默认 6 位小数、`%g` 自动选择——与 `defaultfloat`/`fixed` 的组合语义可对照记忆。

---
