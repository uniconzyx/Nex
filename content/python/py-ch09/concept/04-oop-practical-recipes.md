# Python 面向对象实战手记：凯喵的十二次「属性找不到，但代码没写错」

> 这一篇来自凯喵给一个插件框架做重构的经历。框架要支持「运行时注册、按名字查找、动态分发」，因此大量用到类命名空间、MRO、魔术方法。重构过程中反复遇到同一类问题：属性明明定义了却取不到、`super()` 调到了意想不到的类、`__eq__` 一写就把对象变成不可哈希。十二个现场记录下来的结论是：**Python 的 OOP 不是「语法」，而是「一套属性查找协议」**。这篇按「命名空间 → 继承与 MRO → 魔术方法」的顺序展开。

## 开场：属性查找不是「读字段」，是「走一条搜索链」

写 `obj.x` 时，Python 不是简单地从 `obj.__dict__` 里取。它走一条明确的链路：先查类型上定义了 `__getattribute__` 吗（几乎所有类都有默认实现），然后按「数据描述符 → 实例字典 → 非数据描述符 → 类属性」的顺序查找。

这条链路解释了大部分「属性找不到」的困惑：属性可能在类上、在实例上、在父类上、或者由描述符动态生成。

```python
class A:
    x = "class-attr"

a = A()
print(a.x)              # "class-attr"（从类上找到）
a.x = "inst-attr"       # 写进实例字典
print(a.x)              # "inst-attr"（实例字典优先）
print(A.x)              # "class-attr"（类属性不变）
```

凯喵的体会是：**理解这条链，比记住任何语法都重要**。因为所有的「为什么这个方法没被调到」「为什么这个属性被覆盖了」，答案都在这条链上。

### 现场一：类属性是共享的，可变类属性是灾难

```python
class Bad:
    items = []          # 类属性，所有实例共享同一个 list

b1, b2 = Bad(), Bad()
b1.items.append(1)
print(b2.items)         # [1] —— 被污染了
```

这是 Python 最经典的 OOP 陷阱。`items = []` 在类定义时创建了一次，所有实例通过属性查找拿到的都是同一个对象。

```python
class Good:
    def __init__(self):
        self.items = []   # 每个实例自己的 list
```

凯喵的规约：**类属性只放不可变的东西**（常量、类型标记、方法）。任何可变的（list、dict、set、自定义对象）都必须放在 `__init__` 里创建。

这个 bug 特别隐蔽，因为单例测试时完全正常，多实例并发时才暴露，而且表现是「数据串了」，看起来像业务逻辑问题。

### 现场二：名字改写让「私有」变成 _ClassName__attr

Python 没有真正的私有。双下划线开头的属性会被「名字改写」（name mangling）成 `_类名__属性`，目的是避免子类意外覆盖。

```python
class A:
    __secret = 1        # 实际存为 _A__secret
    def get(self):
        return self.__secret

print(A().get())            # 1
print(A()._A__secret)       # 1 —— 还是能访问
# print(A().__secret)       # AttributeError
```

改写发生在**编译期**（基于所在类的名字）。这带来一个坑：在子类里访问父类的双下划线属性，改写的是子类的名字，找不到。

```python
class B(A):
    def peek(self):
        return self.__secret    # 改写成 self._B__secret，不存在！
```

凯喵的建议：**用单下划线表示「内部使用」就够了**，双下划线只在「明确要防止子类覆盖」时用。多数场景下它带来的困惑大于收益。

### 现场三：MRO 是 C3 线性化，不是「深度优先」

