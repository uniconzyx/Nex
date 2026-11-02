# -*- coding: utf-8 -*-
"""以 goals.md 表格为权威，回写 manifest 的 github / github_stars / github_notes。

适用场景：manifest 是历史批量生成的、表格是后补的章节级路线，两侧漂移后
审计（读 manifest）与读者（看表格）看到的不是同一份来源。
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')


def parse_rows(text):
    seg = text
    if '## 本章 GitHub' in text:
        seg = text[text.find('## 本章 GitHub'):]
        if '## 本章 B 站' in seg:
            seg = seg[:seg.find('## 本章 B 站')]
    rows = []
    for ln in seg.split('\n'):
        if not ln.startswith('|'):
            continue
        cells = ln.split('|')
        if len(cells) < 6:
            continue
        m = re.search(r'github\.com/([\w.-]+/[\w.-]+)', cells[2])
        if not m:
            continue
        repo = m.group(1).rstrip('.')
        stars_raw = cells[3].strip().replace(',', '')
        stars = int(stars_raw) if stars_raw.isdigit() else 0
        sec = cells[4].strip()
        what = cells[5].strip()
        rows.append((repo, stars, ('%s %s' % (sec, what)).strip()))
    return rows


def main(argv):
    targets = argv[1:]
    for mf in sorted(__import__('glob').glob(os.path.join(CONTENT, '*', '_manifest.json'))):
        subj = os.path.basename(os.path.dirname(mf))
        m = json.loads(io.open(mf, encoding='utf-8').read())
        units = list(m.get('chapters', [])) + list(((m.get('clang_module') or {}).get('units')) or [])
        touched = 0
        for u in units:
            cid = u.get('id')
            if targets and cid not in targets:
                continue
            gp = os.path.join(CONTENT, subj, cid, 'goals.md')
            if not os.path.exists(gp):
                continue
            rows = parse_rows(io.open(gp, encoding='utf-8').read())
            if not rows:
                print('[warn] 表格无 GitHub 行', cid)
                continue
            res = u.setdefault('resources', {})
            res['github'] = [r[0] for r in rows]
            res['github_stars'] = [r[1] for r in rows]
            res['github_notes'] = [r[2] for r in rows]
            touched += 1
            print('[ok] %-12s %d 个仓库' % (cid, len(rows)))
        if touched:
            io.open(mf, 'w', encoding='utf-8', newline='\n').write(
                json.dumps(m, ensure_ascii=False, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
