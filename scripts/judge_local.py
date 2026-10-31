#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""judge0 协议兼容的本地轻量判题服务（仅用于本地联调，不依赖 Docker/网络）。

用本机 g++/javac 编译运行参考解，模拟 judge0 的
  POST /submissions            -> {"token": ...}
  POST /submissions/batch      -> [{"token": ...}, ...]
  GET  /submissions/batch?tokens=...&fields=...  -> {"submissions": [...]}
  GET  /languages             -> [{id, name}, ...]
使 server/app/services/judge0.py 零改动即可端到端判题。

运行：server/.venv/Scripts/python.exe scripts/judge_local.py
端口：2358（对齐 settings.judge0_url 默认 http://localhost:2358）
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

GPP = r"D:\mingw64\bin\g++.exe"
JAVAC = shutil.which("javac") or "javac"
JAVA = shutil.which("java") or "java"
TMP = r"D:\tmp_judge_local"
os.makedirs(TMP, exist_ok=True)

# language_id -> 语言族（对齐 judge0 1.13 风格 id：50=c, 54=cpp, 62=java）
LANG = {50: "c", 54: "cpp", 62: "java"}

STATUS = {
    1: "In Queue", 2: "Processing", 3: "Accepted", 4: "Wrong Answer",
    5: "Time Limit Exceeded", 6: "Compilation Error", 7: "Runtime Error (SIGSEGV)",
    8: "Runtime Error (SIGXFSZ)", 9: "Runtime Error (SIGFPE)",
    10: "Runtime Error (SIGABRT)", 11: "Runtime Error (NZEC)",
    12: "Runtime Error (Other)", 13: "Internal Error", 14: "Exec Format Error",
}

store = {}
store_lock = threading.Lock()


def _popen(cmd, wd, timeout):
    """运行命令；超时则杀整个进程树（含子进程），返回 (returncode|None, out, err, elapsed)。"""
    t0 = time.time()
    try:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env={**os.environ, "TMP": wd, "TEMP": wd, "TMPDIR": wd},
        )
    except Exception:
        return None, "", "", timeout + 1
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), time.time() - t0
    except subprocess.TimeoutExpired:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
        except Exception:
            pass
        try:
            p.kill()
        except Exception:
            pass
        return None, "", "", timeout + 1


def _norm(s):
    return (s or "").replace("\r\n", "\n").rstrip("\n")


def _mk(status_id, stdout, stderr, compile_output, elapsed, exit_code):
    return {
        "status": {"id": status_id, "description": STATUS.get(status_id, "")},
        "stdout": stdout or "",
        "stderr": stderr or "",
        "compile_output": compile_output or None,
        "time": round(elapsed, 4) if isinstance(elapsed, (int, float)) else None,
        "memory": 0,
        "exit_code": exit_code,
    }


def run_one(lang_id, code, stdin, expected, compiler_options, cpu_limit):
    """编译运行单份代码，返回 judge0 风格结果 dict（status.id / stdout / stderr ...）。"""
    if lang_id not in LANG:
        return _mk(13, "", "", f"unsupported language_id={lang_id}", 0.0, None)
    fam = LANG[lang_id]
    wd = tempfile.mkdtemp(prefix="jl_", dir=TMP)

    if fam in ("c", "cpp"):
        srcname = "src.c" if fam == "c" else "src.cpp"
        src = os.path.join(wd, srcname)
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        opts = compiler_options.split() if compiler_options else (
            ["-std=c11", "-O2"] if fam == "c" else ["-std=c++17", "-O2"])
        rc, _, cerr, _ = _popen([GPP, *opts, src, "-o", os.path.join(wd, "a.exe")], wd, 30.0)
        if rc != 0:
            return _mk(6, "", cerr, cerr, 0.0, rc)
        run_cmd = [os.path.join(wd, "a.exe")]
    else:  # java
        m = re.search(r"public\s+class\s+(\w+)", code)
        cls = m.group(1) if m else "Main"
        src = os.path.join(wd, cls + ".java")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        rc, _, cerr, _ = _popen([JAVAC, "-d", wd, src], wd, 30.0)
        if rc != 0:
            return _mk(6, "", cerr, cerr, 0.0, rc)
        run_cmd = [JAVA, "-cp", wd, cls]

    t0 = time.time()
    try:
        p = subprocess.Popen(
            run_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env={**os.environ, "TMP": wd, "TEMP": wd, "TMPDIR": wd},
        )
    except Exception:
        return _mk(7, "", "", "run spawn failed", 0.0, None)
    try:
        out, err = p.communicate(input=(stdin or "").encode("utf-8", "replace"), timeout=cpu_limit)
        rc = p.returncode
        elapsed = time.time() - t0
        out = out.decode("utf-8", "replace")
        err = err.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
        except Exception:
            pass
        try:
            p.kill()
        except Exception:
            pass
        return _mk(5, "", "", "time limit exceeded", cpu_limit, None)
    if rc != 0:
        return _mk(7, out, err, err, elapsed, rc)
    # expected 为空字符串表示自由运行台（不判对错）；非空则严格比对
    if expected is not None and expected != "" and _norm(out) != _norm(expected):
        return _mk(4, out, err, err, elapsed, rc)
    return _mk(3, out, err, err, elapsed, rc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默访问日志
        pass

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except Exception:
            return {}

    def _send(self, code, obj):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/submissions/batch":
            q = parse_qs(u.query)
            toks = [t for t in q.get("tokens", [""])[0].split(",") if t]
            with store_lock:
                subs = [dict(store.get(t, {"status": {"id": 1}}), token=t) for t in toks]
            self._send(200, {"submissions": subs})
        elif u.path == "/languages" or u.path.startswith("/languages"):
            self._send(200, [{"id": k, "name": v} for k, v in LANG.items()])
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        body = self._body()
        if u.path == "/submissions/batch":
            items = body.get("submissions", [body]) if isinstance(body, dict) and "submissions" in body else [body]
        else:
            items = [body]
        results = []
        with store_lock:
            for it in items:
                res = run_one(
                    int(it.get("language_id", 54)),
                    it.get("source_code", ""),
                    it.get("stdin", ""),
                    it.get("expected_output"),
                    it.get("compiler_options", ""),
                    float(it.get("cpu_time_limit", 2.0)),
                )
                tok = uuid.uuid4().hex
                res["token"] = tok
                store[tok] = res
                results.append({"token": tok})
        if u.path == "/submissions/batch":
            self._send(200, results)
        else:
            self._send(200, results[0])


def main():
    port = int(os.environ.get("JUDGE_PORT", "2358"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[judge-local] listening on http://127.0.0.1:{port}  (g++={GPP}, javac={JAVAC})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
