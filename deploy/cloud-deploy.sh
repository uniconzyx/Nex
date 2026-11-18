#!/usr/bin/env bash
# =============================================================================
# Nex 云端一键部署脚本（Ubuntu 22.04+ / 任意已装 Docker 的 Linux）
#
# 作用：在「一台公网可达的云主机」上把整套 Nex 后端（nginx + api + worker
#       + postgres + redis + minio + judge0）拉起来并初始化数据库，
#       使任意电脑/手机装了对应客户端后都能连上。
#
# 前置：
#   - 一台云主机（≥2核4G，开放入站 80；若要直连 api 则再开 8000）
#   - 你能 SSH 进去并以 root 或有 sudo 的账号执行本脚本
#   - 代码已就位（git clone 本仓库，或 scp 整个 CppMind 目录）
#
# 用法：
#   sudo ./cloud-deploy.sh                                # 交互：自动探测公网 IP
#   NEX_PUBLIC_BASE=http://1.2.3.4/ ./cloud-deploy.sh    # 显式指定对外地址（推荐）
#   NEX_SKIP_DEPS=1 ./cloud-deploy.sh                    # 已装好 docker 时跳过安装
#
# 注意：本脚本只管「后端上线」。客户端（EXE/APK）需用 NEX_PUBLIC_BASE
#       重打，见 deploy/DEPLOY.md 第 4 节。
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE="docker compose -f deploy/docker-compose.yml"

echo "==> 仓库根: $REPO_ROOT"

# ---------- 1. 依赖 ----------
if [[ "${NEX_SKIP_DEPS:-0}" != "1" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "==> 未检测到 docker，正在安装（Ubuntu）..."
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      >/etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
  else
    echo "==> docker 已安装: $(docker --version)"
  fi
fi

# ---------- 2. .env ----------
if [[ ! -f server/.env ]]; then
  echo "==> 由 .env.example 生成 server/.env"
  cp server/.env.example server/.env
  # 随机生成 JWT 双密钥（生产必须，不要再留 change-me）
  if command -v openssl >/dev/null 2>&1; then
    S1=$(openssl rand -hex 32); S2=$(openssl rand -hex 32)
    sed -i "s#^JWT_SECRET=.*#JWT_SECRET=$S1#" server/.env
    sed -i "s#^JWT_REFRESH_SECRET=.*#JWT_REFRESH_SECRET=$S2#" server/.env
    echo "    已随机生成 JWT 密钥，请再补填 AI Key（DEEPSEEK_API_KEY 等）。"
  else
    echo "    ⚠ 未找到 openssl，JWT 仍是占位值，请手动改 server/.env 的 JWT_SECRET/JWT_REFRESH_SECRET"
  fi
else
  echo "==> server/.env 已存在，沿用。"
fi

# ---------- 3. 对外地址 ----------
if [[ -z "${NEX_PUBLIC_BASE:-}" ]]; then
  # 探测公网 IP（失败则提示手动填）
  PUB_IP=$(curl -s --max-time 5 https://ip.sb 2>/dev/null || true)
  if [[ -n "$PUB_IP" ]]; then
    NEX_PUBLIC_BASE="http://${PUB_IP}/"
    echo "==> 探测到公网 IP: $PUB_IP  →  NEX_PUBLIC_BASE=$NEX_PUBLIC_BASE"
  else
    echo "==> 无法探测公网 IP，客户端需手动在设置页填写「内容服务」地址。"
  fi
fi

# ---------- 4. 拉起服务 ----------
echo "==> docker compose up（首次会构建 api 镜像，可能需 1-3 分钟）..."
$COMPOSE up -d --build

echo "==> 等待 api 健康..."
for i in $(seq 1 30); do
  if curl -s --max-time 3 http://127.0.0.1/api/v1/system/health >/dev/null 2>&1 \
     || curl -s --max-time 3 http://127.0.0.1:8000/api/v1/system/health >/dev/null 2>&1; then
    echo "    api 已就绪"; break
  fi
  sleep 3
done

# ---------- 5. 初始化数据库 ----------
echo "==> 初始化数据库（建表 + 种子数据）..."
$COMPOSE exec -T api python -m scripts.init_db || echo "    ⚠ init_db 失败，请查看日志: $COMPOSE logs api"

# ---------- 6. 完成 ----------
echo ""
echo "==================== 部署完成 ===================="
echo "后端健康检查： curl http://<本机公网IP>/health"
if [[ -n "${NEX_PUBLIC_BASE:-}" ]]; then
  echo "客户端「内容服务」地址填： $NEX_PUBLIC_BASE"
  echo "重打客户端（在本机开发环境执行）："
  echo "  NEX_API_BASE=$NEX_PUBLIC_BASE python deploy/package/prepare_app.py"
  echo "  # 然后重新构建 EXE / APK"
fi
echo "日志查看： $COMPOSE logs -f api"
echo "停止：     $COMPOSE down"
echo "================================================="
