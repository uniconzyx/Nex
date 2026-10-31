"""把 Windows 侧 TCP 端口桥到 WSL 里的 Unix socket（绕过不稳定的 WSL NAT）。

背景：本机 WSL 的 vEthernet(NAT) 转发会周期性失效（`WinError 1225` 间歇出现），
但 WSL 的 `/mnt/c` 文件系统互通始终可用。所以：
    Windows 127.0.0.1:55432 --(本脚本)--> //wsl.localhost/Ubuntu/run/nex/pg.sock --> WSL:55432
让后端只连 127.0.0.1，不受 NAT 抖动影响。

用法：
    python -m scripts.wsl_bridge
"""
from __future__ import annotations

import asyncio
import sys

SOCK_DIR = r"\\wsl.localhost\Ubuntu\run\nex"
ROUTES = [(55532, "pg.sock"), (56579, "redis.sock")]


async def pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while chunk := await reader.read(65536):
            writer.write(chunk)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        try:
            writer.close()
        except Exception:  # noqa: BLE001
            pass


async def handle(tcp_r, tcp_w, sock_name: str) -> None:
    path = f"{SOCK_DIR}\\{sock_name}"
    try:
        unix_r, unix_w = await asyncio.open_unix_connection(path)
    except Exception as exc:  # noqa: BLE001
        print(f"[bridge] {sock_name} 打开失败: {exc}", flush=True)
        tcp_w.close()
        return
    await asyncio.gather(pump(tcp_r, unix_w), pump(unix_r, tcp_w))


async def main() -> None:
    servers = []
    for port, sock in ROUTES:
        srv = await asyncio.start_server(lambda r, w, s=sock: handle(r, w, s), "127.0.0.1", port)
        servers.append(srv)
        print(f"[bridge] 127.0.0.1:{port} -> {SOCK_DIR}\\{sock}", flush=True)
    async with asyncio.TaskGroup() as tg:
        for srv in servers:
            tg.create_task(srv.serve_forever())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
