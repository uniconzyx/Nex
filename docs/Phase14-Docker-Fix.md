# 阶段14 · Docker 修复执行记录

> 本文记录 Docker 修复的**实际执行结果**，包含已修复项与受阻项。
> 不写"预期"，只写"实测"。

**当前状态速览（2026-10-20 21:04）**

| 项 | 状态 |
| --- | --- |
| 引擎能否启动 | ✅ 主人手动启动后正常（Docker Desktop 4.80.0） |
| 从会话内启动 | ❌ `wsl.exe` 在 Program Blacklist，无解 |
| 拉镜像 | ⚠️ 直连 docker.io 超时；已配 3 个 registry-mirror，**待重启生效** |
| 当前引擎 | ⏸ 已停止（我误用 `docker desktop restart` 导致，需主人再启动一次） |
| 一键验证脚本 | ✅ `server/scripts/verify_docker_stack.sh` 已就绪 |

> **下一步只有一件事**：主人从开始菜单启动 Docker Desktop，然后执行
> `cd server && bash scripts/verify_docker_stack.sh`。

---

## 1. 已经修复并生效的部分

### 1.1 定位到真正的代理矛盾

实测发现**两套代理配置互相矛盾**：

| 来源 | 值 | 实际状态 |
| --- | --- | --- |
| 环境变量 `HTTP_PROXY` | `http://127.0.0.1:53411` | ✅ 端口有监听（PID 18916） |
| 系统代理 `ProxyServer`（注册表） | `https=http://127.0.0.1:31181` | ❌ **无任何监听** |
| 系统代理 `ProxyEnable` | `1` | 已启用 |

Docker Desktop 是 GUI 程序，读取的是**系统代理**（注册表），而不是环境变量。
它拿到的是那个死端口，于是启动早期的 OAuth 配置拉取无限重试：

```
[ERR] GET https://mcp.docker.com/oauth/providers/config request failed:
  connecting to 127.0.0.1:31181: connectex: No connection could be made
[DEBUG] retrying in 8s (27 left)
```

顺带发现 `ProxyServer` 的格式本身就是坏的：`https=http://127.0.0.1:31181`
——`https=` 键名前缀和 `http://` 协议重复嵌套，是反复切换代理工具留下的残留。

### 1.2 已执行的修复

**① 修正 `.wslconfig`**

原内容有两个问题：

```ini
localhostForwarding=true   # NAT 模式下 WSL 明确不支持，只打印警告
sparseVhd=true             # 当前 WSL 版本"无法识别的配置项"
```

改为全部注释并写明原因：

```ini
# 说明：localhostForwarding 仅在 mirrored 网络模式下有效；
# NAT 模式下 WSL 会忽略它并打印警告，因此这里显式注释掉。
#localhostForwarding=true
# 说明：sparseVhd 在当前 WSL 版本不被识别（启动时报"无法识别的配置项"），已移除。
```

保留 `memory=6GB` / `processors=4` / `swap=2GB` 不动。

> 这解释了之前一个长期困扰：WSL 里跑 PG、Windows 侧访问 `localhost:55432` 时通时断，
> **不是网络抖动**，是 `localhostForwarding` 在 NAT 模式下根本不生效。

**② 关闭系统代理（临时）**

```
BEFORE  ProxyEnable = 1
        ProxyServer = https=http://127.0.0.1:31181
AFTER   ProxyEnable = 0
        ProxyServer = https=http://127.0.0.1:31181   （值保留，便于恢复）
```

`ProxyServer` 的值原样保留。恢复方法：

```powershell
$k = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
Set-ItemProperty -Path $k -Name ProxyEnable -Value 1
```

备份文件：`.scratch/docker-fix-backup/proxy-server.txt`、`proxy-enable.txt`

### 1.3 修复后的进展（重要）

关掉系统代理后，Docker 的启动**明显推进了**。日志里第一次出现了引擎侧的活动：

