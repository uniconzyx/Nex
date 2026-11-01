#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 project.json 的 requirement_md 规整为带 ### 小节的文档。

背景：audit_correctness.py 对 project#N 的硬性判据是 requirement_md 必须含
`###` 小节。历史上大量 requirement_md 是「一段引言 + 编号列表 + 一句约束」
的纯文本，内容完整但没有小节结构，于是成片假 FAIL。

本脚本只做**结构重排**，不改写、不增删语义内容：
  - 已有 `###` 的跳过（幂等）
  - 围栏块（``` / ~~~）内部不参与切分，避免把代码块拆散
  - 粗体独占行（如 `**约束**`）识别为小节标题
  - 编号列表段自动归入「功能要求」
  - 含 验收/交付/要求自带/不做什么 等关键词的尾段归入「验收与约束」

用法：
    python scripts/structure_project_requirement.py            # 干跑，打印将要改的章
    python scripts/structure_project_requirement.py --write    # 落盘
    python scripts/structure_project_requirement.py --check    # 只报缺 ### 的章，非零退出
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

# 粗体小标题 -> 目标小节名
BOLD_MAP = {
    '背景': '背景', '背景设定': '背景', '题目背景': '背景',
    '必须实现的功能': '功能要求', '功能要求': '功能要求', '任务': '功能要求',
    '必须输出的实测判据': '验收标准', '必须输出的结论': '验收标准',
    '验收标准': '验收标准', '验收要求': '验收标准', '交付物': '验收标准',
    '约束': '约束与边界', '约束与边界': '约束与边界', '额外要求': '附加要求',
    '不做什么': '不做与验收', '不做': '不做与验收',
}

# 段落首行的关键词 -> 归入「验收与约束」
TAIL_KW = ('要求自带', '要求自测', '要求', '验收', '交付', '约束', '不做什么', '不做',
           '禁止', '必须输出', '自测', '加分')

NUM_RE = re.compile(r'^\s*\d+[.、)]\s')
BOLD_RE = re.compile(r'^\*\*(.+?)\*\*$')
FENCE_RE = re.compile(r'^(```|~~~)')


def split_blocks(text: str) -> list[str]:
    """按空行切块，但不切围栏块内部。"""
    out, buf, fence = [], [], None
    for ln in text.split('\n'):
        m = FENCE_RE.match(ln.strip())
        if m:
            if fence is None:
                fence = m.group(1)
            elif ln.strip().startswith(fence):
                fence = None
            buf.append(ln)
            continue
        if fence is None and not ln.strip():
            if buf:
                out.append('\n'.join(buf).strip('\n'))
                buf = []
            continue
        buf.append(ln)
    if buf:
        out.append('\n'.join(buf).strip('\n'))
    return [b for b in out if b.strip()]


def map_bold(title: str) -> str:
    """粗体小标题 -> 目标小节名（先精确后前缀，容忍括号补充说明）。"""
    t = title.strip()
    if t in BOLD_MAP:
        return BOLD_MAP[t]
    if t.startswith('必须实现') or t.startswith('功能要求'):
        return '功能要求'
    if t.startswith('必须输出') or t.startswith('验收') or t.startswith('交付'):
        return '验收标准'
    if t.startswith('约束'):
        return '约束与边界'
    if t.startswith('额外') or t.startswith('附加'):
        return '附加要求'
    if t.startswith('不做'):
        return '不做与验收'
    return t


def to_items(blocks: list[str]) -> list[tuple[str, str]]:
    """把块序列拆成 ('hdr', 标题) / ('blk', 正文) 序列。

    粗体小标题经常紧跟编号列表、中间不留空行（`**任务要求**\\n1. …`），
    所以「块级」识别不够，必须把块首的粗体行单独提出来。
    """
    items: list[tuple[str, str]] = []
    for b in blocks:
        lines = b.split('\n')
        while lines:
            head = lines[0].strip()
            mb = BOLD_RE.match(head)
            if not mb:
                break
            items.append(('hdr', mb.group(1)))
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines = lines[1:]
        if lines:
            items.append(('blk', '\n'.join(lines)))
    return items


def split_inner(block: str) -> list[str]:
    """把「引言 + 编号列表 + 尾句」挤在同一段里的块二次切开。

    历史数据里大量 requirement_md 在段落内不留空行，直接
    「……要求：\\n1. …\\n2. …\\n要求自带单测……」写成一块。
    不切的话整块会被当成背景，小节就切不出来。
    """
    lines = block.split('\n')
    idx_num = next((i for i, l in enumerate(lines) if NUM_RE.match(l)), None)
    start = 0
    parts: list[str] = []
    if idx_num is not None and idx_num > 0:
        parts.append('\n'.join(lines[:idx_num]))
        start = idx_num
    tail = next((i for i in range(start, len(lines))
                 if any(lines[i].strip().startswith(k) for k in TAIL_KW)), None)
    if tail is not None and tail > start:
        parts.append('\n'.join(lines[start:tail]))
        parts.append('\n'.join(lines[tail:]))
    else:
        parts.append('\n'.join(lines[start:]))
    return [p.strip('\n') for p in parts if p.strip()]


def _norm(s: str) -> str:
    return re.sub(r'\s+', '', s)


