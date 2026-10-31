# -*- coding: utf-8 -*-
"""给 py-ch09 补 bilibili_list（原为空的真实缺口）。

BV 号均经 `x/web-interface/view` 实测可播，标题/时长/UP 人工核对：
  BV1FXDVYkEQh  一鼓作气拿下Python的拦路虎：面向对象  158min  苑昊老师
  BV1Vt411E7E3  【Python】Python中的类与对象           46min   小渔学长
  BV1b84y1e7hG  【python】魔术方法大全（一）——基础篇    7min    码农高天
  BV1mT43zhE8L  Python 魔术方法入门：__new__ 与 init 顺序验证  16min  水哥澎湃

用法：python scripts/fix_py09_sources.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "python" / "_manifest.json"
CID = "py-ch09"

BILI = [
    {
        "name": "一鼓作气拿下 Python 的拦路虎：面向对象",
        "url": "https://www.bilibili.com/video/BV1FXDVYkEQh/",
        "note": "主干课。按「类与实例 → 继承与多态 → 魔术方法」顺序看，"
                "重点看它如何用 `__dict__` 演示属性查找；配合本篇第一节验证「可变类属性共享」",
        "bv": "BV1FXDVYkEQh",
    },
    {
        "name": "Python 中的类与对象",
        "url": "https://www.bilibili.com/video/BV1Vt411E7E3/",
        "note": "46 分钟讲清 self、实例化、类属性与实例属性的区别；"
                "看完能自己解释「为什么 a.tags.append 会影响 b.tags」",
        "bv": "BV1Vt411E7E3",
    },
    {
        "name": "Python 魔术方法大全（一）：基础篇",
        "url": "https://www.bilibili.com/video/BV1b84y1e7hG/",
        "note": "7 分钟速览 `__init__`/`__repr__`/`__eq__`/`__len__` 等常用魔术方法，"
                "用来建立「魔术方法 = 语言协议」的直觉",
        "bv": "BV1b84y1e7hG",
    },
    {
        "name": "魔术方法入门：__new__ 详解与 __init__ 执行顺序验证",
        "url": "https://www.bilibili.com/video/BV1mT43zhE8L/",
        "note": "直接对应本篇「`__init__` 不负责创建对象」一节：视频里现场演示了 `__new__` 在前、"
                "以及 `__new__` 返回非本类实例时 `__init__` 不执行",
        "bv": "BV1mT43zhE8L",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ch = next((c for c in m["chapters"] if c["id"] == CID), None)
    if ch is None:
        print(f"  [fail] 找不到 {CID}")
        return 1

    res = ch.setdefault("resources", {})
    old = res.get("bilibili_list") or []
    print(f"  {CID} 原 bilibili_list: {len(old)} 条 -> 新 {len(BILI)} 条")
    res["bilibili_list"] = BILI
    res["bilibili"] = BILI[0]["url"]

    if not args.apply:
        print("\n  （dry-run，未写盘；加 --apply 生效）")
        return 0

    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  已写入 {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
