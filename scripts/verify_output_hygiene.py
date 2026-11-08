"""回归验证 audit_correctness.py 的「输出卫生」判据。

四类用例（直接调用 check_examples，不依赖全库）：
  A. Python 实跑通过、expect 含 ValueError:  -> 不 warn，hygiene_verified +1
  B. bash 走 env_blocked、expect 含 Error:   -> 仍 warn（无 stdout 实跑证据）
  C. Python expect 含 Traceback 且 code 没有 -> FAIL（强信号判据未失效）
  D. Python 正常输出、不含 error            -> 无 warn、无 hygiene 计数
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
        ("四个示例都被检查", rep.checked == 4),
    ]
    for label, passed in checks:
        print(("  PASS " if passed else "  FAIL ") + label)
        ok &= passed
    print("RESULT:", "PASS %d/%d" % (sum(1 for _, p in checks if p), len(checks)) if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
