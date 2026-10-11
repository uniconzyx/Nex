# Nex

一张导图，从 C 到深度学习部署 —— 移动优先的 C/C++（及 13 大学科）系统化学习 APP。

> 形象 **CppCat**（蓝白小猫咪），蓝白设计系统，主蓝 `#3B82F6`。

## 仓库结构

```
Nex/
├── docs/          阶段交付文档（PRD / 架构 / 数据库与 API / 审计）
├── server/        FastAPI 后端（AI 助手 CppCat、内容/习题/检索 API）
├── app/           Flutter 客户端（Android / iOS / Web，蓝白猫咪版）
├── web-preview/   自包含产品演示 SPA（双击即可在浏览器预览）
├── shared/        共享配置：GitHub 仓库清单、LeetCode 映射、题库样例
├── content/       学习内容源文件（13 学科 / 114 章 × 7 类内容，阶段 7 量产）
├── deploy/        Docker Compose / Nginx / Prometheus / 桌面启动器
└── .github/       云端构建流水线（.apk / .exe 发布物）
```

## 当前进度

- [x] 阶段 1：PRD（v0.2 含蓝白猫咪版 UI/UX）
- [x] 阶段 2：技术架构
- [x] 阶段 3：数据库与 API
- [x] 阶段 4：后端代码（本仓库 `server/`）
- [x] 阶段 5：移动端 / Web 客户端（`app/`）
- [x] 阶段 6：AI 助手深化（CppCat，DeepSeek 链路已打通）
- [x] 阶段 7：内容填充（**114 章 × 7 类，全库通过三重校验**）
- [ ] 阶段 8：深度学习模块（内容已含 `ai` 学科，待独立模块）
- [ ] 阶段 9：测试与部署
- [ ] 阶段 10：迭代计划

## 内容规模（阶段 7 收官自检）

| 指标 | 结果 |
|---|---|
| 学科数 | 13（cpp / clang / java / python / database / fullstack / spring / middleware / bigdata / fundamentals(408) / tooling / data / ai） |
| 章节数 | **114 / 114** 全部达标 |
| 概念文件三视角 | **436 / 436** 齐备（🧑‍💻程序员 / 🎓博士生 / 📚考研者） |
| 习题 | **818 道**（基础 562 / 算法 256），字段缺失 0、平台题缺链接 0 |
| 示例真实回放 | **1303 / 1303** 通过（C/C++/Java/Python/SQL 等真实编译器实测） |
| 八股模块 | 13 / 13 学科达标 |
| 学习来源 | **每章 `goals.md` 同时含 GitHub（star 最高）+ B 站真实教程双来源** |

校验入口（常驻 `server/scripts/`）：

```bash
python server/scripts/validate_content.py     # 门禁：7 类门槛 + 三视角 + 八股 + 规划覆盖
python server/scripts/verify_examples.py       # 真实重编译重跑 examples，与 expected_output 比对
python server/scripts/verify_exercises.py      # 题集健康度：字段/链接/语法/题数一致性
python server/scripts/audit_learning_lines.py  # 学习线独立性审计
```

## AI 助手 CppCat（阶段 6，链路已打通）

后端 `server/app/api/v1/ai.py` + `server/app/services/ai_provider.py`，默认接入 **DeepSeek**
（OpenAI 兼容协议，`deepseek-chat` 轻量 / `deepseek-reasoner` 重量），已用真实密钥实测流式返回可用。

功能矩阵：

| 能力 | 端点 | 前端页面 |
|---|---|---|
| 流式对话（6 模式：苏格拉底/诊断/审查/面试/计划/DL 向导） | `POST /api/v1/ai/chat`（SSE） | `ai_page.dart` |
| 薄弱点诊断（聚合错题本 + 进度） | `GET /api/v1/ai/insight` | `ai_insight_page.dart` |
| 自适应测验（基于错题抽真题依据题） | `POST /api/v1/ai/generate-quiz` | `ai_quiz_page.dart` |
| 每日配额 | `GET /api/v1/ai/quota` | — |
| 会话管理 / 学习计划（流式） | `/api/v1/ai/conversations`、`POST /api/v1/ai/plan` | 后端能力（按需接 UI） |

回答均锚定到真实课程资料与真题依据（RAG 检索），避免凭空编造。

> ⚠️ 密钥安全：`server/.env` 含 `DEEPSEEK_API_KEY` 等，**已被 `.gitignore` 排除，绝不进仓库**。
> 部署时通过 `deploy/docker-compose.yml` 的 `env_file` 注入，或通过 `--dart-define=DEEPSEEK_API_KEY=...` 注入前端构建。

## 快速体验（后端 + 桌面启动器）

### 方式 A：一键桌面启动器（推荐 Windows 用户）

`deploy/launcher/Nex-Launcher.exe`（由 `deploy/launcher/launcher.py` 用 PyInstaller 打包）：

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
2. 双击 `Nex-Launcher.exe` → 自动 `docker compose up -d` 起全部服务（Postgres/Redis/API/...）→
   等待 `/health` → 自动打开 `web-preview/index.html` 演示页。

> 启动器为纯标准库实现，仅编排 Docker 与浏览器；若本机无 Docker 会给出友好提示。
> 重新构建见 `deploy/launcher/build_exe.ps1`（或 `build_exe.sh`）。

### 方式 B：命令行

```bash
# 1) 起依赖与后端（含 Postgres / Redis / API / Nginx）
cd deploy && docker compose up -d --build
docker compose exec api python -m scripts.init_db   # 首次初始化表结构
curl http://localhost/health

# 2) 移动端（需 Flutter SDK）
cd app && flutter pub get && flutter run

# 3) Web 演示
# 直接用浏览器打开 web-preview/index.html，或：
cd web-preview && python -m http.server 8080   # 然后访问 http://localhost:8080
```

本地开发（不依赖 Docker，需本机 Postgres + Redis）：

```bash
cd server
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY 等
uvicorn app.main:app --reload --port 8000
```

## 打包发布（.apk / .exe）

发布二进制由 GitHub Actions 云端构建，不在仓库内提交大文件：

- **Android APK**：`.github/workflows/build_apk.yml`（`flutter build apk --release`，
  通过 `API_BASE_URL` secret 注入后端地址），在打 `v*` tag 时产出 `app-release.apk` artifact。
- **Windows 启动器**：`.github/workflows/build_exe.yml`（Windows runner + PyInstaller 打包
  `deploy/launcher/launcher.py`），在打 `v*` tag 时产出 `Nex-Launcher.exe` artifact。

本地手动构建见各脚本内注释。

## 贡献指南

见 [CONTRIBUTING.md](./CONTRIBUTING.md)：学科结构、7 类内容规范、三视角要求、GitHub star 最高 +
B 站双来源规则、门禁与校验脚本、合规红线（LeetCode/牛客只存元数据 + 链接）、密钥安全。

## 许可证

见 [LICENSE](./LICENSE)。