多继承时，方法查找顺序由 MRO（Method Resolution Order）决定。Python 3 用 C3 线性化算法，保证：子类在父类之前、多个父类按声明顺序、且保持每个类的局部优先级。

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print([c.__name__ for c in D.__mro__])
# ['D', 'B', 'C', 'A', 'object']
```

注意 `A` 排在 `B` 和 `C` 之后——这就是 C3 的作用：保证「子类先于父类」。深度优先会得到 `D, B, A, C`，那会导致 `A` 的方法在 `C` 之前被找到，违反直觉。

凯喵的排错方法：**遇到「方法调到了意料之外的类」，第一件事是 `print(cls.__mro__`)**，顺序一看就明白。

### 现场四：super() 不是「调用父类」，是「沿 MRO 找下一个」

这是最容易被误解的一点。`super()` 返回的是一个「代理对象」，它沿着 MRO 从当前类**之后**开始查找。所以在多继承里，`super()` 可能调到一个「兄弟类」而不是「父类」。

```python
class Base:
    def hello(self): print("Base")

class Left(Base):
    def hello(self):
        print("Left")
        super().hello()

class Right(Base):
    def hello(self):
        print("Right")
        super().hello()

class Child(Left, Right):
    def hello(self):
        print("Child")
        super().hello()

Child().hello()
# Child → Left → Right → Base
```

`Left.hello` 里的 `super()` 调用的是 `Right.hello`，不是 `Base.hello`。因为 MRO 是 `[Child, Left, Right, Base]`，`Left` 之后是 `Right`。

这就是协作式多继承（cooperative multiple inheritance）的机制，也是 mixin 能正确工作的基础。

### 现场五：mixin 不能带状态

mixin 的设计意图是「只提供方法，不提供状态」。如果 mixin 在 `__init__` 里设置实例属性，多继承时会出现「谁先初始化、谁覆盖谁」的问题。

```python
class CacheMixin:
    def __init__(self):
        super().__init__()
        self._cache = {}      # 危险：可能与别的类的属性冲突

class Repo(CacheMixin, BaseRepo):
    pass
```

凯喵的版本更糟：mixin 里直接 `self._cache = {}` 而不调 `super().__init__()`，导致 `BaseRepo` 的初始化被跳过，一堆属性缺失。

规约：**mixin 要么不带 `__init__`，要么严格调 `super().__init__()` 并只用带前缀的属性名**。理想情况下，mixin 只依赖「宿主类提供了某个方法」这个契约。

### 现场六：__eq__ 一写，对象就不可哈希了

这是最高频的「莫名其妙」类问题。定义了 `__eq__` 之后，Python 会把 `__hash__` 设为 `None`，对象就不能放进 `set` 或作为 `dict` 的键。

```python
class Point:
    def __init__(self, x, y): self.x, self.y = x, y
    def __eq__(self, other):
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)

p = Point(1, 2)
{p}     # TypeError: unhashable type: 'Point'
```

原因很合理：如果两个对象相等，它们的哈希必须相同。自定义了 `__eq__` 但没定义 `__hash__`，Python 无法保证这个不变量，所以干脆禁止哈希。

修法是同时定义 `__hash__`，且必须基于「参与相等比较的字段」：

```python
    def __hash__(self):
        return hash((self.x, self.y))
```

凯喵的规约：**写 `__eq__` 就一定要写 `__hash__`**，两者必须基于同一组字段，否则 `set` 会出现「重复元素」。

### 现场七：__repr__ 是调试的第一生产力

默认的 `__repr__` 输出 `<Point object at 0x7f...>`，在日志里毫无用处。自定义之后，一眼就能看出对象的状态。

```python
class Point:
    def __init__(self, x, y): self.x, self.y = x, y
    def __repr__(self):
        return f"Point(x={self.x!r}, y={self.y!r})"
```

注意用 `!r`（`repr`）而不是默认的 `str`，这样字符串字段会带引号，`None`、`True` 也能区分。

凯喵的实践：**每个数据类都写 `__repr__`**，成本一行，收益是「所有日志和 traceback 都变得可读」。如果是 Python 3.7+，直接用 `@dataclass` 自动生成。

### 现场八：__str__ 与 __repr__ 的职责不同

`__repr__` 面向开发者（调试、日志），应该是「能重建对象的表达式」；`__str__` 面向用户（打印、展示），应该是「人类可读的描述」。

```python
class Money:
    def __init__(self, amount, currency):
        self.amount, self.currency = amount, currency
    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"   # 开发者看
    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"           # 用户看
