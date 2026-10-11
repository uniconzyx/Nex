# Dockerfile：指令语义、构建缓存与镜像瘦身
> 本节目标：把 Dockerfile 从「照抄模板」变成可推理的确定性过程。每个主题按 🧑‍💻 程序员 / 🎓 博士生 / 📚 考研者 三视角解析。

---

## 一、指令语义：CMD vs ENTRYPOINT、COPY vs ADD

| 指令 | 作用 |
|---|---|
| `FROM` | 指定基础镜像（尽量固定版本或 digest，不用 latest） |
| `RUN` | 在构建期执行命令，产生**新的一层**（唯一会「做事」的指令） |
| `COPY` | 把构建上下文的文件拷进镜像 |
| `ADD` | 同 COPY，额外支持**本地归档自动解压**与**远程 URL 下载** |
| `ENV` / `ARG` | 运行时环境变量 / **构建期**变量（ARG 不会进入最终镜像） |
| `EXPOSE` | 声明端口（**只是文档**，真正的映射靠 `docker run -p`） |
| `WORKDIR` | 设置后续指令的工作目录（会自动创建） |
| `USER` | 切换后续指令与运行时的用户（非 root 的关键） |
| `HEALTHCHECK` | 声明健康检查命令 |
| `CMD` | 容器启动的**默认命令/默认参数**（可被 `docker run` 覆盖） |
| `ENTRYPOINT` | 容器启动的**可执行文件**（不被 run 参数覆盖） |

**CMD 与 ENTRYPOINT 的组合规则**（examples/ex10 实测 8 组用例）：

1. 有 ENTRYPOINT（exec 形式）时，CMD 的内容**整体作为参数**追加在其后；
2. ENTRYPOINT 为 **shell 形式**时，CMD **被完全忽略**，且 PID 1 是 `/bin/sh`；
3. 没有 ENTRYPOINT 时，CMD 就是完整命令，`docker run <img> --help` 会**整体替换** CMD；
4. `docker run` 的尾部参数替换的是 **CMD**，不是 ENTRYPOINT。

**COPY 与 ADD 的取舍**（examples/ex11）：**除「确实需要自动解压本地归档」外一律用 COPY**。
ADD 对远程 URL 是反模式——无法校验完整性，还会让缓存悄悄失效；应改用
`RUN curl -fsSL <url> | tar ...` 并校验校验和。

### 🧑‍💻 程序员视角
- 推荐写法：`ENTRYPOINT ["/app/server"]` + `CMD ["--port", "8080"]`，
  这样 `docker run img --help` 能优雅透传给应用，又不会让人误改可执行文件。
- 血泪坑：用 shell 形式的 `CMD python app.py`，PID 1 变成 `/bin/sh`，
  **SIGTERM 不会转给 python**，`docker stop` 每次都等 10 秒超时。一律用 exec 形式的 JSON 数组。
- `ARG` 与 `ENV` 的选择：只在构建期需要的（如版本号、代理）用 `ARG`；
  **不要把密钥写进 `ENV`/`ARG`**——它们会留在镜像层里，任何拿到镜像的人都能 `docker history` 看到。
- `EXPOSE` 不映射端口，新手常以为写了它宿主就能访问——必须 `docker run -p`。

### 🎓 博士生视角
- 为什么分出 CMD 与 ENTRYPOINT：把「**不变的可执行文件**」与「**可变的默认参数**」解耦。
  ENTRYPOINT 是镜像作者定的契约，CMD 是给使用者的默认值，二者在运行时拼接成 argv。
- shell 形式与 exec 形式的本质差异：shell 形式等于 `exec("/bin/sh", ["-c", cmd])`，
  多引入一个进程，且 **exec 不会自动转发信号**——这是「PID 1 收不到 SIGTERM」的根因。
- `RUN` 是唯一在**构建期**执行、且产出文件系统改动的指令；`CMD`/`ENTRYPOINT` 是
  **运行时**元数据，不产生新数据，只写进镜像配置。

