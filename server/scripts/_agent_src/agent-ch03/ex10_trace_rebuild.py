# title: 从散乱日志还原一次调用链：parent 缺失比慢更可怕
# 本地模拟：12 条日志、两种格式、顺序被打乱。重建 span 树，算 self time 与关键路径。
# 工程价值：总耗时 900ms 时，只有 self time 能告诉你「该优化谁」。

import json
import random
import re

# 两种格式混排：SDK 结构化日志 + 网关文本日志
LOGS = [
    '{"ts": 0, "req": "r1", "span": "s1", "parent": null, "svc": "gateway", "dur": 900, "status": "ok"}',
    "2026-10-21T10:00:00.010Z INFO [req=r1 span=s2 parent=s1] auth dur=20ms status=ok",
    '{"ts": 30, "req": "r1", "span": "s3", "parent": "s1", "svc": "retriever", "dur": 300, "status": "ok"}',
    "2026-10-21T10:00:00.040Z INFO [req=r1 span=s4 parent=s3] embed dur=100ms status=ok",
    '{"ts": 150, "req": "r1", "span": "s5", "parent": "s3", "svc": "reranker", "dur": 160, "status": "ok"}',
    '{"ts": 320, "req": "r1", "span": "s6", "parent": "s1", "svc": "llm", "dur": 540, "status": "ok"}',
    "2026-10-21T10:00:00.690Z INFO [req=r1 span=s7 parent=s6] stream dur=170ms status=ok",
    '{"ts": 870, "req": "r1", "span": "s8", "parent": "s1", "svc": "logger", "dur": 10, "status": "ok"}',
    '{"ts": 400, "req": "r1", "span": "s9", "parent": "sX", "svc": "tool", "dur": 10, "status": "ok"}',
    "2026-10-21T10:00:00.120Z INFO [req=r1 span=s10 parent=s2] cache dur=8ms status=ok",
    '{"ts": 130, "req": "r1", "span": "s11", "parent": "s3", "svc": "filter", "dur": 30, "status": "ok"}',
    "2026-10-21T10:00:00.400Z INFO [req=r1 span=s12 parent=s6] retry dur=120ms status=error",
]

TEXT_RE = re.compile(
    r"\[req=(?P<req>\w+) span=(?P<span>\w+) parent=(?P<parent>\w+)\] "
    r"(?P<svc>\w+) dur=(?P<dur>\d+)ms status=(?P<status>\w+)"
)


def parse(line):
    if line.startswith("{"):
        d = json.loads(line)
        return {"req": d["req"], "span": d["span"], "parent": d["parent"],
                "svc": d["svc"], "dur": d["dur"], "status": d["status"]}
    m = TEXT_RE.search(line)
    return {"req": m["req"], "span": m["span"], "parent": m["parent"],
            "svc": m["svc"], "dur": int(m["dur"]), "status": m["status"]}


spans = [parse(x) for x in LOGS]
random.Random(3).shuffle(spans)
by_id = {s["span"]: s for s in spans}
children = {s["span"]: [] for s in spans}
orphans = []
for s in spans:
    p = s["parent"]
    if p and p in by_id:
        children[p].append(s)
    elif p:
        orphans.append(s)

for k in children:
    children[k].sort(key=lambda x: x["span"])

root = by_id["s1"]
total = root["dur"]


def self_time(s):
    return s["dur"] - sum(c["dur"] for c in children[s["span"]])


def walk(s, depth=0, out=None):
    out = out if out is not None else []
    out.append((depth, s, self_time(s)))
    for c in children[s["span"]]:
        walk(c, depth + 1, out)
    return out


rows = walk(root)
print(f"从 {len(LOGS)} 条日志解析出 {len(spans)} 个 span（两种格式），按 parent 重建树：\n")
for depth, s, st in rows:
    flag = " [error]" if s["status"] == "error" else ""
    print(f"{'  ' * depth}{s['span']} {s['svc']:<10} dur={s['dur']:>4}ms self={st:>4}ms{flag}")

print(f"\n{'span':<6}{'svc':<11}{'dur':>6}{'self':>6}{'占比':>7}  说明")
for depth, s, st in rows:
    note = "关键路径" if s["span"] in ("s1", "s6", "s7") else ""
    print(f"{s['span']:<6}{s['svc']:<11}{s['dur']:>6}{st:>6}{st/total:>7.0%}  {note}")

print(f"\n总耗时 {total}ms；子树 self time 之和 = {sum(st for _, _, st in rows)}ms（应与总耗时一致）")
print(f"孤儿 span：{len(orphans)} 个（{', '.join(s['span'] + '→' + s['parent'] for s in orphans)}）")
print(f"  s9 的 parent=sX 在日志里不存在：它可能是异步任务，也可能是日志丢了——")
print(f"  两种情况的处理完全不同，所以 trace 里必须记录 span 结束事件，而不是只记录开始。")

path = ["s1", "s6", "s7"]
crit = sum(self_time(by_id[p]) for p in path)
print(f"\n关键路径 {' -> '.join(path)}：{crit}ms，占总耗时 {crit/total:.0%}")
print("读法：llm 的 self time 250ms 是最大单项；retriever 的 300ms 里 160ms 在 rerank、")
print("      100ms 在 embed、30ms 在 filter，三者串行——只看 dur 会误以为整个 retriever 都要重写。")
print("结论：调用链还原的三件事——统一 request_id、补齐 parent、区分 dur 与 self time；")
print("      没有 parent 的日志只能算「事件流」，不能算「链路」。")
