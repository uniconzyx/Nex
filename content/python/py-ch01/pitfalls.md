# 本章避坑指南

1. **可变默认参数陷阱** —— `def f(x=[]): x.append(1); return x` 的默认值在定义期只创建一次，多次调用共享同一列表。正确写法：`def f(x=None): x = x or []`。
2. **`is` 与 `==` 混用** —— `is` 比较对象身份，`==` 比较值。`a = [1]; b = [1]; a == b` 为 `True`，`a is b` 为 `False`。比较值用 `==`。
3. **遍历中修改列表** —— `for x in xs: xs.remove(x)` 会跳过元素或越界。正确做法：遍历副本 `for x in xs[:]` 或列表推导生成新列表。
4. **浅拷贝误当深拷贝** —— `ys = xs.copy()` 只复制外层，嵌套列表仍共享。需要 `import copy; copy.deepcopy(xs)`。
5. **整数缓存区间** —— `-5~256` 的小整数会被复用，`a = 256; b = 256; a is b` 可能为 `True`，但 `257` 不一定。永远用 `==` 比较值，不要依赖 `is`。
6. **`range` 左闭右开** —— `range(3)` 是 `0,1,2` 不含 3；想包含末尾须 `range(0, n+1)`，常因差一错误（off-by-one）踩坑。
7. **`if x:` 当 `is not None` 用** —— `x = 0`、`x = ""`、`x = []` 都会被判为假，逻辑分支走错。判断"缺失"必须写 `if x is None:`。
8. **`xs.sort()` 返回 `None`** —— `ys = xs.sort()` 会让 `ys` 变成 `None`（原地排序无返回值）。要新列表用 `ys = sorted(xs)`。
9. **循环变量泄漏到外层作用域** —— `for x in xs: pass` 之后 `x` 仍然存在，是最后一个元素。与 C/Java 的块级作用域不同，别在循环后依赖"x 已消失"。
10. **`+=` 对列表是原地操作** —— `ys = xs; xs += [1]` 会同时改到 `ys`；`xs = xs + [1]` 才创建新列表。关键字：`__iadd__` 与 `__add__` 的区别。
11. **`for...else` 误读** —— `else` 在"循环未被 break"时执行，不是"否则"。查找未命中分支用它，但要加注释，否则 reviewer 会看错。
12. **`dict` 键必须可哈希** —— `d[[1, 2]] = 1` 抛 `TypeError: unhashable type`。要按值作键就转成 `tuple`（元素也得可哈希）。
13. **`set` 无序导致测试不稳定** —— `assert set(items) == [1, 2, 3]` 类型就不对；比较集合用集合，比较顺序要先 `sorted`。
14. **遍历 `dict` 时增删键** —— 抛 `RuntimeError: dictionary changed size during iteration`。先 `for k in list(d):` 再改。
15. **自定义类当 `dict` 键却只重写 `__eq__`** —— 重写 `__eq__` 后 `__hash__` 被置为 `None`，实例直接不可哈希。要么两个都写，要么用 `@dataclass(frozen=True)`。
16. **生成器只能遍历一次** —— `g = (x for x in xs)` 消费完就是空，`list(g)` 第二次得到 `[]`。需要多次遍历就存成列表。
17. **`in list` 写在循环里** —— 整体 O(n²)。成员判断频繁就换成 `set` 或 `dict`。
