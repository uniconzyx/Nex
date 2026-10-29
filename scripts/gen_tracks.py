#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 content/_tracks/*.json 生成前端可 import 的专轨数据文件。

前端无法直读文件系统 JSON，所以把专轨映射（考研 408 / 就业八股 / 考研复试）生成为 TS 常量。
当前生成：
  - frontend/src/data/track408.ts     ← content/_tracks/408.json
  - frontend/src/data/employment.ts   ← content/_tracks/employment.json
  - frontend/src/data/reexam.ts       ← content/_tracks/reexam.json

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


def gen_reexam() -> None:
    src = TRACKS / "reexam.json"
    out = ROOT / "frontend" / "src" / "data" / "reexam.ts"
    data = json.loads(src.read_text(encoding="utf-8"))

    lines = [
        "/* 由 scripts/gen_tracks.py 从 content/_tracks/reexam.json 生成，请勿手改。 */",
        "/* eslint-disable */",
        "export interface ReexamInterviewQuestion { q: string; tip?: string; }",
        "export interface ReexamInterviewCategory { category: string; desc: string; questions: ReexamInterviewQuestion[]; }",
        "export interface ReexamInterview { name: string; desc: string; categories: ReexamInterviewCategory[]; }",
        "export interface ReexamMachineTest {",
        "  id: string;",
        "  title: string;",
        "  university: string;",
        "  year: number;",
        "  module: string;",
        "  /** 题型（模拟/贪心/二分/DP/图/树/字符串/位运算…），用于按题型筛题 */",
        "  type: string;",
        "  scene: string;",
        "  framework: string;",
        "  algorithm: string;",
        "  code: string;",
        "  /** 可复跑样例输入（audit_reexam_code.py 用它重编译重跑验真） */",
        "  sampleIn?: string;",
        "  /** 样例期望输出（真实运行所得，非人脑推算） */",
        "  sampleOut?: string;",
        "}",
        "export interface ReexamPlaybookPattern {",
        "  name: string;",
        "  when: string;",
        "  template: string;",
        "  trap: string;",
        "  complexity: string;",
        "}",
        "export interface ReexamPlaybookGroup {",
        "  group: string;",
        "  /** 这组题的共性 / 为什么归为一类（一句话，便于先判断该不该用） */",
        "  why?: string;",
        "  /** 该组框架覆盖的机试题题型（与 ReexamMachineTest.type 同名词表） */",
        "  types: string[];",
        "  patterns: ReexamPlaybookPattern[];",
        "}",
        "export interface ReexamPlaybookStep {",
        "  name: string;",
        "  detail: string;",
        "}",
        "export interface ReexamPlaybook {",
        "  title: string;",
        "  intro: string;",
        "  steps: ReexamPlaybookStep[];",
        "  groups: ReexamPlaybookGroup[];",
        "  checklist: string[];",
        "}",
        "export interface ReexamDef {",
        "  trackId: string;",
        "  name: string;",
        "  interview: ReexamInterview;",
        "  machineTests: ReexamMachineTest[];",
        "  algorithmPlaybook: ReexamPlaybook;",
        "}",
        "",
        f"export const REEXAM: ReexamDef = {json.dumps(data, ensure_ascii=False, indent=2)};",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    n_q = sum(len(c["questions"]) for c in data["interview"]["categories"])
    n_t = len(data["machineTests"])
    n_types = len({t.get("type") for t in data["machineTests"] if t.get("type")})
    pb = data.get("algorithmPlaybook") or {"groups": []}
    n_pat = sum(len(g["patterns"]) for g in pb["groups"])
    print(
        f"写入 {out.relative_to(ROOT)}：{data['trackId']} · 面试 {n_q} 题 · "
        f"机试 {n_t} 题（{n_types} 类题型）· 算法框架 {len(pb['groups'])} 组 {n_pat} 个"
    )


if __name__ == "__main__":
    gen_408()
    gen_employment()
    gen_reexam()
