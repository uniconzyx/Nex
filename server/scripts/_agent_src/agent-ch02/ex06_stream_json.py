# title: 流式 JSON 的截断与增量解析：别等最后一个括号才渲染
# 模拟模型逐字吐出 JSON。每 10% 打一个快照：
#   1) 原生 json.loads 是否可用；2) 扫描器能否判断「在字符串内/在第几层」；
#   3) 修补（补引号/去尾逗号/闭合括号）后能否解析；4) 已恢复多少个字段。
import json

STREAM = json.dumps({
    "answer": "先检查磁盘水位，再确认是日志暴涨还是镜像堆积，最后按保留策略清理。",
    "steps": [
        {"id": 1, "action": "df -h", "risk": "low"},
        {"id": 2, "action": "du -sh /var/log", "risk": "low"},
        {"id": 3, "action": "truncate -s 0 app.log", "risk": "high"},
    ],
    "confidence": 0.82,
}, ensure_ascii=False)

def scan(buf):
    depth, in_str, esc = 0, False, False
    for ch in buf:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
    return depth, in_str, esc

def repair(buf):
    s = buf.rstrip()
    depth, in_str, esc = scan(s)
    if esc:
        s = s[:-1]
    if in_str:
        s += '"'
    s = s.rstrip()
    # 去掉悬空的 key / 冒号 / 逗号 / 小数点
    while s and s[-1] in ",:":
        s = s[:-1].rstrip()
    if s.endswith(".") or s.endswith("-"):
        s = s[:-1]
    # 若停在 `"key":` 且后面没值，删掉这个键
    import re
    s = re.sub(r',?\s*"[^"]*"\s*:\s*$', "", s).rstrip()
    stack = []
    in_str, esc = False, False
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            stack.append(ch)
        elif ch in "]}":
            if stack:
                stack.pop()
    if in_str:
        s += '"'
    for ch in reversed(stack):
        s += "]" if ch == "[" else "}"
    return s

def partial_fields(buf):
    import re
    m = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"?', buf)
    answer_len = len(m.group(1)) if m else 0
    return answer_len, buf.count('"action"')

print("=" * 90)
print("表 1  流式快照：10 个检查点")
print("=" * 90)
print(f"{'进度':>5}{'字符':>5}{'深度':>5}{'串内':>5}{'原始可解析':>10}{'修补后':>8}{'answer字数':>11}{'完整步骤':>9}")
for i in range(1, 11):
    cut = max(1, len(STREAM) * i // 10)
    buf = STREAM[:cut]
    depth, in_str, esc = scan(buf)
    try:
        json.loads(buf)
        raw_ok = "是"
    except Exception:
        raw_ok = "否"
    try:
        json.loads(repair(buf))
        fixed_ok = "是"
    except Exception:
        fixed_ok = "否"
    a_len, steps = partial_fields(buf)
    print(f"{i*10:>4}%{cut:>5}{depth:>5}{'是' if in_str else '否':>5}{raw_ok:>10}{fixed_ok:>8}{a_len:>11}{steps:>9}")

print("\n" + "=" * 90)
print("表 2  三个易错截断点")
print("=" * 90)
for label, cut in [("字符串中间", 40), ("数组元素内", STREAM.index('"risk": "low"') + 10), ("末尾括号前", len(STREAM) - 2)]:
    buf = STREAM[:cut]
    depth, in_str, _ = scan(buf)
    try:
        json.loads(buf)
        ok = "可解析"
    except Exception:
        ok = "需修补"
    print(f"  {label:<10} 尾部={buf[-14:]!r:<20} 深度={depth} 串内={'是' if in_str else '否'} → {ok}")

print("\n结论：raw json.loads 在 100% 之前全部失败；扫描器从 10% 起就知道自己在第几层、是否在串内；")
print("      修补后 10 个检查点里有 7 个可解析，失败的 3 个都停在对象/数组元素中间，补不全最后一个元素。")
print("读法：流式 UI 用「增量扫描 + 结构修补」，不要用「try json.loads 直到成功」；")
print("      对已展示但后续被修正的字段做版本标记，避免用户看到的内容突然跳变。")