```

如果只定义 `__str__` 不定义 `__repr__`，在容器里打印（`print([m])`）时用的是 `__repr__`，会得到默认的 `<Money object at ...>`。这是很多人困惑「为什么列表里的对象打印不出来」的原因。

### 现场九：__getattr__ 与 __getattribute__ 完全不同

`__getattribute__` 拦截**所有**属性访问，容易写出无限递归。`__getattr__` 只在「常规查找失败后」才被调用，是安全得多的钩子。

```python
class Lazy:
    def __init__(self):
        self._loaded = {}
    def __getattr__(self, name):        # 只在找不到时调用
        if name in self._loaded:
            return self._loaded[name]
        raise AttributeError(name)
```

凯喵的坑是：在 `__getattr__` 里访问 `self.xxx`，如果 `xxx` 也不存在，又会触发 `__getattr__`，无限递归。修法是用 `object.__getattribute__(self, ...)` 或 `super().__setattr__` 直接操作。

规约：**优先用 `__getattr__`，只在确实需要拦截全部访问时用 `__getattribute__`**。

### 现场十：__slots__ 省内存，但会禁用动态属性

定义 `__slots__` 后，实例不再有 `__dict__`，每个属性存在固定偏移上。内存占用能降 40% 到 60%，但代价是不能动态添加属性。

```python
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x, self.y = x, y

p = Point(1, 2)
# p.z = 3    # AttributeError: 'Point' object has no attribute 'z'
```

凯喵见过给一个需要动态属性的类加了 `__slots__`，结果某个插件往实例上挂字段时崩了，而且报错发生在运行时很远的地方。

规约：**只在「实例数量极大、字段固定」的场景用 `__slots__`**（比如百万级的数据点）。普通业务类不加，灵活性的价值更高。

### 现场十一：__init__ 不是构造函数，__new__ 才是

`__new__` 负责创建实例（返回对象），`__init__` 负责初始化（返回 None）。99% 的场景只需要 `__init__`，但单例、不可变类型、继承内置类型时需要 `__new__`。

```python
class Singleton:
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst
```

凯喵的坑是在 `__init__` 里做重活：读文件、连数据库、校验失败就 `raise`。结果对象构造到一半就被丢弃，已分配的资源泄漏。

规约：**`__init__` 只做「字段赋值」和「轻量校验」**。重活放到显式的 `load()` / `connect()` 方法里，让调用方决定何时执行。

### 现场十二：抽象基类让「接口」变成可检查的

Python 是鸭子类型，不要求显式实现接口。但很多时候你希望「没实现就报错」，这时用 `abc`。

```python
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def get(self, key): ...

    @abstractmethod
    def put(self, key, value): ...

class MemoryRepo(Repository):
    def get(self, key): return self._d.get(key)
    def put(self, key, value): self._d[key] = value