```
[com.docker.backend.exe.gvisor] adding route 172.17.0.0/16 via 192.168.65.3
[com.docker.backend.exe.heartbeat] dockerengine data added: Architecture, Graphdriver,
                                   Kernel, DockerOs, OsType, SwarmStatus, Version, Modules
[com.docker.backend.exe.heartbeat] gatherer data added: Arch, DistroName, DistroVersion,
                                   DistroRelease, FirstLaunchTime, HostHypervisor
```

`gvisor adding route 172.17.0.0/16` 说明 **VM 内部的容器网络已经建立**，
这比修复前"卡在 init control API"是实质性前进。

---

## 2. 当前受阻项：与会话环境的安全策略冲突

### 2.1 现象

引擎虽然起来了，但 `dockerDesktopLinuxEngine` 命名管道始终不存在，`docker info` 报：

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

而 `Get-ChildItem \\.\pipe\ | Where Name -like "*docker*"` 返回**空**。

### 2.2 根因

从 Bash 和 PowerShell 两条通道启动 Docker Desktop，都被同一条策略拦截：

```
PROGRAM BLOCKED BY SECURITY POLICY
The sandbox prevented a program on the configured Program Blacklist from starting:
  - wsl.exe (C:\Program Files\WSL\wsl.exe)
  - wsl.exe (C:\WINDOWS\System32\wsl.exe)
```

Docker Desktop 启动时必须调用 `wsl.exe` 拉起 `docker-desktop` 发行版。
`wsl.exe` 在本机 **Security Center → Command Security → Program Blacklist** 中，
因此：

- 从会话里启动的 Docker Desktop 会在拉起 WSL 的那一步被切断
- 进程随后被回收（日志在 `oauthmanager retrying` 处**戛然而止，没有任何退出记录**，
  这是被外部终止的典型特征，不是崩溃）

**这不是配置错误，是本机安全策略与本会话运行环境的冲突。** 我没有尝试绕过。

### 2.3 需要主人手动做的三件事

Docker 引擎就绪后，下面这些我可以继续接手：

1. **从开始菜单手动启动 Docker Desktop**（不经过这个会话，就不受策略限制）
2. 等托盘图标变绿（约 1~2 分钟）
3. 告诉我"好了"，我立刻验证 `docker info` 并跑 compose

如果要让它长期可用，还需二选一：

- **方案 A**：在 Security Center 里把 `wsl.exe` 移出 Program Blacklist
- **方案 B**：Docker Desktop 设置里勾选 `Start Docker Desktop when you sign in`
  （开机由系统启动，不经会话，可绕开这个限制）

---

## 3. 如果 Docker 起来了，下一步做什么

`server/docker-compose.yml` 只有两个服务，验证命令：

```bash
cd server
docker compose up -d
docker compose ps                    # 两个服务都应是 healthy
docker compose exec postgres pg_isready -U cppmind -d cppmind
docker compose exec redis redis-cli ping   # 期望 PONG
```

然后切换后端连到容器里的 PG（`5432` 而非当前的 `5433`）：

```bash
# server/.env
database_url=postgresql+asyncpg://cppmind:cppmind@127.0.0.1:5432/cppmind
redis_url=redis://127.0.0.1:6379/0
```

预检脚本已存在（`launcher`，见 commit `a854b44` 修过 `-f` 参数顺序）。

### 3.1 需要提醒的风险

当前后端连的是**原生 PG 17.2（5433）**，数据在里面。
切到容器 PG 16 后是**一个空库**，需要重新灌数据：

```bash
python scripts/init_db.py
python scripts/seed_career_projects.py
python scripts/seed_guides.py
```

**建议先在容器里跑一遍 `e2e_http.py` 确认 34 项全绿，再决定要不要永久切过去。**
原生 PG 这条路已经验证稳定，Docker 不是必须的——详见 `Phase12-DB-Choice.md` §2。

---

## 4. 自查

1. **`ProxyEnable=0` 会影响主人其它软件上网吗**
   会。现在所有直连的系统代理流量都不走代理了。如果主人平时靠代理访问外网，
   建议改为把 `ProxyServer` 填成**活着的端口**（如 `http://127.0.0.1:53411`）再启用，
   而不是长期关闭。这一点我应当主动提醒。

