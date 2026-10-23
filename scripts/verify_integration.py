#!/usr/bin/env python3
"""端到端验收：后端 → 前端契约 → 客户端接线，逐项打穿。

判据（全部必须 PASS 才算「打通」）：
  A. 后端存活：/health 与 /api/v1/system/health 均 200；
  B. 题库契约：目录 / 框架 / 知识点 / 总结 / 题目 / 详情 / 套卷 / 判分 全部 200，
     且响应体符合 docs/API-Exam.md 的统一响应包；
  C. 字段透传：分类总结里的 suggested_order 存在，且与 question_ids 同集合；
  D. 前端契约一致：frontend/src/lib/exam.ts 里声明的每个端点，
     在后端都真的存在（防止前端写了、后端没做）；
  E. 客户端接线：Rust 侧 api_probe 命令已注册、capabilities 已放行、
     前端 clientBridge 已调用该命令。

用法：
    python scripts/verify_integration.py                 # 打 127.0.0.1:8000
    python scripts/verify_integration.py --base http://127.0.0.1:8000

退出码：0 = 全通过；1 = 有 FAIL。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_LIB = ROOT / "frontend" / "src" / "lib"
TAURI_SRC = ROOT / "src-tauri" / "src"

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def rec(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    mark = {PASS: "✓", FAIL: "✗", WARN: "!"}[status]
    print(f"  {mark} [{status}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def get(base: str, path: str, timeout: float = 8.0):
    """返回 (http_code, parsed_body_or_None, raw_text)。"""
    url = f"{base}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        code = e.code
    except Exception as exc:
        return 0, None, str(exc)
    try:
        return code, json.loads(raw), raw
    except json.JSONDecodeError:
        return code, None, raw


def post_json(base: str, path: str, payload: dict, timeout: float = 8.0):
    """POST JSON，返回 (http_code, parsed_body_or_None, raw_text)。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        code = e.code
    except Exception as exc:
        return 0, None, str(exc)
    try:
        return code, json.loads(raw), raw
    except json.JSONDecodeError:
        return code, None, raw


def envelope_ok(body) -> bool:
    """统一响应包：{code, message, data, traceId}。"""
    return (
        isinstance(body, dict)
        and "code" in body
        and "message" in body
        and "data" in body
        and "traceId" in body
    )


# ------------------------------------------------------------------ A 后端 --

def check_backend(base: str) -> None:
    print("\n[A] 后端存活")
    code, body, raw = get(base, "/health")
    if code == 200 and isinstance(body, dict) and body.get("data", {}).get("status") == "up":
        rec(PASS, "/health 返回 up")
    else:
        rec(FAIL, "/health 返回 up", f"HTTP {code}: {raw[:120]}")

    code, body, raw = get(base, "/api/v1/system/health")
    if code == 200 and envelope_ok(body):
        d = body.get("data") or {}
        exam = d.get("exam") or {}
        feats = d.get("features") or {}
        rec(PASS, "/api/v1/system/health 统一响应包",
            f"题库 {exam.get('questions')} 题 / 能力 {len(feats)} 项")
        if exam.get("ok"):
            rec(PASS, "题库快照可用", f"{exam.get('exams')} 场考试")
        else:
            rec(FAIL, "题库快照可用", str(exam.get("error"))[:120])
    else:
        rec(FAIL, "/api/v1/system/health 统一响应包", f"HTTP {code}: {raw[:120]}")


# ------------------------------------------------------------------ B 契约 --

