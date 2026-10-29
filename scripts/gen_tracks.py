#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 content/_tracks/*.json 生成前端可 import 的专轨数据文件。

前端无法直读文件系统 JSON，所以把专轨映射（考研 408 等）生成为 TS 常量。
当前生成：
  - frontend/src/data/track408.ts  ← content/_tracks/408.json

后续 P5 就业板块可扩展生成 employment.ts（content/_tracks/employment.json）。
幂等；纯生成，不回写 content/_tracks。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "_tracks" / "408.json"
OUT = ROOT / "frontend" / "src" / "data" / "track408.ts"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    lines = [
        "/* 由 scripts/gen_tracks.py 从 content/_tracks/408.json 生成，请勿手改。 */",
        "/* eslint-disable */",
        "export interface TrackModule {",
        "  module: string;",
        "  chapters: string[];",
        "}",
        "export interface TrackDef {",
        "  trackId: string;",
        "  name: string;",
        "  modules: TrackModule[];",
        "}",
        "",
        f"export const TRACK_408: TrackDef = {json.dumps(data, ensure_ascii=False, indent=2)};",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    n_ch = sum(len(m["chapters"]) for m in data["modules"])
    print(f"写入 {OUT.relative_to(ROOT)}：{data['trackId']} · {len(data['modules'])} 模块 · {n_ch} 章")


if __name__ == "__main__":
    main()