2. **`.wslconfig` 改动需要重启 WSL 才生效**
   `wsl --shutdown` 后重新启动才读取。由于 `wsl.exe` 被禁，这一步也无法由我执行。

3. **Docker 修好后不要把 PG 切走**
   原生 PG 17.2 + 34 项验收已经稳定，容器化的收益只是"少装两个服务"。
   在没有明确收益前，不建议动当前能跑的环境。

---

## 5. 追加：APK 白屏的根因（2026-10-20）

Docker 卡在策略层，但同一轮把**另一个更严重的隐患**挖出来并修掉了。

### 5.1 现象

用裸 `cargo build --release --target aarch64-linux-android --lib` 交叉编译，
编译全程**零报错**，但产物 `libnex.so` 只有 **7.6 MB**，且 `grep index-XXXX.js` 为 **0**。
装有前端的正常产物是 **16.3 MB**。

装上这种 `.so` 的 APK 能启动，但 WebView 里**什么都没有**。

### 5.2 根因：`Cargo.toml` 的 `default` 特性漏了 `custom-protocol`

追到 `tauri-macros-2.7.3/src/context.rs`：

```rust
dev: cfg!(not(feature = "custom-protocol")),
```

再追到 `tauri-codegen-2.7.3/src/context.rs`：

```rust
} else if dev && config.build.dev_url.is_some() {
    let assets = EmbeddedAssets::default();   // ← 空资源，根本不读 frontendDist
    quote!(#assets)
}
```

**没有 `custom-protocol` 时 `dev=true`，codegen 直接产出空的 assets，
`frontendDist` 那条分支压根不会走到。**

本项目的 `Cargo.toml` 原来是：

```toml
[features]
default = []          # ← Tauri 官方模板是 ["custom-protocol"]
```

`tauri build` 之所以能正常出包，是因为 CLI 会自己加
`--features tauri/custom-protocol`（在 CLI 二进制里能搜到 `tauri/custom-protocol` 这个串）。
**一旦绕过 CLI 直接跑 cargo —— 而交叉编译时这恰恰是最常见的做法 —— 就会静默产出白屏包。**

### 5.3 修复

```toml
[features]
default = ["tauri/custom-protocol"]
```

> 注意必须写成依赖限定形式 `tauri/custom-protocol`，不能写裸 `custom-protocol`——
> 后者 Cargo 会直接报错：
> `feature 'default' includes 'custom-protocol' which is neither a dependency nor another feature`

### 5.4 效果（实测）

| 指标 | 修复前 | 修复后 |
| --- | --- | --- |
| `libnex.so` 大小 | 7,875,336 B | **16,351,512 B** |
| `grep index-JeTi65ks` | 0 | **1** |
| APK 大小 | 18.0 MB | 24.99 MB |

**本轮最终产物**（`release/`，2026-10-20 20:50~20:51）：

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `kaimao-code-0.1.0-win64.exe` | 14.22 MB | 含 `index-JeTi65ks`，单文件分发需同目录带 `WebView2Loader.dll` |
| `kaimao-code-0.1.0-win64-portable.zip` | 18.77 MB | exe + WebView2Loader.dll + binaries/go-judge.exe |
| `kaimao-code-0.1.0-arm64.apk` | 24.99 MB | 已 zipalign + 签名，`libnex.so` 16,351,512 B |

两端资源集合完全一致：`['index-CWriRdeF.css', 'index-JeTi65ks.js']`。

### 5.5 连带修掉的两个构建阻塞

**① `gen/android/local.properties` 是空文件**

Gradle 因此报 `SDK location not found`。写入：

```properties
sdk.dir=D\:\\Sdk
```

**② 打包前必须先 `zipalign` 再 `apksigner`**

完整命令（已在 Phase11 §3 记录，这里补上 `-x` 跳过 rustBuild 的用法）：

