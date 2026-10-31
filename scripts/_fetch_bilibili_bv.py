# -*- coding: utf-8 -*-
"""为每个新章搜 B 站相关视频并核验真实标题/时长/UP，输出 _bilibili_bv.json。

用法：python scripts/_fetch_bilibili_bv.py
仅产出数据，不改任何内容文件。
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "scripts" / "_bilibili_bv.json"

HEADERS = [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "-H", "Referer: https://search.bilibili.com",
    "-H", "Accept: application/json",
]

SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/all/v2?keyword="
VIEW_URL = "https://api.bilibili.com/x/web-interface/view?bvid="

# 每章搜索关键词（取最相关的一组）
KW = {
    "fs-ch10": "Vue3 响应式原理 依赖收集",
    "fs-ch11": "Spring Boot 实战 全局异常处理",
    "fs-ch12": "微服务 网关 Spring Cloud Gateway",
    "fs-ch13": "前端自动化测试 Playwright 教程",
    "fs-ch14": "Agent 流式响应 全栈 LangChain",
    "fs-ch15": "Go Gin 教程 goroutine channel",
    "ai-ch12": "大模型 SFT 数据工程 微调",
    "ai-ch13": "vLLM 推理引擎 KV Cache 量化部署",
    "ai-ch14": "多模态 VLM CLIP 图文理解",
}

_TAG = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return _TAG.sub("", s or "").strip()


def curl_json(url: str) -> dict:
    cmd = ["curl", "-s"] + HEADERS + [url]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {}


def search(kw: str, n: int = 4):
    u = SEARCH_URL + urllib.parse.quote(kw)
    d = curl_json(u)
    res = []
    for block in d.get("data", {}).get("result", []):
        if block.get("result_type") != "video":
            continue
        for it in block.get("data", []):
            bv = it.get("bvid")
            if not bv:
                continue
            res.append({
                "bvid": bv,
                "title": strip_tags(it.get("title", "")),
                "author": it.get("author", ""),
            })
            if len(res) >= n:
                return res
    return res


def verify(bv: str) -> dict:
    d = curl_json(VIEW_URL + bv)
    if d.get("code") != 0:
        return {}
    v = d.get("data", {})
    dur = v.get("duration", 0)
    mm = int(dur) // 60
    ss = int(dur) % 60
    return {
        "bvid": bv,
        "title": v.get("title", ""),
        "author": v.get("owner", {}).get("name", ""),
        "dur": f"{mm}m{ss}s",
    }


def main() -> int:
    result = {}
    for ch, kw in KW.items():
        print(f"[search] {ch}: {kw}", file=sys.stderr)
        cands = search(kw, 5)
        verified = []
        for c in cands:
            v = verify(c["bvid"])
            if v:
                verified.append(v)
                print(f"    OK {v['bvid']} | {v['title'][:36]} | {v['author']} | {v['dur']}", file=sys.stderr)
            if len(verified) >= 3:
                break
            time.sleep(0.4)
        result[ch] = verified
        time.sleep(0.6)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写出 {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
