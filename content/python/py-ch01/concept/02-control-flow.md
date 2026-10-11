# 02 · 流程控制

条件用 `if / elif / else`，靠缩进划分代码块（无大括号）。循环有 `for ... in` 遍历可迭代对象，以及 `while` 条件循环，配合 `break` / `continue` / `else`（循环正常结束才执行）。

```python
n = 7
if n % 2 == 0:
    print("even")
else:
    print("odd")          # odd

for i in range(3):
    if i == 0:
        continue
    print(i)               # 1 2

s = 0
for i in range(1, 5):
    s += i
else:
    print("done")          # 循环未被 break 打断，打印 done
```

`range(start, stop, step)` 生成整数序列（左闭右开）；`for ... else` 的 `else` 常用于"查找失败"分支，但可读性存争议，团队约定优先。

---

## 三视角解析

### 🧑‍💻 程序员视角
- `for...else` / `while...else` 的 `else` 在**循环未被 break 时**执行——用来写「查找未命中」的逻辑很优雅，但团队不熟时建议加注释。
- 迭代时**不要修改正在遍历的容器**（会跳过元素或抛 `RuntimeError`），要改就先构造成新列表或倒序遍历。
- `range` 是惰性序列，`range(10**9)` 不占内存；海量数据用生成器替代一次性列表。

### 🎓 博士生视角
- Python 的 `for` 基于**迭代器协议**（`__iter__` / `__next__`），不是 C 那种下标计数循环；因此自定义容器只要实现协议就能被 `for` 消费——这是「协议优先于继承」的鸭子类型体现。
- 生成器把控制流变成**可暂停的协程雏形**（`yield` 保存栈帧状态）；`async/await` 是它在事件循环上的推广。
- 用异常做控制流（`try/except` 做分支）代价不低：异常对象创建 + 栈回溯展开（`fillInStackTrace` 类操作），热路径上应避免。

### 📚 考研者视角
- 与 408 的循环结构、**循环的复杂度分析**直接对应（嵌套循环、循环不变式）。
- 若考程序设计语言，常考「迭代器与生成器的实现机制」「惰性求值」。
- 记忆锚点：**`for` 走迭代器协议、`else` 在未 `break` 时执行**。
