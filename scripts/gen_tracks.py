#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 content/_tracks/*.json 生成前端可 import 的专轨数据文件。

前端无法直读文件系统 JSON，所以把专轨映射（考研 408 / 就业八股）生成为 TS 常量。
当前生成：
  - frontend/src/data/track408.ts     ← content/_tracks/408.json
  - frontend/src/data/employment.ts   ← content/_tracks/employment.json

幂等；纯生成，不回写 content/_tracks；可重复运行。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ROOT / "content" / "_tracks"


def gen_408() -> None:
    src = TRACKS / "408.json"
    out = ROOT / "frontend" / "src" / "data" / "track408.ts"
    data = json.loads(src.read_text(encoding="utf-8"))
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
    out.write_text("\n".join(lines), encoding="utf-8")
    n_ch = sum(len(m["chapters"]) for m in data["modules"])
    print(f"写入 {out.relative_to(ROOT)}：{data['trackId']} · {len(data['modules'])} 模块 · {n_ch} 章")


def gen_employment() -> None:
    src = TRACKS / "employment.json"
    out = ROOT / "frontend" / "src" / "data" / "employment.ts"
    data = json.loads(src.read_text(encoding="utf-8"))

    lines = [
        "/* 由 scripts/gen_tracks.py 从 content/_tracks/employment.json 生成，请勿手改。 */",
        "/* eslint-disable */",
        "export interface EmpSource {",
        "  id: string;",
        "  name: string;",
        "  type: 'repo' | 'site';",
        "  url: string;",
        "  role: string;",
        "  covers?: string;",
        "  subjects?: string[];",
        "}",
        "export interface EmpZone {",
        "  zone: string;",
        "  name: string;",
        "  desc: string;",
        "  color: string;",
        "  sources: EmpSource[];",
        "}",
        "export interface AgentLayer { layer: string; desc: string; ref: string; }",
        "export interface AgentModule { module: string; sources: string[]; scale: string; }",
        "export interface EmpMockPaper { level: string; rule: string; source: string; }",
        "export interface AgentTrack { name: string; layers: AgentLayer[]; modules: AgentModule[]; mockPapers: EmpMockPaper[]; }",
        "export interface EmploymentDef {",
        "  trackId: string;",
        "  name: string;",
        "  zones: EmpZone[];",
        "  agentTrack: AgentTrack;",
        "}",
        "",
        f"export const EMPLOYMENT: EmploymentDef = {json.dumps(data, ensure_ascii=False, indent=2)};",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    n_src = sum(len(z["sources"]) for z in data["zones"])
    n_mod = len(data["agentTrack"]["modules"])
    print(
        f"写入 {out.relative_to(ROOT)}：{data['trackId']} · {len(data['zones'])} 区 · {n_src} 资源 · Agent {n_mod} 模块"
    )


if __name__ == "__main__":
    gen_408()
    gen_employment()