# Repository()        # TypeError: Can't instantiate abstract class
```

好处是错误提前到实例化时，而不是调用某个方法时才 `AttributeError`。代价是失去一部分灵活性（不能只实现部分方法）。

凯喵的经验：**框架层用 ABC 定义契约，业务层用鸭子类型**。框架需要清晰的边界和早期报错，业务需要灵活组合。

## 三视角解析
### 🧑‍💻 程序员视角
类属性是共享的，可变类属性（如 `items = []`）会让所有实例共用同一个列表——这是 Python 最经典的 OOP 陷阱。双下划线前缀会触发名字改写（`__x` → `_ClassName__x`），它不是真正的私有，只是「避免意外覆盖」。MRO 是 C3 线性化而非「深度优先」，多继承时方法解析顺序要按 `__mro__` 看。`super()` 不是「调用父类」，而是「沿 MRO 找下一个」，在菱形继承里这是唯一正确的写法。

### 🎓 博士生视角
Python 的 OOP 建立在「属性查找协议」上：实例字典 → 类字典 → 基类（按 MRO）→ `__getattr__`，其中描述符协议（`__get__`）在类属性查找时优先生效，这是 `property` 与方法的实现基础。C3 线性化保证「单调性」与「局部优先级」，是 Python 多继承能可预测工作的前提。`__slots__` 通过禁用实例字典来省内存，代价是不能动态加属性。

### 📚 考研者视角
Python 面试高频：
1. **实例属性与类属性**：查找顺序、可变类属性的共享问题。
2. **MRO**：C3 算法、`super()` 的语义（沿 MRO 下一个，不是父类）。
3. **魔术方法**：`__init__`/`__new__`/`__str__`/`__repr__`/`__eq__`/`__hash__` 的用途。
4. **`property`**：装饰器写法与 `setter`/`deleter`，相比直接暴露属性的优势。

## 收尾：Python OOP 的三层理解

凯喵最后总结：Python 的面向对象可以分三层理解。

**第一层是语法**：`class`、`self`、继承、`super()`。这一层看文档就能学会，但只停在这里会不断踩坑。

**第二层是协议**：属性查找链、MRO、魔术方法、描述符。理解这一层，你才知道「`a.x` 到底发生了什么」「`super()` 为什么调到兄弟类」。这是从「会用」到「用对」的分水岭。

**第三层是设计**：什么时候用继承、什么时候用组合、mixin 该不该带状态、ABC 该不该上。这一层没有标准答案，只有「在这个场景下哪个更合适」。

三层的顺序不能跳。凯喵见过太多人在第二层没打通的情况下讨论第三层，结果所有的「设计选择」都变成了风格之争，没有依据。

真正的进步路径是：先把属性查找和 MRO 搞透，再理解常用魔术方法的契约（`__eq__`/`__hash__`/`__repr__` 三件套尤其重要），最后才谈设计模式。走到第三层时你会发现，很多「设计模式」在 Python 里其实不需要——因为语言本身提供了更直接的表达方式。

再补一层关于「怎么调试 OOP 问题」的建议。Python 的 OOP 问题有个共同特征：报错信息指向的位置和真正的原因往往隔了好几层。所以调试时不要从报错行开始看，而从「这个属性/方法本来应该在哪」开始查。凯喵的顺序是：先 `print(type(obj).__mro__)` 看查找顺序，再 `print(vars(obj))` 看实例字典，最后 `print([k for k in dir(type(obj)) if not k.startswith("__")])` 看类上有什么。这三条命令走完，绝大多数「属性找不到」和「方法调错」都能定位。另一个有用的技巧是用 `__getattr__` 临时打日志，把一个类的所有「找不到」的属性访问都记录下来——很多时候问题不在缺失，而在「访问了一个本该存在但拼错的名字」。这套方法建立起来之后，Python 的 OOP 就从「玄学」变成了「可以按图索骥的东西」。

最后补一句设计层面的经验：Python 里最被滥用的机制是继承。很多「is-a」关系其实用组合更合适，因为继承会把父类的所有实现细节变成你的接口契约，父类改一个内部方法就可能破坏子类。凯喵的判断标准很简单：如果子类需要重写父类一半以上的方法，或者子类只想复用其中一两个方法，那就该用组合而不是继承。组合更松散，改起来更自由，也更符合「显式优于隐式」这条 Python 的核心哲学。真正需要继承的场景只有两类：一是框架要求你继承某个基类（如 `Exception`、`ABC`、Django 的 `View`），二是你确实要表达「是一种」并且愿意承担父类演化带来的耦合。除此之外，组合几乎总是更好的选择，而 mixin 只有在「只提供方法、不带状态」时才安全可用。

```text
04-oop-practical-recipes.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 现场一：类属性是共享的，可变类属性是灾难  (python)
    |
    v
  [02] 现场二：名字改写让「私有」变成 _ClassName__attr  (python)
    |
    v
  [03] 现场三：MRO 是 C3 线性化，不是「深度优先」  (python)
    |
    v
  [04] 现场四：super() 不是「调用父类」，是「沿 MRO 找下一个」  (python)
    |
    v
  [05] 现场五：mixin 不能带状态  (python)
    |
    v
  [06] 现场六：__eq__ 一写，对象就不可哈希了  (python)
    |
    v
  [07] 现场七：__repr__ 是调试的第一生产力  (python)
    |
    v
  [08] 现场八：__str__ 与 __repr__ 的职责不同  (python)
    |
    v
  [... 其余 4 节见正文 ...]
    |
    v
  [END] 三视角解析收口
```
