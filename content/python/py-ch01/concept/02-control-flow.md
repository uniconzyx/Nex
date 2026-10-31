# 02 · 流程控制

条件用 `if / elif / else`，靠缩进划分代码块（无大括号）。循环有 `for ... in` 遍历可迭代对象，以及 `while` 条件循环，配合 `break` / `continue` / `else`（循环正常结束才执行）。

Python 的 `for` 与 C/Java 的 `for` 是**两种不同的东西**：它不是"初始化—判断—递增"，而是"取下一个元素"。理解这一点，`for` 能遍历什么、不能遍历什么就都清楚了。

## 一、`if` 与真值：一切皆可判真假

条件不必是 `bool`，任何对象都能转换真假值：

- **假值**：`False`、`None`、`0`、`0.0`、`""`、`[]`、`()`、`{}`、`set()`、`range(0)`
- **真值**：其余一切

```python
if []:                 # False，不进入
    ...
if [0]:                # True —— 非空列表就是真，哪怕内容是 0
    ...
```

这条规则让代码简洁（`if items:` 比 `if len(items) > 0:` 好），但也制造了一个 bug 模式：**用 `if x:` 判断"是否为 None"**。`x = 0` 或 `x = ""` 时会走错分支。语义明确地写 `if x is None:`。

### 链式比较与三元表达式

```python
if 0 < n < 10:                      # 链式比较，等价于 0 < n and n < 10
    ...
label = "big" if n > 100 else "small"   # 条件表达式，不是三元运算符的简写
```

链式比较是 Python 独有的可读性优势；条件表达式适合短分支，超过一行就该写 `if`。

## 二、`for` 的本质：迭代器协议

```python
for x in obj:
    body(x)
```

等价于：

```python
it = iter(obj)          # 调 obj.__iter__() 得到迭代器
while True:
    try:
        x = next(it)    # 调 it.__next__()
    except StopIteration:
        break
    body(x)
```

于是三个结论：

1. **能 `for` 的对象必须实现 `__iter__`**（或 `__getitem__` 的旧式序列协议）。
2. **迭代器是"一次性"的**：`it` 走完就空，再次 `for it` 什么也不会有。列表可以反复遍历，因为每次 `iter(list)` 返回**新的**迭代器。
3. **`for` 不需要索引**：这正是 `enumerate` 存在的原因——需要下标时用 `for i, x in enumerate(xs)`。

```text
可迭代对象 vs 迭代器

  可迭代对象（iterable）        迭代器（iterator）
  ┌──────────────┐            ┌──────────────┐
  │ __iter__()   │──产生──────►│ __next__()   │ 逐个给值
  │ list/tuple/  │             │ 内部记位置    │ 耗尽后 StopIteration
  │ dict/set/str │             └──────────────┘
  └──────────────┘              一次性，不能重置
```

## 三、`range` 是惰性序列

`range(start, stop, step)` **左闭右开**，且不占内存：

```python
range(5)            # 0,1,2,3,4
range(2, 10, 3)     # 2,5,8
range(10**9)        # 瞬间创建，不分配 10 亿个整数
len(range(10**9))   # 10**9 —— O(1)，靠算术而不是计数
```

`range` 是 `Sequence` 的子类（支持索引、切片、`in`），但不是列表。要真列表才 `list(range(...))`。

## 四、`for ... else`：容易被误读的语法

`else` 子句在**循环未被 `break` 打断**时执行，也就是"跑完了"或"条件自然结束"：

```python
for x in xs:
    if x == target:
        print("found")
        break
else:
    print("not found")     # 只有没 break 才走到这里
```

它把"查找失败"分支从"设一个 flag 再判断"里解放出来。`while ... else` 同理。可读性有争议（很多人不知道这个语法），团队里用就加注释，或者干脆改用 `any()`/`next(...)`。

## 五、`while` 与"循环中修改容器"

```python
i = 0
while i < len(xs):
    if bad(xs[i]):
        xs.pop(i)      # 删除后索引不前进，否则跳过下一个
        continue
    i += 1
```

在 `for x in xs` 里改 `xs` 结构会出问题：列表迭代器按索引走，删除元素会让后续元素前移，于是**跳过一个**；字典/集合会直接抛 `RuntimeError: dictionary changed size during iteration`。

三种正确做法：

1. **遍历副本**：`for x in xs[:]`（列表切片复制）。
2. **构造新容器**：`xs = [x for x in xs if not bad(x)]`。
3. **倒序遍历删除**：`for i in range(len(xs)-1, -1, -1)`。

