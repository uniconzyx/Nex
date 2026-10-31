# 魔术方法：让对象接入语言协议

`__len__`、`__iter__`、`__eq__` 这些双下划线方法不是「特殊函数」，而是 Python 语言语法的
**钩子**。写对了，你的对象就能用在 `len()`、`for`、`==`、`in` 里；写错了，就会出现「看着对、
行为怪」的对象。

```python
class Playlist:
    def __init__(self, songs):
        self._songs = list(songs)

    def __len__(self):              # len(pl)
        return len(self._songs)

    def __getitem__(self, i):       # pl[0] / 切片 / for 循环（旧协议）
        return self._songs[i]

    def __iter__(self):             # for x in pl（新协议，优先于 __getitem__）
        return iter(self._songs)

    def __contains__(self, x):      # "x" in pl —— 不写的话会退化成 for 循环
        return x in self._songs

    def __repr__(self):             # 给开发者看，应可重建对象
        return f"Playlist({self._songs!r})"

    def __eq__(self, other):        # pl1 == pl2
        if not isinstance(other, Playlist):
            return NotImplemented
        return self._songs == other._songs

    def __hash__(self):             # 想放进 set / 当 dict 键才需要
        return hash(tuple(self._songs))
```

## 三个必须知道的规矩

**1. 定义 `__eq__` 会把 `__hash__` 置为 `None`。**
Python 认为「相等的对象应该 hash 相同」，你改了相等语义就默认你不能被 hash（否则会破坏 dict 的
不变式）。要可 hash 就显式实现，并且只 hash 不可变的部分。

**2. `__eq__` 遇到陌生类型要返回 `NotImplemented`，不要 `return False`。**
`NotImplemented` 是让 Python 去试对方的 `__eq__`（可能是更精确的实现）；`False` 会直接终止比较，
导致 `a == b` 为 False 而 `b == a` 为 True 这种不对称。

**3. `__repr__` 是给开发者，`__str__` 是给用户。**
只写一个时写 `__repr__`（`print()` 会自动回退到它）。`__repr__` 的目标是
`eval(repr(obj))` 能重建对象——这条判据能帮你避免写出 `<Playlist object at 0x...>` 这种毫无信息的东西。

## `@property` 与三种方法修饰符

```python
class Circle:
    def __init__(self, r):
        self._r = r

    @property
    def area(self):                 # 调用时不用写 ()：c.area
        return 3.14159 * self._r ** 2

    @area.setter
    def area(self, v):              # 赋值时校验：c.area = 10 会走这里
        raise AttributeError("area 是只读的")

    @classmethod
    def unit(cls):                  # 第一个参数是类，适合做工厂
        return cls(1.0)

    @staticmethod
    def is_valid(r):                # 不接收 self/cls，纯函数挂在类上
        return r > 0
```

判据：需要访问实例状态用普通方法；需要创建实例（工厂）或访问类属性用 `classmethod`；
与类型无关的纯工具函数用 `staticmethod`（很多场景直接写模块级函数更清楚）。

## 魔术方法查找为什么绕过实例字典

这是 Python 对象模型里最反直觉的一条规则，理解了它就能解释一批「明明写了却不生效」的现象：

```python
class Sneaky:
    def __len__(self):
        return 3

s = Sneaky()
s.__len__ = lambda: 99          # 往实例上塞一个同名方法
print(len(s))                    # 3，不是 99
print(s.__len__())               # 99，直接调用才走实例字典
```

实测确实如此：

```text
3
99
--- 挂 lambda 到实例，len 仍走类型 ---
len(s2) = 3
--- 改类则生效 ---
len(s) = 99
```

注意最后一行：把 `Sneaky.__len__` 换成 `lambda self: 99` 之后，`len(s)` 立刻变成 99。
所以**魔术方法的改动必须落在类上**，落在实例上无效。

同一个名字，`len(s)` 得 3，`s.__len__()` 得 99。原因是解释器对**特殊方法**走的是
`type(s).__len__(s)` 而不是 `s.__len__()`——它在**类型层面**查找，显式跳过实例字典。

为什么这样设计？因为如果特殊方法可被实例属性覆盖，那么几乎所有优化都失效了。
比如 `len()` 的返回值可以直接用 C 层的 `Py_ssize_t` 缓存，前提是「这个类的方法表不会变」；
如果实例能在运行时替换 `__len__`，解释器每次都得到实例字典里翻一遍。

**实践含义**：

- 想在运行时改行为，改类不改实例：`Sneaky.__len__ = lambda self: 99`。
- 用 `mock.patch.object(cls, "__len__")` 而不是 `patch.object(obj, "__len__")`。
- 单元测试里给对象打桩方法时，普通方法可以直接打到实例上，魔术方法必须打到类上——这是
  「同一个 mock 技巧有的生效有的不生效」的根因。

## 三视角解析

### 🧑‍💻 程序员视角
- 只写 `__repr__` 不写 `__str__` 是绝大多数场景的正确选择。`__repr__` 里用 `!r` 格式化字段（`f"{self.name!r}"`），这样字符串字段带引号，能一眼看出类型。
- 自定义类要放进 `set` 或当 `dict` 键时，`__eq__` 与 `__hash__` 必须成对实现，且参与 hash 的字段必须不可变。用 `@dataclass(frozen=True)` 可以自动生成正确的这一对。
- 需要「看起来像数字/容器/可调用」时优先用 `collections.abc` 的基类继承（如 `MutableSequence`），它会补齐 `__contains__`/`__reversed__` 等一大批方法，并让 `isinstance` 通过。

### 🎓 博士生视角
- 魔术方法是「语言协议」而非「命名约定」，因此它们由解释器在**类型上**查找，绕过实例字典——`obj.__len__ = lambda: 5` 不会让 `len(obj)` 返回 5。这是 CPython 的 special method lookup 特例。
- `__eq__` 与 `__hash__` 的耦合是「等价关系」的必然要求：hash 必须对相等元素给出相同值，因此一旦相等更「宽」（比较更多字段），hash 也必须更「窄」（只用不可变子集）——否则 dict 会找不到刚放进去的键。
- Python 的协议是隐式的（structural），没有显式 `implements` 声明；这与 Java interface、Go interface 的选择相反。收益是无需预先声明，代价是无法静态确认「这个类真的完整实现了序列协议」。

### 📚 考研者视角
- 与 408 的「运算符重载」对照：C++ 通过 `operator+` 等实现，编译期决定；Python 通过 `__add__`，运行期按类型查找。两者都是「让自定义类型接入语言语法」，只是绑定时机不同。
- 面试常问「`__new__` 和 `__init__` 的区别」「为什么定义了 `__eq__` 之后对象不能当 dict 键」——后者答：`__hash__` 被隐式置为 `None`。
- 记忆锚点：**`__eq__` 与 `__hash__` 成对；`__repr__` 给开发者；魔术方法在类型上查找**。
