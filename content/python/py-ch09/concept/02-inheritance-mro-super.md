# 继承、MRO 与 super()

Python 支持多继承，这带来一个必须回答的问题：`obj.method()` 到底调哪一个？答案是沿
**方法解析顺序（MRO）** 找第一个。

```python
class A:
    def hello(self): return "A"
class B(A):
    def hello(self): return "B"
class C(A):
    def hello(self): return "C"
class D(B, C):
    pass

print(D().hello())      # B —— B 在 MRO 里排在 C 前面
print([c.__name__ for c in D.__mro__])   # ['D', 'B', 'C', 'A', 'object']
```

MRO 用的算法是 **C3 线性化**：保证「子类在父类之前」「同一父类的多个子类保持声明顺序」
「每个类只出现一次」。出现无法同时满足的情况时直接报 `TypeError`，而不是让你猜。

## `super()` 不是「父类」

这是最深的误解。`super()` 返回的是「MRO 上当前类的**下一个**类」，不一定是父类：

```python
class Base:
    def __init__(self):
        print("Base")
class A(Base):
    def __init__(self):
        print("A"); super().__init__()
class B(Base):
    def __init__(self):
        print("B"); super().__init__()
class C(A, B):
    def __init__(self):
        print("C"); super().__init__()

C()     # C → A → B → Base
```

在 `A.__init__` 里 `super()` 找到的是 **B**，不是 `Base`——因为它的查找起点是 A 在
`type(self).__mro__`（这里是 C 的 MRO）中的位置。这个「按实例的实际 MRO 走」的行为叫
协作式多继承（cooperative multiple inheritance）。

工程后果：**多继承链上的每个 `__init__` 都必须调用 `super().__init__()` 并接受 `**kwargs` 透传**，
否则链会断。标准库的 `collections.abc` 容器类、Django 的 mixin 全部遵守这条约定。

## 什么时候真的该用多继承

大多数情况下不该。Python 界的共识是：

- **mixin（能力混入）**：每个 mixin 只提供一小块正交能力（如 `JSONMixin` 提供 `to_json()`），
  且不定义 `__init__` 状态——这是多继承唯一被广泛认可的用法。
- **抽象基类（ABC）**：用 `abc.ABC` + `@abstractmethod` 声明接口，`isinstance` 检查会生效。
- **菱形继承的「数据」部分**：几乎总是该用组合（composition）。`has-a` 用组合，`is-a` 用继承，
  这条判据在 Python 里比其他语言更要紧，因为允许多继承会让错误更容易被发现得晚。

### 手算一次 C3 线性化

MRO 不是「谁先声明谁在前」这么随意，它有明确的合并规则（C3）。规则一句话：

> 一个类的 MRO = 它自己 + 把所有父类的 MRO 与父类声明顺序**依次合并**，
> 合并时始终取「不出现在其他列表尾部的那个头」。

看一个经典例子：

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print([c.__name__ for c in D.__mro__])
```

手算过程：

```text
L(A) = [A, object]
L(B) = [B] + merge(L(A))            = [B, A, object]
L(C) = [C] + merge(L(A))            = [C, A, object]

L(D) = [D] + merge([B,A,object], [C,A,object], [B,C])
     = [D, B] + merge([A,object], [C,A,object], [C])     # 取 B：它不在任何列表尾部
     = [D, B, C] + merge([A,object], [A,object], [])     # 取 C：A 在第二表尾部，跳过
     = [D, B, C, A, object]
```

结果是 `D → B → C → A → object`。注意 `A` 排在最后：因为它在 `L(B)` 和 `L(C)` 的尾部，
必须先让 `C` 出来。这就是为什么 `D.__init__` 调 `super()` 会先到 `B` 再到 `C`。

反过来，如果声明顺序写成 `class D(C, B)`，结果变成 `D → C → B → A`——
**只改父类顺序就能改变初始化顺序**，这也是多继承要小心的地方。

C3 还有一个副产品：**当线性化无法完成时直接报错**。比如 `class X(A, B)` 与 `class Y(B, A)`
同时是某个类的父类，就找不到合法的合并顺序：

```python
class A2: pass
class B2: pass
class X(A2, B2): pass
class Y(B2, A2): pass
class Z(X, Y): pass      # TypeError
```

实测输出：

```text
['D', 'B', 'C', 'A', 'object']
['D2', 'C', 'B', 'A', 'object']
X: ['X', 'A2', 'B2', 'object']
Y: ['Y', 'B2', 'A2', 'object']
Z 报错: Cannot create a consistent method resolution order (MRO) for bases A2, B2
```

这个错误在**定义类时**就抛出，不是运行时才炸——C3 的价值之一就是「不让矛盾的继承关系存在」。

## 三视角解析

### 🧑‍💻 程序员视角
- 写 mixin 时**不要**有 `__init__` 状态，也不要假设自己的方法被谁调用。mixin 只承诺「我提供这些方法」，不承诺调用顺序。
- 多继承链上的 `__init__` 统一写成 `def __init__(self, *args, **kwargs)` 再 `super().__init__(*args, **kwargs)`，否则协作链必断。
- `isinstance` 配合 ABC 比 `type(x) is T` 好：前者尊重子类与鸭子类型的注册（`register()`），后者在代理/装饰器场景下必然失败。

### 🎓 博士生视角
- C3 线性化是为了同时满足「局部优先序」与「单调性」——父类的 MRO 必须在子类的 MRO 中保持相对顺序。Python 2.2 时期的旧式类用的是深度优先，导致菱形继承行为反直觉，C3 是那次的正式修复。
- `super()` 的零参数形式依赖编译器注入 `__class__` 闭包单元，这使它在运行时能知道「我是在哪个类里被调用的」。这也是为什么 `super()` 不能用在类外的普通函数里。
- 把 mixin 与 Haskell 的 type class、Rust 的 trait 对比可见：后两者是「列出的能力由类型显式声明」，Python 的 mixin 是「谁在 MRO 上谁生效」，更隐式、更难静态检查（mypy 对 MRO 的推导有限）。

### 📚 考研者视角
- 与 408 的「多继承二义性」对照：C++ 用虚继承解决菱形问题，Java 干脆禁止类多继承、只允许多实现接口。Python 选择全开放 + C3 线性化，代价是运行期才能确定行为。
- 面试常问「Python 支持多继承吗？怎么解决菱形问题？」——答：支持；用 C3 线性化生成 MRO，冲突时报 TypeError，配合 `super()` 做协作式调用。
- 记忆锚点：**MRO 是 C3 线性化；super() 找的是 MRO 上下一个，不是父类**。
