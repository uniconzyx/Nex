# -*- coding: utf-8 -*-
"""内容正确性审计（可复跑）。

做什么：
  1. examples: 重新编译 + 运行，stdout 与 expected_output 逐字符比对；
  2. exercises: 实跑 answer.code；choice 题校验 answer.correct 是 options 的子集；
  3. 三视角标记：每个 concept/*.md 必须含三个规范标题（含 ZWJ）；
  4. 来源真实性：goals.md 里每个 github.com/<owner>/<repo> 必须 HTTP 200；
  5. 星数一致性：同一仓库在所有章节里必须用同一个快照值；
  6. 输出卫生：Traceback / bash: / command not found 直接 FAIL；error:/Error: 只在
     「该示例没有 stdout 实跑证据」时 warn（实跑通过即证明是程序正常打印的教学反例）。

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

from verify_softlang import verify as verify_softlang

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Node 可执行文件：优先托管版本（隔离环境），否则回落到 PATH 里的 node。
_NODE_CANDIDATES = [
    r'C:\Users\zyx\.workbuddy\binaries\node\versions\22.22.2-3\node.exe',
]
NODE_BIN = next((p for p in _NODE_CANDIDATES if os.path.exists(p)), None) or 'node'

TRI_VIEWS = [
    '### \U0001F9D1\u200D\U0001F4BB 程序员视角',
    '### \U0001F393 博士生视角',
    '### \U0001F4DA 考研者视角',
]
# 强信号：几乎只出现在「把崩溃/构建失败输出当成期望值」的造假场景，直接 FAIL。
# Python 崩溃转储必带 Traceback；shell 失败带 bash:/command not found。
BAD_OUTPUT_FAIL = ['Traceback', 'bash:', 'command not found']
# 弱信号：error:/Error: 在合法教学示例里高频出现（argparse 的 "prog: error:"、
# TypeError:/ValueError: 等异常类名、HTTPError 等）。它是子串匹配，几乎必然命中
# 异常类名，单独出现不足以判定造假。对能实跑的示例，下面 stdout 逐字符比对 +
# 退出码检查已经证明「这串由程序正常打印」，无需再 warn；仅对走 verify_softlang
# 分层验证（没有 stdout 实跑证据）的示例保留 warn 提示人工复核。
BAD_OUTPUT_WARN = ['error:', 'Error:']
VIEW_RE = re.compile(r'^\| *(\U0001F9D1\u200D\U0001F4BB|[\U0001F393\U0001F4DA])', re.M)
DEFAULT_CHAPTERS = ['fund-ch%02d' % i for i in range(13, 24)]


def _norm_std(raw, is_cpp: bool) -> str:
    """把 content 里的 code_std 归一成编译器认识的标准名。

    数据里同时存在 'c++17' / 'cpp17' / 'cpp20' 几种写法（还有 python 章的 '3.13'），
    此前 C++ 分支硬编码 '-std=c++17'，导致声明了 cpp20 的 ranges / jthread 示例
    一律「编译失败」——那是审计没有尊重数据，不是示例写错。
    """
    s = (raw or '').strip().lower()
    if is_cpp:
        s = s.replace('cpp', 'c++')
        if not s.startswith('c++'):
            s = 'c++' + s.lstrip('+') if s else 'c++17'
        return s
    return s or 'c11'


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.warns: list[str] = []
        self.checked = 0
        # 已按「通过」处理、只做信息统计的项：不占 warn 名额，否则会淹没真问题
        self.soft_newline = 0
        self.soft_lang: dict[str, int] = {}
        # 非 Python 示例的分层验证计数（见 scripts/verify_softlang.py）
        self.soft_exec: dict[str, int] = {}
        self.soft_struct: dict[str, int] = {}
        self.soft_blocked: dict[str, int] = {}
        # 含 error:/Error: 但已由 stdout 实跑比对 + 退出码证实为正常输出的示例数
        self.hygiene_verified = 0

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
def check_examples(cdir: str, cid: str, rep: Report, tmp_root: str) -> None:
    """逐示例实跑。注意每个示例用**独立子目录**，不能共用一个工作目录。

    共用目录会被前面的示例污染：某个示例在默认包里定义了 `Target` 之后，
    后续示例里的 `@Target(ElementType.FIELD)` 会解析到这个类而不是
    `java.lang.annotation.Target`，javac 报
    「incompatible types: Target cannot be converted to Annotation」——
    完全无关的两个示例互相干扰，属审计自身的假 FAIL。
    """
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

        # 每个示例一个干净目录（见函数 docstring：共用目录会造成跨示例污染）
        tmp = tempfile.mkdtemp(dir=tmp_root)

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
        # 「可疑字样」是用来拦住「把崩溃/构建失败输出当成期望值」。
        # 但 Tooling 等章会刻意演示真实报错（反例教学）：报错文本本身写在 code 里，
        # 由被测程序正常打印出来。这种情况属于合法期望输出，降级为 warn。
        for bad in BAD_OUTPUT_FAIL:
            if bad not in expect:
                continue
            if bad in code:
                rep.warn(cid + '/' + name,
                         'expected_output 含 %r，但该串来自 code 中的样例数据（反例教学）' % bad)
            else:
                rep.fail(cid + '/' + name, 'expected_output 含可疑字样 %r' % bad)
        # error:/Error: 不再在这里无条件 warn：它几乎总是 TypeError: 这类异常类名。
        # 判定后移到实跑结果处 —— 有 stdout 比对证据的算合法（hygiene_verified），
        # 没有实跑证据的（verify_softlang 分层）才 warn 提示人工复核。

        if lang in ('c', 'cpp', 'c++'):
            is_cpp = lang in ('cpp', 'c++')
            # 源文件名影响 __FILE__ / __FILE_NAME__，示例输出若引用它就靠 run_filename 对齐。
            # 编译用「相对文件名 + cwd=tmp」：GCC 的 __FILE__ 取自命令行实参，
            # 传绝对路径会把临时目录写进输出，导致示例永远对不上。
            src_name = obj.get('run_filename') or ('m.cpp' if is_cpp else 'm.c')
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            std = _norm_std(obj.get('code_std'), is_cpp)
            if is_cpp:
                # 尊重 code_std（cpp20 的 ranges / jthread 在 c++17 下编不过）
                cc = ['g++', '-std=' + std, '-O2', '-pthread', '-o', 'm.exe', src_name]
            else:
                cc = ['gcc', '-std=' + std, '-O2', '-o', 'm.exe', src_name]
            r = subprocess.run(cc, capture_output=True, text=True, encoding='utf-8',
                               errors='replace', cwd=tmp)
            if r.returncode != 0:
                rep.fail(cid + '/' + name, '编译失败: ' + (r.stderr or '')[-300:])
                continue
            run = subprocess.run([os.path.join(tmp, 'm.exe')], input=stdin, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace', timeout=30)
        elif lang in ('python', 'py', 'python3'):
            # __file__ / sys.argv[0] 会进输出，示例可用 run_filename 指定脚本名
            src_name = obj.get('run_filename') or 'm.py'
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            run = subprocess.run([sys.executable, src_name], input=stdin, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace',
                                 timeout=60, cwd=tmp)
        elif lang in ('java',):
            # 源文件名必须与 public class 同名，否则 javac 直接拒绝编译。
            # 注意优先级：public 类名 > run_filename > 首个类型名。
            # （run_filename 只是给人看的描述名，如 UserService.java，而代码里
            #  往往写的是 public class Main —— 用它命名会编译失败。）
            mpub = re.search(r'\bpublic\s+(?:final\s+|abstract\s+|sealed\s+|static\s+)*'
                             r'(?:class|interface|enum|record)\s+(\w+)', code)
            many = re.search(r'\b(?:class|interface|enum|record)\s+(\w+)', code)
            if mpub:
                cls = mpub.group(1)
            else:
                cls = (obj.get('run_filename') or '').rsplit('.', 1)[0] or \
                      (many.group(1) if many else 'Main')
                cls = cls or 'Main'
            src_name = cls + '.java'
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            # -J-Duser.language=en：中文 Windows 上 javac 诊断是 GBK，直接按 UTF-8
            # 读会变乱码；强制英文可保证诊断信息可读。
            r = subprocess.run(['javac', '-J-Duser.language=en', '-J-Duser.country=US',
                                '-encoding', 'UTF-8', '-d', '.', src_name],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', cwd=tmp)
            if r.returncode != 0:
                rep.fail(cid + '/' + name, '编译失败: ' + (r.stderr or '')[-300:])
                continue
            # JDK 18+ 重定向时按 native 编码写 stdout，显式指定避免中文乱码
            run = subprocess.run(['java', '-Dstdout.encoding=UTF-8',
                                  '-Dstderr.encoding=UTF-8', '-cp', '.', cls],
                                 input=stdin, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=60, cwd=tmp)
        elif lang in ('javascript', 'js', 'node'):
            src_name = obj.get('run_filename') or 'm.js'
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            run = subprocess.run([NODE_BIN, src_name], input=stdin, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace',
                                 timeout=60, cwd=tmp)
        else:
            # 非 C/C++/Python/Java/JS 示例：分层验证，不冒充 stdout 逐字符比对。
            # 四层判据见 scripts/verify_softlang.py 模块文档。
            level, ok, detail = verify_softlang(lang, code, expect)
            bucket = {'executed': rep.soft_exec, 'structural': rep.soft_struct,
                      'env_blocked': rep.soft_blocked,
                      'unverified': rep.soft_lang}[level]
            bucket[lang] = bucket.get(lang, 0) + 1
            if not ok:
                rep.fail(cid + '/' + name, '[%s] %s' % (level, detail))
            elif any(b in expect for b in BAD_OUTPUT_WARN):
                # 这一层没有 stdout 实跑证据，无法自证「报错串是程序正常打印」，
                # 保留 warn 让人工复核；不能因为判据放宽就一并静默。
                rep.warn(cid + '/' + name,
                         'expected_output 含 error:/Error:，且该示例未经 stdout 实跑比对'
                         '（%s 层），请人工确认不是崩溃输出误当期望值' % level)
            continue

        # 示例可声明 expect_rc：'nonzero' 表示「故意崩溃」的演示（assert / 测试失败），
        # 具体退出码跨平台不一致（Windows abort=3、Linux=134），所以不写死数字。
        want_rc = obj.get('expect_rc')
        if want_rc == 'nonzero':
            rc_ok = run.returncode != 0
            rc_desc = '非零'
        elif want_rc is None:
            rc_ok = run.returncode == 0
            rc_desc = '0'
        else:
            rc_ok = run.returncode == int(want_rc)
            rc_desc = str(want_rc)
        if not rc_ok:
            err = (run.stderr or '')[-400:]
            miss = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\".]+)", err)
            if miss:
                # 缺包是审计环境问题，不是内容错误。报清楚，别让它伪装成「运行失败」
                rep.fail(cid + '/' + name,
                         '缺 Python 依赖 %r —— 审计机先执行 '
                         'pip install -r server/requirements-audit.txt'
                         % miss.group(1))
            else:
                rep.fail(cid + '/' + name,
                         '运行失败(rc=%d，期望 %s): %s'
                         % (run.returncode, rc_desc, err[-300:]))
            continue
        got = (run.stdout or '').replace('\r\n', '\n')
        # expected 侧同口径归一化：历史数据里存在 CRLF 被截断成孤立 '\r' 的情况，
        # 若只替换 '\r\n'，残留的 '\r' 会让逐行 diff 显示成「两行一模一样却不等」
        want = expect.replace('\r\n', '\n').replace('\r', '\n')
        # 能走到这里，说明退出码符合声明、stdout 与 expected_output 一致：
        # expect 里的 error:/Error: 必是程序正常打印出来的，不是崩溃输出误当期望值。
        # 计入 hygiene_verified（透明统计），不再占 warn 名额。
        weak_error = any(b in expect for b in BAD_OUTPUT_WARN)
        if got == want:
            if weak_error:
                rep.hygiene_verified += 1
            continue
        # 允许「末尾换行数不同」不算错，否则报差异首行
        if got.rstrip('\r\n') == want.rstrip('\r\n'):
            rep.soft_newline += 1
            if weak_error:
                rep.hygiene_verified += 1
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
def _detect_code_lang(code: str) -> str:
    """按强特征判断 answer.code 的语言；无强特征时视为 python。

    参考实现可能是 C / C++ / Java，用 `python -c` 跑必然语法报错（假 FAIL）。
    这里先识别语言，再交给对应工具链真编译，而不是简单跳过。
    """
    if 'public class' in code or re.search(r'\bimport\s+java\.', code):
        return 'java'
    if re.search(r'\b(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?'
                 r'(?:class|interface|enum|record)\s+\w+', code) or 'System.out.' in code:
        return 'java'
    if '#include' in code or '#define' in code:
        if ('std::' in code or 'iostream' in code or 'template<' in code
                or 'using namespace std' in code):
            return 'cpp'
        return 'c'
    if 'func main(' in code or 'package main' in code:
        return 'go'
    return 'python'


def _verify_answer_code(code: str, tag: str, rep: Report) -> None:
    """按语言真编译/运行 answer.code。

    - C/C++：有 main 就编译链接后运行；只有函数/片段则只编译（-c），仍能查出语法与类型错。
    - Java：javac 编译；有 main 再运行。
    - Python：`python -c` 直接跑。
    - 其它语言：无法验证，告警（不谎称通过）。
    """
    lang = _detect_code_lang(code)
    tmp = tempfile.mkdtemp(prefix='ans_')
    try:
        if lang in ('c', 'cpp'):
            is_cpp = lang == 'cpp'
            src_name = 'ans.cpp' if is_cpp else 'ans.c'
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            has_main = re.search(r'\bmain\s*\(', code) is not None
            cc = ['g++' if is_cpp else 'gcc', '-std=' + _norm_std(None, is_cpp)]
            cc += ['-o', 'ans.exe', src_name] if has_main else ['-c', '-o', 'ans.o', src_name]
            r = subprocess.run(cc, capture_output=True, text=True, encoding='utf-8',
                               errors='replace', cwd=tmp)
            if r.returncode != 0:
                rep.fail(tag, 'answer.code 编译失败: ' + (r.stderr or '')[-300:])
                return
            if has_main:
                run = subprocess.run([os.path.join(tmp, 'ans.exe')], capture_output=True,
                                     text=True, encoding='utf-8', errors='replace',
                                     timeout=30, cwd=tmp)
                if run.returncode != 0:
                    rep.fail(tag, 'answer.code 运行失败: ' + (run.stderr or '')[-300:])
        elif lang == 'java':
            mcls = re.search(r'\b(?:public\s+)?(?:final\s+|abstract\s+|sealed\s+)?'
                             r'(?:class|interface|enum|record)\s+(\w+)', code)
            cls = mcls.group(1) if mcls else 'Ans'
            src_name = cls + '.java'
            io.open(os.path.join(tmp, src_name), 'w', encoding='utf-8',
                    newline='\n').write(code)
            r = subprocess.run(['javac', '-J-Duser.language=en', '-J-Duser.country=US',
                                '-encoding', 'UTF-8', '-d', '.', src_name],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', cwd=tmp)
            if r.returncode != 0:
                rep.fail(tag, 'answer.code 编译失败: ' + (r.stderr or '')[-300:])
                return
            if 'static void main(' in code:
                run = subprocess.run(['java', '-Dstdout.encoding=UTF-8',
                                      '-Dstderr.encoding=UTF-8', '-cp', '.', cls],
                                     capture_output=True, text=True, encoding='utf-8',
                                     errors='replace', timeout=60, cwd=tmp)
                if run.returncode != 0:
                    rep.fail(tag, 'answer.code 运行失败: ' + (run.stderr or '')[-300:])
        elif lang == 'python':
            r = subprocess.run([sys.executable, '-c', code], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=60)
            if r.returncode != 0:
                rep.fail(tag, 'answer.code 运行失败: ' + (r.stderr or '')[-300:])
        else:
            rep.warn(tag, 'answer.code 语言 %r 暂无可验证工具链' % lang)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
            _verify_answer_code(code, tag, rep)


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
    # star 列允许千分位逗号（教材表格常用 34,813 这种写法），匹配后统一去逗号
    r'\|\s*\d+\s*\|\s*\[[^\]]+\]\((https://github\.com/[^)]+)\)\s*\|\s*([\d,]+)\s*\|')


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

    rows = [(u, s.replace(',', '')) for u, s in STAR_ROW.findall(t)]
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
    ap.add_argument('--warn-out', default='',
                    help='把完整 warn 清单写入该文件（控制台只显示前 20 条）')
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
    if rep.soft_newline:
        print('[info] %d 个示例仅末尾换行不同（已按通过处理）' % rep.soft_newline)
    def fmt_lang(d):
        return ', '.join('%s×%d' % (k, v) for k, v in sorted(d.items()))

    if rep.soft_exec:
        print('[info] 已实跑验证（sqlite3 执行 SQL + 代码/输出关联检查）: %s'
              % fmt_lang(rep.soft_exec))
    if rep.soft_struct:
        print('[info] 已结构校验（声明式/说明型，非 stdout 比对）: %s'
              % fmt_lang(rep.soft_struct))
    if rep.soft_blocked:
        print('[info] 环境限制，仅静态配对（本机策略禁止启动 bash）: %s'
              % fmt_lang(rep.soft_blocked))
    if rep.soft_lang:
        print('[info] 仍未验证的 code_lang: %s' % fmt_lang(rep.soft_lang))
    if rep.hygiene_verified:
        print('[info] 输出卫生：%d 个含 error:/Error: 的示例已由 stdout 逐字符比对 + '
              '退出码证实为程序正常打印（教学反例），不再计入 warn'
              % rep.hygiene_verified)
    # 无条件写 --warn-out：warn 归零时也要把文件清空，否则上一轮的旧清单会残留，
    # 让人误以为告警还在（2026-11-08 实测：判据修好后文件里仍是上一轮残留的旧措辞）。
    print('\n[warn] %d 条' % len(rep.warns))
    for w in rep.warns[:20]:
        print('  - ' + w)
    if len(rep.warns) > 20:
        print('  ... 另 %d 条（加 --warn-out 可看全量）' % (len(rep.warns) - 20))
    if args.warn_out:
        with io.open(args.warn_out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(rep.warns) + ('\n' if rep.warns else ''))
        print('  （完整清单已写入 %s%s）'
              % (args.warn_out, '' if rep.warns else '，本次为空'))
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