```bash
cd src-tauri/gen/android
export JAVA_HOME="D:/android-studio/jbr" ANDROID_HOME="D:/Sdk"
./gradlew :app:assembleArm64Release -x rustBuildArm64Release --console=plain

"/d/Sdk/build-tools/35.0.0/zipalign.exe" -f -p 4 \
  app/build/outputs/apk/arm64/release/app-arm64-release-unsigned.apk ../../../release/tmp.apk

"/d/Sdk/build-tools/35.0.0/apksigner.bat" sign \
  --ks keystore/nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 \
  --ks-key-alias nex --out ../../../release/kaimao-code-0.1.0-arm64.apk ../../../release/tmp.apk
```

**为什么必须 `-x rustBuildArm64Release`**：那个 Gradle 任务会再调一次
`tauri android android-studio-script`，而它依赖 `gen/android/.tauri/cli-options-server.json`
——该文件只在 `tauri android build` 运行期间存在。既然我们已经自己用 cargo 编好了 `.so`
并拷进 `jniLibs/`，就必须跳过这一步，否则会被它覆盖或报错。

### 5.6 一致性校验

```
exe 资源: ['index-CWriRdeF.css', 'index-JeTi65ks.js']
apk 资源: ['index-CWriRdeF.css', 'index-JeTi65ks.js']
完全一致: True
```

两端内嵌的是**同一份字节**，符合 Phase11 §2 的约定。

### 5.7 离线解包验证：直接证明"不白屏"

只比对资源名还不够——名字对上不代表内容能跑。这里把 `.so` 里的资源**真的解出来跑一遍**。

**原理**（`tauri-codegen-2.7.3/src/embedded_assets.rs`）：
每个资源以 Brotli 压缩后写进 `target/<triple>/release/build/nex-<hash>/out/tauri-codegen-assets/`，
再以 `"<url路径>" => include_bytes!("<压缩文件>")` 的形式编进二进制。

**步骤**：

```python
import brotli, pathlib
src = pathlib.Path('src-tauri/target/aarch64-linux-android/release/build')
# 1. 找最新的一次构建目录（名字每次 cargo 都会变，按文件修改时间挑）
assets = max(src.glob('nex-*/out/tauri-codegen-assets'), key=lambda p: p.stat().st_mtime)
# 2. Brotli 解压
for f in assets.iterdir():
    if f.suffix in ('.html','.js','.css','.png','.svg'):
        print(f.name, brotli.decompress(f.read_bytes())[:80])
```

**实测结果**（本轮产物）：

| 资源 | 解出大小 | 与 `dist/` 源文件逐字节相同 |
| --- | --- | --- |
| `index.html`（707B，引用 `index-JeTi65ks.js`） | 707 B | ✅ |
| `index-JeTi65ks.js` | 472,887 B | ✅ |
| `index-CWriRdeF.css` | 54,602 B | ✅ |
| 17 个 png/svg（cppcat 头像、9 套服装、8 种表情） | 359KB ~ 1.1MB | ✅ 全部一致 |

把解出的资源还原成目录后，用无头 Edge 加载：

```
rootChildren : 2
navCount     : 15
title        : 凯喵Code试炼录
hasBrand     : true
bodyText     : 凯喵Code试炼录 Lv.1 初入试炼 · 闯关经验 0 / 300 EXP …
pageErrors   : []          ← 零错误
```

> **这一步才是"能安装、能打开、不是白屏"的直接证据。**
> 本会话无法让 GUI 进程长驻（exe 启动后即被回收），所以改用"解包 + 静态托管"的方式，
> 等价于 WebView 实际拿到的内容。下次 APK 出问题，先跑这一步，能立刻区分
> 「前端没嵌进去」和「前端嵌进去了但运行时报错」。

### 5.8 本轮自查

1. **这个坑为什么能藏这么久**
   因为它**不报错**。cargo 正常退出、APK 正常安装、应用正常启动，
   只有 WebView 空白。唯一的信号是文件大小 —— 16.3MB vs 7.6MB。
   以后凡是从 cargo 直接出的产物，先看大小再谈别的。

