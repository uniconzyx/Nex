# -*- coding: utf-8 -*-
"""把「学科级复制」的 GitHub 读法升级为「章节级路线」。

判定（scripts/audit_sources.py）：同一学科内多章 `resources.github_notes` 完全相同 →
视为学科级复制。本章级路线要求每条注里出现 `§x.y`（概念文件序号.文件内 ## 序号）、
入口文件/模块名，以及「这份代码证明了什么」。

本模块只负责写：manifest 的 github_notes 与 goals.md 表格的「对应本章 / 读什么」两列，
两者必须同步，否则前端展示与审计口径会打架。

用法：
    from _route_granularity import apply
    apply('java', {'java-ch01': {'Snailclimb/JavaGuide': ('§1.2', '…'), ...}})
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')


def _repo_key(url_or_text):
    m = re.search(r'github\.com/([\w.-]+/[\w.-]+)', url_or_text)
    if m:
        return m.group(1)
    m = re.search(r'([\w.-]+/[\w.-]+)', url_or_text)
    return m.group(1) if m else url_or_text


def apply(subject, data, root=None):
    """data: {chapter_id: {repo: (对应本章, 读什么)}}"""
    root = root or ROOT
    mf_path = os.path.join(root, 'content', subject, '_manifest.json')
    manifest = json.loads(io.open(mf_path, encoding='utf-8').read())
    units = {u['id']: u for u in manifest.get('chapters', [])}

    for cid, mapping in data.items():
        unit = units.get(cid)
        if unit is None:
            print('[skip] manifest 无此章', cid)
            continue
        res = unit.setdefault('resources', {})
        repos = res.get('github') or []
        notes = list(res.get('github_notes') or [])
        if not repos:
            print('[skip] 无 github 列表', cid)
            continue

        # 1) manifest：按 github 数组顺序写 notes
        new_notes = []
        for i, g in enumerate(repos):
            name = _repo_key(g if isinstance(g, str) else json.dumps(g, ensure_ascii=False))
            hit = mapping.get(name)
            if hit is None:
                # 允许用 owner/repo 的主名匹配
                hit = next((v for k, v in mapping.items() if k.split('/')[-1] == name.split('/')[-1]), None)
            if hit is None:
                new_notes.append(notes[i] if i < len(notes) else '')
                continue
            sec, what = hit
            new_notes.append('%s %s' % (sec, what))
        res['github_notes'] = new_notes

        # 2) goals.md 表格
        gp = os.path.join(root, 'content', subject, cid, 'goals.md')
        if not os.path.exists(gp):
            print('[warn] 缺 goals.md', cid)
            continue
        text = io.open(gp, encoding='utf-8').read()
        lines = text.split('\n')
        changed = 0
        for idx, ln in enumerate(lines):
            if not ln.startswith('|'):
                continue
            cells = ln.split('|')
            if len(cells) < 6:
                continue
            name = _repo_key(cells[2])
            hit = mapping.get(name)
            if hit is None:
                hit = next((v for k, v in mapping.items() if k.split('/')[-1] == name.split('/')[-1]), None)
            if hit is None:
                continue
            sec, what = hit
            # 行格式：| # | [repo](url) | ★ | 对应本章 | 读什么 |
            # split('|') 后：[0]='' [1]=序号 [2]=repo [3]=★ [4]=对应本章 [5]=读什么
            cells[4] = ' %s ' % sec
            cells[5] = ' %s ' % what
            lines[idx] = '|'.join(cells)
            changed += 1
        if changed == 0:
            print('[warn] goals.md 表格未命中', cid)
        else:
            io.open(gp, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        print('[ok] %-12s 更新 %d 行' % (cid, changed))

    io.open(mf_path, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('manifest 已写回', mf_path)
    return 0