## 六、`break` / `continue` / `return` 的边界

- `break` 只跳出一层循环，嵌套循环需要 flag 或抽成函数用 `return`。
- `continue` 跳过本次剩余语句，直接进入下一次判断（`for` 里是取下一个元素，`while` 里是重新判条件）。
- 在 `try/finally` 里 `break`，`finally` 仍会执行——这是资源清理能可靠工作的原因。

## 七、边界与陷阱

- **`if x:` 当 `is not None` 用**：`0`、`""`、`[]` 会被判为假。语义是"空"就用真值判断，语义是"缺失"就必须 `is None`。
- **在 `for` 中改容器**：见上，跳过元素或抛 `RuntimeError`。
- **`range` 差一错误**：`range(n)` 不含 `n`；要含末尾写 `range(n + 1)`。
- **`for...else` 误读为"否则"**：它是"没 break 才执行"，不是 `if/else` 的 else。
- **嵌套循环里 `break` 只跳一层**：外层继续跑，是常见逻辑错误。
- **浮点循环条件**：`while x != 0.3` 可能永不结束，用 `<=` 加容差或改成整数计数。
- **`while` 忘改条件变量**：死循环。`for` 天然没有这个问题。

## 八、可运行示例：协议、else 与容器修改

```python
xs = [1, 2, 3, 4]

it = iter(xs)
print("next:", next(it), next(it))          # 1 2
print("rest:", list(it))                    # [3, 4]（迭代器已前进，不回头）
print("re-iterable:", list(it))             # []（迭代器耗尽）

for x in xs:
    if x == 3:
        print("found 3")
        break
else:
    print("not found")

target = 99
for x in xs:
    if x == target:
        break
else:
    print("not found", target)              # 未 break → else 执行

evens = [x for x in xs if x % 2 == 0]
print("evens:", evens)                      # [2, 4]
print("range len:", len(range(10**9)))      # O(1)

s = 0
for i in range(1, 5):
    s += i
else:
    print("sum:", s)                        # 循环正常结束，else 执行
```

`rest` 与 `re-iterable` 两行是"迭代器一次性"的实证：`list(it)` 消费完 `it`，再调 `list(it)` 就是空列表。

## 三视角解析

### 🧑‍💻 程序员视角
- `for...else` / `while...else` 的 `else` 在**循环未被 break 时**执行——用来写「查找未命中」的逻辑很优雅，但团队不熟时建议加注释。
- 迭代时**不要修改正在遍历的容器**（会跳过元素或抛 `RuntimeError`），要改就先构造成新列表或倒序遍历。
- `range` 是惰性序列，`range(10**9)` 不占内存；海量数据用生成器替代一次性列表。
- 需要下标时用 `enumerate(xs)`，需要并行遍历两个序列用 `zip(a, b)`——别手写 `range(len(...))`。

### 🎓 博士生视角
- Python 的 `for` 基于**迭代器协议**（`__iter__` / `__next__`），不是 C 那种下标计数循环；因此自定义容器只要实现协议就能被 `for` 消费——这是「协议优先于继承」的鸭子类型体现。
- 生成器把控制流变成**可暂停的协程雏形**（`yield` 保存栈帧状态）；`async/await` 是它在事件循环上的推广。
- 用异常做控制流（`try/except` 做分支）代价不低：异常对象创建 + 栈回溯展开（`fillInStackTrace` 类操作），热路径上应避免。
- `for` 循环变量的作用域**不限于循环体**（与 C/Java 不同）：循环结束后 `x` 仍是最后一个值。这是 Python 没有块级作用域的直接后果。
- 列表迭代器的"跳过"行为源于它是**按索引游走**而非快照：`__next__` 取 `self.index` 处元素后 `index += 1`，删除导致元素前移，于是下一个被跳过。字典迭代器则用版本号检测，直接抛错。

### 📚 考研者视角
- 与 408 的循环结构、**循环的复杂度分析**直接对应（嵌套循环、循环不变式）。
- 若考程序设计语言，常考「迭代器与生成器的实现机制」「惰性求值」。
- 常考辨析：`while` 与 `do-while` 的区别（Python 没有 `do-while`，要"至少执行一次"用 `while True: ... if cond: break`）。
- 记忆锚点：**`for` 走迭代器协议、`else` 在未 `break` 时执行**；**`range` 左闭右开且惰性**；**循环变量会泄漏到外层作用域**。