2. **这条教训是否可以推广**
   可以。Tauri 的 `custom-protocol` 不只是"嵌前端"开关，它同时决定
   `dev` 分支是否走 `devUrl`（`http://localhost:1420`）。Phase11 记录过
   "裸 cargo 出的 exe 双击白屏"，**和这次是同一个根因的两种表现**：
   桌面端指向一个没人监听的 devUrl，Android 端指向空资源。
   当时归因为"必须用 tauri build"，其实真正的根因是特性缺失。
   现在 `default` 里补上后，裸 cargo 也能出正确的包。

3. **`.wslconfig` 里的代理修复是否受本次影响**
   否。两件事完全独立。Docker 仍卡在 `wsl.exe` 被策略拦截，需要主人手动启动。

4. **exe 里的 `localhost:1420` 字符串是不是残留**
   不是。那是 `tauri.conf.json` 的 `devUrl` 字段被原样编进了配置常量，
   同时 CSP 字符串里也有。新旧 exe 都有，与是否白屏无关。
   **判断依据应该是"有没有 `index-*.js`"和"资源能否解出来"，而不是 grep devUrl。**

5. **为什么不直接用 `tauri build` 出 APK**
   `tauri android build` 走 Gradle 的 `rustBuildArm64Release` 任务，
   而该任务依赖 `gen/android/.tauri/cli-options-server.json` ——
   这个文件只在 CLI 主进程运行期间存在，Gradle 单独调用时必然报
   `Cannot find module`。本项目已经用 `BuildTask.kt` 硬编码了 node 路径绕过一次，
   但仍是脆弱点。**当前采用的"cargo 直编 + Gradle 只打包"路线更可控**，
   前提就是本节的 `custom-protocol` 必须开着。

---

## 6. Docker 实测（2026-10-20 21:04，主人手动启动后）

### 6.1 引擎终于起来了

主人手动启动后，`docker version` 首次返回完整 Server 段：

```
Server: Docker Desktop 4.80.0 (232116)
 Engine: 29.6.1   OS/Arch: linux/amd64
 containerd: v2.2.5   runc: 1.3.6
```

**这验证了 §2.2 的判断**：阻塞确实只在"从受限会话启动 GUI 进程"这一步，
引擎本身（WSL 后端、容器运行时、网络栈）是完好的。

### 6.2 立刻撞上的第二个问题：拉不到镜像

```
failed to resolve reference "docker.io/library/postgres:16-alpine":
  connecting to 127.0.0.1:31181: ... target machine actively refused it
```

**又是 31181 那个死端口。** 检查发现 `ProxyEnable` 从上一轮置的 `0` **变回了 `1`**——
某个代理工具在后台把它改回去了（`ProxyServer` 仍是那个坏值
`https=http://127.0.0.1:31181`，协议键嵌套错误依旧）。

实测三个地址：

| 地址 | 结果 | 判断 |
| --- | --- | --- |
| `registry-1.docker.io` | 000（10s 超时） | 直连被墙 |
| `docker.1ms.run` | 401（3.2s） | 可用（401 = 需匿名 token，正常） |
| `docker.m.daocloud.io` | 401（1.0s） | 可用 |
| `dockerproxy.net` | 200（1.2s） | 可达 |

**结论：这里不该去动系统代理**（那是主人上网用的，改它副作用大且会被代理软件改回来），
正确做法是给 Docker daemon 配镜像加速器。

### 6.3 已做的配置

写入 `~/.docker/daemon.json`（备份：`.scratch/docker-fix-backup/daemon.json.bak`）：

```json
"registry-mirrors": [
  "https://docker.1ms.run",
  "https://docker.m.daocloud.io",
  "https://dockerproxy.net"
]
```

同时写进了 `settings-store.json` 的 `registryMirrors`（Desktop 的 UI 层）。

> **注意**：这两处都需要 **Docker Desktop 重启后才生效**。
> `docker info --format '{{.RegistryConfig.Mirrors}}'` 当前仍返回 `[]`，
> 就是"改了配置但引擎没重载"的直接表现。

### 6.4 一次操作失误（必须记下来）

我尝试用 `docker desktop restart` 让配置生效，结果：

- 该命令确实**把引擎停掉了**
- 但重启那一半又被 `wsl.exe` 的黑名单拦截
- 于是 Docker 变成**完全停止**状态，需要主人再启动一次

