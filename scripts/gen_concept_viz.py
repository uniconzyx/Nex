# -*- coding: utf-8 -*-
"""把 concept/*.md 的结构 + 本章真题 + 工程坑 + 面试追问抽成「概念图解」数据。

产物：
  1. viz/data.js                      → window.VIZ = {subjects, chapters}
     （独立工作台 viz/index.html 用，可离线双击打开）
  2. frontend/src/data/viz/<学科>.ts  → 每学科一个模块，给应用内的 ConceptViz 组件
     动态 import（按学科 code-split，165 章全量 1.8MB 不会压进首屏）

只用标准库，可重复执行：

    python scripts/gen_concept_viz.py            # 两个产物都写
    python scripts/gen_concept_viz.py --skip-js  # 只写前端模块

设计取舍：
  * 图解节点 = concept 文件里的 `##` 小节（三视角/收尾不算），因为作者本来就是
    按「理论 → 机制 → 实践 → 陷阱」分节的，这比按段落切更像一张机制图；
  * 每节只保留首句（≤110 字）与第一个代码块的前 8 行，控制体积；
  * 真题/坑/面经按章存一份，概念按关键词在工作台里匹配，避免重复膨胀。
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
OUT = os.path.join(ROOT, 'viz', 'data.js')
TS_DIR = os.path.join(ROOT, 'frontend', 'src', 'data', 'viz')

SUBJECTS = [
    ('cpp', 'C / C++', 'C++'), ('clang', 'C 语言', 'C'), ('java', 'Java', 'Java'),
    ('spring', 'Spring 生态', 'Spring'), ('python', 'Python', 'Python'),
    ('fullstack', '全栈开发', '全栈'), ('database', '数据库', '数据库'),
    ('middleware', '中间件', '中间件'), ('ai', 'AI / Agent 开发', 'AI'),
    ('agent', 'Agent 工程', 'Agent'), ('bigdata', '大数据', '大数据'),
    ('data', '数据分析', '数据分析'), ('ml', '机器学习', 'ML'),
    ('fundamentals', '计算机基础', '基础'), ('discrete-math', '离散数学', '离散'),
    ('tooling', '工具链', '工具链'),
]

SKIP_SECTIONS = ('三视角解析', '三视角小结')
TRIM = 118


def read(p):
    try:
        return io.open(p, encoding='utf-8').read()
    except (IOError, OSError):
        return ''


def plain(s, limit=None):
    """去掉行内 markdown 标记，压成一行。"""
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = s.replace('**', '').replace('`', '').replace('*', '')
    s = re.sub(r'^\s*[-*+]\s+', '', s)
    s = re.sub(r'^\s*>\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if limit and len(s) > limit:
        s = s[:limit].rstrip('，。；、 ') + '…'
    return s


FENCE = re.compile(r'^```([\w+-]*)\s*$', re.M)


def split_sections(md, level=2):
    """按 `## `（或 `### `）切节；返回 [(heading, body)]。"""
    mark = '#' * level + ' '
    out = []
    cur_h, buf = None, []
    for ln in md.split('\n'):
        if ln.startswith(mark) and not ln.startswith(mark + '#'):
            if cur_h is not None:
                out.append((cur_h, '\n'.join(buf)))
            cur_h, buf = ln[len(mark):].strip(), []
        elif cur_h is not None:
            buf.append(ln)
    if cur_h is not None:
        out.append((cur_h, '\n'.join(buf)))
    return out


def first_para(body):
    """第一段真正的散文（跳过代码块、列表符号、表格）。"""
    in_code = False
    for ln in body.split('\n'):
        s = ln.strip()
        if s.startswith('```'):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith(('|', '#', '>', '-', '*', '+')):
            continue
        return plain(s, TRIM)
    return ''


def first_code(body):
    m = re.search(r'^```([\w+-]*)\s*$', body, re.M)
    if not m:
        return None
    lang = m.group(1) or 'text'
    rest = body[m.end():]
    end = rest.find('```')
    if end < 0:
        return None
    code = rest[:end].strip('\n')
    lines = code.split('\n')
    if len(lines) > 9:
        code = '\n'.join(lines[:9]) + '\n…'
    if len(code) > 460:
        code = code[:460] + '\n…'
    return {'lang': lang, 'code': code}


KIND_RULES = [
    ('stack', ('内存', '栈', '堆', '布局', '字节', '地址', '对象模型', '存储', '对齐', '结构体')),
    ('timeline', ('时序', '事件循环', '生命周期', '调度', '握手', '请求', '流程', '异步', '并发', '重试', '状态机', '流水线')),
    ('compare', ('对照', '对比', '取舍', 'vs', '区别', '异同', '选型')),
]


def pick_kind(title, sections):
    """图形先按语义选，再按规模收口：
       * 实战手记/片段集是「一串现场」，天生该走链，不是对照；
       * 超过 8 节的概念压成链（对照只有两列，塞不下十节）；
       * 对照类要求标题里真的在比两样东西。
    """
    n = len(sections)
    blob = title + ' ' + ' '.join(h for h, _ in sections[:3])
    if any(k in title for k in ('手记', 'snippets', 'recipes', '实战')):
        return 'flow'
    if n > 8:
        return 'flow'
    for kind, keys in KIND_RULES:
        if any(k in blob for k in keys):
            return kind
    return 'flow'


def load_exams(path):
    d = json.loads(read(path) or '{}')
    items = []
    for it in d.get('items', []):
        ans = it.get('answer') or {}
        corr = ans.get('correct')
        if isinstance(corr, list):
            corr = ''.join(corr)
        items.append({
            'kind': it.get('type', 'choice'),
            'q': plain(it.get('title') or '', 90),
            'stem': plain(it.get('content_md') or '', 200),
            'opts': [{'k': o.get('key'), 't': plain(o.get('text') or '', 60)}
                     for o in (it.get('options') or []) if isinstance(o, dict)],
            'ans': plain(str(corr or ans.get('output') or ans.get('reference_code') or ''), 160),
            'why': plain(it.get('explanation') or '', 190),
        })
    return items[:8]


def load_works(path):
    """pitfalls.md 有两种写法：
       1. **标题** —— 正文（同行）
       1. **标题**\\n   正文（换行缩进，可能多行，带 现象/根因/正确做法）
     """
    md = read(path)
    items = []
    cur = None
    for ln in md.split('\n'):
        m = re.match(r'^\s*\d+\.\s+\*\*(.+?)\*\*\s*(.*)$', ln)
        if m:
            if cur:
                items.append(cur)
            cur = {'h': plain(m.group(1), 46), 'body': [m.group(2)]}
            continue
        if cur is None:
            continue
        if re.match(r'^#{1,3}\s', ln):
            items.append(cur)
            cur = None
            continue
        if ln.strip():
            cur['body'].append(ln)
        elif len(cur['body']) > 1:
            items.append(cur)
            cur = None
    if cur:
        items.append(cur)

    out = []
    for it in items:
        body = ' '.join(x for x in it['body'] if x.strip())
        body = re.sub(r'^[\s—\-–:：]+', '', body)
        body = re.sub(r'[✅⚠️👉]', '', body)
        body = re.sub(r'\s+-\s+', ' ', body)
        d = plain(body, 168)
        if d:
            out.append({'h': it['h'], 'd': d})
    return out[:8]


def load_interviews(path):
    d = json.loads(read(path) or '{}')
    out = []
    for it in d.get('items', []):
        out.append({
            'q': plain(it.get('question') or '', 90),
            'a': plain(it.get('answer_md') or '', 200),
            'fu': [plain(x, 60) for x in (it.get('follow_ups') or [])][:2],
            'tag': '/'.join((it.get('company_tags') or [])[:2]),
        })
    return out[:4]


def build_chapter(subj, ch_dir, meta):
    cid = os.path.basename(ch_dir)
    concepts = []
    cdir = os.path.join(ch_dir, 'concept')
    if os.path.isdir(cdir):
        for f in sorted(os.listdir(cdir)):
            if not f.endswith('.md'):
                continue
            md = read(os.path.join(cdir, f))
            title = ''
            m = re.search(r'^#\s+(.+)$', md, re.M)
            if m:
                title = plain(m.group(1))
            if not title:
                title = f[:-3]
            secs = []
            for h, body in split_sections(md):
                if any(k in h for k in SKIP_SECTIONS):
                    continue
                secs.append({'h': plain(h, 46), 's': first_para(body), 'c': first_code(body)})
            if not secs:
                # 实战手记这类文件正文用 `### 现场一…` 分节，没有 `##` 正文节
                for h, body in split_sections(md, 3):
                    if any(k in h for k in SKIP_SECTIONS):
                        continue
                    secs.append({'h': plain(h, 46), 's': first_para(body), 'c': first_code(body)})
            if not secs:
                continue
            concepts.append({
                'id': cid + '/' + f[:-3],
                'file': f,
                'title': title,
                'kind': pick_kind(title, [(s['h'], '') for s in secs]),
                'secs': secs,
            })
    return {
        'id': cid,
        'subj': subj,
        'title': plain(meta.get('title') or cid),
        'summary': plain(meta.get('summary') or '', 120),
        'concepts': concepts,
        'exams': load_exams(os.path.join(ch_dir, 'exercises.json')),
        'works': load_works(os.path.join(ch_dir, 'pitfalls.md')),
        'asks': load_interviews(os.path.join(ch_dir, 'interview.json')),
    }


TS_HEADER = """/* AUTO-GENERATED by scripts/gen_concept_viz.py —— 勿手改。
   数据源：content/<学科>/<章>/concept/*.md 的 `##` 小节 + exercises/pitfalls/interview。
   真题、工程坑、面经都是只读引用，本文件只是它们的索引，不改一个字。
   改完 content 后重跑：python scripts/gen_concept_viz.py */

