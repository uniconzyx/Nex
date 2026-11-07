# -*- coding: utf-8 -*-
"""非 Python 示例的分层验证器（供 audit_correctness.py 调用）。

背景：原 check_examples 的 else 分支把所有 C/C++/Python/Java/JS 之外的
code_lang 直接计入「未经验证」。这些示例其实分三种性质，一刀切既浪费了
可验证的部分，也容易让人误以为「没报错 = 没问题」。

本模块把验证分成四层，**不冒充 stdout 逐字符比对**：

  executed    真在 sqlite3 里执行全部 SQL 语句，无异常；并做「代码 ↔
              expected_output」弱关联检查（数据行 token 归一化后有交集），
              能查出「示例输出与代码完全脱节」。
  structural  说明型 / MySQL 专有语法 / 声明式语言：做语法与结构校验
              （YAML 解析、HTML 标签闭合、CSS 花括号、CMake 括号、
              SQL 分词与引号/括号配对），明确标注「非 stdout 比对」。
  env_blocked 本机安全策略禁止启动 bash（Python 调 bash 会拉起 WSL 启动器，
              命中程序黑名单），只做 heredoc/引号静态配对；仅在 POSIX 且
              显式设置 NEX_SOFTLANG_ALLOW_BASH=1 时才实跑并逐字符比对。
  unverified  确实无法验证，保留原 soft_lang 计数，不谎称通过。

为什么不逐字符比对 SQL：历史 expected_output 格式并不统一 —— 有的漏记
DDL 的 `Query OK, 0 rows affected` 回显、有的用空格而非 `|` 分隔、有的
不带表头、有的把 DECIMAL 写成 8000 而另一个写成 8000.00。强行逐字符
会制造大量假失败；统一改内容又会动到教材原意。因此 L1 只承诺「真的
执行过、无异常、代码与声明输出没有完全脱节」。

用法（一般由审计脚本调用）：
    level, ok, detail = verify(lang, code, expected_output)
"""
from __future__ import annotations

import os
import re
import sqlite3
from html.parser import HTMLParser

try:
    import yaml
except ImportError:                                              # pragma: no cover
    yaml = None

# 讲解型示例：code 里混入中文说明，或 expected_output 明说是静态说明
STATIC_HINT = ('只作语法', '说明型', '未在本地执行', '未安装', '语法结构要点',
               '静态说明', '本机无')
# MySQL 专有、sqlite 不支持的语句特征
PROPRIETARY = ('SHOW ', 'SET ', 'DELIMITER', 'BEGIN', 'START TRANSACTION',
               'COMMIT', 'ROLLBACK', '@@', 'INFORMATION_SCHEMA', 'AUTO_INCREMENT',
               'ENGINE=', 'FOR UPDATE', 'LOCK IN SHARE MODE')
DDL = ('CREATE', 'DROP', 'ALTER', 'TRUNCATE')
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
             'link', 'meta', 'param', 'source', 'track', 'wbr'}
DEC = re.compile(r'[`"\']?(\w+)[`"\']?\s+DECIMAL\s*\(\s*\d+\s*,\s*(\d+)\s*\)', re.I)


def strip_comments(s: str) -> str:
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    return '\n'.join(l for l in s.splitlines() if not l.strip().startswith('--'))


def split_stmts(code: str) -> list[str]:
    """按分号切 SQL，保护字符串字面量里的分号。"""
    code = strip_comments(code)
    out, buf, quote = [], [], None
    for ch in code:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"`":
            quote = ch
            buf.append(ch)
        elif ch == ';':
            out.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = ''.join(buf).strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


def _balanced(s: str, left: str = '(', right: str = ')') -> bool:
    depth = 0
    for ch in s:
        if ch == left:
            depth += 1
        elif ch == right:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _quotes_balanced(stmts: list[str]) -> bool:
    for s in stmts:
        for q in "'\"`":
            if s.count(q) % 2:
                return False
    return True


def _tokens(line: str) -> set[str]:
    """把一行数据拆成可比较的 token：数字归一化，分隔符统一。"""
    out = set()
    for t in re.split(r'[\s|,;=]+', line.strip()):
        if not t:
            continue
        try:
            out.add('%.6g' % float(t))
        except ValueError:
            out.add(t)
    return out


def _row_overlap(got_rows: list[str], want: str) -> bool:
    """声明输出里至少有一行与执行结果的数据行有关联。

    多列行要求 >=2 个相同 token；单列结果集只有 1 个 token，改为精确命中，
    否则 db-ch02 的 IN / EXISTS / UNION 单列示例会被误判成「输出脱节」。
    """
    got = [_tokens(r) for r in got_rows]
    got = [g for g in got if g]
    if not got:
        return True                       # 该示例没有结果集，无可比
    for line in (want or '').splitlines():
        w = _tokens(line)
        if not w:
            continue
        if len(w) == 1:
            if any(w <= g for g in got):        # 单列结果集：单个 token 精确命中
                return True
        elif any(len(w & g) >= 2 for g in got):
            return True
    return False


def _fmt(v, scale):
    if v is None:
        return 'NULL'
    if scale is not None and isinstance(v, (int, float)):
        return ('%%.%df' % scale) % float(v)
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _exec_sql(stmts: list[str], code: str):
    scales = {m.group(1).lower(): int(m.group(2)) for m in DEC.finditer(code)}
    con = sqlite3.connect(':memory:')
    data_rows: list[str] = []
    for s in stmts:
        cur = con.execute(s)
        if cur.description:
            cols = [c[0] for c in cur.description]
            for row in cur.fetchall():
                data_rows.append('|'.join(_fmt(v, scales.get(c.lower()))
                                          for c, v in zip(cols, row)))
    return data_rows


