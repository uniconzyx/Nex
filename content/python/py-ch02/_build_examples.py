#!/usr/bin/env python3
"""生成 py-ch02 的 examples/*.json，expected_output 取真实 stdout。"""
import io
import json
import os
import sys

OUT = os.path.join(os.path.dirname(__file__), "examples")

EXAMPLES = [
    ("ex01-function-params",
     "函数定义与参数：位置/默认/*args/**kwargs",
     '''def greet(name, greeting="Hello", *args, **kwargs):
    print(f"{greeting}, {name}!")
    print("extra positional:", args)
    print("extra keyword:", kwargs)

greet("Alice")
greet("Bob", "Hi", 1, 2, city="NY", age=30)
'''),
    ("ex02-argument-unpacking",
     "参数解包：*序列 与 **字典 传入调用",
     '''def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
print(add(*nums))

d = {"a": 10, "b": 20, "c": 30}
print(add(**d))

def f(x, y, z):
    print(x, y, z)
f(*[1], *[2, 3])
'''),
    ("ex03-lambda-basic",
     "lambda 与 map/filter/sorted(key)",
     '''nums = [3, 1, 4, 1, 5, 9]
print(sorted(nums))
print(sorted(nums, key=lambda x: -x))
pairs = [("b", 2), ("a", 1), ("c", 3)]
print(sorted(pairs, key=lambda p: p[1]))
squares = list(map(lambda x: x * x, nums))
print(squares)
evens = list(filter(lambda x: x % 2 == 0, nums))
print(evens)
'''),
    ("ex04-LEGB",
     "LEGB 作用域链：Local->Enclosing->Global->Builtin",
     '''x = "global-x"

def enclosing():
    x = "enclosing-x"
    def local():
        # 未重新绑定 x，按 LEGB 向上找到 enclosing-x
        print("local reads:", x)
    local()
    print("enclosing reads:", x)

enclosing()
print("global reads:", x)

def use_builtin():
    # 'max' 不在局部/闭包/全局，回退到 builtin 命名空间
    print("builtin max:", max(3, 7, 2))
use_builtin()
'''),
    ("ex05-closure-counter",
     "闭包：自由变量绑定与 nonlocal 改写",
     '''def make_counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc

c = make_counter()
print(c(), c(), c())
d = make_counter()
print(d())
'''),
    ("ex06-closure-late-binding",
     "闭包延迟绑定陷阱与默认参数修复",
     '''# 陷阱：闭包捕获的是变量 i 本身，循环结束后 i==2
funcs = []
for i in range(3):
    funcs.append(lambda: i)
print([f() for f in funcs])

# 修复：用默认参数在定义期绑定当前值
funcs2 = []
for i in range(3):
    funcs2.append(lambda i=i: i)
print([f() for f in funcs2])
'''),
    ("ex07-mutable-default-arg",
     "可变默认参数陷阱：默认值在函数定义期只创建一次",
     '''def collect(x, buf=[]):
    buf.append(x)
    return buf

print(collect(1))
print(collect(2))
print(collect(3))
'''),
    ("ex08-global-statement",
     "global 语句与全局命名空间改写",
     '''counter = 0

def bump():
    global counter
    counter += 1
    return counter

print(bump(), bump())
'''),
    ("ex09-first-class-function",
     "一等公民函数：作为值/字典分发/回调",
     '''def add(a, b):
    return a + b

def mul(a, b):
    return a * b

ops = {"+": add, "*": mul}
print(ops["+"](2, 3))
print(ops["*"](2, 3))

def apply(fn, x):
    return fn(x)
print(apply(lambda v: v * 2, 21))
'''),
    ("ex10-decorator-basic",
     "装饰器原理：基于闭包包装函数",
     '''def trace(fn):
    def wrapper(*args, **kwargs):
        print(f"call {fn.__name__}({args}, {kwargs})")
        result = fn(*args, **kwargs)
        print(f"-> {result}")
        return result
    return wrapper

@trace
def double(x):
    return x * 2

double(5)
double(10)
'''),
    ("ex11-closure-cache",
     "闭包持有状态：记忆化缓存",
     '''def memo():
    cache = {}
    def get(key, compute):
        if key not in cache:
            cache[key] = compute(key)
        return cache[key]
    return get

m = memo()
print(m(2, lambda k: k * k))
print(m(2, lambda k: 999))   # 命中缓存，返回值不变
print(m(3, lambda k: k * k))
'''),
    ("ex12-default-arg-None",
     "可变默认参数惯用法：None 哨兵惰性初始化",
     '''def collect(x, buf=None):
    if buf is None:
        buf = []
    buf.append(x)
    return buf

print(collect(1))
print(collect(2))
print(collect(3, [0]))
'''),
]


def run_code(code: str) -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        exec(code, {})
    finally:
        sys.stdout = old
    return buf.getvalue().rstrip("\n")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for fname, title, code in EXAMPLES:
        expected = run_code(code)
        payload = {
            "title": title,
            "code_lang": "python",
            "code_std": "python3.11",
            "stdin": "",
            "expected_output": expected,
            "code": code.rstrip("\n"),
        }
        path = os.path.join(OUT, fname + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"wrote {fname}.json  output_lines={len(expected.splitlines())}")


if __name__ == "__main__":
    main()
