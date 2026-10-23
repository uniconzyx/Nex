#!/usr/bin/env python3
"""
pull_via_mirror.py —— 绕过 Docker daemon 的网络，直接从 registry 镜像站下载镜像。

为什么需要它：
    本机系统代理 `ProxyServer=https=http://127.0.0.1:31181` 是个死端口，
    而 `com.docker.backend.exe` 在启动时把这个值快照进了 VM，
    之后改注册表 / daemon.json 都不会重读 —— 于是 docker pull 永远连 31181。
    虽然 `docker info` 里 registry-mirrors 已生效（URL 确实被改写成了 docker.1ms.run），
    但真正的 TCP 连接仍然先交给那个死代理。

做法：
    用 Python 自己走加速器完成 registry v2 协议（token → manifest → blobs），
    拼出 `docker load` 能吃的 tar（legacy 格式：manifest.json + layer tar + config）。

实测得到的坑（写代码时容易忽略）：
    1. blob 请求**必须带 User-Agent**，否则 1ms.run 直接回 403；
       而 manifest 请求不带 UA 也能过 —— 只有下载层会炸，极易误判成鉴权失败。
    2. 1ms.run 的 blob 会 307 跳到 CloudFront 签名地址
       （cloudfront-docker-cf.mrs.1ms.run），而这个 CDN 在本机**读不动**
       （握手 12s 超时 / 读 30s 只推 2MB）。所以它 manifest 很快、拉镜像必挂。
       实测吞吐：dockerproxy.net 约 0.45 MB/s，m.daocloud.io 约 0.2 MB/s，
       1ms.run 的 CDN ≈ 0。默认用 dockerproxy.net。
    3. 换源时不能只换域名：鉴权地址（realm）是服务端 401 头给的，必须现取。

用法：
    python scripts/pull_via_mirror.py postgres:16-alpine redis:7-alpine
    docker load -i ../.scratch/images/library_postgres_16-alpine.tar

环境变量：
    MIRROR    加速器地址，默认 https://dockerproxy.net
    PROXY     下载用代理；默认读本机 http_proxy。设成空串可强制直连
    JOBS      并发下载层数，默认 4

限制：
    - 只处理 linux/amd64 单架构（本机就是 amd64）
    - 只支持 Docker Hub 上的镜像名（repo 不带域名）
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tarfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

MIRROR = os.environ.get("MIRROR", "https://dockerproxy.net").rstrip("/")
OUT_DIR = Path(__file__).resolve().parent.parent.parent / ".scratch" / "images"
LAYER_CACHE = OUT_DIR / "_layers"
PLATFORM = ("linux", "amd64")
# 没有 UA 就 403 —— 见模块 docstring 第 1 条
UA = "docker/29.6.1 (windows) pull-via-mirror"
JOBS = int(os.environ.get("JOBS", "4"))

_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def _client() -> httpx.Client:
    # 默认 trust_env=True 会读 http_proxy；PROXY="" 时显式禁用
    trust = os.environ.get("PROXY", os.environ.get("http_proxy", "")) != ""
    return httpx.Client(
        timeout=httpx.Timeout(30.0, read=300.0),
        follow_redirects=True,
        trust_env=trust,
        headers={"User-Agent": UA},
        http2=False,
    )


def _auth(c: httpx.Client, repo: str) -> str | None:
    """返回 Bearer token；镜像站免鉴权时返回 None。

    不同加速器行为差别很大：
      - dockerproxy.net：/v2/ 直接 200，manifest 匿名可拉，**完全不需要 token**
      - docker.1ms.run：401 + Www-Authenticate 指向 /openapi/v1/auth/token
    所以不能写死鉴权流程，必须先探。
    """
    r = c.get(f"{MIRROR}/v2/")
    if r.status_code == 200:
        return None
    auth = r.headers.get("www-authenticate", "")
    realm = re.search(r'realm="([^"]+)"', auth)
    if not realm:
        return None
    svc = re.search(r'service="([^"]+)"', auth)
    params = {"scope": f"repository:{repo}:pull"}
    if svc:
        params["service"] = svc.group(1)
    tr = c.get(realm.group(1), params=params)
    tr.raise_for_status()
    data = tr.json()
    tok = data.get("token") or data.get("access_token")
    if not tok:
        raise RuntimeError(f"token 获取失败: {data}")
    return tok


def _hdr(tok: str | None, extra: dict[str, str] | None = None) -> dict[str, str]:
    h = dict(extra or {})
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _manifest(c: httpx.Client, repo: str, tag: str, tok: str | None) -> dict:
    hdr = _hdr(tok, {"Accept": _ACCEPT})
    r = c.get(f"{MIRROR}/v2/{repo}/manifests/{tag}", headers=hdr)
    r.raise_for_status()
    doc = r.json()

    if "manifests" in doc:  # 多架构 index → 挑 linux/amd64
        for m in doc["manifests"]:
            p = m.get("platform") or {}
            if (p.get("os"), p.get("architecture")) == PLATFORM:
                r2 = c.get(f"{MIRROR}/v2/{repo}/manifests/{m['digest']}", headers=hdr)
                r2.raise_for_status()
                return r2.json()
        raise RuntimeError(f"{repo}:{tag} 找不到 {PLATFORM[0]}/{PLATFORM[1]} 架构")
    return doc


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch_blob(c: httpx.Client, repo: str, digest: str, tok: str | None) -> Path:
    """下载到缓存目录，已有且校验通过则直接复用。"""
    LAYER_CACHE.mkdir(parents=True, exist_ok=True)
    short = digest.split(":", 1)[1]
    dest = LAYER_CACHE / short
    if dest.exists() and "sha256:" + _sha256(dest) == digest:
        log(f"      cache hit {short[:12]}")
        return dest

    tmp = dest.with_suffix(".part")
    h = hashlib.sha256()
    # note: Windows 上必须等文件句柄完全关闭才能 rename（否则 WinError 32），
    # 所以把 open() 独立成 with 块，不要和 stream 嵌套。
    with c.stream("GET", f"{MIRROR}/v2/{repo}/blobs/{digest}", headers=_hdr(tok)) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        with open(tmp, "wb") as f:
            n = 0
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                h.update(chunk)
                n += len(chunk)
                if n % (8 << 20) < (1 << 20):
                    pct = f" {n * 100 // total}%" if total else ""
                    log(f"      {short[:12]} {n / 1048576:.0f} MB{pct}")
    actual = "sha256:" + h.hexdigest()
    if actual != digest:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{digest} 校验失败，实际 {actual}")
    dest.unlink(missing_ok=True)
    os.replace(tmp, dest)
    return dest


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


def build_image_tar(spec: str) -> Path:
    name, _, tag = spec.partition(":")
    tag = tag or "latest"
    repo = name if "/" in name else f"library/{name}"

    with _client() as c:
        log(f"[{spec}] 探测鉴权 …")
        tok = _auth(c, repo)
        log(f"[{spec}] 取 manifest …（{'匿名' if tok is None else 'Bearer'}）")
        man = _manifest(c, repo, tag, tok)

        cfg_digest = man["config"]["digest"]
        layer_digests = [l["digest"] for l in man["layers"]]
        log(f"[{spec}] config + {len(layer_digests)} 个 layer，并发 {JOBS} 路下载 …")

        with ThreadPoolExecutor(max_workers=JOBS) as pool:
            futs = [pool.submit(_fetch_blob, c, repo, d, tok) for d in layer_digests]
            cfg_fut = pool.submit(_fetch_blob, c, repo, cfg_digest, tok)
            layer_paths = []
            for i, f in enumerate(futs):
                try:
                    p = f.result()
                except Exception as exc:  # noqa: BLE001
                    log(f"[{spec}]   layer {i + 1}/{len(layer_digests)} ✗ {exc}")
                    raise
                layer_paths.append(p)
                log(f"[{spec}]   layer {i + 1}/{len(layer_digests)} ✓ {p.stat().st_size / 1048576:.1f} MB")
            cfg_path = cfg_fut.result()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = repo.replace("/", "_")
    out = OUT_DIR / f"{safe}_{tag}.tar"
    cfg_name = f"{cfg_digest.split(':', 1)[1]}.json"
    layer_names = [f"{d.split(':', 1)[1]}/layer.tar" for d in layer_digests]

    log(f"[{spec}] 打包 {out.name} …")
    with tarfile.open(out, "w", format=tarfile.GNU_FORMAT) as tar:
        _add_bytes(tar, cfg_name, cfg_path.read_bytes())
        for p, lname in zip(layer_paths, layer_names):
            info = tarfile.TarInfo(lname)
            info.size = p.stat().st_size
            info.mtime = 0
            with open(p, "rb") as f:
                tar.addfile(info, f)
        manifest = [{"Config": cfg_name, "RepoTags": [f"{name}:{tag}"], "Layers": layer_names}]
        _add_bytes(tar, "manifest.json", json.dumps(manifest).encode())

    log(f"[{spec}] 已写出 {out}  ({out.stat().st_size / 1048576:.1f} MB)")
    return out


def main() -> int:
    specs = sys.argv[1:]
    if not specs:
        print(__doc__)
        return 2
    outs = []
    for s in specs:
        try:
            outs.append(build_image_tar(s))
        except Exception as exc:  # noqa: BLE001
            print(f"[{s}] 失败: {exc}", file=sys.stderr, flush=True)
            return 1
    print("\n全部完成。导入命令：", flush=True)
    for o in outs:
        print(f"  docker load -i {o}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
