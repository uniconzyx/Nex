# -*- coding: utf-8 -*-
"""抽取全学科现有链接 + 批量核验真伪，产出 scripts/_link_cache.json。

为什么先抽取再核验：本项目已有 141 章资源段，里面写了不少仓库与 B 站视频。
**不能凭空造新链接**，正确做法是先把已有的全捞出来，逐条打 API 验证，
留下真实可访问的，再按章重排。核验结果缓存下来，供 attach_all_sources.py 使用。

核验口径：
    GitHub  -> GET https://api.github.com/repos/<owner>/<repo>
                code 200 记 stars / license / pushed_at / language；
                404 记 missing（该链接是坏的，必须替换或删除）。
    B 站     -> GET https://api.bilibili.com/x/web-interface/view?bvid=<BV>
                code 0 记 title / owner / videos / pubdate；其它记 missing。

用法：
    python scripts/collect_links.py            # 抽取 + 核验（带缓存，可重复跑）
    python scripts/collect_links.py --report   # 只看统计
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CACHE_PATH = ROOT / "scripts" / "_link_cache.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"

RE_GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
RE_BV = re.compile(r"bilibili\.com/video/(BV[0-9A-Za-z]{10})")


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"github": {}, "bili": {}, "fetched_at": ""}


def save_cache(c: dict) -> None:
    CACHE_PATH.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")


def collect() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """返回 {subject: repos} 与 {subject: bvs}，来源是 goals.md + _manifest.json。"""
    repos: dict[str, set[str]] = defaultdict(set)
    bvs: dict[str, set[str]] = defaultdict(set)
    for subj in sorted(CONTENT.iterdir()):
        if not subj.is_dir() or subj.name.startswith("_"):
            continue
        mf = subj / "_manifest.json"
        if mf.exists():
            blob = mf.read_text(encoding="utf-8")
            for a, b in RE_GH.findall(blob):
                if b.removesuffix(".git") not in {"github.com"}:
                    repos[subj.name].add(f"{a}/{b.removesuffix('.git')}")
            for bv in RE_BV.findall(blob):
                bvs[subj.name].add(bv)
        for goals in subj.glob("*/goals.md"):
            t = goals.read_text(encoding="utf-8")
            for a, b in RE_GH.findall(t):
                repos[subj.name].add(f"{a}/{b.removesuffix('.git')}")
            for bv in RE_BV.findall(t):
                bvs[subj.name].add(bv)
    # 清掉明显不是仓库的匹配（如 github.com/features/xxx）
    for s in repos:
        repos[s] = {r for r in repos[s] if not r.split("/")[0] in
                    {"features", "topics", "about", "pricing", "login", "marketplace", "sponsors"}}
    return repos, bvs


def http_json(url: str, timeout: int = 20) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "ignore"))
        except Exception:
            return e.code, {}
    except Exception as e:  # 网络抖动
        return -1, {"error": str(e)[:120]}


def http_head(url: str, timeout: int = 20) -> int:
    """不消耗 GitHub API 配额的存在性探测：直接 HEAD 仓库页。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def verify_github(repo: str, cache: dict, retry: bool = False) -> dict:
    """先打 API 取 star（配额用完就退回 HEAD 判存在性，star 留空不伪造）。"""
    hit = cache["github"].get(repo)
    if hit and not retry and hit.get("status") in ("ok", "missing", "exists_nostar"):
        return hit
    code, data = http_json(f"https://api.github.com/repos/{repo}")
    if code == 200:
        rec = {"status": "ok", "stars": data.get("stargazers_count"),
               "license": ((data.get("license") or {}).get("spdx_id")),
               "pushed_at": (data.get("pushed_at") or "")[:10],
               "lang": data.get("language"), "desc": (data.get("description") or "")[:160],
               "archived": bool(data.get("archived"))}
    elif code == 404:
        rec = {"status": "missing", "http": 404}
    elif code in (403, 429):
        # 配额用尽：退回 HTML 探测，star 记 None（不用假数字填充）
        st = http_head(f"https://github.com/{repo}")
        if st == 200:
            rec = {"status": "exists_nostar", "stars": hit.get("stars") if hit else None,
                   "note": "GitHub API 限流，仅验证存在性"}
        elif st == 404:
            rec = {"status": "missing", "http": 404}
        else:
            rec = {"status": "error", "http": st}
    else:
        rec = {"status": "error", "http": code, "msg": (data.get("message") or "")[:80]}
    cache["github"][repo] = rec
    return rec


