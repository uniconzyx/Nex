# 01 · 对象模型与命名空间：从 CPython 视角看"变量"

## 一、理论根基：一切皆对象与名字绑定

（博士视角）Python 是"一切皆对象"的纯面向对象语言：整型、函数、类、模块、甚至代码块都是 `PyObject*`。变量不是"盒子"，而是**名字到对象的绑定（binding）**——赋值把名字"贴"到对象上，而非把值搬进存储位置。这与 C++（变量=带类型的存储位置）、Java（基本类型在栈/引用在堆）有本质区别。

```python
a = 1        # a 绑定到小整数对象 1（CPython 对 -5~256 整数池 intern）
b = a        # b 绑定到同一个对象，对象 ob_refcnt 加 1
a = a + 1    # 创建新对象 2，a 重新绑定；b 仍指向 1
print(a, b)  # 2 1
```

## 二、实现机制：CPython 的对象头与引用计数

每个对象在 C 层是 `PyObject`（变长对象为 `PyVarObject`）：

```c
struct _object { PyObject_HEAD; ... };
/* PyObject_HEAD 展开为:
   struct _typeobject *ob_type;   // 类型指针
   Py_ssize_t ob_refcnt;          // 引用计数
*/
```

- **引用计数（refcount）**：`ob_refcnt` 在每次 `Py_INCREF/Py_DECREF` 时增减，归零即同步释放（无分代 GC 的"即时"回收）。`sys.getrefcount(x)` 可观察（该函数本身会 +1）。
- **GIL（Global Interpreter Lock）**：CPython 用一把全局锁保护引用计数的原子性——这就是单进程多线程无法用多核做纯 Python 计算的根因。GIL 不是对象模型本身，而是 CPython 为线程安全付出的实现代价，与 C++/Java 的对象头（无解释器级锁）不同。
- **不可变对象语义**：`int/str/tuple/frozenset/bytes` 创建后不可改；"修改"= 创建新对象 + 重新绑定。好处：哈希可缓存（可作 dict 键）、默认线程安全；代价：大整数频繁改写有分配开销。

## 三、命名空间与作用域（LEGB）

（程序员视角）名字存在于**命名空间**——本质就是 dict（`func.__globals__`、`locals()`、`type(obj).__dict__`）。查找顺序 **LEGB**：

1. **L**ocal：当前函数局部
2. **E**nclosing：外层嵌套函数的局部
3. **G**lobal：模块全局
4. **B**uiltin：`builtins` 模块

关键：Python 是**静态（词法）作用域**——名字在哪**定义**决定去哪找，与调用位置无关。作用域在**编译期**由 `def`/`lambda`/`class`/推导式划定，而非运行期。

## 四、工程实践与对比

- C++：变量是内存位置，传参有值/引用/指针；Java：基本类型值传递、对象引用值传递。Python 只有"对象引用"一种模型——所谓"传值 vs 传引用"的争论被**统一为传对象引用（call by sharing）**。
- 用 `id()` 看对象身份，`is` 比身份，`==` 比值；绝不依赖小整数池判断 `is`。
- 要修改外层变量：闭包内用 `nonlocal`，模块级用 `global`。

## 五、可运行代码

见 `examples/ex04-LEGB.json`（LEGB 查找）、`examples/ex08-global-statement.json`（global 改写）。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 名字查找顺序 **LEGB**（Local → Enclosing → Global → Built-in）；函数内给变量赋值会自动把它变成局部变量，想改外层要用 `global` / `nonlocal`。
- 不要用 `global` 传状态，那是隐式耦合；改用返回值、类或依赖注入。
- `dir()` / `vars()` / `globals()` 是排查「名字到底绑到哪去了」的实用工具。

### 🎓 博士生视角
- 命名空间就是**名字到对象的 dict 映射**：模块、类、函数、内建各有一层。名字查找在运行时进行（`LOAD_GLOBAL` 带 dict 版本号缓存），与静态语言的「符号表 + 栈帧偏移」根本不同。
- 赋值语句决定**写哪一层命名空间是编译期决定的**（`STORE_FAST` / `STORE_DEREF` / `STORE_GLOBAL`），不是运行时判断——这解释了为什么在函数里赋值后，之前的读取也变成局部引用（`UnboundLocalError` 的成因）。
- 闭包的自由变量被编译进 **cell 对象**，使内外层共享同一变量；这与「拷贝值」语义截然不同。

### 📚 考研者视角
- 与**编译原理**的符号表、作用域链、嵌套作用域访问链（静态链/Display 表）直接对应，是很好的交叉理解素材。
- 若考程序设计语言原理，常考「静态作用域 vs 动态作用域」「闭包与自由变量」。
- 记忆锚点：**LEGB**；**函数内赋值会让名字变局部，除非声明 `global` / `nonlocal`**。
