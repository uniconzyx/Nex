# py-ch02 · 函数与作用域：易错点（Pitfalls）

本章坑多来自一个根因：**Python 的"名字绑定"语义与`默认参数/闭包变量`的求值时机**。
理解这三点，80% 的坑自动消失：① 变量是名字不是盒子；② 默认参数在 **`def` 执行时求值一次**；③ 闭包捕获的是**变量本身**而非当时的值。

---

1. **可变默认参数（最经典的坑）**
   ```python
   def add(x, lst=[]):        # 错：[] 在函数定义时创建一次，被所有调用共享
       lst.append(x)
       return lst
   add(1); add(2)             # [1, 2] 而不是 [2]
   ```
   **原理**：`def` 语句执行时，默认参数表达式被求值并绑定到函数对象的 `__defaults__`（可用 `add.__defaults__` 查看）。列表是可变对象，多次调用共享同一份。
   **正解**：用 `None` 哨兵惰性初始化 `def add(x, lst=None): lst = [] if lst is None else lst`。

2. **闭包延迟绑定（循环里创建 lambda/函数）**
   ```python
   funcs = [lambda: i for i in range(3)]
   [f() for f in funcs]       # [2, 2, 2] 而不是 [0, 1, 2]
   ```
   **原理**：闭包捕获的是**变量 `i` 这个 cell**（自由变量按引用绑定），调用时才去查值；循环结束时 `i=2`。
   **正解**：用默认参数固化当时值 `lambda i=i: i`，或 `functools.partial`。

3. **`global` / `nonlocal` 误用导致 `UnboundLocalError`**
   ```python
   x = 10
   def f():
       print(x)   # UnboundLocalError：本函数内有 x=... 赋值，x 被判为局部
       x = 1
   ```
   **原理**：作用域在**编译期**决定——函数体内任何位置对名字赋值，该名字在整个函数内都是局部的（存于 `f.__code__.co_varnames`）。
   **正解**：要改外层用 `global`（模块级）或 `nonlocal`（闭包外层，Python 3 专属，且外层必须已绑定）。

4. **lambda 里塞语句 / 多表达式**
   `lambda` 主体只能是**单个表达式**，不能写 `return`、`if` 语句块、`for` 循环。
   **正解**：用条件表达式 `lambda x: x if x > 0 else -x`，或改用 `def`。lambda 适合短小回调，超过一行就该用 `def`（可读性也是工程指标）。

5. **参数顺序写错：`SyntaxError: non-default argument follows default argument`**
   `def f(a=1, b)` 非法。顺序必须是：位置参数 → 默认参数 → `*args` → 仅关键字（`*` 后）→ `**kwargs`。
   **深层**：这是**调用侧能否无歧义匹配**的语法保证；仅关键字参数（`def f(a, *, debug=False)`）正是为了强制调用方写清 `debug=`。

6. **装饰器丢元信息（不用 `functools.wraps`）**
   ```python
   def deco(f):
       def wrapper(*a, **k): return f(*a, **k)
       return wrapper
   @deco
   def foo(): "doc"
   foo.__name__   # 'wrapper'，文档与签名丢失
   ```
   **后果**：日志/文档工具（Sphinx）、依赖注入框架（按签名）、`inspect.signature` 全部失真，调试时堆栈也难读。
   **正解**：`@wraps(f)` 复制 `__name__/__doc__/__module__/__wrapped__`。

7. **`*args` / `**kwargs` 解包顺序与重复键**
   调用时 `f(*a, **b, *c)` 中多个 `**` 解包**不允许重复键**（`TypeError: got multiple values for keyword argument`）；定义时 `*args` 之后的普通参数是**仅关键字**。
   另外 `f(*a, **b)` 在 Python 3.5+ 才支持一次调用里多次解包。

8. **把函数属性当"静态变量"却忘了它是全局共享**
   `def f(): f.counter = getattr(f, "counter", 0) + 1` 能工作，但 **递归/并发下不是线程安全**，且测试之间互相污染。
   **正解**：需要状态就用类、闭包工厂或 `collections.Callable` 对象；并发场景加锁或 `threading.local`。

9. **误以为 `del`/重新赋值能改外部可变对象**
   `def f(lst): lst = []` 不会清空调用方的列表（只是重新绑定局部名字 `lst`）。要原地改必须 `lst.clear()` 或 `lst[:] = []`。
   **根因**：仍是"名字绑定"——赋值改的是名字指向，不是对象内容。

---

## 速记表

| 陷阱 | 一句话原理 | 防御写法 |
|---|---|---|
| 可变默认参数 | 默认参数在 `def` 时求值一次 | `None` 哨兵 |
| 闭包延迟绑定 | 捕获变量 cell，调用时求值 | `lambda i=i` |
| `UnboundLocalError` | 作用域编译期决定 | `global` / `nonlocal` |
| 装饰器丢信息 | wrapper 覆盖元信息 | `@wraps(f)` |
| 参数顺序 | 调用侧匹配无歧义 | 位置→默认→`*args`→仅关键字→`**kwargs` |