### 📚 考研者视角
- Docker 不在 408 考纲，但这是**工程/面试笔试**的高频标准化考点。
- 标准问法与口径：
  - 「CMD 和 ENTRYPOINT 的区别？」——**ENTRYPOINT 定可执行文件、不可被 run 参数覆盖；
    CMD 是默认参数、会被 run 参数整体替换；ENTRYPOINT 为 shell 形式时 CMD 被忽略。**
  - 「COPY 和 ADD 的区别？」——**ADD 多了「本地归档自动解压」和「远程 URL 下载」两个能力，
    其余场景都应用 COPY。**
- 易错点：把 `EXPOSE` 当成端口映射；把 `ARG` 当成运行时变量（**ARG 不进最终镜像**）。

---

## 二、构建缓存与多阶段构建

**缓存规则**（examples/ex06 实测）：

1. 每层的缓存键 = **父层键 + 本指令键**，父层失效则其后**全部**重建；
2. `RUN` 的键是**命令行字符串**；`COPY`/`ADD` 的键是**被拷贝文件的内容摘要**；
3. 所以：**只要被 COPY 的任一文件变了，该层之后的所有层都白干。**

由此得到 Dockerfile 第一原则：**把变化频率低的指令放前面，变化频率高的放后面**
（依赖先于源码）。examples/ex06 实测：只改一行源码时——

- 正例（`COPY requirements.txt` → `pip install` → `COPY src/`）：重建 **2 层**，不需重装依赖；
- 反例（`COPY . .` → `pip install`）：重建 **3 层**，且**必须重装全部依赖**。

**多阶段构建**：用多个 `FROM` 把「构建期」与「运行期」分开，最终镜像只 `COPY --from` 产物。
examples/ex07 实测：单阶段 1555.6MB → 多阶段 14.0MB，**降幅 99.1%**。

### 🧑‍💻 程序员视角
- 指令顺序的工程模板：
  `FROM` → 系统依赖（apt）→ `COPY 依赖清单` → 安装依赖 → `COPY 源码` → `USER` → `CMD`。
- `.dockerignore` 是缓存的保险丝：少了它，`.git`、日志、`node_modules` 全进构建上下文，
  **改任何一个日志文件都会击穿 `COPY . .` 的缓存**（examples/ex09 实测）。
- CI 提速：把依赖层单独做一个 base 镜像，或给 `docker build` 配 `--cache-from` 复用远端缓存。
- 多阶段还能顺带满足安全：运行阶段换 distroless（**连 shell 都没有**），攻击面大幅缩小。

### 🎓 博士生视角
- 缓存的本质是**增量计算**：把构建过程建模为函数序列 `f_n ∘ ... ∘ f_1(inputs)`，
  若某步的输入未变且前序结果未变，其结果可直接复用。Docker 的缓存键正是这条链的哈希。
- 为什么 `COPY` 的键要用**文件内容**而不是 mtime/路径：内容才是真正影响产物的输入；
  用 mtime 会导致「内容没变却重建」，用路径则会漏掉内容变化。
- 多阶段构建的形式化：最终镜像 = `runtime_base ∪ {被显式 COPY 的产物}`。
  中间阶段的层不在最终镜像的层集合里，因此**构建期工具链的体积被完全排除**，
  这是唯一能真正「删除」大文件的方法（而不是用 whiteout 遮蔽）。

### 📚 考研者视角
- 对应考点：这是**工程实践**考点，笔试常以「给出 Dockerfile 判断哪些层会命中缓存」的形式出现。
- 标准口径：
  - 「为什么要先 COPY 依赖清单再装依赖？」——**依赖清单变化频率远低于源码，
    放在前面可以让「只改源码」的构建跳过最耗时的依赖安装层。**
  - 「多阶段构建解决了什么问题？」——**把构建期工具链挡在最终镜像之外，显著减小体积。**
- 易错点：以为「把 `RUN` 拆细可以提高缓存命中率」——拆细确实提高粒度，
  但每层都有元数据开销，且**任何一层失效都会让后面全失效**，需要在粒度与层数间权衡。

