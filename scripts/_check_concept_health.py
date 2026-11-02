# -*- coding: utf-8 -*-
"""扫描所有 concept 文件的三视角完整度与围栏内 H1 异常。

用途：audit_correctness 的 check_concepts 要求每个 concept/*.md 都含三个
规范视角标题；但该审计默认只跑 DEFAULT_CHAPTERS，容易漏。这里做全量体检。
"""
import collections
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISS = ['### \U0001F9D1\u200D\U0001F4BB 程序员视角',
        '### \U0001F393 博士生视角',
        '### \U0001F4DA 考研者视角']


def fence_h1(lines):
    """返回围栏外的 H1 行号（1-based）。"""
    infence = False
    out = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith('```'):
            infence = not infence
            continue
        if infence:
            continue
        if re.match(r'^# \S', ln):
            out.append(i + 1)
    return out


def main() -> int:
    files = sorted(glob.glob(os.path.join(ROOT, 'content', '*', '*', 'concept', '*.md')))
    miss = []
    multi = []
    for fp in files:
        text = io.open(fp, encoding='utf-8').read()
        n = sum(1 for t in MISS if t in text)
        rel = os.path.relpath(fp, os.path.join(ROOT, 'content')).replace(os.sep, '/')
        if n < 3:
            miss.append((rel, 3 - n))
        h1 = fence_h1(text.split('\n'))
        if len(h1) > 1:
            multi.append((rel, h1))

    print('concept 文件总数 %d' % len(files))
    print('缺三视角 %d 个' % len(miss))
    by_sub = collections.Counter(r.split('/')[0] for r, _ in miss)
    print('  按学科:', dict(by_sub))
    for rel, n in miss:
        print('   缺%d %s' % (n, rel))
    print('围栏外多 H1 %d 个' % len(multi))
    for rel, h1 in multi:
        print('   %s 行号=%s' % (rel, h1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
