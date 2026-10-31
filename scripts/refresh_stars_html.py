# -*- coding: utf-8 -*-
"""绕开 GitHub API 限流：直接抓仓库页 HTML 里的星数，补齐 scripts/_link_cache.json。

背景：未认证的 GitHub REST API 每小时只有 60 次配额，全学科 113 个仓库一轮就爆，
爆了之后 stars 为 None，页面上就会出现一堆「—」。仓库页的星数在
`<span id="repo-stars-counter-star" title="70,073">` 里，抓页面同样能验证仓库存在（200/404），
且不受 API 配额限制。

用法：
    python scripts/refresh_stars_html.py            # 只补缺星数的
    python scripts/refresh_stars_html.py --all      # 全部重抓
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CACHE_PATH = ROOT / "scripts" / "_link_cache.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
RE_REPO = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
RE_STAR = re.compile(r'id="repo-stars-counter-star"[^>]*title="([\d,]+)"')
RE_STAR_ALT = re.compile(r'aria-label="([\d,]+) users starred this repository"')


def fetch(url: str) -> tuple[int, str]:
    """用 curl 抓页面。

    Python 的 urllib 在本机访问 github.com 会 read timeout（curl 同一秒就回 200），
    这是本机网络栈/代理层的问题，不是 GitHub 的问题，所以这里直接调 curl 子进程。
    """
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "30", "-A", UA,
             "-H", "Accept: text/html,application/xhtml+xml",
             "-w", "__CODE__%{http_code}", url],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=45)
        out = r.stdout or ""
        m = re.search(r"__CODE__(\d{3})\s*$", out)
        code = int(m.group(1)) if m else -1
        body = out[: m.start()] if m else out
        return code, body
    except Exception:
        return -1, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    repos: set[str] = set()
    for f in CONTENT.glob("*/*/goals.md"):
        for a, b in RE_REPO.findall(f.read_text(encoding="utf-8")):
            repos.add(f"{a}/{b}")

    todo = []
    for r in sorted(repos):
        cur = cache["github"].get(r) or {}
        if args.all or not isinstance(cur.get("stars"), int):
            todo.append(r)
    print(f"文中仓库 {len(repos)} 个，待补星数 {len(todo)} 个")

    fixed = failed = 0
    for i, r in enumerate(todo, 1):
        code, html = fetch(f"https://github.com/{r}")
        if code == 200:
            m = RE_STAR.search(html) or RE_STAR_ALT.search(html)
            stars = int(m.group(1).replace(",", "")) if m else None
            lang = None
            ml = re.search(r'itemprop="programmingLanguage">([^<]+)<', html)
            if ml:
                lang = ml.group(1).strip()
            cur = cache["github"].get(r) or {}
            cache["github"][r] = {**cur, "status": "ok", "stars": stars,
                                  "lang": lang or cur.get("lang"),
                                  "star_source": "repo-page-html"}
            if stars is None:
                failed += 1
            else:
                fixed += 1
        elif code == 404:
            cache["github"][r] = {"status": "missing", "http": 404}
            print(f"  [404] {r}")
            failed += 1
        else:
            failed += 1
            print(f"  [{code}] {r}")
        if i % 15 == 0:
            print(f"  {i}/{len(todo)} …")
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(0.8)

    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    have = sum(1 for r in repos if isinstance((cache["github"].get(r) or {}).get("stars"), int))
    print(f"补齐 {fixed} 个，失败 {failed} 个；现在 {have}/{len(repos)} 个仓库有星数")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