---

## 三、体积优化与安全基线

**体积优化清单**：

1. 选小基础镜像：`alpine`（~5MB，musl libc）或 `distroless`（~2MB，无 shell）；
   musl 与 glibc 的行为差异（DNS 解析、locale）要先验证。
2. 合并 `RUN` 并清理缓存：
   `apt-get update && apt-get install -y --no-install-recommends <pkg> && rm -rf /var/lib/apt/lists/*`；
   `pip install --no-cache-dir`；`npm ci --omit=dev && npm cache clean --force`。
3. 必配 `.dockerignore`：排除 `.git`、`node_modules`、`__pycache__`、日志、本地产物。
4. 多阶段构建，只带产物。

**安全基线**（examples/ex13 实测合规率）：非 root 运行（显式 `USER`）、
基础镜像固定版本或 digest、声明 `HEALTHCHECK`、存在 `.dockerignore`、
清理包管理器缓存、镜像内无明文密钥；运行时再加 `--cap-drop=ALL`、
`--security-opt no-new-privileges`、`--read-only` + tmpfs。

### 🧑‍💻 程序员视角
- 事故案例：`apt-get update` 与 `apt-get install` 写在**两条 RUN** 里，
  update 那层被缓存了半年，某天突然装到一个已被撤销/改名的包，构建在半夜失败且难以复现。
  **必须写在同一条 RUN。**
- 密钥泄漏是最贵的事故：`ENV API_TOKEN=xxx` 或 `COPY .env .` 会把密钥**永久留在镜像层**，
  即使后面 `RUN rm` 也删不掉（whiteout 不删数据）。正确做法：运行时通过环境变量/
  密钥挂载注入，构建期用 BuildKit 的 `--secret`。
- 非 root 是硬性要求：容器逃逸时 root 的危害远大于普通用户；
  注意 bind mount 的宿主目录属主要与非 root uid 对齐，否则 Permission denied。
- 体积优化的收益不止是存储：镜像越小，拉取越快、冷启动越快、CVE 扫描面越小。

### 🎓 博士生视角
- `apt-get update && install` 同 RUN 的必要性，本质是**缓存的时间一致性问题**：
  包索引是一个「随时间变化的外部状态」，缓存它相当于把一个 T 时刻的快照固化进镜像，
  与 T+n 时刻的 install 组合会产生**不可复现的构建**。合并到一条 RUN 只保证同一次构建内一致，
  更彻底的做法是固定版本 + 固定基础镜像 digest。
- 为什么 distroless 更安全：它只有应用与最小运行时，**没有 shell、没有包管理器**，
  攻击者即使拿到 RCE 也缺少可用的落地工具（无 curl、无 sh）。
- 最小权限原理的实例化：`--cap-drop=ALL` + `--read-only` + 非 root 三者叠加，
  把「容器内可写」「可提权」「有特权能力」三条攻击路径同时收紧。

### 📚 考研者视角
- 这是**面试笔试**的工程安全考点，常问「如何写出一个安全、体积小的 Dockerfile」。
- 标准答题要点（可速记）：
  **固定版本基础镜像 → 合并 RUN 且同 RUN 内 update+install+清理 → 依赖先于源码 →
  配 .dockerignore → 多阶段构建 → USER 非 root → HEALTHCHECK → 密钥运行时注入。**
- 易错点：以为 `RUN rm` 能删掉密钥（**不能，层里还在**）；
  以为 `alpine` 一定更好（musl 与 glibc 有行为差异，需验证）。

## 三视角小结

| 视角 | 一句话结论 |
|---|---|
| 程序员 | 依赖先于源码、.dockerignore 必配、多阶段瘦身、非 root、密钥不进层 |
| 博士生 | 缓存是增量计算的哈希链；多阶段是唯一能真正排除构建期体积的方法 |
| 考研者 | 面试高频：CMD/ENTRYPOINT 组合、COPY vs ADD、缓存失效层号、Dockerfile 八条优化 |