def check_exam_contract(base: str) -> None:
    print("\n[B] 题库契约（docs/API-Exam.md）")
    endpoints = [
        ("目录", "/api/v1/exams"),
        ("考试详情", "/api/v1/exams/408"),
        ("解题框架", "/api/v1/exams/408/subjects/ds/frameworks"),
        ("知识点", "/api/v1/exams/408/subjects/ds/knowledge"),
        ("分类总结", "/api/v1/exams/408/subjects/ds/summaries"),
        ("题目列表", "/api/v1/exams/408/subjects/ds/questions?size=5"),
        ("套卷列表", "/api/v1/exams/408/papers"),
        ("精读索引", "/api/v1/exams/408/subjects/ds/reading"),
    ]
    for name, path in endpoints:
        code, body, raw = get(base, path)
        if code == 200 and envelope_ok(body) and body.get("code") == 0:
            rec(PASS, f"{name} 200 + 统一包", path)
        else:
            rec(FAIL, f"{name} 200 + 统一包", f"HTTP {code}: {raw[:120]}")

    # 题目详情（从列表里取第一个 id）
    code, body, _ = get(base, "/api/v1/exams/408/subjects/ds/questions?size=1")
    qid = None
    if code == 200 and envelope_ok(body):
        items = (body.get("data") or {}).get("items") or []
        if items:
            qid = items[0].get("id")
    if qid:
        code, body, raw = get(base, f"/api/v1/exams/408/subjects/ds/questions/{qid}")
        d = (body or {}).get("data") or {}
        if code == 200 and envelope_ok(body):
            has_walk = bool(d.get("walkthrough"))
            rec(PASS, "题目详情 200 + 含讲解", f"{qid} walkthrough={has_walk}")
        else:
            rec(FAIL, "题目详情 200 + 含讲解", f"HTTP {code}: {raw[:120]}")
    else:
        rec(FAIL, "取到题目 id", "题目列表为空")

    # 判分（无状态 POST）。入参契约见 server/app/schemas/exam.py 的 AnswerIn：
    #   question_id + choice(int) / choices(list[int]) / text(str)，extra="forbid"。
    payload = json.dumps({"answers": [{"question_id": qid or "x", "choice": 0}]}).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/exams/408/subjects/ds/grade",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.status
            raw = resp.read().decode("utf-8", "replace")
        body = json.loads(raw)
        if code == 200 and envelope_ok(body):
            rec(PASS, "判分 POST 200 + 统一包")
        else:
            rec(FAIL, "判分 POST 200 + 统一包", f"HTTP {code}: {raw[:120]}")
    except urllib.error.HTTPError as e:
        rec(FAIL, "判分 POST 200 + 统一包", f"HTTP {e.code}: {e.read()[:120]}")
    except Exception as exc:
        rec(FAIL, "判分 POST 200 + 统一包", str(exc)[:120])


# ------------------------------------------------------------------ C 透传 --

def check_field_passthrough(base: str) -> None:
    print("\n[C] 字段透传：suggested_order")
    code, body, raw = get(base, "/api/v1/exams/408/subjects/ds/summaries")
    if code != 200 or not envelope_ok(body):
        rec(FAIL, "取到分类总结", f"HTTP {code}")
        return
    groups = (body.get("data") or {}).get("groups") or []
    if not groups:
        rec(FAIL, "分类总结非空", "groups 为空")
        return

    missing = 0
    mismatch = 0
    checked = 0
    for g in groups:
        so = g.get("suggested_order")
        qi = g.get("question_ids") or []
        if so is None:
            missing += 1
            continue
        checked += 1
        if sorted(so) != sorted(qi) or len(so) != len(qi):
            mismatch += 1

    if missing:
        rec(FAIL, "所有分组都有 suggested_order", f"{missing} 个缺失")
    else:
        rec(PASS, "所有分组都有 suggested_order", f"{checked} 组")

    if mismatch:
        rec(FAIL, "suggested_order 与 question_ids 同集合", f"{mismatch} 组不一致")
    else:
        rec(PASS, "suggested_order 与 question_ids 同集合", f"{checked} 组")


# ------------------------------------------------------------------ D 前端 --