def classify(blocks: list[str]) -> list[tuple[str, str]]:
    """返回 [(小节名, 内容)]，按出现顺序。"""
    secs: list[tuple[str, str]] = []
    cur = '背景'
    seen_num = False

    def push(name: str, body: str) -> None:
        body = body.strip('\n')
        if not body.strip():
            return
        if secs and secs[-1][0] == name:
            secs[-1] = (name, secs[-1][1] + '\n\n' + body)
        else:
            secs.append((name, body))

    for kind, payload in to_items(blocks):
        if kind == 'hdr':
            cur = map_bold(payload)
            continue
        for piece in split_inner(payload):
            head = piece.strip().split('\n', 1)[0]
            if piece.strip().startswith('```') or piece.strip().startswith('~~~'):
                push(cur, piece)
                continue
            if NUM_RE.match(head):
                if not seen_num:
                    cur, seen_num = '功能要求', True
                push(cur, piece)
                continue
            if any(piece.strip().startswith(k) for k in TAIL_KW):
                cur = '验收与约束'
                push(cur, piece)
                continue
            if seen_num and cur == '功能要求' and not NUM_RE.match(head):
                # 编号列表后的散段（如「要求自带 main() 单测…」）归入验收
                cur = '验收与约束'
                push(cur, piece)
                continue
            push(cur, piece)
    return secs


def rebuild(secs: list[tuple[str, str]]) -> str:
    if not secs:
        return ''
    # 背景为空时不要留空小节
    parts = []
    for name, body in secs:
        parts.append('### %s\n\n%s' % (name, body))
    return '\n\n'.join(parts) + '\n'


def content_digest(md: str, drop_headers: bool) -> str:
    """取「去空白后的字符序列」用于校验零内容丢失。

    重排只允许两种文本变化：
      1. 新增 `### 小节名` 行（drop_headers=True 时剔除）
      2. 把独立成行的 `**粗体小标题**` 替换成 `### 小节名`（原始侧剔除该类行）
    """
    lines = []
    for ln in md.split('\n'):
        if drop_headers and ln.startswith('### '):
            continue
        if not drop_headers and BOLD_RE.match(ln.strip()):
            continue
        lines.append(ln)
    return _norm('\n'.join(lines))


def splice_requirement_md(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """只替换 requirement_md 的值，其余字节（缩进、单行数组、行尾）原样保留。

    整文件 json.dumps 会把原本写成单行的 `"tags": [...]` 展开成多行，
    在 82 个文件上制造大量无关 diff。所以这里按 JSON 字符串边界精确替换。
    """
    dec = json.JSONDecoder()
    out, pos, n = [], 0, 0
    while True:
        k = text.find('"requirement_md"', pos)
        if k < 0:
            break
        j = k + len('"requirement_md"')
        while j < len(text) and text[j] in ' \t\r\n':
            j += 1
        if j >= len(text) or text[j] != ':':
            pos = k + 1
            continue
        j += 1
        while j < len(text) and text[j] in ' \t\r\n':
            j += 1
        if j >= len(text) or text[j] != '"':
            pos = k + 1
            continue
        old, end = dec.raw_decode(text[j:])
        new = mapping.get(old)
        out.append(text[pos:j])
        if new is None:
            out.append(text[j:j + end])
        else:
            out.append(json.dumps(new, ensure_ascii=False))
            n += 1
        pos = j + end
    out.append(text[pos:])
    return ''.join(out), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--content', default='content')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    todo, missing_before, lossy = [], [], []
    for p in sorted(glob.glob(os.path.join(args.content, '*', '*-ch*', 'project.json'))):
        raw = io.open(p, 'rb').read()
        text = raw.decode('utf-8')
        d = json.loads(text)
        cid = os.path.basename(os.path.dirname(p))
        mapping: dict[str, str] = {}
        for i, it in enumerate(d.get('items') or [], 1):
            req = it.get('requirement_md') or ''
            if not req.strip() or '###' in req:
                continue
            missing_before.append('%s#%d' % (cid, i))
            new = rebuild(classify(split_blocks(req)))
            if not new.strip():
                print('[SKIP] %s #%d 无法切分' % (cid, i))
                continue
            # 零内容丢失校验：重排不得改变正文
            if content_digest(new, True) != content_digest(req, False):
                lossy.append('%s#%d' % (cid, i))
                continue
            mapping[req] = new
        if mapping:
            todo.append((p, text, mapping, d))

    print('缺 ### 的 project: %d 条' % len(missing_before))
    if lossy:
        print('内容校验不通过（已跳过，需人工处理）: %d 条' % len(lossy))
        for t in lossy:
            print('  !', t)
    if args.check:
        return 1 if missing_before else 0
    if not args.write:
        print('\n（干跑）将改写 %d 个文件；加 --write 落盘' % len(todo))
        for p, _t, mapping, _d in todo[:1]:
            print('\n' + '=' * 30, p)
            print(list(mapping.values())[0])
        return 0

    for p, text, mapping, d in todo:
        new_text, n = splice_requirement_md(text, mapping)
        # 落盘前双重校验：JSON 仍合法，且目标值确实都换掉了
        chk = json.loads(new_text)
        assert n == len(mapping), '%s: 替换 %d != 预期 %d' % (p, n, len(mapping))
        assert len((chk.get('items') or [])) == len((d.get('items') or []))
        io.open(p, 'wb').write(new_text.encode('utf-8'))
        print('写入 %s（%d 处）' % (p, n))
    print('\n完成：%d 个文件' % len(todo))
    return 0


if __name__ == '__main__':
    sys.exit(main())
