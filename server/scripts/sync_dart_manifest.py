"""同步 app/lib/core/models/content_manifest.dart 的 done 标志。

数据源：content/_coverage.json（由 server/scripts/validate_content.py 产出）。
只改 `chapters` 列表区间内的 done 标志，clangUnits 保持不动。
"""
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DART = REPO / "app/lib/core/models/content_manifest.dart"
COVERAGE = REPO / "content/_coverage.json"

if not COVERAGE.exists():
    sys.exit("缺少 content/_coverage.json，请先运行 validate_content.py")

cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
done_ids = {c["id"] for c in cov["chapters"] if c["complete"]}

src = DART.read_text(encoding="utf-8")
start = src.index("static const List<ChapterSummary> chapters = [")
end = src.index("];", start) + 2
block = src[start:end]

changed = []
out_lines = []
for line in block.splitlines():
    m = re.search(r'id:\s*"(cpp-ch\d+)".*?done:\s*(true|false)', line)
    if m:
        cid, cur = m.group(1), m.group(2)
        want = "true" if cid in done_ids else "false"
        if cur != want:
            line = re.sub(r'done:\s*(true|false)', f'done: {want}', line, count=1)
            changed.append(f"{cid} {cur} -> {want}")
    out_lines.append(line)

src = src[:start] + "\n".join(out_lines) + src[end:]

# 修正过期注释
src = src.replace(
    "/// 20 章 C/C++ 课程体系（ch01-ch04 已通过 7 类内容校验）。",
    "/// 20 章 C/C++ 课程体系。done 标志须与 content/_coverage.json 保持同步\n"
    "/// （数据源：server/scripts/validate_content.py 产出的覆盖率报告）。",
)
src = src.replace(
    "/// 由 server/scripts/validate_content.py 校验 7 类内容完整性后同步更新。",
    "/// done 为静态镜像，无自动生成环节，改完内容后需重新同步。",
)

DART.write_text(src, encoding="utf-8")
print("已同步 done 标志:", changed or "（无需变更）")
print("done: true =", src.count("done: true"), "| done: false =", src.count("done: false"))
