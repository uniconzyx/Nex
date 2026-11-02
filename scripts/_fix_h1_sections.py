# -*- coding: utf-8 -*-
"""治理 concept 文件里「用 H1 当分节标题」的问题。

现象：bigdata 系列把「# 一、xxx」「# 二、xxx」当节标题，一个文件出现多个 H1，
Markdown 渲染出多条顶级标题、目录层级错乱，也让 `# 一、` 行在解析器里失去从属关系。

规则：
  1. 只处理围栏外、且形如 `# 一、…` 的行（避免误伤代码注释与正常标题）。
  2. 首个这种行 → 去掉「一、」前缀，作为文档 H1；若它不在文件开头，搬到第一行。
  3. 其余这种行 → 降为 `## 二、…`（保留序号，便于读者对位）。
"""
import glob
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEQ = re.compile(r'^#\s+([一二三四五六七八九十]+、)\s*(.+)$')


def main() -> int:
    changed = []
    for fp in sorted(glob.glob(os.path.join(ROOT, 'content', '*', '*', 'concept', '*.md'))):
        lines = io.open(fp, encoding='utf-8').read().split('\n')
        infence = False
        hits = []          # (index, seq, title)
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith('```'):
                infence = not infence
                continue
            if infence:
                continue
            m = SEQ.match(ln)
            if m:
                hits.append((i, m.group(1), m.group(2)))
        if len(hits) < 2:
            continue

        first_i, _, first_title = hits[0]
        # 逐行改写：首个 → H1 去序号；其余 → H2 保留序号
        for k, (i, seq, title) in enumerate(hits):
            if k == 0:
                lines[i] = '# ' + title
            else:
                lines[i] = '## ' + seq + title

        # 首个 H1 若不在文件开头，搬到第一行
        if first_i > 0:
            body = lines.pop(first_i)
            lines.insert(0, body)
            # 若原位置留下连续空行，压缩为一个
            while len(lines) > 1 and lines[1].strip() == '' and lines[2:3] and lines[2].strip() == '':
                del lines[1]

        io.open(fp, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        changed.append((os.path.relpath(fp, os.path.join(ROOT, 'content')).replace(os.sep, '/'),
                        len(hits), first_i + 1))

    print('修复文件 %d 个' % len(changed))
    for rel, n, ln in changed:
        print('  %-62s H1×%d 首个原行=%d' % (rel, n, ln))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