import type { VizChapter } from './types';

const CHAPTERS: VizChapter[] = """


def write_ts(chapters):
    """按学科拆成独立模块：应用里按学科 dynamic import，165 章不会压进首屏。"""
    by_subj = {}
    for ch in chapters:
        by_subj.setdefault(ch['subj'], []).append(ch)
    os.makedirs(TS_DIR, exist_ok=True)
    total = 0
    for subj, lst in sorted(by_subj.items()):
        body = json.dumps(lst, ensure_ascii=False, separators=(',', ':'))
        # U+2028/2029 在 JSON 里合法、在旧版 JS 字符串里会断行；统一转义
        body = body.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
        path = os.path.join(TS_DIR, subj + '.ts')
        src = TS_HEADER + body + ';\n\nexport default CHAPTERS;\n'
        io.open(path, 'w', encoding='utf-8', newline='\n').write(src)
        total += os.path.getsize(path)
        print('  %-16s %3d 章  %6.1f KB' % (subj, len(lst), os.path.getsize(path) / 1024))
    print('前端图解模块 %d 个学科 / %.1f KB' % (len(by_subj), total / 1024))


def main():
    skip_js = '--skip-js' in sys.argv
    subjects, chapters = [], []
    for key, label, short in SUBJECTS:
        mf = os.path.join(CONTENT, key, '_manifest.json')
        base = os.path.join(CONTENT, key)
        if not os.path.isdir(base):
            continue
        if os.path.exists(mf) and key != 'clang':
            manifest = json.loads(read(mf))
            units = list(manifest.get('chapters') or [])
        elif key == 'clang':
            units = []   # 目录扫一遍会与下面的 clang_module 重复，只走单元登记
        else:
            # 没有 manifest 的学科（如离散数学）直接扫目录，标题取 goals.md 首行
            units = []
            for d in sorted(os.listdir(base)):
                if d.startswith('_') or not os.path.isdir(os.path.join(base, d)):
                    continue
                head = read(os.path.join(base, d, 'goals.md')).split('\n')[0]
                units.append({'id': d, 'title': plain(head.lstrip('# ')) or d, 'summary': ''})
        subs = []
        for u in units:
            d = os.path.join(base, u['id'])
            if not os.path.isdir(d):
                continue
            ch = build_chapter(key, d, u)
            if ch['concepts']:
                chapters.append(ch)
                subs.append(u['id'])
        # clang 的单元登记在 cpp manifest 的 clang_module 里，目录却在 content/clang 下
        if key == 'clang':
            cpp_m = json.loads(read(os.path.join(CONTENT, 'cpp', '_manifest.json')))
            for u in ((cpp_m.get('clang_module') or {}).get('units') or []):
                d = os.path.join(base, u['id'])
                if not os.path.isdir(d):
                    continue
                ch = build_chapter('clang', d, u)
                if ch['concepts']:
                    chapters.append(ch)
                    subs.append(u['id'])
        if subs:
            subjects.append({'k': key, 'n': label, 's': short, 'n_ch': len(subs)})

    payload = {
        'subjects': subjects,
        'chapters': chapters,
    }
    if not skip_js:
        js = 'window.VIZ = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, 'w', encoding='utf-8', newline='\n').write(js)
    n_c = sum(len(c['concepts']) for c in chapters)
    n_s = sum(len(c['secs']) for ch in chapters for c in ch['concepts'])
    print('学科 %d / 章 %d / 概念 %d / 小节 %d / 真题 %d / 坑 %d / 面经 %d'
          % (len(subjects), len(chapters), n_c, n_s,
             sum(len(c['exams']) for c in chapters),
             sum(len(c['works']) for c in chapters),
             sum(len(c['asks']) for c in chapters)))
    if not skip_js:
        print('写出 %s  %.1f KB' % (OUT, os.path.getsize(OUT) / 1024))
    print('--- 前端模块 ---')
    write_ts(chapters)


if __name__ == '__main__':
    main()
