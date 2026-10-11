# fs-ch08 易错点（Pitfalls）

1. **把 `apt-get update` 与 `apt-get install` 拆成两条 RUN** —— 缓存命中会让 update 层复用过期索引，install 层要么 404 要么装到旧版本，且 `rm -rf /var/lib/apt/lists/*` 也失去意义。✅ 写在同一 RUN：`RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*`；ex01 对拆分写法报 `apt_get_update_split_across_runs`。

2. **基础镜像用 `node:latest` 或不带 tag** —— 构建不可复现，同一 Dockerfile 昨天成功今天失败。✅ 固定到具体版本（`node:22.11-bookworm`）或直接固定 digest；ex01 对 `node:latest` 报 `base_image_latest:node:latest`。

3. **先 `COPY . .` 再 `RUN npm ci`（依赖安装顺序倒置）** —— 改一行源码就让「装依赖」这一最贵的层失效。✅ 先 `COPY package.json package-lock.json ./` → `RUN npm ci` → 再 `COPY . .`。ex02 实测：改 `src/app.js` 时 deps-first 重建 2 层且 `npm_ci_layer_rebuild=False`，反模式重建 3 层且 `npm_ci_layer_rebuild=True`。

4. **不写 `.dockerignore`** —— `COPY . .` 会把宿主的 `node_modules`、`.git`、`.env`、日志一起送进 build context 与镜像。✅ 用 `.dockerignore` 排除（ex04 实测 `node_modules/dist/.git/**/*.log/coverage/` 被排除）；注意取反规则 `!dist/keep.txt` 可以让某个被排除目录下的文件重新纳入（ex04 的 `negation_keeps_dist_keep_txt=True`）。

5. **用 `ADD` 代替 `COPY`** —— `ADD` 隐式解压 tar、支持 URL 下载，语义不唯一且难以预测构建结果。✅ 除非确实需要自动解压，一律用 `COPY`；ex01 报 `add_instruction_used`。

6. **以为 `RUN rm secret.env` 能把文件从镜像里删掉** —— 分层只增不减，删除只是在新层写了一条遮蔽记录，文件字节仍留在下方层，`docker save`/`docker history` 能捞出来。✅ 让敏感文件**一开始就不进任何层**：在构建上下文打包前用 `.dockerignore` 挡掉，或用构建期 secret 挂载（`--mount=type=secret`）。

7. **最终镜像以 root 运行** —— 容器内 root 叠加内核漏洞即逃逸面，且挂载宿主目录时可写任意宿主文件。✅ `USER node` 或 `USER 10001`（非 0）；ex01 对最终阶段无 `USER` 或 `USER root` 报 `final_stage_runs_as_root`。

8. **多阶段构建却没用 `COPY --from=`** —— 第二阶段又把宿主上下文整份拷了一遍，builder 白建、镜像没瘦下来。✅ `COPY --from=build /app/dist ./dist`；ex01 对多阶段但全文无 `--from=` 报 `multi_stage_without_from`。

9. **只写 `depends_on` 列表而不配 healthcheck** —— 列表语法只保证「已启动」不保证「已就绪」，api 会在 db 尚未接受连接时启动并崩溃，重启后自愈导致故障偶发。✅ 用长语法 + `condition: service_healthy`，并给依赖服务写 `healthcheck`（测 `pg_isready`、`redis-cli ping` 这类真实就绪判据）；ex07 实测分层 wave0=`cache,db`、wave1=`api,worker`、wave2=`gateway`。

10. **Compose 服务依赖成环** —— 拓扑序不存在，启动顺序无解，Compose 只能报错（或死等）。✅ 抽掉共享依赖或改为「启动后重试」而非硬依赖；ex07 对 `a→b→c→a` 报 `circular_dependency:a,b,c`。

11. **把配置与密钥硬编码进代码** —— 换环境要改代码重新构建；密钥会随 Git 历史永久存在，且已被推送到远端。✅ 外置到环境变量并在启动时 fail-fast 校验；密钥泄露的正确顺序是**先轮换密钥、再清理历史**，只删提交等于没止血。ex11 实测 8 项中 3 项违规、其中 2 项为 `VIOLATION_CRITICAL_HARDCODED_SECRET`。

12. **`rm` 了日志文件但磁盘空间没释放** —— 进程仍持有该文件的 fd，inode 未回收（`i_nlink=0` 但打开计数 > 0），空间只会在进程关闭 fd 后才归还。✅ 用 logrotate 的 `create + postrotate`（发信号让进程重开文件）或 `copytruncate`；排查用 `lsof +L1` 找带 `(deleted)` 的句柄。

13. **journald 不设容量上限** —— 二进制 journal 会把 `/var` 撑满，最终表现为服务写日志失败（`No space left on device`）。✅ 设 `SystemMaxUse=`，并定期 `journalctl --disk-usage` 监控、必要时 `journalctl --vacuum-size=500M`。

14. **容器里套 pm2 / supervisor** —— 容器的正确姿势是「一个进程在前台」；套一层进程管理器后，`docker stop` 的 SIGTERM 到达管理器而非工作进程，信号转发与僵尸回收都可能出问题，优雅停机失效后只能等 SIGKILL。✅ 容器里直接 `CMD ["node", "dist/server.js"]`，重启与扩缩交给编排层；裸机上才用 systemd/pm2。ex13 演示了 systemd 侧的对应能力（`Restart=on-failure` + `RestartSec=2` + `StartLimitBurst=3`，第 4 次启动被 `start-limit-hit` 熔断）。

15. **liveness 与 readiness 混用** —— 用 liveness 探测「数据库是否可用」，一次依赖抖动会让所有实例的 liveness 同时失败并集体重启，把秒级抖动放大成分钟级故障。✅ liveness 只探自身进程存活（如心跳计数器），readiness 才探依赖；慢启动用 `startupProbe` 而不是把 liveness 的初始延迟调很大。

16. **回滚只看单个窗口的指标** —— 单点尖峰就回滚会产生「发布-回滚」抖动，团队最后不敢发版；反过来只看平均值又会漏掉持续劣化。✅ 用「最小样本量 + 连续 N 个窗口越界」双条件；ex09 实测 `single_spike_then_ok` 不触发、`sustained_degradation` 在第 1 个窗口触发、`requests<200` 时跳过不下结论。

17. **金丝雀用随机分配而不是稳定哈希分桶** —— 同一用户会在两次请求间来回切版本，问题无法复现，会话与缓存也错乱。✅ 用稳定哈希（如 `crc32(user) % 100`）分桶；ex10 实测权重 5→25→50 时新版本用户数为 107→510→1007，集合具备嵌套性，且 `bucketing_is_stable=True`。

18. **CI 里让部署 job 与测试 job 并行** —— 测试没过就可能上线，等于取消了质量门。✅ 用 `needs:` 把 job 串成 DAG，并遵循「快速失败」顺序 lint → build → test → 镜像 → 部署；ex06 实测该 DAG 的 makespan 由关键路径 `lint->build->test->image->deploy`（15 分钟）决定，而非关键活动再优化也压不下来。

19. **workflow 里 `needs` 指向不存在的 job 或写成环** —— 前者在 GitHub 上直接报「依赖的 job 不存在」，后者（配合缓存/并发设置时）可能表现为永久排队，排查成本极高。✅ 提交前用静态校验器挡住；ex05 对拼错依赖报 `unknown_needs:deploy>buidl`、对环报 `cycle:build->test->build`，并同时检出 `missing_runs_on` 与 `missing_trigger`。
