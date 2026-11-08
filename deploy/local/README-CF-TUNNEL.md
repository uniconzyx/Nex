# 方案 C：Cloudflare Tunnel 公网暴露 Nex 后端（免服务器、免备案）

适用于「想让别人电脑上的 App 走在线后端，但不想买云服务器、不想等 ICP 备案」的场景。
本质：**你的本机就是服务器**，Cloudflare Tunnel 把公网请求打回你本机 `127.0.0.1:8000`。

> 代价：本机必须一直开机且后端/tunnel 常驻；CF 免费节点在大陆访问可能偏慢、有速率限制。

## 一、本机常驻后端

双击 `deploy/local/start_backend.cmd`（保持窗口开着）。
依赖的 postgres/redis 用已起的 Docker 容器（`server/docker-compose.yml` 的 `cppmind-postgres`/`cppmind-redis`）。
首次若库为空，另开终端：

```bat
cd server
.venv\Scripts\python.exe -m scripts.init_db
```

验证：`curl http://127.0.0.1:8000/api/v1/system/health` 应返回 200。

## 二、装 cloudflared（本机）

```bat
winget install cloudflare.cloudflared
:: 或去 https://developers.cloudflare.com/.../downloads/ 下载 Windows 版，改名 cloudflared.exe 放进 PATH
```

## 三、零域名先验证（5 分钟看到别人能连）

双击 `deploy/local/start_tunnel.cmd`（保持窗口开着），或手敲：

```bat
cloudflared tunnel --url http://localhost:8000
```

终端会吐一个 `https://xxxx.trycloudflare.com` 临时地址（每次不同）。
把它发给助手，由助手跑 `deploy/local/rebuild_dist.cmd <该地址>` 重编分发版，你装给朋友实测即可。

## 四、正式绑域名（验证通了再做）

1. 注册 Cloudflare 免费账号，把你的域名 DNS 托管到 CF（域名可在阿里云/腾讯云买，再改 NS 到 CF；或直接在 CF 注册）。
2. 登录并创建命名隧道：

```bat
cloudflared login
cloudflared tunnel create nex
cloudflared tunnel route dns nex nex.你的域名.com
```

3. 写 `%USERPROFILE%\.cloudflared\config.yml`：

```yaml
url: http://localhost:8000
tunnel: <上面创建的隧道 UUID>
credentials-file: C:\Users\你的用户名\.cloudflared\<隧道UUID>.json
```

4. 常驻运行：`cloudflared tunnel run nex`（保持开着）。
5. 把 `https://nex.你的域名.com` 发给助手，跑 `rebuild_dist.cmd` 重编正式分发版。

## 五、重建分发版（拿到地址后）

```bat
deploy/local/rebuild_dist.cmd https://nex.你的域名.com
:: 然后双击：
deploy/package/build-app-exe.cmd    重编桌面 EXE
deploy/package/build-app-apk.cmd    重编安卓 APK
```

App 里烤进的默认后端就是这个地址，装到任何电脑默认连线上，不再掉离线。
CORS 已放行 `tauri.localhost`（原生壳 origin），公网访问不受影响。
