#!/usr/bin/env bash
# =============================================================================
# verify_docker_stack.sh —— Docker 版 PG/Redis 一键验证
#
# 用途：Docker Desktop 启动后，跑这一条命令就能走完「拉起 → 健康检查 → 灌数据 →
#      34 项黑盒验收 → 报告结果」的全流程，不需要人工盯中间步骤。
#
# 设计原则：
#   1. **不碰原生 PG(5433)**。原生库里是主人当前在用的数据，本脚本只操作容器内的
#      5432 端口，验证完把 .env 恢复原样。
#   2. **幂等**。init_db 用 `create_all` + 按自然键跳过已存在行；两个 seed 脚本同理，
#      重复执行不会撞 unique 约束，也不会产生重复数据。
#   3. **失败即停并打印定位信息**，不吞错误。
#
# 用法：
#   cd server && bash scripts/verify_docker_stack.sh
#
# 退出码：0 = 全部通过；1 = 某一环失败（看最后的 FAIL 行）
# =============================================================================
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

PY="${PY:-/c/Users/zyx/.workbuddy/binaries/python/envs/default/Scripts/python.exe}"
ENV_FILE=".env"
ENV_BAK=".env.docker-verify.bak"

green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*"; }
step()  { printf '\n\033[36m==> %s\033[0m\n' "$*"; }

fail() {
  red "FAIL: $*"
  # 无论怎么失败，都要把 .env 还原，否则后端会连到不存在的库
  if [ -f "$ENV_BAK" ]; then
    mv -f "$ENV_BAK" "$ENV_FILE"
    echo "（已恢复 .env）"
  fi
  exit 1
}

# ---------------------------------------------------------------------------
step "① 引擎连通性"
docker version --format '{{.Server.Version}}' >/dev/null 2>&1 \
  || fail "Docker 引擎未就绪。请先从开始菜单启动 Docker Desktop，等托盘变绿。"
green "引擎 OK: $(docker version --format '{{.Server.Version}}' 2>/dev/null)"

# ---------------------------------------------------------------------------
step "② 镜像源是否生效"
MIRRORS=$(docker info --format '{{json .RegistryConfig.Mirrors}}' 2>/dev/null)
echo "mirrors = $MIRRORS"
case "$MIRRORS" in
  *docker.1ms.run*|*daocloud*|*dockerproxy*) green "加速器已生效" ;;
  *) red "警告：加速器未生效（daemon.json 改了但引擎没重载？）。继续尝试直连拉取，可能很慢。" ;;
esac

# ---------------------------------------------------------------------------
step "③ 拉起 postgres + redis"
docker compose up -d || fail "docker compose up 失败"
echo "等待健康检查（最多 90s）…"
for i in $(seq 1 45); do
  sleep 2
  PG=$(docker inspect -f '{{.State.Health.Status}}' cppmind-postgres 2>/dev/null || echo none)
  RD=$(docker inspect -f '{{.State.Health.Status}}' cppmind-redis   2>/dev/null || echo none)
  [ "$PG" = healthy ] && [ "$RD" = healthy ] && break
done
echo "postgres=$PG  redis=$RD"
[ "$PG" = healthy ] || fail "postgres 未 healthy（docker logs cppmind-postgres 查看）"
[ "$RD" = healthy ] || fail "redis 未 healthy"
green "两个服务都 healthy"

# ---------------------------------------------------------------------------
step "④ 连通性实测"
docker compose exec -T postgres pg_isready -U cppmind -d cppmind || fail "pg_isready 失败"
PONG=$(docker compose exec -T redis redis-cli ping 2>/dev/null | tr -d '\r')
[ "$PONG" = "PONG" ] || fail "redis ping 返回 '$PONG'，期望 PONG"
green "pg_isready / redis PONG 均正常"

# ---------------------------------------------------------------------------
step "⑤ 临时指向容器库并灌数据"
cp "$ENV_FILE" "$ENV_BAK" || fail "备份 .env 失败"
# 用 python 改，避免 sed 在不同平台上的行为差异
"$PY" - "$ENV_FILE" <<'PYEOF'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding='utf-8')
t = t.replace('@127.0.0.1:5433/', '@127.0.0.1:5432/')
p.write_text(t, encoding='utf-8')
print('database_url ->', [l for l in t.splitlines() if l.startswith('database_url')])
PYEOF

"$PY" scripts/init_db.py || fail "init_db.py 失败（可能表结构不兼容，看上面的 Alembic/DDL 报错）"
"$PY" scripts/seed_career_projects.py || fail "seed_career_projects.py 失败"
"$PY" scripts/seed_guides.py || fail "seed_guides.py 失败"

# ---------------------------------------------------------------------------
step "⑥ 数据落库抽查"
docker compose exec -T postgres psql -U cppmind -d cppmind -c \
  "select 'users' t, count(*) from users
   union all select 'career_projects', count(*) from career_projects
   union all select 'guide_items', count(*) from guide_items;" \
  || fail "抽查 SQL 失败"

# ---------------------------------------------------------------------------
step "⑦ 34 项黑盒验收（对着容器库跑一个临时后端）"
# 关键：**不碰主人正在跑的 8000 端口后端**。
# 这里用 DATABASE_URL/REDIS_URL 环境变量覆盖（pydantic-settings 里 env 优先级高于
# .env 文件），在 8011 另起一个只读容器库的实例，测完即 kill。
# 这样既验证了容器库的真实可用性，也不会打断主人手上的环境。
CODE=$(curl -s --noproxy '*' -m 3 -o /dev/null -w "%{http_code}" \
  http://127.0.0.1:8011/api/v1/health 2>/dev/null || echo 000)
if [ "$CODE" != "000" ]; then
  red "8011 已被占用，跳过验收（换个端口或先关掉占用进程）"
else
  echo "在 8011 起临时后端 …"
  DATABASE_URL="postgresql+asyncpg://cppmind:cppmind@127.0.0.1:5432/cppmind" \
  REDIS_URL="redis://127.0.0.1:6379/0" \
  "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8011 --log-level warning \
    > .scratch-verify-backend.log 2>&1 &
  TMP_PID=$!

  # 等它起来（最多 30s）
  for i in $(seq 1 30); do
    sleep 1
    curl -s --noproxy '*' -m 2 -o /dev/null http://127.0.0.1:8011/api/v1/health && break
  done

  if E2E_BASE_URL="http://127.0.0.1:8011" "$PY" scripts/e2e_http.py; then
    green "34 项全绿"
  else
    red "验收未全绿，见 .scratch-verify-backend.log"
  fi

  kill "$TMP_PID" 2>/dev/null
  wait "$TMP_PID" 2>/dev/null
  rm -f .scratch-verify-backend.log
fi

# ---------------------------------------------------------------------------
step "⑧ 恢复 .env"
if [ -f "$ENV_BAK" ]; then
  mv -f "$ENV_BAK" "$ENV_FILE"
  green ".env 已恢复为原生 PG(5433)"
else
  echo ".env 已是恢复状态"
fi

echo
green "=== 容器侧验证结束 ==="
echo "容器保持运行中。如需停止： docker compose down"
echo "如需让后端长期连容器库：把 .env 的 5433 改成 5432 后重启后端（注意原生库与容器库是两套数据）。"
