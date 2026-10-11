# Docker 基础：镜像、容器与 Dockerfile — 学习目标

## 一、本章定位

本章是「工程工具」学科第五章，开启 Docker 这条线（tool-ch06 继续讲 Compose 与部署实践）。
前面四章你掌握了 Linux 文件系统/进程模型与 Git 的版本控制模型；本章回答一个工程问题：
**如何把「应用 + 依赖 + 运行环境」打包成一个可复制、可版本化、到处都能跑起来的交付物**。
理解分层与缓存之后，Dockerfile 的每一行指令都不再是咒语，而是「往只读层栈里加一层」或
「改一次元数据」的确定性动作。

- **先修**：无硬前置（Docker 线首章，本线可独立起步）；tool-ch01/02 的进程与权限直觉有助于理解隔离。
- **衔接**：tool-ch06（Compose 与部署）建立在本章的镜像、数据卷、网络与健康检查之上。
- **面试权重**：★★★★★ —— 容器 vs 虚拟机、镜像分层与写时复制、CMD 与 ENTRYPOINT、
  构建缓存与多阶段构建、数据卷生命周期，是后端/SRE/云原生方向的必考题。

## 二、学习目标

学完本章，你应当能够：

1. **讲清容器的隔离原理**：namespace 隔离「视图」（mount/pid/net/ipc/uts/user 六类），
   cgroup 限制「用量」（cpu/memory/pids/io）；容器共享宿主内核、虚拟机有独立 Guest OS，
   由此推出两者在启动速度与体积上的量级差异。
2. **画出镜像的分层结构**：镜像是若干只读层的栈，每层一个内容摘要（digest）；
   联合文件系统 overlayfs 用 lower/upper/merged/work 把多层拼成一个视图；
   写时复制（CoW）保证镜像层永不被改动，删除靠 whiteout 遮蔽。
3. **区分镜像与容器**：镜像是只读模板（类），容器是镜像的运行实例（对象）；
   容器在镜像之上加一个**可写层**，`docker rm` 之后可写层随之消失——持久化必须挂卷。
4. **熟用生命周期命令**：`run`/`start`/`exec`/`logs`/`stop`/`rm` 各自的语义与副作用，
   能说清 `stop`（SIGTERM→超时 SIGKILL）与 `rm`（删可写层）的差别。
5. **写对 Dockerfile**：`FROM`/`RUN`/`COPY`/`ADD`/`ENV`/`ARG`/`EXPOSE`/`CMD`/`ENTRYPOINT`/
   `WORKDIR`/`USER`/`HEALTHCHECK` 各自的作用；**CMD 与 ENTRYPOINT 的组合规则**、
   **COPY 与 ADD 的取舍**。
6. **解释构建缓存并按它组织指令**：缓存键由「父层 + 指令内容（COPY 还要算文件内容）」决定，
   一旦某层失效其后全部重建；因此**依赖先于源码**。能判出 `COPY . .` 反模式的代价。
7. **用多阶段构建瘦身**：把编译器/SDK/包缓存留在中间阶段，只 `COPY --from` 产物；
   能估算最终镜像体积与降幅，并知道 `RUN rm -rf` 减不了体积的原因。
8. **掌握体积优化与安全基线**：alpine/distroless、合并 RUN、清理包缓存、`.dockerignore`、
   非 root 运行、HEALTHCHECK 与能力裁剪。

## 三、能力验收标准

| 层级 | 标准 | 检验方式 |
|---|---|---|
| 记忆 | 能默写出六类 namespace 与四条 cgroup 限流维度 | 习题 choice |
| 理解 | 给一段 Dockerfile 推断缓存命中/失效的层号 | 习题 output |
| 应用 | 用 Python 复算层 digest、模拟构建缓存与 overlayfs | examples 实跑 13 个 |
| 分析 | 能定位「改一行源码就要重装全部依赖」的根因 | pitfalls 第 5/6 条 |
| 评价 | 能论证「为什么数据不能写在容器可写层」 | interview 第 4 题 |

## 四、常见认知误区（先破后立）

1. **「容器是一个轻量虚拟机」** —— 错。容器是**被 namespace + cgroup 约束的进程**，
   没有独立内核；虚拟机才需要引导一份 Guest OS。
2. **「镜像是一个大文件」** —— 错。镜像是**只读层的有序栈**，层与层之间靠内容摘要寻址，
   可以跨镜像共享（examples/ex03 实测两个镜像复用同一批层）。
3. **「在 Dockerfile 里 `RUN rm -rf` 大目录能减小镜像」** —— 错。删除只在可写层生成
   whiteout，下层数据依旧躺在镜像里；要靠**多阶段构建**把它挡在最终镜像之外。
4. **「容器里写的文件会随镜像保存」** —— 错。写操作全落在**容器可写层**，
   `docker rm` 即丢；要持久化必须挂 volume 或 bind mount。
5. **「`CMD` 和 `ENTRYPOINT` 差不多」** —— 错。ENTRYPOINT 定可执行文件、CMD 给默认参数，
   `docker run` 尾部参数替换的是 CMD 而非 ENTRYPOINT。

## 五、学习路径建议

1. 读 concept/01（隔离原理），用 examples/ex01~ex02 把 namespace/cgroup 与 VM 代价变成直觉。
2. 读 concept/02（分层与 overlayfs），用 examples/ex03~ex04 复算层 digest、观察 copy-up 与 whiteout。
3. 读 concept/03（生命周期/数据卷/网络），用 examples/ex12 判定卷保留与端口可达性。
4. 读 concept/04（Dockerfile 与缓存/瘦身），用 examples/ex05~ex11、ex13 跑解析器、
   缓存模拟器、反模式检查器与安全基线。
5. 做 exercises.json 的 coding 题，自测 interview.json，再用 project.json 交付一个
   Dockerfile 静态分析器。

## 六、与 GitHub 顶级资源的对接

- bregman-arie/devops-exercises（84k★）—— DevOps 练习题集，含 Docker 专项练习
- trimstray/the-book-of-secret-knowledge（248k★）—— 运维与工程工具知识合集
- jlevy/the-art-of-command-line（162k★）—— 命令行体系化进阶
- ohmyzsh/ohmyzsh（190k★）—— Shell 生产力框架
- 推荐读物：《Docker 技术入门与实战》、Docker 官方 Get Started 与 Dockerfile reference


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | 248407 | 运维与工程工具知识合集：Linux、网络、排障命令速查 |
| [ohmyzsh/ohmyzsh](https://github.com/ohmyzsh/ohmyzsh) | 190209 | Shell 生产力框架（工程效率的入门必装） |
| [jlevy/the-art-of-command-line](https://github.com/jlevy/the-art-of-command-line) | 162576 | 命令行艺术：Linux 命令的体系化进阶指南 |
| [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | 84793 | DevOps 练习题集：Linux/Docker/K8s/Git/CI 全覆盖 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 韩顺平 · 一周学会 Linux | [视频](https://www.bilibili.com/video/BV1Sv411r7vd/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · Linux 教程（千万级学习人次） | [视频](https://www.bilibili.com/video/BV1dW411M7xL/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 尚硅谷 · 5h 打通 Git 全套教程 | [视频](https://www.bilibili.com/video/BV1vy4y1s7k6/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 狂神说 · Docker 教程 | [视频](https://www.bilibili.com/video/BV1og4y1q7M4/) | 本学科配套视频，建议结合本章示例与习题观看 |
