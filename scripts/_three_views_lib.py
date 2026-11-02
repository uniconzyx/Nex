# -*- coding: utf-8 -*-
"""把「## 三视角解析」写入 concept 文件（audit_correctness 硬性要求）。

用法：
    from _three_views_lib import apply
    apply({'cpp/cpp-ch01/concept/04-xxx.md': dict(prog='…', phd='…', exam='…')})

插入位置：`## 收尾` 之前；没有该小节则追加到末尾。已含三视角的文件自动跳过。
"""
import io
import os

TPL = '''## 三视角解析
### 🧑‍💻 程序员视角
{prog}

### 🎓 博士生视角
{phd}

### 📚 考研者视角
{exam}
'''

MARK = '### \U0001F9D1\u200D\U0001F4BB 程序员视角'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply(blocks, root=None, verbose=True):
    root = root or ROOT
    done = 0
    for rel, blk in blocks.items():
        fp = os.path.join(root, 'content', rel.replace('/', os.sep))
        if not os.path.exists(fp):
            print('[skip 不存在]', rel)
            continue
        text = io.open(fp, encoding='utf-8').read()
        if MARK in text:
            print('[skip 已有]', rel)
            continue
        add = TPL.format(**blk)
        lines = text.split('\n')
        idx = next((i for i, ln in enumerate(lines) if ln.startswith('## 收尾')), None)
        if idx is None:
            new = text.rstrip('\n') + '\n\n' + add
        else:
            head = '\n'.join(lines[:idx]).rstrip('\n')
            tail = '\n'.join(lines[idx:])
            new = head + '\n\n' + add + '\n' + tail
        io.open(fp, 'w', encoding='utf-8', newline='\n').write(new)
        done += 1
        if verbose:
            print('[ok] %-64s +%d 字' % (rel, len(add)))
    print('共写入 %d 个文件' % done)
    return done
