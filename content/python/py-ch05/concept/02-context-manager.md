# 上下文管理器：`with` 的三件事与自定义写法

## 1. `with` 究竟做了什么

```python
with open("a.txt") as f:
    data = f.read()
```

等价于：

```python
mgr = open("a.txt")
f = mgr.__enter__()
try:
    data = f.read()
except BaseException:
    if not mgr.__exit__(*sys.exc_info()):
        raise                 # __exit__ 返回假值 -> 异常继续往外抛
else:
    mgr.__exit__(None, None, None)
```

三件事：**获取资源**（`__enter__`）、**保护代码块**（`try`）、
**无论如何都释放**（`__exit__`）。

## 2. `__exit__` 的返回值是开关

`__exit__(exc_type, exc_val, exc_tb)` 有三个语义：

| 参数 | 正常退出时 | 异常退出时 |
|---|---|---|
| `exc_type` | `None` | 异常类 |
| `exc_val` / `exc_tb` | `None` | 异常实例 / traceback |

返回值决定**异常是否被吞掉**：

- 返回 `True`（真值）→ **抑制异常**，`with` 之后的代码继续执行；
- 返回 `False` / `None`（假值）→ 异常继续向外交代。

```python
class Suppress:
    def __enter__(self):
        return self
    def __exit__(self, et, ev, tb):
        return et is not None      # 有异常就吞掉
```

⚠️ 只在**明确知道后果**时返回 `True`。静默吞异常是排查噩梦；
标准库的 `contextlib.suppress(SomeError)` 是唯一推荐的"吞异常"写法。

## 3. 自定义上下文管理器

最小可用形态是「类 + 两个方法」；只有清理逻辑的函数式写法用
`contextlib.contextmanager` 装饰一个**恰好 yield 一次**的生成器：

```python
import contextlib, time

@contextlib.contextmanager
def timer(label):
    t0 = time.perf_counter()
    try:
        yield                      # 这里把控制权交回 with 块
    finally:
        print(label, "耗时档位:", "快" if time.perf_counter() - t0 < 1 else "慢")
```

要点：

- `finally` 保证异常时也清理；
- `yield` 的值就是 `as` 绑定的对象（不需要时可以不 yield 值）；
- 生成器**必须且只能 yield 一次**，多 yield 会抛 `RuntimeError`。
### 🧑‍💻 程序员视角
## 4. 一个真实的资源管理器：原子写入

「写文件到一半崩了」会留下半截文件。工程做法是
**写临时文件 → `flush` + `fsync` → 原子替换**：

```python
import os, pathlib, tempfile

def atomic_write_text(path, text, encoding="utf-8"):
    path = pathlib.Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()                  # 推到 OS
            os.fsync(f.fileno())       # 推到磁盘
        os.replace(tmp, path)          # 同目录内原子替换
    except BaseException:
        os.path.exists(tmp) and os.unlink(tmp)
        raise
```

三个关键点：

1. **临时文件必须与目标同目录** —— `os.replace` 只在同一文件系统内保证原子性；
   跨盘（如 `/tmp` → `/data`）实际是"复制 + 删除"，不原子。
2. **`os.replace` 而不是 `os.rename`** —— 在 Windows 上 `os.rename` 目标存在会失败，
   `os.replace` 会覆盖。
3. **`fsync` 是必需的** —— 否则断电后可能只剩一个空文件（元数据已提交、数据未落盘）。
### 🎓 博士生视角
## 5. 契约层面的形式化

上下文管理器实现的是**资源获取即初始化（RAII）**思想在 Python 中的投影：
把「获取」与「释放」绑定在同一词法作用域上，使释放**不依赖控制流的正确性**——
早退、`break`、`return`、异常，都不影响 `__exit__` 的执行。

这在类型论上对应一个"括号化"（bracketing）的效应处理：
`with R as r: e` 的求值保证 `R.__exit__` 在 `e` 的任何终止路径上都被调用一次且仅一次
（前提是 `__enter__` 成功返回）。

`contextlib.ExitStack` 把这一保证**扩展到动态数量**的资源：
它是一个显式的 LIFO 栈，`enter_context()` 逐个压栈，
退出时逆序释放——解决"循环里打开 N 个文件、必须全部关闭"的问题。

### 与 `try/finally` 的关系

`with` 并不比 `try/finally` 更强，二者可互相翻译；
`with` 的价值在于**把正确性从调用方搬到被封装的一侧**：
`try/finally` 要求每个调用者都写对，`with` 只要求实现者写对一次。
### 📚 考研者视角
## 6. 常见的错误用法

```python
# ✗ 一个 with 里塞多个不相关资源 -> 异常时难以判断哪个失败
with open("a"), open("b"), open("c"):
    ...

# ✓ 用括号换行（Python 3.10+）或 ExitStack，保持可读
with (
    open("a", encoding="utf-8") as fa,
    open("b", encoding="utf-8") as fb,
):
    ...
```

```python
# ✗ 只 catch 不 re-raise，掩盖了真实故障
try:
    with open("x", encoding="utf-8") as f:
        do(f)
except Exception:
    pass
```

## 三视角解析

### 🧑‍💻 程序员视角

- **什么时候自己写**：清理逻辑超过 3 行、或同一套清理要在多处复用时，
  抽成上下文管理器；只有一两行就用 `contextlib.suppress` / `ExitStack`。
- **排查顺序**：资源没释放 → 先看是否用了 `with`；
  再看 `__exit__` 是否返回了 `True` 把异常吞了（异常丢了最误导人）；
  最后看是否在 `__init__` 里获取资源（应该放在 `__enter__`）。
- **踩坑**：`@contextmanager` 装饰的函数若在 `yield` 之前抛异常，
  `with` 块根本不会执行，`as` 也拿不到值——错误信息会指向 `with` 那一行。

### 🎓 博士生视角

- `with` 是**语法糖**，编译后就是 `SETUP_WITH` / `WITH_EXCEPT_START` 字节码，
  没有独立的运行时支持；因此它的保证强度等同手写 `try/finally`。
- `__exit__` 返回真值**抑制异常**这一设计，等价于给了一个"局部异常处理器"；
  它的存在让 `with` 可以表达"预期内的失败"（如 `suppress(FileNotFoundError)`），
  但也引入了"异常被静默吞掉"的可观测性风险。
- `ExitStack` 把 RAII 从**静态嵌套**推广到**动态集合**，
  是实现「不确定数量资源」的正确抽象；`AsyncExitStack` 是异步对应物。

### 📚 考研者视角

非 408 统考内容，按**笔面工程题**口径：

- **标准问法**：「`with` 语句的原理是什么？」标准答题结构 =
  「调用 `__enter__` 拿资源 → `try` 保护代码块 → 无论正常/异常都调 `__exit__`；
  `__exit__` 返回真值可抑制异常」。
- **易错口径**：
  1. 说成「`with` 会自动调用 `close()`」——不准确，它调用的是 `__exit__`，
     `close()` 只是文件对象在 `__exit__` 里的**实现细节**。
  2. 忘记提 `__exit__` 的布尔返回值语义，这通常是**追问**点。
  3. 以为 `with` 是语言级的资源管理机制（类似 Java 的 try-with-resources 还需要
     `AutoCloseable` 接口约束），Python 里只要实现两个魔术方法即可。
- **记忆锚点**：**`with` = `__enter__` + `try/finally(__exit__)`**。