def verify_bili(bv: str, cache: dict, retry: bool = False) -> dict:
    hit = cache["bili"].get(bv)
    if hit and not retry and hit.get("status") in ("ok", "missing"):
        return hit
    code, data = http_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}")
    if code == 200 and data.get("code") == 0:
        v = data.get("data") or {}
        rec = {"status": "ok", "title": (v.get("title") or "")[:90],
               "owner": ((v.get("owner") or {}).get("name") or "")[:40],
               "videos": v.get("videos"), "pubdate": v.get("pubdate"),
               "view": v.get("stat", {}).get("view") if isinstance(v.get("stat"), dict) else None}
    elif code == 200:
        rec = {"status": "missing", "code": data.get("code"), "msg": data.get("message")}
    else:
        rec = {"status": "error", "http": code}
    cache["bili"][bv] = rec
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--retry", action="store_true", help="忽略缓存重新核验")
    args = ap.parse_args()

    repos, bvs = collect()
    cache = load_cache()

    all_repos = sorted({r for s in repos.values() for r in s})
    all_bvs = sorted({b for s in bvs.values() for b in s})

    if not args.report:
        print(f"待核验：GitHub {len(all_repos)} 个仓库 / B 站 {len(all_bvs)} 个视频")
        for i, r in enumerate(all_repos, 1):
            rec = verify_github(r, cache, args.retry)
            if i % 20 == 0 or rec["status"] != "ok":
                print(f"  [{i}/{len(all_repos)}] {r:52s} {rec['status']:8s} "
                      f"{rec.get('stars', '')}")
            if rec["status"] == "ok" and cache["github"][r].get("stars") is None:
                pass
            time.sleep(0.35 if rec["status"] == "ok" else 1.2)
        for i, b in enumerate(all_bvs, 1):
            rec = verify_bili(b, cache, args.retry)
            if i % 20 == 0 or rec["status"] != "ok":
                print(f"  [{i}/{len(all_bvs)}] {b} {rec['status']:8s} {rec.get('title', '')[:40]}")
            time.sleep(0.25 if rec["status"] == "ok" else 1.2)
        cache["fetched_at"] = time.strftime("%Y-%m-%d")
        save_cache(cache)

    # ---- 统计
    print("\n学科          章数  仓库数(ok)  视频数(ok)")
    tot_r = tot_b = 0
    okr = okb = 0
    for s in sorted(repos):
        rs = repos[s]
        bs = bvs[s]
        n_ok_r = sum(1 for r in rs if cache["github"].get(r, {}).get("status") in ("ok", "exists_nostar"))
        n_ok_b = sum(1 for b in bs if cache["bili"].get(b, {}).get("status") == "ok")
        n_ch = len([d for d in (CONTENT / s).iterdir() if d.is_dir()])
        tot_r += len(rs); tot_b += len(bs); okr += n_ok_r; okb += n_ok_b
        print(f"  {s:12s} {n_ch:3d}   {n_ok_r:3d}/{len(rs):<3d}    {n_ok_b:3d}/{len(bs):<3d}")
    print(f"\n合计：仓库 {okr}/{tot_r} 可用；视频 {okb}/{tot_b} 可用")

    bad_r = [(s, r) for s in repos for r in repos[s]
             if cache["github"].get(r, {}).get("status") not in ("ok", "exists_nostar")]
    bad_b = [(s, b) for s in bvs for b in bvs[s]
             if cache["bili"].get(b, {}).get("status") != "ok"]
    if bad_r:
        print("\n失效仓库：")
        for s, r in bad_r:
            print(f"  {s:12s} {r:50s} {cache['github'].get(r, {})}")
    if bad_b:
        print("\n失效视频：")
        for s, b in bad_b:
            print(f"  {s:12s} {b} {cache['bili'].get(b, {})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