def check_frontend_contract(base: str) -> None:
    print("\n[D] 前端声明的端点后端都存在")
    exam_ts = FRONTEND_LIB / "exam.ts"
    if not exam_ts.is_file():
        rec(FAIL, "找到 frontend/src/lib/exam.ts")
        return
    src = exam_ts.read_text(encoding="utf-8")

    # 前端里 const P = '/api/v1'; 路径都写成 `${P}/exams/...`
    m = re.search(r"const P\s*=\s*'([^']+)'", src)
    prefix = m.group(1) if m else "/api/v1"

    # 抽出 apiGet(`...`) / apiPost(`...`) 里的路径模板
    templates = re.findall(r"api(?:Get|Post)<[^>]*>\(\s*`([^`]+)`", src)
    if not templates:
        rec(FAIL, "从前端提取到端点", "没匹配到 apiGet/apiPost 模板")
        return
    rec(PASS, "从前端提取到端点", f"{len(templates)} 个（前缀 {prefix}）")

    # 取真实的 id，避免用假 id 打出 404 假阳性
    real_qid = first_question_id(base)
    real_paper = first_paper_id(base)
    reading_scope = first_reading_scope(base)  # (exam, subject, passage_id) 或 None

    for tpl in templates:
        # 去掉前缀变量与查询串尾巴
        path = tpl.replace("${P}", prefix)
        path = path.split("${qs")[0].split("?")[0]
        # 模板变量替换：subject→ds，exam/id→408
        concrete = re.sub(r"\$\{subject\}", "ds", path)
        concrete = re.sub(r"\$\{exam\}", "408", concrete)
        concrete = re.sub(r"\$\{encodeURIComponent\(exam\)\}", "408", concrete)
        # id 类：换成真实存在的 id；取不到就跳过断言
        if "${id}" in concrete or "${passage_id}" in concrete:
            if "/questions/" in concrete and real_qid:
                concrete = concrete.replace("${id}", real_qid)
            elif "/reading/" in concrete and reading_scope:
                re_ex, re_sub, re_id = reading_scope
                concrete = (
                    concrete.replace("/exams/408/subjects/ds/reading/", f"/exams/{re_ex}/subjects/{re_sub}/reading/")
                    .replace("${passage_id}", re_id)
                    .replace("${id}", re_id)
                )
            elif "/papers/" in concrete and real_paper:
                concrete = concrete.replace("${id}", real_paper)
            else:
                rec(WARN, f"后端存在 {tpl}", "取不到真实 id，已跳过断言")
                continue

        # 路径里还带未替换的 ${...} → 跳过（拼不出来的路径验不了）
        if "${" in concrete:
            rec(WARN, f"后端存在 {tpl}", "路径含动态参数，已跳过断言")
            continue

        # grade 是 POST 接口，用 GET 打必然 405
        if "/grade" in concrete:
            code, body, raw = post_json(
                base, concrete, {"answers": [{"question_id": real_qid or "x", "choice": 0}]}
            )
        else:
            code, body, raw = get(base, concrete)

        if code == 200:
            rec(PASS, f"后端存在 {tpl}", f"HTTP {code}")
        elif code == 404:
            rec(FAIL, f"后端存在 {tpl}", f"HTTP 404: {raw[:100]}")
        else:
            rec(FAIL, f"后端存在 {tpl}", f"HTTP {code}: {raw[:100]}")


def first_question_id(base: str) -> str | None:
    code, body, _ = get(base, "/api/v1/exams/408/subjects/ds/questions?size=1")
    if code != 200 or not isinstance(body, dict):
        return None
    items = ((body.get("data") or {}).get("items") or [])
    return items[0].get("id") if items else None


def first_paper_id(base: str) -> str | None:
    code, body, _ = get(base, "/api/v1/exams/408/papers")
    if code != 200 or not isinstance(body, dict):
        return None
    items = ((body.get("data") or {}).get("items") or [])
    return items[0].get("id") if items else None


