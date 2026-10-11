"""CppMind Flutter 前端静态健康检查（无法本地编译时的替代手段）。

本机没有 flutter/dart 工具链，`flutter analyze` 跑不了，因此用脚本覆盖
三类**高频、静默、编译期才会暴露**的问题：

  A. 相对 import 路径失效
     `lib/widgets/` 与 `lib/features/**/` 到 `lib/core/` 的层级深度不同
     （前者 `../core/`，后者 `../../core/`），手写极易多/少一层。

  B. 枚举成员悬空引用
     如 `CatMood.sad` —— CatMood 里并没有 sad，属于编译错误。

  C. 音效「三处同源」一致性
     同一套音效定义在三个地方，任何一处漏改都会造成 Flutter 与 Web
     听感不一致（或运行时找不到资源）：
       1. app/tool/gen_audio_assets.py  的 SOUNDS（生成 WAV）
       2. app/assets/audio/*.wav        实际资源
       3. app/lib/core/audio/sound_service.dart 的 CppSound 枚举
       4. web-preview/index.html        的 Web Audio 引擎 S 表

用法：
    python app/tool/check_dart_health.py
退出码：发现问题时为 1
"""

from __future__ import annotations

import pathlib
import re
import sys

APP = pathlib.Path(__file__).resolve().parents[1]      # app/
LIB = APP / "lib"
REPO = APP.parent

IMPORT_RE = re.compile(r'^\s*(?:import|export|part)\s+[\'"]([^\'"]+)[\'"]', re.MULTILINE)


# ---------------------------------------------------------------- A. import

def check_imports() -> list[str]:
    problems: list[str] = []
    for f in sorted(LIB.rglob("*.dart")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in IMPORT_RE.finditer(text):
            target = m.group(1)
            if not target.startswith("."):
                continue
            if not (f.parent / target).exists():
                rel = str(f.relative_to(LIB)).replace("\\", "/")
                problems.append(f"import 无效  {rel}: {target}")
    return problems


# ---------------------------------------------------------------- B. enum

def parse_enums(root: pathlib.Path) -> dict[str, set[str]]:
    """解析所有 enum 的成员名（容忍行内注释与带构造参数的枚举）。"""
    enums: dict[str, set[str]] = {}
    for f in root.rglob("*.dart"):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\benum\s+(\w+)\s*\{", text):
            name, i, depth = m.group(1), m.end(), 1
            while i < len(text) and depth:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            body = text[m.end(): i - 1]
            body = re.sub(r"//[^\n]*", "", body)
            body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
            body = re.sub(r"\([^()]*\)", "", body)   # 去掉构造参数
            members = set()
            for part in body.split(","):
                mm = re.match(r"\s*(\w+)", part)
                if mm:
                    members.add(mm.group(1))
            enums[name] = members
    return enums


def check_enum_refs(enums: dict[str, set[str]]) -> list[str]:
    problems: list[str] = []
    for f in sorted(LIB.rglob("*.dart")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\b(\w+)\.(\w+)", text):
            en, val = m.group(1), m.group(2)
            members = enums.get(en)
            if members is None or not members:
                continue
            # 跳过 values / name / index 等 Enum 内置
            if val in ("values", "name", "index", "value", "entries"):
                continue
            if val not in members:
                line = text[: m.start()].count("\n") + 1
                rel = str(f.relative_to(LIB)).replace("\\", "/")
                problems.append(f"枚举悬空  {rel}:{line}  {en}.{val}")
    return problems


# ---------------------------------------------------------------- C. 音效同源

def audio_sources() -> dict[str, set[str]]:
    """收集四处音效名。"""
    out: dict[str, set[str]] = {}

    gen = APP / "tool" / "gen_audio_assets.py"
    out["生成器(SOUNDS)"] = set(re.findall(r'^\s{4}"(\w+)":\s*\w+,', gen.read_text(encoding="utf-8"), re.M))

    d = APP / "assets" / "audio"
    out["WAV 资源"] = {p.stem for p in d.glob("*.wav")} if d.is_dir() else set()

    svc = LIB / "core" / "audio" / "sound_service.dart"
    dart = set()
    if svc.exists():
        body = svc.read_text(encoding="utf-8")
        for m in re.finditer(r'^\s{2}(\w+)\("(\w+)"', body, re.M):
            dart.add(m.group(2))
    out["Dart 枚举"] = dart

    web = REPO / "web-preview" / "index.html"
    if web.exists():
        html = web.read_text(encoding="utf-8")
        seg = re.search(r"const S = \{(.*?)\n  \};", html, re.S)
        out["Web 引擎"] = set(re.findall(r"^\s{4}(\w+)\(\)\s*\{", seg.group(1), re.M)) if seg else set()
    else:
        out["Web 引擎"] = set()

    return out


def check_audio_sync() -> list[str]:
    sources = audio_sources()
    names = [k for k, v in sources.items() if v]
    if len(names) < 2:
        return []
    union = set().union(*sources.values())
    problems: list[str] = []
    for key, vals in sources.items():
        missing = union - vals
        if missing:
            problems.append(f"音效不同步  {key} 缺: {sorted(missing)}")
    return problems


# ---------------------------------------------------------------- main

def main() -> int:
    print("=" * 66)
    print("CppMind Flutter 前端静态健康检查")
    print("=" * 66)

    print(f"\n[A] 相对 import 路径（扫描 {len(list(LIB.rglob('*.dart')))} 个 .dart）")
    pa = check_imports()
    print("    无问题" if not pa else "\n".join("    " + x for x in pa))

    print("\n[B] 枚举成员引用")
    enums = parse_enums(LIB)
    print(f"    解析到 {len(enums)} 个枚举: {', '.join(sorted(enums))}")
    pb = check_enum_refs(enums)
    print("    无悬空引用" if not pb else "\n".join("    " + x for x in pb))

    print("\n[C] 音效三处同源")
    for k, v in audio_sources().items():
        print(f"    {k:14s} {len(v)} 项: {sorted(v)}")
    pc = check_audio_sync()
    print("    四处一致" if not pc else "\n".join("    " + x for x in pc))

    total = pa + pb + pc
    print("\n" + "=" * 66)
    print(f"结论：{'全部通过' if not total else f'发现 {len(total)} 个问题'}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
