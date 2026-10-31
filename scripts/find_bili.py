# -*- coding: utf-8 -*-
"""B 站课程检索助手：给关键词，返回真实存在、按播放量排序的候选（BV 号 + 标题 + UP 主）。

为什么需要它：核验发现 cpp 科目原有的 6 条侯捷/黑马链接**全部失效**
（-404 啥都木有 / 62002 稿件不可见），fundamentals、java 各 1 条失效，
agent 科目干脆没有 BV 直链。补链接**不能靠记忆拼 BV 号**，必须走站内检索。

用法：
    python scripts/find_bili.py "侯捷 C++ 面向对象" "黑马 C++"
    python scripts/find_bili.py --top 8 "翁恺 C语言"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "scripts" / "_link_cache.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"


def get(url: str, tries: int = 3) -> dict:
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            if i == tries - 1:
                return {"code": -1, "message": str(e)[:120]}
            time.sleep(1.5 * (i + 1))
    return {"code": -1}


def search(kw: str, top: int) -> list[dict]:
    # order=click 按播放量；duration=0 不限时长
    q = urllib.parse.urlencode({"search_type": "video", "keyword": kw,
                                "page": 1, "order": "click"})
    d = get(f"https://api.bilibili.com/x/web-interface/search/type?{q}")
    if d.get("code") != 0:
        return [{"_err": f"code={d.get('code')} {d.get('message')}"}]
    res = (d.get("data") or {}).get("result") or []
    out = []
    for it in res[:top]:
        title = re.sub(r"<[^>]+>", "", it.get("title") or "")
        out.append({
            "bv": it.get("bvid"), "title": title, "owner": it.get("author"),
            "play": it.get("play"), "danmaku": it.get("video_review"),
            "duration": it.get("duration"), "pubdate": it.get("pubdate"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kws", nargs="+")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"github": {}, "bili": {}}
    known_ok = {b for b, v in cache.get("bili", {}).items() if v.get("status") == "ok"}

    all_out: dict[str, list] = {}
    for kw in args.kws:
        rows = search(kw, args.top)
        all_out[kw] = rows
        print(f"\n### {kw}")
        for r in rows:
            if "_err" in r:
                print("   !", r["_err"])
                continue
            mark = "✓已收录" if r["bv"] in known_ok else " "
            print(f"   {r['bv']} {mark} {r['play']:>9,} 播  {r['title'][:52]}")
            print(f"        UP={r['owner']}  时长={r['duration']}")
        time.sleep(1.2)

    if args.json:
        p = ROOT / "scripts" / "_bili_search.json"
        old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        old.update(all_out)
        p.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n写入 {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
