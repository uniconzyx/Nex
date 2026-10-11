# fs-ch08 · 二、Docker 镜像、分层与构建优化

## 一、镜像分层、写时复制与构建缓存

**镜像**是一组只读层（layer）加一份元数据（entrypoint/cmd/env 等）；**容器**是「镜像 + 一个可写层」。Dockerfile 里每一条会改变文件系统的指令（`RUN`、`COPY`、`ADD`）产生一层；`ENV`、`WORKDIR`、`EXPOSE`、`USER`、`CMD` 这类只改元数据的指令不产生新层。

分层带来两个直接后果：

1. **层可共享**：不同镜像若前缀相同（同上一个 base），这些层只存一份。
2. **构建缓存是前缀链**：缓存按「父层 + 指令文本 + 该指令用到的上下文内容」匹配；某个匹配失败，**它之后的所有层都必须重建**。

本章 ex02 用分层哈希实测了这一点。基础文件内容固定为 `package.json=p1|package-lock.json=l1|src/app.js=a1|src/style.css=c1`：

```
=== deps_first (layers=6) ===
  change=src/app.js     cached=4 rebuilt=2 npm_ci_layer_rebuild=False
  change=package.json   cached=2 rebuilt=4 npm_ci_layer_rebuild=True
=== copy_all_first (layers=5) ===
  change=src/app.js     cached=2 rebuilt=3 npm_ci_layer_rebuild=True
  change=package.json   cached=2 rebuilt=3 npm_ci_layer_rebuild=True
=== judgement ===
source_edit_rebuilds_deps_first=2
source_edit_rebuilds_copy_all_first=3
cache_is_prefix_chain=True
```

关键读数：改一行源码，**deps-first 顺序只重建 2 层且 `npm ci` 层命中缓存**；而 `COPY . .` 在依赖安装之前的反模式要重建 3 层，**并且被迫重跑 `npm ci`**（`npm_ci_layer_rebuild=True`）。这就是「订单一次依赖安装」与「每次改代码都重装依赖」的差距。

### 🧑‍💻 程序员视角
- 标准顺序（本章 ex01 的 good 基准）：`FROM 固定 tag` → `WORKDIR` → `COPY package.json package-lock.json ./` → `RUN npm ci` → `COPY . .` → `RUN npm run build`。清单文件变动少、源码变动多，把变动少的放前面就是缓存策略的全部。
- 必须写 `.dockerignore`：ex04 实测 `node_modules`、`dist`、`.git`、`**/*.log`、`coverage/` 被排除，`!dist/keep.txt` 的取反规则把它保留下来。少了这一行，宿主机的 `node_modules`（可能是 macOS/Windows 平台的原生模块）会被拷进 Linux 镜像，出现「本地能跑、镜像里 `invalid ELF header`」。
- 事故画像：CI 不给 buildkit 缓存，也不挂载依赖缓存，每次构建都重新下载全部依赖，构建时间从 40 秒涨到 6 分钟；修复是复用 `--mount=type=cache` 或分层顺序 + registry 缓存。
- 排查动作：`docker history <image>` 看每层大小；`docker build --progress=plain` 看哪个 `CACHED` 断了；`dive` 之类工具能定位「哪一层带进了几百 MB 的无用文件」。

### 🎓 博士生视角
- 形式化：把镜像看成一个有序的层序列 $L_1,\dots,L_n$，容器视图是这些层按序叠加后的**联合挂载**（overlayfs 的 `lowerdir` 只读、`upperdir` 可写、`merged` 是视图）。读未修改文件直接命中下层，首次写触发 **copy-up**（把整文件复制到 upperdir 再改）——这解释了「容器里修改大文件很慢」。
- 内容寻址：层以其内容的哈希（digest）命名，因此相同内容的层天然去重；这也是「同一个 base 被一百个镜像共享」不占一百份空间的原因。
- 缓存匹配的键是**链式哈希**：`key_i = H(key_{i-1}, instruction_i, context_i)`。这个递推结构直接给出「前缀链」性质：一旦 `key_i` 变化，`key_{i+1}` 的输入也变化，于是其后全部失效。可证明「重建的层数 = 失效点之后的层数」。
- 为什么时间戳不是缓存键：如果用 mtime 参与，`COPY` 的缓存将永不稳定；Docker 因此在打包上下文时把 mtime 归一到固定值，使「内容相同即缓存命中」成立。这是为了让哈希成为纯粹的内容函数。

