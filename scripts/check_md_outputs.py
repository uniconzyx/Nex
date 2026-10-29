# -*- coding: utf-8 -*-
"""校验「正文里声明为程序输出」的代码块，是否真的出自某个真实程序。

为什么需要它：教材正文常把程序跑出来的结果抄进 ```text 块。一旦后来改了程序
（修 bug、换数据、调格式），正文就悄悄过期了 —— 看起来像真输出，其实是旧数字。
`audit_correctness.py` 只能保证「examples 的 expected_output == 重新编译运行的真实
输出」，管不到「正文抄的那段是不是同一份」。本脚本补这一环。

判定规则：
  1. 只检查上文 3 行内出现「输出 / 运行结果 / stdout / 打印 / 终端」字样的
     ```text 块（教材表格、ASCII 流程图、手算过程本来就不是程序输出，不参与）；
  2. 比对池 = 同章 examples/*.json 的 expected_output + 概念程序的 stdout
     （概念程序的输出由各章 .scratch/gen_chNN.py 运行时落在 .scratch/chNN_out.txt）；
  3. 块内每个非空行都必须能在同一个输出里找到，否则判「无出处」。

用法：
    python scripts/check_md_outputs.py                 # 检查 ch13..ch23
    python scripts/check_md_outputs.py --chapters fund-ch20,fund-ch21
"""
import argparse
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUE = re.compile(r'输出|运行结果|stdout|打印|终端')
FENCE = re.compile(r'^```text')


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def pools_for(cid: str, ch: str) -> dict:
    """比对池：examples 的 expected_output + 概念程序 stdout。"""
    pools = {}
    for f in glob.glob(os.path.join(ROOT, 'content', '*', cid, 'examples', '*.json')):
        try:
            d = json.load(io.open(f, encoding='utf-8'))
        except Exception:                                        # noqa: BLE001
            continue
        out = d.get('expected_output') or ''
        if out.strip():
            pools[os.path.basename(f)[:4]] = norm(out)
    gen_out = os.path.join(ROOT, '.scratch', 'ch%s_out.txt' % ch)
    if os.path.exists(gen_out):
        t = io.open(gen_out, encoding='utf-8').read()
        body = t.split('=== examples ===')[0]
        parts = re.split(r'\n----- (c0\d) [^\n]*-----\n', body)
        for i in range(1, len(parts), 2):
            pools[parts[i]] = norm(parts[i + 1])
    return pools


def check(cid: str, ch: str) -> tuple[int, int]:
    pools = pools_for(cid, ch)
    total = bad = 0
    for md in sorted(glob.glob(os.path.join(ROOT, 'content', '*', cid, 'concept', '*.md'))):
        lines = io.open(md, encoding='utf-8').read().splitlines()
        for i, ln in enumerate(lines):
            if not FENCE.match(ln):
                continue
            if not CUE.search('\n'.join(lines[max(0, i - 3):i])):
                continue
            j, buf = i + 1, []
            while j < len(lines) and not lines[j].startswith('```'):
                buf.append(lines[j])
                j += 1
            body = [l for l in buf if l.strip() and not re.fullmatch(r'[-\s=]+', l)]
            if len(body) < 2:
                continue
            total += 1
            hit = next((k for k, v in pools.items() if all(norm(l) in v for l in body)), None)
            if hit:
                print('  [OK   ] %s %s 第%d行 -> %s' % (cid, os.path.basename(md), i + 1, hit))
            else:
                bad += 1
                print('  [STALE] %s %s 第%d行（%d 行无出处）'
                      % (cid, os.path.basename(md), i + 1, len(body)))
                for l in body[:4]:
                    print('          %r' % l[:88])
    return total, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters', default='')
    args = ap.parse_args()
    ids = [c.strip() for c in args.chapters.split(',') if c.strip()] or [
        'fund-ch%d' % n for n in range(13, 24)]
    total = bad = 0
    for cid in ids:
        ch = cid.replace('fund-ch', '').lstrip('0')
        print('· %s' % cid)
        t, b = check(cid, ch)
        total += t
        bad += b
    print('\n共校验 %d 个「声明为输出」的块：%s'
          % (total, '全部有真实出处' if bad == 0 else '%d 个无出处' % bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
