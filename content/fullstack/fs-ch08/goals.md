# fs-ch08 · 部署 / CI-CD / Docker · 学习目标

## 学习目标
完成本章后，你能：
1. 用密钥对完成 SSH 免密登录，写出可复用的 `~/.ssh/config`（固定 IdentityFile、禁 root 直连、禁密码认证），并用 `-L/-R/-D` 建立本地/远程/动态端口转发。
2. 说清 systemd / pm2 / supervisor 的定位差异，写出一个正确的 unit 文件（`Restart=on-failure`、`RestartSec`、`StartLimitBurst`、非 root 的 `User`），并解释为什么**容器里不该套进程管理器**。
3. 用 `journalctl -u <unit> --since --priority` 做时间与优先级过滤，用 logrotate 做**不丢日志**的轮转（`create` + `postrotate` 让进程重开文件，或 `copytruncate` 的取舍）。
4. 讲清镜像＝只读层栈、容器＝镜像＋一个可写层（copy-on-write），并据此推出**构建缓存是前缀链**：某层失效则其后全部重建。
5. 按「先 COPY 清单文件 → 装依赖 → 再 COPY 源码」的顺序写 Dockerfile，并用**重建层数**（而非观感）证明它比反模式更省；用 `.dockerignore` 把 `node_modules/.git/dist/*.log` 挡在 build context 之外。
6. 用多阶段构建（`FROM ... AS build` + `COPY --from=`）把构建工具链与源码树排除出最终镜像，并用**层数与体积估算**给出量化收益（本章示例实测 963MB → 147MB）。
7. 写 `compose.yaml` 编排多服务：自定义网络的服务名 DNS、named volume 的数据生命周期、`depends_on` + `condition: service_healthy` 的就绪门，并能**检测循环依赖**。
8. 按 12-Factor 把配置外置到环境变量，识别硬编码配置与硬编码密钥（后者为 critical），并说明为什么「删掉含密钥的提交」不等于止血（必须轮换密钥）。
9. 读懂 GitHub Actions 的 workflow → job → step 三层结构，用 `needs:` 把 job 串成 DAG，并用静态校验器检出**缺失触发条件 / 缺失 runs-on / needs 指向不存在的 job / 依赖成环**。
10. 用拓扑排序 + 最早开始时间求出流水线的 **makespan 与关键路径**，用「最大并行度」说明并行化的收益上限（本章示例实测：串行 21 分钟 → DAG 15 分钟）。
11. 设计 dev/staging/prod 三环境与「同一 artifact 逐级晋级」；对比蓝绿（原子切换）与金丝雀（权重渐进）的流量分配，并用**稳定哈希分桶**保证同一用户不来回切版本。
12. 用「样本量门槛 + 连续窗口越界」设计回滚判据（单点尖峰不回滚），用 `failureThreshold/successThreshold` 不对称阈值实现**滞回**探针，并说明 liveness 与 readiness 混用为何会导致雪崩。

