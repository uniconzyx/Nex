"""回归验证 audit_correctness.py 的输出判据（CI content-health 第 2 步）。

七个用例（直接调 check_examples，不依赖全库、不联网），覆盖两类判据：
  「输出卫生」——弱信号 error:/Error: 是否该 warn
    A. Python 实跑通过、expect 含 ValueError:  -> 不 warn，hygiene_verified +1
    B. bash 走 env_blocked、expect 含 Error:   -> 仍 warn（无 stdout 实跑证据）
    C. Python expect 含 Traceback 且 code 没有 -> FAIL（强信号判据未失效）
    D. Python 正常输出、不含 error            -> 无 warn、无 hygiene 计数
  「输出口径」——末尾换行不参与判定，但绝不许放宽成全放行
    E. 声明侧省略末尾换行（want "ok" / got "ok\\n"）  -> 通过，计入 decl
    F. 运行侧省略末尾换行（want "ok\\n" / got "ok"）  -> 通过，计入 run
    G. 中间行不同（want "WRONG" / got "ok")          -> 仍 FAIL

为什么 G 不可省：归一末尾换行只是显式口径，不是「忽略输出差异」。若有人把
比对改成 rstrip 后一律放行，E/F 仍会通过，只有 G 能当场抓到判据被放坏。

为什么能进 CI：只用标准库；check_examples 的 Python 分支用 sys.executable
（CI 有 setup-python 即可），bash 分支在 posix / nt 下都因未设
NEX_SOFTLANG_ALLOW_BASH 而落 env_blocked，Linux 与本机 Windows 判定一致；
PyYAML 只是 verify_softlang 的惰性可选依赖，缺包不影响本用例。
示例全部落在临时目录（每例一个子目录，见 check_examples 的 docstring），
不读写仓库里的任何内容，可与其它 CI step 并行而不互相污染。

返回码：0 = 8/8 断言全通过；1 = 任一断言失败，CI 据此阻塞合并。
"""
import io
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import audit_correctness as ac  # noqa: E402

CASES = [
    ("01-python-error.json", {
        "code_lang": "python",
        "code": 'print("ValueError: demo")\n',
        "expected_output": "ValueError: demo\n",
    }),
    ("02-bash-error.json", {
        "code_lang": "bash",
        "code": 'echo "Error: demo"\n',
        "expected_output": "Error: demo\n",
    }),
    ("03-python-traceback.json", {
        "code_lang": "python",
        "code": 'print("ok")\n',
        "expected_output": "Traceback (most recent call last):\n",
    }),
    ("04-python-clean.json", {
        "code_lang": "python",
        "code": 'print("ok")\n',
        "expected_output": "ok\n",
    }),
    # 声明侧省略末尾换行：Python 的 print 必带 '\n'，声明里没写。
    ("05-python-decl-no-newline.json", {
        "code_lang": "python",
        "code": 'print("ok")\n',
        "expected_output": "ok",
    }),
    # 运行侧省略末尾换行：sys.stdout.write 不补 '\n'，声明里却写了。
    ("06-python-run-no-newline.json", {
        "code_lang": "python",
        "code": 'import sys; sys.stdout.write("ok")\n',
        "expected_output": "ok\n",
    }),
    # 中间行不同：口径只忽略末尾换行，内容不一致必须 FAIL。
    ("07-python-middle-mismatch.json", {
        "code_lang": "python",
        "code": 'print("ok")\n',
        "expected_output": "WRONG\n",
    }),
]


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        cdir = os.path.join(td, "chapter")
        exdir = os.path.join(cdir, "examples")
        os.makedirs(exdir)
        for name, obj in CASES:
            with io.open(os.path.join(exdir, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(obj, ensure_ascii=False, indent=2))
        tmp_root = os.path.join(td, "runs")
        os.makedirs(tmp_root)
        rep = ac.Report()
        ac.check_examples(cdir, "test-ch", rep, tmp_root)

    print("checked:", rep.checked)
    print("hygiene_verified:", rep.hygiene_verified)
    print("soft_newline:", rep.soft_newline,
          "(decl %d / run %d)" % (rep.soft_newline_decl, rep.soft_newline_run))
    print("warns:", rep.warns)
    print("fails:", [f[:110] for f in rep.fails])

    ok = True
    checks = [
        ("A 实跑通过的反例不计 warn，hygiene=1",
         rep.hygiene_verified == 1 and not any("01-python-error" in w for w in rep.warns)),
        ("B 无实跑证据的示例仍 warn",
         any("02-bash-error" in w and "未经 stdout 实跑比对" in w for w in rep.warns)),
        ("C Traceback 强信号仍 FAIL",
         any("03-python-traceback" in f and "可疑字样" in f for f in rep.fails)),
        ("D 干净示例无 warn/无 hygiene",
         not any("04-python-clean" in w for w in rep.warns) and rep.hygiene_verified == 1),
        ("E 声明侧省略末尾换行按口径通过并计入 decl",
         rep.soft_newline_decl == 1
         and not any("05-python-decl-no-newline" in f for f in rep.fails)),
        ("F 运行侧省略末尾换行按口径通过并计入 run",
         rep.soft_newline_run == 1
         and not any("06-python-run-no-newline" in f for f in rep.fails)),
        ("G 中间行不同仍 FAIL（口径未被放宽）",
         any("07-python-middle-mismatch" in f and "输出不一致" in f for f in rep.fails)),
        ("七个示例都被检查，soft_newline 恰好 2",
         rep.checked == 7 and rep.soft_newline == 2),
    ]
    for label, passed in checks:
        print(("  PASS " if passed else "  FAIL ") + label)
        ok &= passed
    total = sum(1 for _, p in checks if p)
    print("RESULT:", "PASS %d/%d" % (total, len(checks)) if ok else "FAIL %d/%d" % (total, len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