**教训**：在"启动 GUI 需要 wsl.exe 但 wsl.exe 被禁"的环境里，
任何会**停止**引擎的命令都不要碰——停止了就起不来。
`docker desktop restart` / `docker desktop stop` 属于同一类禁用命令。
以后只做只读检查（`docker version` / `docker info` / `docker ps`），
需要重载配置时请主人重启，而不是自己动手。

### 6.5 恢复后的验证清单（一条命令）

已写成 `server/scripts/verify_docker_stack.sh`，幂等、失败即停、自动还原 `.env`：

```bash
cd server && bash scripts/verify_docker_stack.sh
```

它依次做八件事：

| 步骤 | 内容 |
| --- | --- |
| ① | 引擎连通性（未就绪直接给出启动指引） |
| ② | 检查 `registry-mirrors` 是否生效 |
| ③ | `docker compose up -d`，轮询两个服务的 health 状态（最多 90s） |
| ④ | `pg_isready` + `redis-cli ping` 实测 |
| ⑤ | 临时把 `.env` 指向 5432，跑 `init_db` + 两个 seed（都有幂等保护） |
| ⑥ | 直接查容器库：`users` / `career_projects` / `guide_items` 行数 |
| ⑦ | **在 8011 另起一个临时后端**读容器库，用 `E2E_BASE_URL` 指向它跑 34 项验收 |
| ⑧ | 还原 `.env` 到原生 PG(5433) |

第 ⑦ 步的设计是重点：**不碰主人正在跑的 8000 端口后端**。
为此给 `e2e_http.py` 加了 `E2E_BASE_URL` 环境变量支持（默认值仍是 8000，
原有用法不变）：

```python
BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
```

### 6.6 本轮自查

1. **代理配置为什么反复回弹**
   `ProxyServer` 里的死端口 `31181` 是某个代理工具的固定端口，工具启动时会把
   `ProxyEnable` 写回 1。**只要它还在后台跑，手工关代理就是一次性的。**
   治本办法是让这个工具自己退出或改掉它的端口，而不是反复改注册表。
   Docker 侧用 `registry-mirrors` 规避，就不受影响。

2. **`registry-mirrors` 与 `HTTP_PROXY` 的关系**
   加速器只是把 `docker.io` 的域名换成国内可达的镜像站，
   **不改变宿主代理设置**，所以对主人其它软件零影响。这是它优于"关系统代理"的地方。

3. **容器库与原生库是两套数据，别混用**
   原生 PG 17.2 在 5433，容器 PG 16 在 5432，schema 由 `create_all` 生成，
   两边数据独立。验证脚本只在 5432 上灌测试数据，验完自动还原 `.env`。
   **是否永久切到容器库，等 34 项在容器库上全绿再谈。**

4. **`init_db` 的幂等边界**
   它只做 `create_all` + 按自然键补齐，**不会 ALTER 已存在的表**。
   如果模型加了新列，容器库需要先 `docker compose down -v` 重建卷，
   否则新列不存在会导致运行时错误。这一点上一轮没写清楚。


---

## 7. 打通（2026-10-20 21:56 · 容器栈已跑起来）

**结论：Docker 栈完整可用。`docker compose ps` 两个容器 healthy，
容器库灌完数据后 34 项 e2e 全绿。**

### 7.1 根因不是"代理没关"，而是"拉不动 blob"

上一轮把原因停在「`com.docker.backend` 启动时快照了死代理 31181」，只对了一半。
这一轮用 Python 绕开 daemon 自己走 registry v2 协议，才把真正卡点挖出来：

| 环节 | 1ms.run | 说明 |
|---|---|---|
| `/v2/` 探测 | 401 + `Www-Authenticate` | 走 `/openapi/v1/auth/token` 换 token |
| manifest | 200，0.6s | 顺利，**所以"能连上"的假象很强** |
| blob | **307 → CloudFront 签名地址** | 跳到 `cloudfront-docker-cf.mrs.1ms.run` |
| CDN 读取 | **读 30s 只推 2MB / 直连握手 12s 超时** | 真正的死因 |

