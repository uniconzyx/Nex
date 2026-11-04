# -*- coding: utf-8 -*-
"""把 `gen_interactive.py` 抽好的全部章节数据写成前端可用的 TS 模块。

为什么单独一个文件：这段逻辑里有大量「写 TS 源码」的字符串拼接，
夹在 700 行的抽取器里读起来很费劲；而且它是**唯一**直接改
`frontend/src/data/labs/` 的地方，单独放便于审阅产物格式。

产物：
    frontend/src/data/labs/<学科>.ts   每学科一个模块（懒加载单位）
    frontend/src/data/labs/index.ts    常驻索引 + 按学科加载

为什么按学科拆而不是按章拆：
    165 个 chunk 太碎（只是把请求数从 16 抬到 165），而单学科最大 161KB
    / gzip ≈ 30KB；打开任一章节时就地下载一科，比按章拆更快，也不会像
    整包内联那样把首屏撑大。
"""
import json
import os
from typing import Any, Dict, List

FE_FILE_HEAD = """/* 自动生成 · 请勿手改 —— python scripts/gen_interactive.py
   数据源：content/<学科>/<章>/interactive.json（由同一脚本从 exercises /
   pitfalls / concept / examples 抽出）。改内容后重跑生成器即可。 */

import type { LabData } from './types';

const LABS: LabData[] = """

FE_INDEX_HEAD = """/* 自动生成 · 请勿手改 —— python scripts/gen_interactive.py */
/**
 * 应用内交互实验的数据入口。
 * 正文按**学科**懒加载，索引常驻：实验台列表与章节卡都读这一份，不重复打包。
 */
import type { LabData } from './types';

export type * from './types';

export interface LabIndexItem {
  /** 完整键：<subject>/<chapter>，与 interactive.json 里的 chapter 对应 */
  key: string;
  subject: string;
  chapter: string;
  title: string;
  kinds: string[];
  fingerprint: string;
}

export const LAB_INDEX: LabIndexItem[] = ["""

FE_INDEX_TAIL = """];

type Loader = () => Promise<LabData[]>;

const LOADERS: Record<string, Loader> = {
%(loaders)s};

const CACHE = new Map<string, LabData[]>();

/** 按学科加载；同一学科只下载一次，之后走内存 */
export function loadLabSubject(subject: string): Promise<LabData[]> {
  const hit = CACHE.get(subject);
  if (hit) return Promise.resolve(hit);
  const load = LOADERS[subject];
  if (!load) return Promise.resolve([]);
  return load().then((list) => {
    CACHE.set(subject, list);
    return list;
  });
}

/** 已经加载过就直接给（避免首帧闪「加载中」） */
export function peekLabSubject(subject: string): LabData[] | undefined {
  return CACHE.get(subject);
}

/** 实验台用：某学科的章节清单（来自常驻索引，不需要等数据包） */
export function labIndexBySubject(subject: string): LabIndexItem[] {
  return LAB_INDEX.filter((x) => x.subject === subject);
}

/** 全部学科（按索引里出现的顺序去重），实验台的学科胶囊用 */
export const LAB_SUBJECTS: string[] = LAB_INDEX.reduce<string[]>((acc, x) => {
  if (!acc.includes(x.subject)) acc.push(x.subject);
  return acc;
}, []);
"""


def write_frontend(all_labs: Dict[str, Dict[str, Any]], out_dir: str) -> List[str]:
    """按学科写 TS 模块 + 索引。返回写出的文件名（供日志）。"""
    os.makedirs(out_dir, exist_ok=True)
    by_subject: Dict[str, List[Dict[str, Any]]] = {}
    for key in sorted(all_labs):
        by_subject.setdefault(all_labs[key]["subject"], []).append(all_labs[key])

    written: List[str] = []
    keep = set()
    for subj, items in by_subject.items():
        fname = f"{subj}.ts"
        keep.add(fname)
        body = ",\n  ".join(
            json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items
        )
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(FE_FILE_HEAD + "[\n  " + body + ",\n];\n\nexport default LABS;\n")
        written.append(fname)

    # 素材消失的学科要清掉，否则 index.ts 里留着指向不存在文件的 import
    for f in os.listdir(out_dir):
        if f.endswith(".ts") and f not in keep and f not in ("index.ts", "types.ts"):
            os.remove(os.path.join(out_dir, f))

    rows = []
    for key in sorted(all_labs):
        d = all_labs[key]
        rows.append(
            "  { key: %s, subject: %s, chapter: %s, title: %s, kinds: %s, fingerprint: %s },"
            % (
                json.dumps(key, ensure_ascii=False),
                json.dumps(d["subject"], ensure_ascii=False),
                json.dumps(key.split("/", 1)[1], ensure_ascii=False),
                json.dumps(d["title"], ensure_ascii=False),
                json.dumps(sorted({m["kind"] for m in d["modules"]}), ensure_ascii=False),
                json.dumps(d["fingerprint"], ensure_ascii=False),
            )
        )
    loaders = "".join(
        "  %s: () => import('./%s').then((m) => m.default),\n"
        % (json.dumps(subj) if "-" in subj else subj, subj)
        for subj in sorted(by_subject)
    )
    with open(os.path.join(out_dir, "index.ts"), "w", encoding="utf-8", newline="\n") as f:
        f.write(FE_INDEX_HEAD + "\n" + "\n".join(rows) + "\n" + (FE_INDEX_TAIL % {"loaders": loaders}))
    written.append("index.ts")
    return written
