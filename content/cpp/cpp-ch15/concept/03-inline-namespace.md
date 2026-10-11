# 03 · inline namespace：版本化、ABI 兼容与别名

## 一、理论根基：为什么需要「inline namespace」

库的演进常面临两难：**改了 API 想要新名字空间隔离（v1/v2），又不想让老用户每次都写 `mylib::v2::foo`**。C++11 的 `inline namespace` 让某个命名空间**「透明」**——其内部的名字可被外层命名空间**直接看到**（无需额外限定），同时保留版本隔离能力。

```cpp
namespace mylib {
    inline namespace v2 {
        void f() { /* 新实现 */ }
    }
    namespace v1 {
        void f() { /* 旧实现 */ }
    }
}
// 调用方写 mylib::f() 默认选中 v2；需要时显式 mylib::v1::f()
```

## 二、实现机制：透明性从何而来

`inline namespace` 的名字在**未限定查找**时会**自动「穿透」**到外层命名空间——等价于编译器在外层「自动 `using` 了它」。因此：
- `mylib::f` 不经限定即可命中 `mylib::v2::f`。
- 它的符号**仍具有外部链接**，且 mangling 中的版本前缀被「抹平」，所以**二进制层面 `mylib::v2::f` 与直接 `mylib::f` 是同一符号**——这正是 ABI 兼容的关键：老二进制调用 `mylib::f@v2` 不受影响，新代码也可直接写 `mylib::f`。

> ABI 兼容要点：当你只想**改实现不改接口**时，把实现放进 `inline namespace` 并切换当前默认版本，已编译的调用方无需重编（符号名不变）；若要**破坏性改接口**，则新增 `v3` 并保留旧 `v2` 不被 inline，让旧符号继续存在。

## 三、工程实践：程序员视角的取舍

- **库的版本切换**：std 自身就用过类似的 `inline namespace std::literals` 等机制。
- **宏式版本宏 + 条件 inline**：用 `#if` 决定哪个版本被 inline，做到编译期切版本。
- **不要和匿名命名空间混淆**：匿名=内部链接（每 TU 一份）；inline=外部链接（透明导出）。二者目的相反。

## 四、边界与陷阱

- inline 嵌套太深会让「默认选中谁」变得不直观，建议版本层保持扁平（一个 `inline` 版本）。
- 若把「破坏性变更」也放进 inline，会**破坏 ABI**（符号名虽同但语义变了）→ 必须新建非 inline 版本命名空间。

## 五、可运行示例（见 `examples/ex04-inline-version.md` 对应 ex04）

```cpp
#include <iostream>
namespace mylib {
    inline namespace v2 { const char* who() { return "v2"; } }
    namespace v1       { const char* who() { return "v1"; } }
}
int main() {
    std::cout << mylib::who() << ' ' << mylib::v1::who() << '\n';
}
```

**输出**：`v2 v1`

---

## 三视角解析

### 🧑‍💻 程序员视角
- **`inline namespace` 用于 ABI 版本化**：`namespace lib { inline namespace v2 { ... } }`，用户仍写 `lib::foo`，但符号名里带上 `v2`，从而实现「同名接口 + 不同符号」的平滑升级（libstdc++ 大量使用此技巧）。
- 升级时把 `inline` 从 v1 移到 v2，**旧二进制仍能链接到 v1 的符号**，这是它相比「改版本号前缀」的关键优势。
- 注意：`inline namespace` 里的名字会被**自动导入父命名空间**，所以可能与父命名空间的同名实体冲突。

### 🎓 博士生视角
- `inline namespace` 的名字**被隐式 `using` 到外层**，因此它对用户透明，但对**名称修饰（name mangling）**可见——这使它成为「**接口不变、符号变化**」的唯一标准手段。
- 从 ABI 兼容看，它把「版本」编码进**符号名**而非源代码结构，因此对源码级兼容与二进制级稳定性可以分开处理——这是大型库长期演进的工程基石。
- 与 `using namespace` 的对照：后者是「名字可见性指令」，前者是「名字可见性 + 符号参与修饰」的复合机制。

### 📚 考研者视角
- 记忆锚点：**`inline namespace` 里的名字对外层透明，但参与符号修饰（ABI 版本化）**。
- 常考辨析：**匿名命名空间（内部链接、TU 私有）vs `inline` 命名空间（对外透明、ABI 版本）**——名字相近但语义几乎相反。
- 若问「如何做二进制兼容的库升级」：答**保持接口名不变、把实现放在新的 `inline namespace` 里**。

---
