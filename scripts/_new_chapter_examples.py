# -*- coding: utf-8 -*-
"""新增章节的 examples（10 个/章，全部真跑过）。

纪律：``expected_output`` 必须是**跑出来的**，不是推出来的。本文件里的每一条
输出都用 node / python 实际执行确认过（见 ../scratch 里的验证脚本），
与正文里的「实际输出」是同一串字符。

字段与既有章节一致：title / code_lang / code_std / stdin / expected_output / code
"""

EXAMPLES: dict[str, list[dict]] = {}

# ═══════════════════════════════════════════ fs-ch09 · TypeScript
_TS = [
    {
        "title": "结构类型：多一个成员不报错，少一个报错",
        "code": """// 只用 JS 表达结构类型的行为（TS 的检查发生在编译期，运行期无痕迹）
function takesPoint(p) { return p.x + p.y; }

const withExtra = { x: 1, y: 2, label: "origin" }; // 多一个 label：合法
const missing = { x: 1 };                          // 少一个 y：TS 会报错

console.log(takesPoint(withExtra));
console.log(takesPoint(missing));
""",
        "expected": "3\nNaN",
    },
    {
        "title": "类型擦除：typeof 看到的是运行时类型",
        "code": """function describe(s) {
  if (s.kind === "circle") return `circle:${typeof s.r}`;
  return `square:${typeof s.side}`;
}

console.log(describe({ kind: "circle", r: 2 }));
console.log(describe({ kind: "square", side: 3 }));
console.log(typeof describe);
""",
        "expected": "circle:number\nsquare:number\nfunction",
    },
    {
        "title": "泛型擦除：同一个函数适配所有类型",
        "code": """function first(arr) { return arr[0]; }

console.log(first([10, 20]));
console.log(first([]));
console.log(String(first(["a"])));
""",
        "expected": "10\nundefined\na",
    },
    {
        "title": "类型守卫单看对象形状会误判",
        "code": """// 只判断「是对象且非 null」的守卫：任何对象都会通过
function isCircleWeak(x) { return typeof x === "object" && x !== null; }

// 逐字段校验的守卫：判别字段 + 必需字段类型
function isCircle(x) {
  return typeof x === "object" && x !== null &&
    x.kind === "circle" && typeof x.r === "number";
}

console.log(isCircleWeak({ r: 1 }), isCircle({ r: 1 }));
console.log(Math.PI * undefined ** 2); // 弱守卫放行后算出来的东西
console.log(isCircle({ kind: "circle", r: 2 }));
""",
        "expected": "true false\nNaN\ntrue",
    },
    {
        "title": "可辨识联合 + 穷尽检查（运行时部分）",
        "code": """function areaShape(s) {
  switch (s.kind) {
    case "circle": return Math.PI * s.r ** 2;
    case "square": return s.side ** 2;
    case "triangle": {
      const p = (s.a + s.b + s.c) / 2;
      return Math.sqrt(p * (p - s.a) * (p - s.b) * (p - s.c));
    }
    default:
      // TS 里这一行是 `const n: never = s;`，加了新形状忘写分支会在此报错
      throw new Error(`未处理的形状: ${JSON.stringify(s)}`);
  }
}

console.log(areaShape({ kind: "square", side: 3 }).toFixed(2));
console.log(areaShape({ kind: "triangle", a: 3, b: 4, c: 5 }).toFixed(2));
try { areaShape({ kind: "rect", w: 1, h: 1 }); } catch (e) { console.log(e.message); }
""",
        "expected": "9.00\n6.00\n未处理的形状: {\"kind\":\"rect\",\"w\":1,\"h\":1}",
    },
    {
        "title": "groupBy：Partial<Record> 语义（键可能不存在）",
        "code": """function groupBy(items, keyOf) {
  const out = {};
  for (const it of items) {
    const k = keyOf(it);
    (out[k] ??= []).push(it);
  }
  return out;
}

const people = [
  { name: "a", dept: "eng" },
  { name: "b", dept: "design" },
  { name: "c", dept: "eng" },
];
const g = groupBy(people, (p) => p.dept);
console.log(JSON.stringify(g));
console.log(g.sales === undefined); // 不存在的键是 undefined，不是 []
console.log(groupBy([], (x) => x).constructor === Object);
""",
        "expected": "{\"eng\":[{\"name\":\"a\",\"dept\":\"eng\"},{\"name\":\"c\",\"dept\":\"eng\"}],\"design\":[{\"name\":\"b\",\"dept\":\"design\"}]}\ntrue\ntrue",
    },
    {
        "title": "unknown 与 any 的区别：在使用点才暴露",
        "code": """// any 直接可用；unknown 必须先收窄
function lenAny(x) { return x.length; }
function lenUnknown(x) {
  if (typeof x === "string" || Array.isArray(x)) return x.length;
  return -1;
}

console.log(lenAny("abc"), lenUnknown("abc"), lenUnknown([1, 2]), lenUnknown(42));
""",
        "expected": "3 3 2 -1",
    },
    {
        "title": "可选链与空值合并：不改行为地躲开 undefined",
        "code": """const user = { name: "mimi", profile: { city: "Hangzhou" } };
const ghost = { name: "nobody" };

console.log(user.profile?.city);
console.log(ghost.profile?.city);
console.log(ghost.profile?.city ?? "未知");
console.log(ghost.profile?.city || "未知"); // || 会把 "" 和 0 也当空
""",
        "expected": "Hangzhou\nundefined\n未知\n未知",
    },
    {
        "title": "readonly 只在类型层生效，运行时可改",
        "code": """function sum(ro) { return ro.reduce((a, b) => a + b, 0); }

const arr = [1, 2, 3];
console.log(sum(arr));
arr.push(4);          // readonly 只是编译期约束，运行期照样能改
console.log(sum(arr), arr.length);
""",
        "expected": "6\n10 4",
    },
    {
        "title": "satisfies：保字面量类型又不失校验",
        "code": """// TS 里 `const conf = { retry: 3 } satisfies Config` 会保留 retry 的窄类型 3
// 运行时等价于普通对象，这里演示「配置读取」的常见写法
const conf = { retry: 3, timeout: 1000, verbose: false };

for (const [k, v] of Object.entries(conf)) {
  console.log(k, typeof v);
}
console.log(conf.retry.toFixed(1));
""",
        "expected": "retry number\ntimeout number\nverbose boolean\n3.0",
    },
]

