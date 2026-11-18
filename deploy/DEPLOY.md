# Nex 上线部署指南（让其他电脑 / 手机可用）

> 目标：把 Nex 后端部署到「一台公网可达的主机」，重打客户端后，任意设备装上即连。
> 适用：Nex 当前交付形态 = Windows 桌面 EXE + Android APK（WebView 壳）。
> 已验证：`deploy/docker-compose.yml` 经 `docker compose config -q` 通过；APK 已开启 `usesCleartextTraffic=true`（明文直连可用，无需先配 HTTPS）。

---

## 0. 架构（一句话）

```
手机/电脑  ──NEX_API_BASE──▶  nginx:80  ──/api/──▶  api:8000
                                         ├─ worker（arq 判题轮询/同步）
                                         ├─ postgres / redis / minio
                                         └─ judge0（编译判题沙箱，需 privileged）
```

客户端不在浏览器跑、不在 nginx 挂静态文件，**只把 `NEX_API_BASE` 指到后端地址**即可。

---

## 1. 免费云选型（2026-11 实测）

| 方案 | 配置 | 期限 | 对 Nex 适配 | 门槛 |
|---|---|---|---|---|
| **Oracle Always Free** | ARM 4核24G | **永久** | 配置碾压，但 **Judge0 官方镜像多为 amd64**，ARM 需自适配；注册风控严 | 需**国际信用卡**（国内卡常被拒） |
| **腾讯云轻量**（新用户） | 2核4G | 免费 1 月，后续 38–99 元/年 | 境内低延迟、可备案、最省心；免费期短 | 大陆身份证实名 |
| **阿里云**（新用户） | 最高 4核8G | 免费 3 月 | 同上，额度更大 | 大陆身份证实名 |

**结论**：
- **不想用信用卡 → 选腾讯云/阿里云轻量免费试用**（2核4G，限时 1–3 月，大陆实名即领，**免信用卡**，微信/支付宝绑的银行卡就能认证；到期可备份迁出，不愿续费约 38–99 元/年）。
- 想「永久免费 + 高配」→ Oracle Always Free（4核24G 永久），但注册**要国际信用卡做身份验证**（扣 $1 预授权后退回，并非付费；且国内 Visa/Master 借记卡常被拒），ARM 架构下 Judge0 镜像还需自适配。
- 想「境内低延迟 + 可备案 + 落地最快」→ 同样是腾讯云/阿里云，实名领机后跑 `cloud-deploy.sh` 即可。
- Nex 这套对免费档偏重（PG+Redis+MinIO+Judge0），**至少 2核4G**，否则判题会卡。

---

## 2. 在云主机上上线（一键）

1. 领/买一台云主机（Ubuntu 22.04+，≥2核4G）。
2. 安全组开放入站：**80**（nginx）；若想客户端直连 api，再加 **8000**。
3. 把代码弄上去：`git clone` 本仓库，或 `scp -r CppMind 用户@主机:/opt/`。
4. 进到 `CppMind/deploy/`，执行：
   ```bash
   # 推荐：显式指定对外地址（用云主机的公网 IP 或已备案域名）
   NEX_PUBLIC_BASE=http://<公网IP>/ sudo ./cloud-deploy.sh
   ```
   脚本会自动：装 Docker → 生成 `.env`（随机 JWT 密钥）→ `compose up --build` → 等健康 → `init_db`。
5. 验证：`curl http://<公网IP>/health` 应返回后端信息。

> 生产增强（可选）：为 nginx 加 443 + Let's Encrypt（certbot），改 `NEX_PUBLIC_BASE` 为 `https://域名`。
> 当前 Nex 客户端已允许明文，无域名也能先用 `http://IP/` 跑通。

---

## 3. 客户端重打（关键：把地址写死进包）

仓库已支持打包时注入线上地址：设 `NEX_API_BASE=<公网地址>`，Rust 端会作为首选候选（优先级高于局域网探测）。

**桌面 EXE（给其他 Windows 电脑）：**
```bash
NEX_API_BASE=http://<公网IP>/ python deploy/package/prepare_app.py
# 然后重新构建 EXE（见 build-app-exe.cmd），分发 Nex.exe
```

**Android APK（给其他手机）：**
```bash
NEX_API_BASE=http://<公网IP>/ python deploy/package/prepare_app.py
# 然后重新构建 APK（见 build-app-apk.cmd），分发 Nex.apk
```
> 移动端候选顺序：用户手填 > `NEX_API_BASE` 环境变量 > 打包注入地址 > 回环兜底。
> 线上打包时 `NEX_API_BASE` 即公网地址，手填为空时自动直连，无需每次配置。

**不想重打包？** 桌面/手机客户端设置页「内容服务」手动填 `http://<公网IP>/` 也能连（需用户填一次并记住）。

---

## 4. 验证「其他设备可用」

- 另一台电脑：装 EXE → 启动应秒连 `api_probe reachable=true`，无重试红条。
- 手机（同 WiFi 或数据网，非同机）：装 APK → 冷启动自动连后端，真题模式套卷可浏览。
- 排错：`deploy/package/verify_android.py --cold --wait 0`（MuMu 实测验收）。

---

## 5. 已知约束 / 注意

- **Judge0 判题**依赖 `privileged` 容器，标准云 ECS/轻量允许；Serverless（如 AWS Fargate）不允许，别选那种。
- **23:00 本机自动关机**不影响云上部署（服务跑在云主机，不在你这台 PC）。
- 本机 Docker 现由你手动开着才可用；agent 无法替你启动它，云主机上则正常自启。
- 免费档到期前请备份数据（pgdata 卷），避免机器释放丢库。
- 数据库密码、JWT 密钥、AI Key 切勿入库；生产用 Docker secrets 或 CI 注入（见 `server/README.md` 部署校准项）。
