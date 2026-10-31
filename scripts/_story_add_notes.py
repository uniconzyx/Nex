#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给台词挂术语批注（note）。

【为什么不给每条都挂】
  141 条里有 21 条含硬术语，但其中一半在本章语境里是自解释的
  （「GC」在本章标题里就写着垃圾回收，「CPU」没人不懂）。
  给它们加注，只会把台词变成词典。所以只挂 9 条：「不懂这个词，这句就读不下去」的那些。

批注写法要求：
  - 一句话，不超过 60 有效字；
  - 解释「是什么」，不解释「怎么用」（用法本章会讲，注释只负责扫清阅读障碍）；
  - 不重复台词里已经说出来的信息。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "_story" / "acts.json"

NOTES = {
    # 术语在本句里承担了核心比喻，不认识就抓不到意思
    "agent-ch06": "KV Cache ＝ 推理时缓存的历史 Key/Value，显存里先扣它，剩下的才留给权重。",
    "ai-ch08": "TTFT ＝ 第一个字吐出来的时间；prefill ＝ 把整段提示词一次算完的那一步。",
    "java-ch08": "GC Root ＝ 可达性分析的起点（如栈上引用、静态字段），从它出发走不到的对象会被回收。",
    "cpp-ch17": "SFINAE ＝ 替换失败不算错误：模板推导失败时静默剔除该重载，而不是报编译错。",
    "fund-ch05": "ASL ＝ 平均查找长度，衡量查找要比较多少次；成功查找与失败查找要分开算。",
    "fund-ch10": "TLB ＝ 页表的高速缓存，专门省掉「取数据前先查页表」的那次访存。",
    "mw-ch02": "RDB ＝ 定时fork子进程拍全量快照；AOF ＝ 追加写命令日志，靠 fsync 策略决定丢多少。",
    "py-ch07": "GIL ＝ 全局解释器锁，同一时刻只允许一个线程执行 Python 字节码。",
    "clang-u02": "realloc ＝ 调整已分配内存大小，可能就地扩展，也可能整块搬到新地址。",
}


def main() -> None:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    hit = 0
    for subj in doc["subjects"].values():
        for act in subj["acts"]:
            for ch in act["chapters"]:
                note = NOTES.get(ch["id"])
                if note:
                    # 保持字段顺序：id / tone / line / note / anchor
                    ordered = {}
                    for k in ("id", "tone", "line"):
                        if k in ch:
                            ordered[k] = ch[k]
                    ordered["note"] = note
                    for k, v in ch.items():
                        if k not in ordered:
                            ordered[k] = v
                    ch.clear()
                    ch.update(ordered)
                    hit += 1
    SRC.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"挂批注 {hit} 条")


if __name__ == "__main__":
    main()