class _TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append('</%s> 与 <%s> 不配对' % (tag, self.stack[-1] if self.stack else '?'))
        else:
            self.stack.pop()


def _check_struct(lang: str, code: str, stmts: list[str] | None = None) -> tuple[bool, str]:
    if lang == 'sql':
        ss = stmts if stmts is not None else split_stmts(code)
        if not ss:
            return False, '没有可解析的 SQL 语句'
        if not _quotes_balanced(ss):
            return False, '引号未配对'
        if any(not _balanced(s) for s in ss):
            return False, '括号未配对'
        return True, '%d 条语句分词/配对通过' % len(ss)
    if lang == 'yaml':
        if yaml is None:
            # verify() 会先拦截并降级为 unverified；这里保留防御性分支，
            # 避免有人绕过 verify() 直接调用时拿到「假通过」。
            return False, 'PyYAML 不可用，无法校验 YAML'
        try:
            obj = yaml.safe_load(code)
        except Exception as e:                                   # noqa: BLE001
            return False, 'YAML 解析失败: %s' % str(e)[:120]
        if not isinstance(obj, dict):
            return False, 'YAML 顶层应为映射'
        return True, 'YAML 可解析，顶层键 %d 个' % len(obj)
    if lang == 'html':
        c = _TagChecker()
        try:
            c.feed(code)
        except Exception as e:                                   # noqa: BLE001
            return False, 'HTML 解析失败: %s' % str(e)[:120]
        if c.errors or c.stack:
            return False, '标签未闭合: %s' % ('; '.join(c.errors) or '剩余 ' + ','.join(c.stack))
        return True, '标签闭合通过'
    if lang == 'css':
        if not _balanced(code, '{', '}'):
            return False, '花括号未配对'
        n = code.count('{')
        if n < 1:
            return False, '没有 CSS 规则块'
        return True, '%d 个规则块括号配对通过' % n
    if lang == 'cmake':
        if not _balanced(code):
            return False, '括号未配对'
        if not re.search(r'^\s*[A-Za-z_]+\s*\(', code, re.M):
            return False, '没有 CMake 命令调用'
        return True, '括号/命令形态通过'
    if lang in ('bash', 'sh'):
        opens = re.findall(r'<<\s*[\'"]?(\w+)[\'"]?', code)
        opens = [m for m in opens if not m.isdigit()]   # 排除 C 位移 1 << 20
        for mark in opens:
            if len(re.findall(r'^\s*%s\s*$' % re.escape(mark), code, re.M)) < 1:
                return False, 'heredoc %s 没有结束标记' % mark
        for q in "'\"":
            if code.count(q) % 2:
                return False, '%s 引号未配对' % q
        return True, 'heredoc/引号静态配对通过'
    return False, '无对应结构校验器'


def verify(lang: str, code: str, expect: str) -> tuple[str, bool, str]:
    """返回 (level, ok, detail)；ok=False 时调用方应记 FAIL。"""
    lang = (lang or '').lower()
    if not code.strip():
        return 'unverified', False, 'code 为空'

    if lang in ('bash', 'sh'):
        # 本机 Windows：Python 调 bash 会命中 WSL 启动器（被安全策略拦截）。
        # 默认完全不尝试启动，只在 POSIX + 显式开关下才实跑。
        if os.name == 'posix' and os.environ.get('NEX_SOFTLANG_ALLOW_BASH') == '1':
            import subprocess
            r = subprocess.run(['bash', '-c', code], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=60)
            got = (r.stdout or '').replace('\r\n', '\n')
            want = (expect or '').replace('\r\n', '\n')
            if r.returncode != 0:
                return 'executed', False, 'bash 运行失败(rc=%d): %s' % (r.returncode, (r.stderr or '')[-160:])
            if got.rstrip('\n') != want.rstrip('\n'):
                return 'executed', False, 'bash 输出与 expected_output 不一致'
            return 'executed', True, 'bash 实跑并逐字符通过'
        ok, detail = _check_struct('bash', code)
        return 'env_blocked', ok, '本机策略禁止启动 bash，' + detail

    if lang == 'sql':
        stmts = split_stmts(code)
        static = any(h in code[:400] for h in STATIC_HINT) or \
            (expect or '').startswith('[静态说明]')
        proprietary = any(any(p in s.upper() for p in PROPRIETARY) for s in stmts)
        if static or proprietary:
            ok, detail = _check_struct('sql', code, stmts)
            return 'structural', ok, ('说明型/MySQL 专有语法，' if static else 'MySQL 专有语法，') + detail
        try:
            rows = _exec_sql(stmts, code)
        except Exception as e:                                   # noqa: BLE001
            ok, detail = _check_struct('sql', code, stmts)
            return 'structural', ok, 'sqlite 不支持(%s)，降级结构校验: %s' % (str(e)[:80], detail)
        if not _row_overlap(rows, expect or ''):
            return 'executed', False, 'SQL 执行成功，但结果集与 expected_output 无关联（示例可能脱节）'
        return 'executed', True, '%d 条语句执行通过，%d 行结果，与声明输出有关联' % (len(stmts), len(rows))

    if lang in ('yaml', 'html', 'css', 'cmake'):
        # 缺依赖是环境问题，不能既报 FAIL（历史上踩过「环境缺包被当成内容错误」
        # 的坑），也不能假装「已结构校验」——明确落到仍未验证层。
        if lang == 'yaml' and yaml is None:
            return 'unverified', True, 'PyYAML 不可用，YAML 未校验（装 PyYAML 后自动升级为结构校验）'
        ok, detail = _check_struct(lang, code)
        return 'structural', ok, detail

    return 'unverified', True, '语言 %r 暂无验证器' % lang