### 📚 考研者视角
- **无 408 直接考点**，但相关考纲概念可对照：**文件系统的层次结构与目录/索引节点**、**存储空间管理**（空闲块管理、位示图）、**文件共享与保护**。把「层」类比成「按序叠加的只读文件系统快照」，能与 inode/目录项的分层理解互相印证。
- **面试/笔试考点**：① 镜像与容器的区别（只读层栈 vs 加一个可写层）；② 为什么分层能共享（内容寻址 + 前缀相同即同层）；③ 为什么改了后面的指令前面的层还能命中（缓存按前缀链匹配）。
- **口径**：`COPY` 与 `ADD` 的区别是高频问法：`ADD` 额外支持 tar 自动解压与 URL 下载，因此语义不唯一；最佳实践是除非必须解压否则一律 `COPY`（ex01 会把 `ADD` 报为 `add_instruction_used`）。
- **易混点**：`ENV` / `WORKDIR` 不产生文件系统层但会改变后续层的执行环境，因此改变 `WORKDIR` 也会让后续 `COPY` 的缓存失效——「元数据指令不影响缓存」是错误说法。

## 二、多阶段构建与镜像瘦身

**多阶段构建**用多个 `FROM ... AS <name>` 描述多个阶段，只有**最后一个阶段**进入最终镜像；前面的阶段可以只作为「生产车间」，用 `COPY --from=<name> <src> <dst>` 把产物挑出来。

本章 ex03 用层数与体积做纯计算：

```
=== single_stage ===
  base=node:22-bookworm 380.0MB
  total_layers=5 image_size=963.0MB
=== multistage_builder (中间阶段，不进最终镜像) ===
  base=node:22-bookworm 380.0MB
  total_layers=5 image_size=963.0MB
  builder_stage_discarded=True
=== multistage_runtime (最终镜像) ===
  base=node:22-bookworm-slim 75.0MB
  + COPY --from=build /app/dist ./dist                   12.0MB
  + COPY --from=build /app/node_modules ./node_modules   60.0MB
  + ENV NODE_ENV=production                               0.0MB
  + USER node                                             0.0MB
  total_layers=5 image_size=147.0MB
saved_mb=816.0
size_reduction_pct=84.7
```

builder 阶段和单阶段镜像一样大（963MB），但它**不出现在最终镜像里**，最终镜像只有 147MB，降幅 84.7%，且 `build_toolchain_in_final=False`、`source_tree_in_final=False`。

### 🧑‍💻 程序员视角
- 瘦身清单：① 多阶段（把编译器、dev 依赖、源码树留在 builder）；② 用 `-slim`/`alpine`/`distroless` 减小 base；③ `apt-get install --no-install-recommends` 且在同一 `RUN` 里 `rm -rf /var/lib/apt/lists/*`；④ 合并 `RUN` 减少层数；⑤ `USER` 非 root；⑥ 固定 base tag 或 digest。
- **删除文件不能减小镜像**：`RUN rm -f /app/.env` 只在新的层里写一个 whiteout 记录，`.env` 的字节仍留在下方层，`docker save` 出来就能捞到。因此密钥绝不能进入 build context，必须靠 `.dockerignore` 在打包上下文之前挡掉。
- 事故画像：镜像里带着 `.env`（含数据库密码与第三方 key）推到了共有 registry；即便事后删文件重推，旧 tag 的层仍在 registry 上可被拉取。止血动作是**轮换全部密钥**，再清理与禁用旧 tag。
- 度量手段：`docker images` 看大小、`docker history` 看层、`trivy image`/`grype` 扫 CVE；把「镜像大小上限」写进 CI 断言能防回归。

### 🎓 博士生视角
- 分层只增不减是**单调性**结论：镜像体积 ≈ Σ 层字节。删除操作产生的是「遮蔽记录」而非回收，因此体积不会因 `rm` 下降。推论：任何「先拷进来再删掉」的做法都是假优化，唯一有效的做法是「让它一开始就不进任何层」。
- 层数与体积非单调：把 3 条 `RUN` 合成 1 条，层数减少但总字节几乎不变（少了少量元数据）；真正的体积来自**内容**而非层数。层数影响的是：pull 的并发粒度（层可并行下载）与缓存粒度（层越细，源码改动时能命中的前缀越长）。
- 多阶段构建的收益来源是**构建期依赖与运行期依赖的分离**：编译器、构建工具、dev 依赖只需在构建期存在，运行期只需产物与生产依赖。这本质上是「依赖闭包按阶段切分」，与静态链接/动态链接的取舍是同一类思想（把不必要的部分排除在交付物之外）。
- base 镜像选择影响的不只是体积：`alpine` 用 musl libc，与 glibc 预编译的原生模块二进制不兼容；`distroless` 去掉 shell 与包管理器，攻击面最小但排障只能靠外部工具。三者是「体积 / 兼容性 / 可排障性」的三角取舍。

