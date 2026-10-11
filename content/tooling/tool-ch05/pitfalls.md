# 常见陷阱：Docker 镜像、容器与 Dockerfile

> 每条都是「命令能跑通、但结果或安全性是错的」类型。按「现象 → 根因 → 正确做法」组织。

1. **把容器当成轻量虚拟机，以为它有独立内核** —— 现象：在容器里 `uname -r` 看到的却是宿主内核版本，想装内核模块失败。根因：容器共享**宿主内核**，「镜像里的 OS」只是 rootfs（glibc、/bin、包管理器），不含内核。正确做法：需要不同内核/内核模块/强隔离时用虚拟机或 Kata/gVisor；不要把容器当作完整的独立机器。

2. **只设了 `memory.max` 却不管应用感知** —— 现象：容器内存上限 512MiB，JVM/Node 仍按宿主内存算堆，一启动就被 OOM-kill（退出码 137）。根因：cgroup 限制是**内核强制**的，但运行时默认读取的是宿主可见资源。正确做法：开启容器感知（JVM `UseContainerSupport`、`MaxRAMPercentage`；Node `--max-old-space-size`），并用 `docker stats` 观察实际用量。

3. **把数据写在容器可写层** —— 现象：`docker rm` 之后数据库数据全没了。根因：所有运行时写入都落在容器的 **overlay upper 层**，该层与容器同生共死。正确做法：数据库数据、上传文件、需要留存的日志一律挂 volume 或 bind mount；容器保持无状态。

4. **用 `RUN rm -rf` 想减小镜像体积** —— 现象：删了几百 MB 的编译期文件，`docker images` 显示体积没变。根因：删除来自只读层的文件只在 upper 生成一个 **whiteout 遮蔽**，下层数据依旧保存在镜像里。正确做法：用**多阶段构建**让这些文件根本不进入最终镜像；这是唯一能真正排除体积的方法。

5. **`COPY . .` 写在安装依赖之前** —— 现象：改一行源码就要重装全部依赖，构建从几秒变成几分钟。根因：`COPY . .` 的缓存键取决于**整个上下文的内容**，源码一变该层失效，其后所有层（含 `pip install`）全部重建。正确做法：先 `COPY requirements.txt .` → `RUN pip install` → 再 `COPY src/ .`，把变化频率低的指令放前面。

6. **`apt-get update` 与 `apt-get install` 分成两条 RUN** —— 现象：构建时装的包版本莫名其妙，某天突然失败。根因：`update` 那层的包索引被长期缓存，与后续的 `install` 处于不同时间点，产生不可复现的组合。正确做法：写在同一条 RUN：`apt-get update && apt-get install -y --no-install-recommends <pkg> && rm -rf /var/lib/apt/lists/*`。

7. **没有 `.dockerignore`** —— 现象：构建上下文几百 MB，改个日志文件就击穿整条缓存链。根因：`.git`、`node_modules`、`__pycache__`、本地日志全被送进上下文，任何文件变动都会让 `COPY . .` 失效。正确做法：必配 `.dockerignore`；注意 `*` 不跨 `/`，子目录要写 `**/*.log`。

8. **基础镜像用 `latest` 标签** —— 现象：同一份 Dockerfile 两周后构建出的镜像行为变了，甚至起不来。根因：`latest` 是浮动标签，上游一更新你的产物就变了，构建**不可复现**。正确做法：固定到具体版本（如 `python:3.13.1-slim`），更严格用 `@sha256:<digest>`。

9. **容器以 root 运行** —— 现象：镜像被扫出高危项，安全评审不过。根因：Dockerfile 不写 `USER` 就默认 root，容器逃逸时直接拿到宿主 root。正确做法：显式 `USER 10001`（或镜像自带的非 root 用户）；同时把 bind mount 的宿主目录属主与该 uid 对齐，否则会 Permission denied。

10. **把密钥写进 `ENV` / `ARG` 或 `COPY .env`** —— 现象：密钥泄漏到镜像仓库，轮换成本极高。根因：`ENV`/`ARG`/`COPY` 的内容会**永久留在镜像层**里，后面 `RUN rm` 也删不掉（只是 whiteout）。正确做法：运行时通过环境变量或密钥挂载注入；构建期用 BuildKit 的 `--secret`；`ARG` 只放非敏感构建参数。

11. **用 shell 形式写 `CMD python app.py`** —— 现象：`docker stop` 每次都要等 10 秒才停，滚动发布很慢。根因：shell 形式等于 `/bin/sh -c "python app.py"`，PID 1 是 sh，**SIGTERM 不会转发**给 python，只能等超时后 SIGKILL。正确做法：用 exec 形式的 JSON 数组：`CMD ["python", "app.py"]`，或 `ENTRYPOINT ["python"]` + `CMD ["app.py"]`。

12. **搞反 CMD 与 ENTRYPOINT 的覆盖关系** —— 现象：`docker run img --help` 没有按预期透传给应用，而是被当成一条命令执行失败。根因：没有 ENTRYPOINT 时，run 的尾部参数会**整体替换** CMD；只有存在 ENTRYPOINT 时，参数才是追加在 ENTRYPOINT 后面的。正确做法：用 `ENTRYPOINT ["/app/server"]` + `CMD ["--port", "8080"]` 固定可执行文件。

13. **滥用 `ADD`** —— 现象：一个本地 `config.ini` 用 `ADD` 拷进去后行为异常，或用 `ADD` 拉远程包却无法校验完整性。根因：`ADD` 会自动解压本地归档、支持远程 URL，语义比 `COPY` 宽且不可预测。正确做法：除「确实需要自动解压本地归档」外一律用 `COPY`；远程资源用 `RUN curl -fsSL ... ` 并校验校验和。

14. **以为 `EXPOSE` 会做端口映射** —— 现象：Dockerfile 写了 `EXPOSE 8080`，宿主 `curl localhost:8080` 却连不上。根因：`EXPOSE` 只是**文档性声明**，bridge 模式下容器有独立 netns 与私有 IP，必须 `-p 宿主端口:容器端口` 做 DNAT。正确做法：`docker run -p 8080:8080`；记住**宿主端口在前，容器端口在后**。

15. **把 `docker stop` 当成 `docker rm`** —— 现象：以为「停掉」就是删除，磁盘被一堆 exited 容器占满。根因：`stop` 只终止 PID 1，容器对象与可写层仍在（可 `docker start` 复活）；`rm` 才删除可写层。正确做法：定期清理 `docker container prune`；临时容器加 `--rm` 让退出即删。

16. **用 `docker commit` 交付镜像** —— 现象：线上跑着一个「不知道怎么来的」镜像，无法复现也无法审计。根因：`commit` 把可写层固化成新镜像，跳过了 Dockerfile 这一可评审、可版本化的环节。正确做法：任何交付都必须走 Dockerfile + 代码评审 + 镜像仓库，`commit` 仅用于临时救急快照。