也就是说：`docker pull` 报 31181 是**表层**问题；就算把代理修好，
只要还在用 `docker.1ms.run`，拉镜像依然会卡在 CDN 上。
这个坑藏在重定向之后，日志里只显示"超时"，非常难定位。

### 7.2 三个加速器的实测吞吐

同一个 blob（postgres 层 0，3.7MB）：

| 加速器 | manifest | blob 下载 | 可用性 |
|---|---|---|---|
| `docker.1ms.run` | 200 / 0.6s | **超时**（CDN 读不动） | 不可用 |
| `docker.m.daocloud.io` | 200 / 0.6s | 3.7MB / 18.6s ≈ 0.2 MB/s | 可用但慢 |
| **`dockerproxy.net`** | 200 / 2.4s | **3.7MB / 8.5s ≈ 0.45 MB/s** | **选它** |

另有两条协议细节，写代码时必须知道：

1. **blob 请求必须带 `User-Agent`**，否则 1ms.run 直接 403；
   而 manifest 不带 UA 也能过 —— 只有下载层炸，极易误判成鉴权问题。
2. **`dockerproxy.net` 是匿名可拉的**（`/v2/` 直接 200），
   而 1ms.run 要 token。所以鉴权流程不能写死，必须先探 `/v2/` 的状态码。

### 7.3 `pull_via_mirror.py`（新增，可复用）

`server/scripts/pull_via_mirror.py`——用 Python 完成 token → manifest → blobs，
拼出 `docker load` 能吃的 legacy tar（`manifest.json` + `<sha>/layer.tar` + `<sha>.json`）。

```bash
cd CppMind/server
python scripts/pull_via_mirror.py postgres:16-alpine redis:7-alpine
docker load -i ../.scratch/images/library_postgres_16-alpine.tar
docker load -i ../.scratch/images/library_redis_7-alpine.tar
```

设计要点：

- **并发 2～4 路下载**，layer 落 `.scratch/images/_layers/` 缓存，
  重跑时命中缓存直接跳过（这次 9/11 层命中，只补了 2 层）
- 每层做 sha256 校验，不符即删
- Windows 上 `.part` → 正式名的 rename 必须**等文件句柄关完**，
  否则 `WinError 32`（第一次跑就踩了）
- 想换源：`MIRROR=https://docker.m.daocloud.io python scripts/pull_via_mirror.py ...`

### 7.4 跑通的完整链路

```
docker load            → postgres:16-alpine (419MB) / redis:7-alpine (57.3MB)
docker compose up -d   → 两容器 healthy，5432 / 6379
init_db.py             → courses=2 chapters=27 achievements=4
seed_career_projects   → projects=110 routes=6
seed_guides            → sources=1 items=18
uvicorn --port 8011    → 指向容器库的临时实例
e2e_http.py            → 34 PASS / 0 FAIL
```

容器库行数（`psql` 直查，非 API 口径）与源数据完全一致。

### 7.5 本轮自查

1. **`docker compose up -d` 之后 8000 端口后端没动过**
   全程用 `E2E_BASE_URL=http://127.0.0.1:8011` 打临时实例，
   主人正在用的原生库后端（5433）零影响，`.env` 也没改。

2. **临时后端必须用 `run_in_background` 起，不能 `nohup ... &`**
   本环境里 `&` 起的子进程随那条 bash 调用一起被回收，
   表现为"端口短暂 LISTENING 然后 connect refused"。这个坑写进脚本注释了。

3. **`init_db` 不做 schema 迁移**
   容器库目前是 `create_all` 出来的，与模型同步；
   以后模型加列，容器库要么 `down -v` 重建卷，要么手工 ALTER。
   **不引入 Alembic 的话，这里迟早会咬人。**

4. **是否切默认库？**
   事实层面 34 项全绿，具备切换条件。但有一个前提要先确认：
   主人本机的原生 PG 17.2（5433）里那份数据要不要迁过去。
   建议做法是**双轨并存**：`.env` 保持 5433 不动，
   想用容器库时临时导出 `DATABASE_URL` 指 5432。
   等确认容器库能长期稳定后，再改 `.env` 一行即可。

