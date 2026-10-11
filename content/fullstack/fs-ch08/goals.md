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


## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Node.js 全套入门教程 | [视频](https://www.bilibili.com/video/BV1a34y167AZ/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Vue3 全家桶（张天禹） | [视频](https://www.bilibili.com/video/BV1Zy4y1K7SH/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · React 全家桶 | [视频](https://www.bilibili.com/video/BV1wy4y1D7JT/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · HTML5+CSS3 前端零基础（李立超） | [视频](https://www.bilibili.com/video/BV14J4114768/) | 本学科配套视频，建议结合本章示例与习题观看 |

## 软前置（可选，不阻断学习）
- 无。本章 `prerequisites` 仅引用本学科已完成章节 fs-ch04。Linux 命令、Docker、GitHub Actions 均从零讲到够用为止，不假设读者有运维经验。

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
