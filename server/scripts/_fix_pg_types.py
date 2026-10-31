"""一次性脚本：把 models 里的 PG 方言类型换成跨库别名（JSONType / UUIDType）。"""
import re
import glob
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

changed = []
for f in sorted(glob.glob("app/models/*.py")):
    base = os.path.basename(f)
    if base == "types.py":
        continue
    s = open(f, encoding="utf-8").read()
    orig = s
    if "JSONB" not in s and "UUID(" not in s:
        continue

    need = []
    m = re.search(r"^from sqlalchemy\.dialects\.postgresql import (.+)$\n", s, re.M)
    if m:
        names = [n.strip() for n in m.group(1).split(",")]
        if "JSONB" in names:
            need.append("JSONType")
        if "UUID" in names:
            need.append("UUIDType")
        s = s[: m.start()] + s[m.end():]

    s = re.sub(r"\bJSONB\b", "JSONType", s)
    s = re.sub(r"UUID\(as_uuid=True\)", "UUIDType", s)

    if need:
        imp = "from app.models.types import " + ", ".join(need) + "\n"
        lines = s.split("\n")
        # 找到最后一个顶层 import 行的位置
        last = -1
        depth = 0
        for i, ln in enumerate(lines):
            if depth == 0 and re.match(r"^(from|import) ", ln):
                last = i
            depth += ln.count("(") - ln.count(")")
            depth = max(depth, 0)
            if depth == 0 and last >= 0 and i > last:
                # import 块中断
                nxt = ln.strip()
                if nxt and not nxt.startswith(")"):
                    break
        lines.insert(last + 1, imp.rstrip("\n"))
        s = "\n".join(lines)

    s = re.sub(r"\n{3,}", "\n\n", s)
    if s != orig:
        open(f, "w", encoding="utf-8").write(s)
        changed.append(base)

print("changed:", changed)
