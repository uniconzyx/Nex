# -*- coding: utf-8 -*-
"""为缺 ```text 图示块的 concept 文件补一张「结构速览图」。

判据来源：scripts/audit_correctness.py::check_concepts

    if '```text' not in t:
        rep.warn(cid + '/concept/' + name, '没有 ```text 图示块')

这类 warn 集中在 *-practical-recipes / *-snippets / *-codes 等「代码速查」文件：
正文全是语言围栏代码块，缺一张把小节串起来的图。本脚本用**文件自身真实的
三级标题**和**每节首个代码块的语言**生成阅读路径图，节点与注解全部来自原文，
不虚构知识点，也不改动已有标题（来源锚点判据依赖 ## 标题）。

约束：
  - 不新增 # / ## / ### 标题，避免影响 audit_depth 的 h3 计数与
    audit_source_anchor 的「锚点 ↔ 真实 ## 标题」重合率；
  - 块前不加「输出 / 运行结果 / stdout / 打印 / 终端」等字样，避免被
    check_md_outputs.py 当成「正文抄录的程序输出」去比对 expected_output；
  - 保持文件原有换行符（agent/ml/cpp 部分文件是 CRLF）；
  - 幂等：已含 ```text 的文件直接跳过，可反复执行。

用法：
    python scripts/add_concept_diagrams.py --dry-run
    python scripts/add_concept_diagrams.py --apply
    python scripts/add_concept_diagrams.py --apply --chapters cpp-ch01,fs-ch10
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENCE = '```text'
MARKER = ' 结构速览（节点=小节，括号=该节代码块语言）'
H3 = re.compile(r'^###\s+(.+?)\s*$')
H2 = re.compile(r'^##\s+(.+?)\s*$')
CODE = re.compile(r'^```([A-Za-z0-9_+-]+)')
# 三视角是统一收口模板，不作为知识节点；速览图自身也不该被当成节点
# 通杀「视角」：项目三视角是 程序员 / 博士生 / 考研者，别只过滤前两个名字
SKIP = ('三视角', '视角', '结构速览', '小结')


def strip_own_block(raw: str, nl: str) -> str:
    """幂等重写：摘掉本脚本上一次追加的速览块，保留正文里原有的 text 块。"""
    pat = re.compile(re.escape(nl + FENCE + nl) + r'.*?' + re.escape(nl + '```' + nl), re.S)
    return pat.sub(lambda m: '' if MARKER in m.group(0) else m.group(0), raw)


def sections(text: str) -> list[tuple[str, str]]:
    """返回 [(小节标题, 该节首个代码块语言)]，优先 h3，h3 太少时退回 h2。"""
    lines = text.splitlines()

    def collect(pattern: re.Pattern) -> list[tuple[str, str]]:
        out = []
        for i, ln in enumerate(lines):
            m = pattern.match(ln)
            if not m:
                continue
            title = m.group(1).strip()
            if any(k in title for k in SKIP):
                continue
            lang = '-'
            j = i + 1
            while j < len(lines) and not re.match(r'^#{2,3}\s+', lines[j]):
                cm = CODE.match(lines[j])
                if cm:
                    lang = cm.group(1)
                    break
                j += 1
            out.append((title, lang))
        return out

    got = collect(H3)
    if len(got) < 2:
        got = collect(H2)
    return got


def diagram(secs: list[tuple[str, str]], filename: str) -> str:
    show = secs[:8]
    rows = [
        '%s · 结构速览（节点=小节，括号=该节代码块语言）' % filename,
        '',
    ]
    for idx, (title, lang) in enumerate(show, 1):
        rows.append('  [%02d] %s  (%s)' % (idx, title, lang))
        if idx < len(show):
            rows += ['    |', '    v']
    if len(secs) > len(show):
        rows += ['    |', '    v',
                 '  [... 其余 %d 节见正文 ...]' % (len(secs) - len(show))]
    rows += ['    |', '    v', '  [END] 三视角解析收口']
    return '\n'.join(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='写盘；缺省只打印计划')
    ap.add_argument('--dry-run', action='store_true', help='显式 dry-run（默认行为）')
    ap.add_argument('--chapters', default='', help='限定章节，逗号分隔')
    args = ap.parse_args()

    want = {c.strip() for c in args.chapters.split(',') if c.strip()}
    files = sorted(glob.glob(os.path.join(ROOT, 'content', '*', '*', 'concept', '*.md')))
    todo = []
    for fp in files:
        cid = os.path.basename(os.path.dirname(os.path.dirname(fp)))
        if want and cid not in want:
            continue
        raw = io.open(fp, encoding='utf-8', newline='').read()
        nl = '\r\n' if '\r\n' in raw else '\n'
        if MARKER in raw:
            raw = strip_own_block(raw, nl)     # 重生成：先摘掉旧块
        elif FENCE in raw:
            continue                            # 作者自己写的图示块，不动
        secs = sections(raw)
        if not secs:
            print('[SKIP] 无可用小节标题: %s' % os.path.relpath(fp, ROOT))
            continue
        todo.append((fp, raw, nl, secs))

    print('缺 text 图示块的 concept 文件: %d 个（扫描 %d 个）' % (len(todo), len(files)))
    for fp, raw, nl, secs in todo[:3]:
        name = os.path.basename(fp)
        print('\n--- 样例 %s（%d 节）---' % (name, len(secs)))
        print(diagram(secs, name))

    if not args.apply:
        print('\n[dry-run] 未写盘。确认后加 --apply。')
        return 0

    for fp, raw, nl, secs in todo:
        name = os.path.basename(fp)
        body = diagram(secs, name).replace('\n', nl)
        block = nl + FENCE + nl + body + nl + '```' + nl
        base = raw if raw.endswith(('\n', '\r')) else raw + nl
        # 原子替换：避免与其它并发读取（如后台全量审计）撞上半截文件
        tmp_fp = fp + '.nx-tmp'
        io.open(tmp_fp, 'w', encoding='utf-8', newline='').write(base + block)
        os.replace(tmp_fp, fp)
    print('\n[apply] 已补 %d 个文件。' % len(todo))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