## 前置
- **fs-ch04 Node.js 与后端 API**（HTTP 服务、路由、中间件、JSON body、状态码）——本章在其之上补齐「把服务送上服务器并持续交付」的工程闭环：进程与日志、镜像与编排、流水线与发布、监控与回滚。
## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04。Linux 命令、Docker、GitHub Actions 均从零讲到够用为止，不假设读者有运维经验。
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) | 196,855 | 全章 | JavaScript 算法与数据结构，含英文详解；本章先读与「SSH 与免密登录」「进程管理」相关的部分 |
| 2 | [Chalarangelo/30-seconds-of-code](https://github.com/Chalarangelo/30-seconds-of-code) | 129,384 | 全章 | 短小精悍的 JS/CSS/HTML 代码片段集，覆盖日常前端技巧；本章先读与「SSH 与免密登录」「进程管理」相关的部分 |
| 3 | [yangshun/front-end-interview-handbook](https://github.com/yangshun/front-end-interview-handbook) | 44,008 | 全章 | 前端面试手册：HTML/CSS/JS/浏览器/性能；本章先读与「SSH 与免密登录」「进程管理」相关的部分 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 尚硅谷 · JavaScript 基础与实战<br><sub>尚硅谷</sub> | [BV1YW411T7GX](https://www.bilibili.com/video/BV1YW411T7GX/) | 全章 | 主线：语法与类型 → 函数与作用域 → 原型与 this → DOM/BOM → ES6+ → 异步与 Promise；看完回 `ex01`（Dockerfile 静态检查器）核对 |
| 2 | 黑马程序员 · AJAX + Node.js + webpack<br><sub>黑马程序员</sub> | [BV1MN411y7pw](https://www.bilibili.com/video/BV1MN411y7pw/) | §2.1 镜像分层、写时复制与构建缓存 | 前后端怎么接上：HTTP 请求、跨域、接口约定、打包构建；看完回 `ex02`（镜像分层与构建缓存模拟）核对 |
| 3 | 黑马程序员 · React 零基础到实战<br><sub>黑马程序员</sub> | [BV1gh411U7JD](https://www.bilibili.com/video/BV1gh411U7JD/) | 全章 | 组件与 props/state、Hooks 的依赖数组、路由与状态管理，最后落到一个完整项目；看完回 `ex03`（多阶段构建体积估算）核对 |
| 4 | HTML + CSS + JS + Vue 前端全套<br><sub>web前端自学官方</sub> | [BV1jj411P7Yp](https://www.bilibili.com/video/BV1jj411P7Yp/) | 全章 | 补页面那一层：盒模型、Flex/Grid 布局、响应式；做「能看的界面」时按需查；看完回 `ex04`（.dockerignore 规则匹配器（）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《JavaScript 高级程序设计（第 4 版）》Zakas |
| 2 | 《深入浅出 Node.js》朴灵 |
| 3 | 《CSS 世界》张鑫旭 |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。

## 真题依据（真实可查，仅存元数据）
- GitHub 资源（见 `_manifest.json`）：trekhleb/javascript-algorithms（196855★）、Chalarangelo/30-seconds-of-code（129326★）、yangshun/front-end-interview-handbook（44008★）。
- LeetCode 题仅存元数据与链接，不搬运题面正文，详见 `exercises.json`。
- 参考书籍：《Docker 深入浅出》；规范与官方文档：The Twelve-Factor App、Docker 官方构建最佳实践、GitHub Actions 语法参考、systemd.exec/unit 手册、logrotate(8)、Kubernetes 探针文档。

## 验收标准
- 给定一个 Dockerfile，能逐条报出问题（latest 标签、apt 拆 RUN、ADD、COPY 先于依赖安装、多阶段缺 `--from`、最终阶段 root、缺 .dockerignore），本章 ex01 给出正反两组基准。
- 给定 Dockerfile 与文件变更集，能用分层哈希算出「改了哪些文件要重建几层」，并证明缓存是前缀链（ex02）。
- 给定多阶段构建的 base 与产物清单，能算出最终镜像层数与体积，并说明删除文件为什么不减小镜像（ex03）。
- 给定 `.dockerignore` 规则与文件清单，能判定每个文件被排除还是保留，含取反规则（ex04）。
- 给定 workflow YAML，能静态报出必需字段缺失、needs 引用不存在与依赖成环（ex05）。
- 给定 job 依赖图与工时，能输出拓扑顺序、最早开始/结束、makespan、关键路径与最大并行度（ex06）。
- 给定 compose 服务依赖，能给出分层启动顺序；依赖成环时必须报错而不是死等（ex07）。
- 给定探针序列与阈值，能算出状态迁移时刻与终态，并解释抖动为何不触发（ex08）。
- 给定逐窗口指标，能按「样本量 + 连续窗口」规则判定是否回滚，并区分单点尖峰与持续劣化（ex09）。
- 给定权重序列与健康指标，能算出金丝雀各级的新版本用户占比与中止点（ex10）。
- 给定配置项来源清单，能输出违规项与合规得分，并把硬编码密钥标为 critical（ex11）。
