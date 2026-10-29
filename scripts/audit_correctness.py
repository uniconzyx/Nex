# -*- coding: utf-8 -*-
"""内容正确性审计（可复跑）。

做什么：
  1. examples: 重新编译 + 运行，stdout 与 expected_output 逐字符比对；
  2. exercises: 实跑 answer.code；choice 题校验 answer.correct 是 options 的子集；
  3. 三视角标记：每个 concept/*.md 必须含三个规范标题（含 ZWJ）；
  4. 来源真实性：goals.md 里每个 github.com/<owner>/<repo> 必须 HTTP 200；
  5. 星数一致性：同一仓库在所有章节里必须用同一个快照值；
  6. 输出卫生：expected_output 不得含 Traceback / bash: / command not found / error:。

用法：
  python scripts/audit_correctness.py                      # 审计 fund-ch13..23
  python scripts/audit_correctness.py --chapters fund-ch19,fund-ch20
  python scripts/audit_correctness.py --all                # 审计全部学科（较慢）
  python scripts/audit_correctness.py --skip-net           # 跳过联网检查
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRI_VIEWS = [
    '### \U0001F9D1\u200D\U0001F4BB 程序员视角',
    '### \U0001F393 博士生视角',
    '### \U0001F4DA 考研者视角',
]
BAD_OUTPUT = ['Traceback', 'bash:', 'command not found', 'error:', 'Error:']
VIEW_RE = re.compile(r'^\| *(\U0001F9D1\u200D\U0001F4BB|[\U0001F393\U0001F4DA])', re.M)
DEFAULT_CHAPTERS = ['fund-ch%02d' % i for i in range(13, 24)]


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.warns: list[str] = []
        self.checked = 0

    def fail(self, where: str, msg: str) -> None:
        self.fails.append('%s: %s' % (where, msg))

    def warn(self, where: str, msg: str) -> None:
        self.warns.append('%s: %s' % (where, msg))


def find_chapter_dir(cid: str) -> str | None:
    hits = glob.glob(os.path.join(ROOT, 'content', '*', cid))
    for h in hits:
        if os.path.isdir(h):
            return h
    return None


# ------------------------------------------------------------------ examples
def check_examples(cdir: str, cid: str, rep: Report, tmp: str) -> None:
    files = sorted(glob.glob(os.path.join(cdir, 'examples', '*.json')))
    if not files:
        rep.fail(cid, 'examples 目录为空')
        return
    for fp in files:
        name = os.path.basename(fp)
        try:
            obj = json.load(io.open(fp, encoding='utf-8'))
        except Exception as e:                                   # noqa: BLE001
            rep.fail(cid + '/' + name, 'JSON 非法: %s' % e)
            continue
        rep.checked += 1

        code = obj.get('code') or ''
        expect = obj.get('expected_output')
        lang = (obj.get('code_lang') or 'c').lower()
        stdin = obj.get('stdin') or ''

        if not code.strip():
            rep.fail(cid + '/' + name, 'code 为空')
            continue
        if expect is None:
            rep.fail(cid + '/' + name, '缺 expected_output')
            continue
        for bad in BAD_OUTPUT:
            if bad in expect:
                rep.fail(cid + '/' + name, 'expected_output 含可疑字样 %r' % bad)

        if lang in ('c', 'cpp', 'c++'):
            src = os.path.join(tmp, 'm.c')
            exe = os.path.join(tmp, 'm.exe')
            io.open(src, 'w', encoding='utf-8', newline='\n').write(code)
            std = obj.get('code_std') or 'c11'
            cc = ['gcc', '-std=' + std, '-O2', '-o', exe, src]
            if lang in ('cpp', 'c++'):
                cc = ['g++', '-std=c++17', '-O2', '-o', exe, src]
            r = subprocess.run(cc, capture_output=True, text=True, encoding='utf-8',
                               errors='replace')
            if r.returncode != 0:
                rep.fail(cid + '/' + name, '编译失败: ' + (r.stderr or '')[-300:])
                continue
            run = subprocess.run([exe], input=stdin, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=30)
        elif lang in ('python', 'py', 'python3'):
            src = os.path.join(tmp, 'm.py')
            io.open(src, 'w', encoding='utf-8', newline='\n').write(code)
            run = subprocess.run([sys.executable, src], input=stdin, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace', timeout=60)
        else:
            rep.warn(cid + '/' + name, 'code_lang=%r 未支持，跳过实跑' % lang)
            continue

        if run.returncode != 0:
            rep.fail(cid + '/' + name,
                     '运行失败(rc=%d): %s' % (run.returncode, (run.stderr or '')[-300:]))
            continue
        got = (run.stdout or '').replace('\r\n', '\n')
        want = expect.replace('\r\n', '\n')
        if got == want:
            continue
        # 允许「末尾换行数不同」不算错，否则报差异首行
        if got.rstrip('\n') == want.rstrip('\n'):
            rep.warn(cid + '/' + name, '仅末尾换行不同')
            continue
        gl, wl = got.split('\n'), want.split('\n')
        for i in range(max(len(gl), len(wl))):
            g = gl[i] if i < len(gl) else '<缺行>'
            w = wl[i] if i < len(wl) else '<缺行>'
            if g != w:
                rep.fail(cid + '/' + name,
                         '输出不一致 第%d行\n    实际: %r\n    声明: %r' % (i + 1, g, w))
                break


# ----------------------------------------------------------------- exercises
def check_exercises(cdir: str, cid: str, rep: Report) -> None:
    fp = os.path.join(cdir, 'exercises.json')
    if not os.path.exists(fp):
        rep.fail(cid, '缺 exercises.json')
        return
    try:
        data = json.load(io.open(fp, encoding='utf-8'))
    except Exception as e:                                       # noqa: BLE001
        rep.fail(cid + '/exercises.json', 'JSON 非法: %s' % e)
        return
    items = data.get('items') or []
    if not items:
        rep.fail(cid, 'exercises 为空')
        return

    seen_titles = set()
    for idx, it in enumerate(items, 1):
        tag = '%s/ex#%d' % (cid, idx)
        rep.checked += 1
        for k in ('type', 'category', 'platform', 'difficulty', 'title',
                  'content_md', 'answer', 'explanation'):
            if not it.get(k):
                rep.fail(tag, '缺字段 %s' % k)
        title = it.get('title') or ''
        if title in seen_titles:
            rep.fail(tag, '标题重复: %s' % title)
        seen_titles.add(title)

        ans = it.get('answer') or {}
        if it.get('type') == 'choice':
            raw_opts = it.get('options') or []
            # 仓库里存在两种写法：[{key,text}] 与 ["A. xxx", ...]，都要能审
            keys = []
            for o in raw_opts:
                if isinstance(o, dict):
                    keys.append(o.get('key'))
                elif isinstance(o, str):
                    m = re.match(r'\s*([A-Za-z])[.、)．:：]', o)
                    keys.append(m.group(1).upper() if m else None)
                else:
                    keys.append(None)
            if any(k is None for k in keys):
                rep.warn(tag, 'options 格式非标准（既非 {key,text} 也无法解析出选项字母）')
            keys = [k for k in keys if k]
            correct = ans.get('correct') or []
            if not raw_opts:
                rep.fail(tag, 'choice 题缺 options')
            if not correct:
                rep.fail(tag, 'choice 题缺 answer.correct')
            for c in correct:
                if keys and c not in keys:
                    rep.fail(tag, 'answer.correct=%r 不在 options %r 中' % (c, keys))
        code = ans.get('code')
        if code:
            r = subprocess.run([sys.executable, '-c', code], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=60)
            if r.returncode != 0:
                rep.fail(tag, 'answer.code 运行失败: ' + (r.stderr or '')[-300:])


# --------------------------------------------------------------- interview/project
def check_interview_project(cdir: str, cid: str, rep: Report) -> None:
    for name, min_items in (('interview.json', 3), ('project.json', 1)):
        fp = os.path.join(cdir, name)
        if not os.path.exists(fp):
            rep.fail(cid, '缺 %s' % name)
            continue
        try:
            data = json.load(io.open(fp, encoding='utf-8'))
        except Exception as e:                                   # noqa: BLE001
            rep.fail(cid + '/' + name, 'JSON 非法: %s' % e)
            continue
        items = data.get('items') or []
        rep.checked += 1
        if len(items) < min_items:
            rep.fail(cid + '/' + name, 'items=%d < %d' % (len(items), min_items))
        if name == 'interview.json':
            for i, it in enumerate(items, 1):
                if not it.get('answer_md'):
                    rep.fail('%s/interview#%d' % (cid, i), '缺 answer_md')
                if not it.get('follow_ups'):
                    rep.warn('%s/interview#%d' % (cid, i), '缺 follow_ups')
        else:
            for i, it in enumerate(items, 1):
                if '###' not in (it.get('requirement_md') or ''):
                    rep.fail('%s/project#%d' % (cid, i), 'requirement_md 缺 ### 小节')
                if not it.get('tasks'):
                    rep.fail('%s/project#%d' % (cid, i), '缺 tasks')


# -------------------------------------------------------------------- concept
def check_concepts(cdir: str, cid: str, rep: Report) -> None:
    files = sorted(glob.glob(os.path.join(cdir, 'concept', '*.md')))
    if len(files) < 3:
        rep.fail(cid, 'concept 文件 %d < 3' % len(files))
    for fp in files:
        name = os.path.basename(fp)
        t = io.open(fp, encoding='utf-8').read()
        rep.checked += 1
        for v in TRI_VIEWS:
            if v not in t:
                rep.fail(cid + '/concept/' + name, '缺三视角标记 %r' % v)
        if '```text' not in t:
            rep.warn(cid + '/concept/' + name, '没有 ```text 图示块')
        if len(t) < 1500:
            rep.warn(cid + '/concept/' + name, '篇幅偏短 %d 字符' % len(t))


# --------------------------------------------------------------------- 来源
REPO_RE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)')
STAR_ROW = re.compile(
    r'\|\s*\d+\s*\|\s*\[[^\]]+\]\((https://github\.com/[^)]+)\)\s*\|\s*(\d+)\s*\|')


def http_code(url: str, retries: int = 1) -> str:
    """取 HTTP 状态码。000 表示未拿到响应（超时/网络抖动），需与 404 区分。

    注意：本机访问 github.com 经常要 10s+ 甚至超时，所以超时不宜设太长，
    否则一次全量审计会被网络拖成几分钟。拿不到响应按 warn 处理。
    """
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(
                ['curl', '-s', '-o', os.devnull, '-w', '%{http_code}', '-m', '12',
                 '-L', url],
                capture_output=True, text=True, timeout=20)
            code = (r.stdout or '').strip()
            if code and code != '000':
                return code
        except Exception:                                        # noqa: BLE001
            pass
    return '000'


def check_sources(cdir: str, cid: str, rep: Report, star_map: dict, cache: dict,
                  net: bool) -> None:
    fp = os.path.join(cdir, 'goals.md')
    if not os.path.exists(fp):
        rep.fail(cid, '缺 goals.md')
        return
    t = io.open(fp, encoding='utf-8').read()

    rows = STAR_ROW.findall(t)
    if len(rows) < 3:
        rep.fail(cid, 'goals GitHub 表行数 %d < 3' % len(rows))
    for url, star in rows:
        repo = url.replace('https://github.com/', '').rstrip('/')
        if repo in star_map and star_map[repo] != int(star):
            rep.fail(cid, '星数不一致 %s: 表里 %s / 快照 %s' % (repo, star, star_map[repo]))
        star_map.setdefault(repo, int(star))

    if net:
        for repo in sorted(set(REPO_RE.findall(t))):
            repo = repo.rstrip('/.')
            if repo in cache:
                code = cache[repo]
            else:
                code = http_code('https://github.com/' + repo)
                cache[repo] = code
            if code == '000':
                # 网络没通（本机代理/超时）不等于仓库不存在，只提醒，不判失败
                rep.warn(cid, '仓库可达性未能校验（网络超时）%s' % repo)
            elif code != '200':
                rep.fail(cid, '仓库不可达 %s (HTTP %s)' % (repo, code))

    bvs = set(re.findall(r'BV[0-9A-Za-z]{10}', t))
    if len(bvs) < 2:
        rep.fail(cid, 'B 站 BV 号 %d < 2' % len(bvs))


# ----------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters', default='')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--skip-net', action='store_true')
    args = ap.parse_args()

    if args.all:
        chapters = sorted(os.path.basename(p) for p in
                          glob.glob(os.path.join(ROOT, 'content', '*', '*-ch*'))
                          if os.path.isdir(p) and os.path.exists(os.path.join(p, 'goals.md')))
    elif args.chapters:
        chapters = [c.strip() for c in args.chapters.split(',') if c.strip()]
    else:
        chapters = DEFAULT_CHAPTERS

    rep = Report()
    star_map: dict[str, int] = {}
    cache: dict[str, str] = {}
    tmp = tempfile.mkdtemp(prefix='audit-')
    try:
        for cid in chapters:
            cdir = find_chapter_dir(cid)
            if cdir is None:
                rep.fail(cid, '章节目录不存在')
                continue
            print('· %s' % cid, flush=True)
            check_sources(cdir, cid, rep, star_map, cache, not args.skip_net)
            check_concepts(cdir, cid, rep)
            check_examples(cdir, cid, rep, tmp)
            check_exercises(cdir, cid, rep)
            check_interview_project(cdir, cid, rep)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n' + '=' * 66)
    print('审计章节 %d · 检查项 %d' % (len(chapters), rep.checked))
    if rep.warns:
        print('\n[warn] %d 条' % len(rep.warns))
        for w in rep.warns[:20]:
            print('  - ' + w)
        if len(rep.warns) > 20:
            print('  ... 另 %d 条' % (len(rep.warns) - 20))
    if rep.fails:
        print('\n[FAIL] %d 条' % len(rep.fails))
        for f in rep.fails:
            print('  - ' + f)
        print('\nAUDIT_FAIL')
        return 1
    print('\nAUDIT_OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