### 📚 考研者视角
- **无 408 直接考点**，相关考纲概念：**文件的存储与分配**（连续/链接/索引分配）、**磁盘空间管理与压缩**。把「层」理解为「只读的分配单元快照」有助于理解为什么删除不回收。
- **面试考点**：① 多阶段构建解决了什么问题（构建期依赖不进运行镜像）；② 为什么 `RUN rm` 不能删掉敏感文件（分层只增不减）；③ 镜像怎么瘦身（多阶段 + slim base + 清缓存 + 合并 RUN）。
- **口径注意**：`--from=build` 里的 `build` 是**阶段别名**（`AS build` 声明的），不是镜像名；写成 `--from=build` 却只写了 `FROM node:22` 会让构建直接失败（ex01 的 `multi_stage_without_from` 规则对应这类配置错误）。
- **易混点**：`EXPOSE` 只是文档元数据，不发布端口；端口映射是运行时 `-p` 的事。把它当成「防火墙开洞」是常见误解。

## 三、容器的隔离边界与 .dockerignore

容器的隔离由两层机制叠加：**namespace** 决定「能看到什么」（PID、网络、挂载、UTS、IPC、user、cgroup 等命名空间），**cgroup**（v2 为统一层级）决定「能用多少」（CPU 权重与上限、内存上限、IO 限速）。容器与宿主机**共享同一个内核**，因此它不是虚拟机。

`.dockerignore` 在**打包 build context 之前**生效：它决定哪些文件根本不会被送到构建器，因此既能省带宽，也是「敏感文件不进镜像」的第一道闸门。本章 ex04 实测的规则集与结果：

```
patterns=node_modules **/*.log .git dist !dist/keep.txt *.md coverage/
=== excluded (7) === node_modules/left-pad/index.js, logs/app.log, logs/2026/app.log, .git/HEAD, dist/bundle.js, README.md, coverage/lcov.info
=== kept (4) === package.json, src/index.js, src/deep/nested/app.js, dist/keep.txt
star_does_not_cross_slash=True
```

### 🧑‍💻 程序员视角
- 选择判据：需要异构内核（Windows 容器）、特异内核模块、GPU 直通（部分场景）、更强隔离边界时用虚拟机；只要进程隔离与资源限额够用就用容器。绝大多数 Web 服务属于后者。
- 安全基线：非 root `USER`、`--read-only` 根文件系统 + 显式挂载可写目录、`--cap-drop=ALL` 按需加回、seccomp/AppArmor 策略、`--security-opt no-new-privileges`；**绝不把 `/var/run/docker.sock` 挂进容器**——那等于把宿主机 root 权限交出去。
- 事故画像：容器内以 root 运行 + 挂载了宿主目录 + 内核存在提权漏洞，三者叠加导致逃逸。修复顺序是「能不给 root 就不给」优先于「打补丁」，因为前者消除整类风险。
- 排查动作：`docker inspect` 看 `HostConfig` 的 `Privileged`/`CapAdd`/`ReadonlyRootfs`；`docker stats` 与 cgroup 文件看实际用量；进程被杀先查内存上限（退出码 137）。

### 🎓 博士生视角
- namespace 与 cgroup 是**正交**的两组机制：前者改的是「进程看到的资源视图」（例如自己的 PID 从 1 开始、看不到宿主进程），后者改的是「资源的分配额度」。只做 namespace 不做 cgroup 会得到「看不见但仍抢光资源」的隔离假象。
- user namespace 的 uid 映射是理解容器安全的关键：容器内 uid 0 可映射到宿主的普通 uid，于是「容器内 root」未必是「宿主 root」。但若以 `--privileged` 运行或映射为宿主 root，这条保护立即失效。
- 共享内核决定了**隔离边界的位置**：容器的边界是内核的权限检查，一旦内核有漏洞，容器逃逸的成本远低于虚拟机逃逸（VM 的边界是 hypervisor）。这是「隔离强度 vs 启动/密度成本」的必然取舍。
- overlayfs 的 copy-up 让「可写层」看似透明，但它带来的性能特征是「首次写放大整文件」；同时 lowerdir 只读意味着你不能通过容器内修改去影响其他容器（共享层不可变），这是镜像共享安全性的基础。

### 📚 考研者视角
- **408 操作系统考点密集**：进程与线程、**进程地址空间与虚拟内存**、**文件系统**（目录、inode、挂载）、**进程调度**、**信号机制**、**死锁与资源分配**。容器只是用这些机制「组合」出的隔离，考点本身仍在 OS 原理。
- **易混点（高频）**：namespace 隔离「视图」（PID/网络/挂载等），cgroup 限制「配额」（CPU/内存/IO）。把 cgroup 说成隔离机制、或把 namespace 说成限流机制，都是概念性错误。
- **口径**：容器共享宿主内核，启动是「创建进程」的代价（毫秒级）；虚拟机虚拟化整套硬件，需 guest 内核，启动是「引导操作系统」的代价（秒级）。答题时把「启动速度差异」归因到内核是否共享。
- **面试考点**：容器与虚拟机的区别、Docker 的实现原理（namespace + cgroup + 联合文件系统）、镜像与容器的关系。