# ═══════════════════════════════════════════ py-ch09 · 面向对象
_PY = [
    {
        "title": "实例属性遮蔽类属性",
        "code": """class Cat:
    sound = "meow"

c = Cat()
print(c.sound)
c.sound = "nya"
print(Cat.sound, c.sound)
print("sound" in vars(c), "sound" in vars(Cat))
""",
        "expected": "meow\nmeow nya\nTrue True",
    },
    {
        "title": "可变类属性：所有实例共享同一个 list",
        "code": """class Box:
    items = []

    def add(self, x):
        self.items.append(x)

a, b = Box(), Box()
a.add(1)
b.add(2)
print(a.items, b.items)
print(a.items is b.items)
""",
        "expected": "[1, 2] [1, 2]\nTrue",
    },
    {
        "title": "MRO 与 C3 线性化",
        "code": """class A:
    def hello(self): return "A"
class B(A):
    def hello(self): return "B"
class C(A):
    def hello(self): return "C"
class D(B, C):
    pass

print(D().hello())
print([x.__name__ for x in D.__mro__])
""",
        "expected": "B\n['D', 'B', 'C', 'A', 'object']",
    },
    {
        "title": "super() 走的是 MRO 下一个，不是父类",
        "code": """class Base:
    def __init__(self):
        print("Base")

class A2(Base):
    def __init__(self):
        print("A")
        super().__init__()

class B2(Base):
    def __init__(self):
        print("B")
        super().__init__()

class C2(A2, B2):
    def __init__(self):
        print("C")
        super().__init__()

C2()
""",
        "expected": "C\nA\nB\nBase",
    },
    {
        "title": "__eq__ 与 __hash__ 必须成对：set 里找得到",
        "code": """class Point:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))

p = Point(1, 2)
s = {Point(1, 2)}
print(p in s, p == Point(1, 2), len({Point(1, 2), Point(1, 2)}))
""",
        "expected": "True True 1",
    },
    {
        "title": "不实现 __hash__ 的后果",
        "code": """class NoHash:
    def __init__(self, x):
        self.x = x

    def __eq__(self, other):
        return isinstance(other, NoHash) and self.x == other.x

print(NoHash.__hash__)
try:
    {NoHash(1)}
except TypeError as e:
    print("TypeError:", e)
""",
        "expected": "None\nTypeError: unhashable type: 'NoHash'",
    },
    {
        "title": "Playlist：接入 len / for / in / 下标 / repr / ==",
        "code": """class Playlist:
    def __init__(self, songs):
        self._songs = list(songs)

    def __len__(self): return len(self._songs)
    def __iter__(self): return iter(self._songs)
    def __contains__(self, x): return x in self._songs
    def __getitem__(self, i): return self._songs[i]
    def __repr__(self): return f"Playlist({self._songs!r})"

    def __eq__(self, other):
        if not isinstance(other, Playlist):
            return NotImplemented
        return self._songs == other._songs

pl = Playlist(["a", "b", "c"])
print(len(pl), list(pl), "b" in pl, pl[0], pl[1:3])
print(pl == Playlist(["a", "b", "c"]))
print(repr(pl))
""",
        "expected": "3 ['a', 'b', 'c'] True a ['b', 'c']\nTrue\nPlaylist(['a', 'b', 'c'])",
    },
    {
        "title": "Mixin + MutableSequence：只写 5 个方法，补齐整个容器协议",
        "code": """import json
from collections.abc import MutableSequence

class JsonMixin:
    def to_json(self):
        return json.dumps(self._items, ensure_ascii=False)

class Bag(JsonMixin, MutableSequence):
    def __init__(self, items=()):
        self._items = list(items)
    def __getitem__(self, i): return self._items[i]
    def __setitem__(self, i, v): self._items[i] = v
    def __delitem__(self, i): del self._items[i]
    def __len__(self): return len(self._items)
    def insert(self, i, v): self._items.insert(i, v)

b = Bag([1, 2])
b.append(3)
print(len(b), list(b), 2 in b, b.pop(), b.to_json())
b.reverse()
print(list(b), isinstance(b, MutableSequence))
""",
        "expected": "3 [1, 2, 3] True 3 [1, 2]\n[2, 1] True",
    },
    {
        "title": "classmethod 工厂在子类上返回子类实例",
        "code": """class Shape:
    def __init__(self, name):
        self.name = name

    @classmethod
    def unit(cls):
        return cls("unit")

    @staticmethod
    def describe():
        return "静态方法拿不到 cls"

class Circle(Shape):
    pass

print(type(Shape.unit()).__name__, type(Circle.unit()).__name__)
print(Shape.describe())
""",
        "expected": "Shape Circle\n静态方法拿不到 cls",
    },
    {
        "title": "@property：只读派生属性与 setter 校验",
        "code": """class Circle:
    def __init__(self, r):
        self.r = r

    @property
    def area(self):
        return round(3.14159 * self.r ** 2, 2)

    @property
    def diameter(self):
        return self.r * 2

c = Circle(2)
print(c.area, c.diameter)
print(isinstance(Circle.area, property))
try:
    c.area = 10
except AttributeError as e:
    print("AttributeError:", e)
""",
        "expected": "12.57 4\nTrue\nAttributeError: property 'area' of 'Circle' object has no setter",
    },
]

EXAMPLES["fs-ch09"] = [
    {"title": e["title"], "code_lang": "javascript", "code_std": "es2022", "stdin": "",
     "expected_output": e["expected"], "code": e["code"]} for e in _TS
]
EXAMPLES["py-ch09"] = [
    {"title": e["title"], "code_lang": "python", "code_std": "3.11", "stdin": "",
     "expected_output": e["expected"], "code": e["code"]} for e in _PY
]