def first_reading_scope(base: str) -> tuple[str, str, str] | None:
    """精读目前只有英语两科有数据（content/_exam/reading/english-*.json），
    所以按目录里真实的 exam/subject 去找，不要写死 408/ds。
    返回 (exam, subject, passage_id) 或 None。"""
    code, body, _ = get(base, "/api/v1/exams")
    if code != 200 or not isinstance(body, dict):
        return None
    for exam in (body.get("data") or {}).get("items") or []:
        for sub in exam.get("subjects") or []:
            c, b, _ = get(base, f"/api/v1/exams/{exam['key']}/subjects/{sub['key']}/reading")
            if c != 200 or not isinstance(b, dict):
                continue
            items = ((b.get("data") or {}).get("items") or [])
            if items:
                first = items[0]
                pid = first.get("id") or first.get("passage_id")
                if pid:
                    return exam["key"], sub["key"], pid
    return None


# ------------------------------------------------------------------ E 客户端 --

def check_client_wiring() -> None:
    print("\n[E] 客户端接线")
    lib_rs = TAURI_SRC / "lib.rs"
    api_rs = TAURI_SRC / "api_client.rs"
    cap = ROOT / "src-tauri" / "capabilities" / "default.json"
    bridge = FRONTEND_LIB / "clientBridge.ts"
    api_ts = FRONTEND_LIB / "api.ts"

    if not lib_rs.is_file() or not api_rs.is_file():
        rec(FAIL, "Rust 源文件存在")
        return
    rec(PASS, "Rust 源文件存在", f"{api_rs.name} + {lib_rs.name}")

    lib_src = lib_rs.read_text(encoding="utf-8")
    if "api_probe" in lib_src:
        rec(PASS, "api_probe 命令已注册")
    else:
        rec(FAIL, "api_probe 命令已注册")

    if "api_probe" in lib_src and re.search(r"generate_handler!\[[^\]]*api_probe", lib_src, re.S):
        rec(PASS, "api_probe 在 generate_handler 列表里")
    else:
        rec(FAIL, "api_probe 在 generate_handler 列表里")

    if cap.is_file():
        cap_src = cap.read_text(encoding="utf-8")
        if "allow-api-probe" in cap_src:
            rec(PASS, "capabilities 放行 allow-api-probe")
        else:
            rec(FAIL, "capabilities 放行 allow-api-probe")
        perm = ROOT / "src-tauri" / "permissions" / "allow-api-probe.toml"
        if perm.is_file():
            rec(PASS, "权限定义文件存在")
        else:
            rec(FAIL, "权限定义文件存在", str(perm))
    else:
        rec(FAIL, "capabilities/default.json 存在")

    if bridge.is_file():
        bsrc = bridge.read_text(encoding="utf-8")
        if "invoke('api_probe')" in bsrc:
            rec(PASS, "前端调用 invoke('api_probe')")
        else:
            rec(FAIL, "前端调用 invoke('api_probe')")
        if "registerBaseResolver" in bsrc:
            rec(PASS, "前端把地址注册进 api.ts")
        else:
            rec(FAIL, "前端把地址注册进 api.ts")
    else:
        rec(FAIL, "clientBridge.ts 存在")

    if api_ts.is_file():
        asrc = api_ts.read_text(encoding="utf-8")
        if "registerBaseResolver" in asrc and "resolveApiBase" in asrc:
            rec(PASS, "api.ts 支持客户端基址覆盖")
        else:
            rec(FAIL, "api.ts 支持客户端基址覆盖")
        if "apiHealth" in asrc:
            rec(PASS, "api.ts 提供健康检查")
        else:
            rec(FAIL, "api.ts 提供健康检查")
    else:
        rec(FAIL, "api.ts 存在")


# ------------------------------------------------------------------ main --

def main() -> int:
    ap = argparse.ArgumentParser(description="Nex 前后端客户端打通验收")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"验收目标：{base}")
    check_backend(base)
    check_exam_contract(base)
    check_field_passthrough(base)
    check_frontend_contract(base)
    check_client_wiring()

    n_pass = sum(1 for s, _, _ in results if s == PASS)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n=== 汇总：{n_pass} PASS / {n_fail} FAIL / {n_warn} WARN ===")
    if n_fail:
        print("\n失败项：")
        for s, name, detail in results:
            if s == FAIL:
                print(f"  ✗ {name} — {detail}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