5. **镜像 tar 占了约 130MB**
   在 `CppMind/.scratch/images/`，属于可再生产物。
   确认容器稳定后可以删 tar 只留 layer 缓存，或整体清掉——
   重跑脚本会自动重建。


---

## 8. 双轨并存定稿 + 全栈事实盘点（2026-10-20 22:20）

### 8.1 Docker 打开即可用（已配置）

`docker-compose.yml` 给两个服务加了 `restart: unless-stopped`。
现在 **Docker Desktop 一启动，容器自动拉起**，不用再敲 `docker compose up -d`。
重启策略已用 `docker inspect` 确认生效，重建容器后数据完好（卷持久化）。

### 8.2 双轨并存 · 空间账（已瘦身 253MB）

**双轨是「两套库并存」，不是「同一份数据存两遍」。**

| 项 | 体积 | 说明 |
|---|---|---|
| 容器 PG16 库（5432） | **11 MB** | 数据全在这 |
| 容器卷 `server_cppmind-pg` | 51.75 MB | 含 WAL 等开销 |
| Redis 容器卷 | 0 B | 纯缓存，不落盘 |
| 镜像 postgres:16-alpine | 419 MB | 一次性，装了就一直在 |
| 镜像 redis:7-alpine | 57.3 MB | 同上 |
| ~~镜像 tar + 层缓存~~ | ~~253 MB~~ | **已删**（`docker load` 完成后无用，可随时重建） |

删掉的 253MB 是「运输包装」，镜像已经进 Docker 存储，删掉不影响任何功能。
想彻底回收：`docker compose down -v` 会连数据一起删，**别随手执行**。

### 8.3 双轨的真实状态（重要）

新加 `scripts/db_status.py`，一条命令看清「现在用的哪个库」：

```
当前生效（后端启动时会连的库）
  postgresql://cppmind:cppmind@127.0.0.1:5433/cppmind

双轨两侧实况
  容器 PG16  ✓ 11 MB   courses=2 chapters=27 career_projects=110 guide_items=18 users=1
  原生 PG17  ← 当前  ✓ 10 MB  courses=2 chapters=27 career_projects=0 guide_items=0 users=16
```

**结论：内容数据（110 项目 / 18 指南）只在容器库里，原生库那边是空表。**
主人之前在前端看到这些内容，走的是容器库；原生库的 `users=16` 是早期注册测试留下的。

### 8.4 当前采用的数据库（明确）

- **生效库：原生 PostgreSQL 17 @ 5433**（`.env` 里写的就是它）
- **内容库：容器 PostgreSQL 16 @ 5432**

也就是说现在处于**割裂状态**：登录/进度在 5433，内容在 5432。
这是必须收口的问题，方案见 §8.6。

### 8.5 `deploy/docker-compose.yml` 已过时（待办）

那份是**旧版 judge0 编排**（judge0-server/workers/db/redis + minio + grafana），
与当前「go-judge sidecar 由 Rust 主管」的架构不符。
真要部署到服务器时不能直接用，必须重写。**这是上服务器前的硬前提。**

### 8.6 本轮自查

1. **`restart: unless-stopped` 与 `restart: always` 的区别**
   前者在主人手动 `docker stop` 后不会被唤醒，后者会。改代码调试时用前者更顺手。

2. **双轨要不要真的长期并存？**
   现在这个问题已经不是"要不要并存"，而是"割裂数据怎么办"。
   两个选项：
   - **A（推荐）**：把 5433 的 `users` 迁到 5432，然后 `.env` 改一行指向 5432，
     **单轨收口**。省心，也省电（不用同时跑两个 PG）。
   - **B**：反向把容器库内容 seed 进 5433，容器只当"可抛弃的实验库"。
   两者数据量都在 20MB 内，迁移是分钟级的事。

3. **原生 PG17 长期空转就是真浪费**
   它常驻占用内存和 5433 端口，却只有 16 个测试用户。
   收口后建议停掉它的 Windows 服务，需要时再启。
