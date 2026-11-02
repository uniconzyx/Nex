# -*- coding: utf-8 -*-
"""校验 manifest 的 resources.github 与 goals.md 表格里的仓库列表是否一致。

背景：路线颗粒度审计读的是 manifest.github_notes，而读者看的是 goals.md 表格。
两侧不同步时会出现「表格写着 cpython，审计按 Python-100-Days 判重复」的假阳性。
"""
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')


def repos_in_goals(text):
    out = []
    seg = text
    if '## 本章 GitHub' in text:
        seg = text[text.find('## 本章 GitHub'):]
        if '## 本章 B 站' in seg:
            seg = seg[:seg.find('## 本章 B 站')]
    for m in re.finditer(r'github\.com/([\w.-]+/[\w.-]+)', seg):
        r = m.group(1).rstrip('.')
        if r not in out:
            out.append(r)
    return out


def main() -> int:
    bad = []
    total = 0
    for mf in sorted(glob.glob(os.path.join(CONTENT, '*', '_manifest.json'))):
        subj = os.path.basename(os.path.dirname(mf))
        m = json.loads(io.open(mf, encoding='utf-8').read())
        units = list(m.get('chapters', []))
        units += list(((m.get('clang_module') or {}).get('units')) or [])
        for u in units:
            cid = u.get('id')
            gp = os.path.join(CONTENT, subj, cid, 'goals.md')
            if not os.path.exists(gp):
                continue
            total += 1
            res = u.get('resources') or {}
            gh = [g if isinstance(g, str) else (g.get('repo') or '') for g in (res.get('github') or [])]
            gh = [g.rstrip('/') for g in gh if g]
            gd = repos_in_goals(io.open(gp, encoding='utf-8').read())
            if set(gh) != set(gd):
                bad.append((subj, cid, gh, gd))
    print('校验章节 %d，不一致 %d 个' % (total, len(bad)))
    for subj, cid, gh, gd in bad:
        print('  %-12s manifest=%s' % (cid, gh))
        print('  %-12s goals   =%s' % ('', gd))
    return 0


if __name__ == '__main__':
    sys.exit(main())
