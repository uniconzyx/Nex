#!/usr/bin/env python3
"""生成 py-ch03 的 examples/*.json，expected_output 取真实 stdout。"""
import io
import json
import os
import sys

OUT = os.path.join(os.path.dirname(__file__), "examples")

EXAMPLES = [
    ("ex01-list-dynamic-array",
     "list 是动态数组：原地扩容，对象身份稳定",
     '''xs = []
for n in range(5):
    xs.append(n)
print(xs)

a = []
before = id(a)
a.append(1)
print("same object after append:", id(a) == before)
print("list 按需 over-allocation 扩容，append 不创建新对象")
'''),
    ("ex02-list-comprehension",
     "列表推导式：映射 + 过滤，嵌套扁平化",
     '''nums = [1, 2, 3, 4, 5]
squares = [x * x for x in nums if x % 2 == 1]
print(squares)
matrix = [[1, 2], [3, 4]]
flat = [v for row in matrix for v in row]
print(flat)
'''),
    ("ex03-dict-comprehension",
     "字典推导式",
     '''words = ["apple", "banana", "cherry"]
lengths = {w: len(w) for w in words}
print(lengths)
squares = {x: x * x for x in range(1, 4)}
print(squares)
'''),
    ("ex04-set-operations",
     "set 集合运算：并/交/差/对称差/子集",
     '''a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
print("union:", a | b)
print("intersection:", a & b)
print("difference:", a - b)
print("symmetric:", a ^ b)
print("subset:", {3, 4}.issubset(a))
'''),
    ("ex05-shallow-vs-deep",
     "浅拷贝 vs 深拷贝：嵌套对象是否共享",
     '''import copy
a = [1, [2, 3], 4]
b = copy.copy(a)          # 浅拷贝：外层新列表，内层共享
b[1].append(99)
print("after shallow, a:", a)
b2 = copy.deepcopy(a)     # 深拷贝：内层也独立
b2[1].append(100)
print("after deep, a:", a)
'''),
    ("ex06-deepcopy-object-graph",
     "深拷贝切断对象图：共享子对象不再共享",
     '''import copy
shared = {"owner": "x"}
a = [shared, shared]
b = copy.copy(a)          # 浅拷贝：两个元素仍指向同一 shared
c = copy.deepcopy(a)      # 深拷贝：shared 也被复制
a[0]["v"] = 1
print("shallow copy b sees:", b[0])
c[0]["v"] = 2
print("deep copy c independent:", c[0], a[0])
'''),
    ("ex07-generator-lazy",
     "生成器表达式惰性求值：用到才计算",
     '''def gen():
    for i in range(3):
        print(f"yield {i}")
        yield i * i

g = gen()
print("created, not yet computed")
print("first:", next(g))
print("second:", next(g))
'''),
    ("ex08-tuple-immutable",
     "tuple 不可变，但内部可变对象可改",
     '''t = (1, 2, 3)
print(t[0])
inner = [4, 5]
t2 = (1, inner)
t2[1].append(6)   # 元组本身不可变，所引用的列表可变
print(t2)
'''),
    ("ex09-dict-order-hash",
     "dict 自 3.7 保留插入序；同一进程内哈希稳定",
     '''d = {}
d["c"] = 3
d["a"] = 1
d["b"] = 2
print(list(d.keys()))   # 插入序
print("hash stable:", hash("hello") == hash("hello"))
'''),
    ("ex10-list-slice-copy",
     "切片产生新列表（浅拷贝）",
     '''xs = [1, 2, 3]
ys = xs[:]
ys.append(4)
print("xs:", xs)
print("ys:", ys)
'''),
    ("ex11-set-comprehension-dedup",
     "集合推导式去重（排序后输出保证稳定）",
     '''text = "abracadabra"
uniq = sorted({ch for ch in text})
print(uniq)
print("count:", len({ch for ch in text}))
'''),
    ("ex12-generator-yield",
     "yield 生成器函数：状态挂起与恢复",
     '''def fib(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

print(list(fib(7)))
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
