# 分支策略、提交规范与仓库卫生
> 本节目标：从「个人用 Git」升级到「团队用 Git」。每个主题按三视角解析。

---

## 一、分支策略选型（Git Flow / GitHub Flow / Trunk Based）与 PR 流程

三种主流策略的本质差异是**长期分支数量**与**发布单元**：

| 策略 | 长期分支 | 发布单元 | 适用信号 | 典型失败模式 |
|---|---|---|---|---|
| Git Flow | 2（main + develop） | release 分支冻结后发布 | 多版本并行维护（1.x / 2.x）、有发布窗口 | develop 长期不合回 main，两个「真相」越走越远 |
| GitHub Flow | 1（main，始终可部署） | 合入即发布 | 单一可部署主干、PR 驱动的小团队 | 合入过快、缺少回归，线上质量波动 |
| Trunk Based | 1（trunk，分支寿命 < 1~2 天） | 主干始终可发布，靠特性开关控制暴露 | 每日多次发布、CI/测试完善、feature flag 成熟 | 没有 feature flag 与测试护栏时，主干持续红 |

决策可以做成规则表：**需要多版本维护 → Git Flow；发布频率≥每天且 CI 完善 → Trunk Based；
有固定发布窗口且团队较大 → Git Flow；其余默认 GitHub Flow**。
`examples/ex13` 用规则表驱动，输入团队规模 / 发布频率 / 是否多版本维护 / CI 覆盖，输出推荐策略与理由。

**PR / Code Review 流程**是策略的地基，与选择哪种策略无关：

1. 短命分支 + 单一职责（一个 PR 只做一件事，通常 ≤ 400 行改动）；
2. 描述写清「为什么要改」与「怎么验证」，关联 issue；
3. CI 全绿（构建 / 单测 / 静态检查 / 覆盖门禁）才允许 Review；
4. Review 用建议而非指责的语气，区分 `nit`（可选）、`must fix`（阻塞）、`question`；
5. Squash merge / Rebase merge / Merge commit 三种合入方式要团队统一；
6. 合入后删掉源分支，保持仓库清爽。

配套的**提交信息规范（Conventional Commits）**：

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]   # BREAKING CHANGE: xxx / Refs #123
```

`type` 取 `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`；
语义化版本推导：**fix → PATCH，feat → MINOR，含 `!` 或 `BREAKING CHANGE` footer → MAJOR**。
`examples/ex11` 实现了正则校验器，并给出合法/非法各六组用例。

### 🧑‍💻 程序员视角
- **策略不是信仰，是取舍**：Git Flow 的 develop 分支一旦超过两周没合回 main，就等于给自己制造第二个主干；
  多数团队真正需要的是 GitHub Flow + tag + release note。
- **短命分支是唯一普适建议**：无论哪种策略，分支寿命越长，合并成本与语义冲突概率越高；建议 feature 分支 < 3 天。
- **CI 是策略的兑现者**：Trunk Based 依赖「主干随时绿」，没有完善的测试护栏就别上；反之 Git Flow 的 release 冻结能换取回归时间。
- **PR 质量公式**：小改动 + 明确描述 + 自动化验证 = 高 Review 效率。大而全的 PR 会把 Review 变成走过场（LGTM 文化）。
- **落地建议**：用 commitlint + husky 做本地校验，CI 再做一次；CHANGELOG 由 conventional-changelog 自动生成，
  版本号由 semantic-release 依据 commit 自动推导。

### 🎓 博士生视角
- 分支策略的本质是**集成频率与反馈延迟的权衡**：合并越频繁，单次冲突越小（集成成本近似 O(改动量)），
  但要求每次集成都有可信的质量门（测试、静态分析）。这是持续集成论文（Fowler 2000）的原始论点。
- 为什么 mainline + feature flag 能替代 release 分支：把「发布」与「部署」解耦——代码可以先进主干并被部署，
  但功能由运行时开关控制是否对用户可见，于是「冻结/决策」从代码管理层上移到**配置与运行时**层。
- Conventional Commits 的价值在于**机器可读的历史**：因为 type 是受控词表、scope 是结构化字段、
  breaking 是可检索标记，CHANGELOG / 版本号 / 影响面分析才能被自动化——这是把「人类写作习惯」变成「可被解析器消费的协议」。
- 复杂度视角：评审成本的实践上限约在一次 400 行（Cisco 的经典数据：>500 行/小时的评审缺陷发现率骤降），
  所以 PR 大小限制不是洁癖，而是**信息论上的注意力约束**。

### 📚 考研者视角
- 本节不属 408 纲内；迁移考点是**决策表/规则引擎**与**语义化版本号（MAJOR.MINOR.PATCH）的推导规则**，
  后者属于软件工程（也有可能作为软考/复试笔试的选择题）。
- 易错点辨析：
  - 「Git Flow 一定比 GitHub Flow 高级」——错，复杂度要与环境匹配，多数 Web 团队用后者更合适；
  - 「提交信息随便写，反正看代码」——错，type 决定版本号与自动化发布，`feat` 与 `fix` 都区分不清就没有可机器读的历史；
  - 「Squash 会丢信息」——Squash 丢的是**中间过程**，保留的是最终语义；要不要 Squash 取决于团队是否要保留开发轨迹。
- 常见笔试/面试问法：「三种分支策略的区别与选型依据」「`v1.2.3` 各段什么时候递增」。

---

## 二、仓库卫生：`.gitignore`、`.gitattributes` 与 Git LFS

三份配置解决三类完全不同的问题：

| 文件 | 解决什么 | 典型内容 |
|---|---|---|
| `.gitignore` | 哪些**未跟踪**文件不进版本库 | `*.log`、`build/`、`/local.env`、`!keep.example` |
| `.gitattributes` | 这些文件在**检出/入库时如何处理** | `* text=auto eol=lf`、`*.png binary`、`*.md diff=markdown`、`*.sh text eol=lf` |
| Git LFS | **大文件不进对象库**，只存指针 | `git lfs track "*.psd"` → 仓库里只留 130 字节指针文件 |

`.gitignore` 的规则语义（`examples/ex12` 实现了完整匹配器）：

1. 空行与 `#` 注释忽略；**逐行依次匹配，最后命中的规则生效**（所以 `!` 必须写在忽略规则之后）；
2. 行首 `/` 锚定该文件所在目录（根目录则只在根生效）；行尾 `/` 表示**只匹配目录**；
3. `*` 不跨 `/`，`?` 匹配单字符，`**/` 跨任意层，`a/**/b` 匹配零或多层；
4. **一旦某目录被排除，Git 不再递归其内部，`!` 无法救回它的子文件**（经典坑：
   `build/` + `!build/keep.txt` 无效，应写成 `build/*` + `!build/keep.txt`）；
5. 只对**未跟踪**文件生效——已经被 track 的文件要先用 `git rm --cached` 摘掉。

大文件与二进制：一旦把 500 MB 的压缩包提交进历史，`git rm` 之后 clone 依然巨大（旧 blob 还在历史里），
必须用 `git filter-repo` / BFG 重写历史清理，并改用 LFS 或外部制品库托管。

### 🧑‍💻 程序员视角
- **新仓库第一步**：先写 `.gitignore` 与 `.gitattributes`，再写第一行代码。事后补 ignore 对已跟踪文件无效，
  还得 `git rm --cached` 逐个清理，代价高得多。
- **跨平台换行**：
  Windows + Linux 混编项目务必设 `core.autocrlf=false` 并在 `.gitattributes` 强制 `* text=auto eol=lf`，
  否则会出现「整个文件被 diff 标红」的幽灵改动；CI 里再加一条 `.gitattributes` 合规检查。
- **LFS 的成本**：仓库瘦了，但每个协作者、每条 CI 都要能连上 LFS 服务器；
  二进制更新还会污染 status/diff，务必 `git lfs prune` 并设置合理的 `--locksverify` 与带宽限流。
  这里的关键是：忽略规则不等于安全手段——密钥一旦进过历史，必须**轮换密钥**再用 filter-repo 清理；
  上线前接 gitleaks / pre-commit 钩子做扫描。

### 🎓 博士生视角
- `.gitattributes` 的 `text=auto` 是「检出/入库时的**规范化变换**」：
  入库时把 CRLF 规范成 LF（保证内容寻址唯一 → 同一 blob SHA），检出时再按平台转回。
  若不做规范化，同一个逻辑文件在不同平台上会算出**不同的 blob**，DAG 上会出现无意义的差异。
- LFS 的指针文件内容是 `version oid size` 三行（约 130 字节的 ASCII），真正字节通过
  `.gitattributes` 里 `filter=lfs` 指定的 **clean/smudge 过滤器**在 add/checkout 时搬运——
  即 Git 的过滤器流水线把「内容」和「存储」解耦，这与把 index 与 worktree 解耦是同一种设计哲学。
- 为什么 `git rm` 清不掉体积：仓库大小 = **对象库（历史全部 blob）**的大小，当前 tree 不含某 blob 不代表历史提交不含它；
  只有重写历史（filter-repo）让这些提交不可达并触发 `gc --prune` 才会真正释放。
- 可以证明的判定：某个路径是否被忽略，等价于在一个**有序规则序列**上做「最后一次命中胜出」的判定，
  再与「祖先目录是否已被排除」做与或组合——这正是 examples/ex12 的实现口径。

### 📚 考研者视角
- 本节不属 408 纲内；迁移考点是 **glob 匹配 / 有限状态自动机**（`*`、`?`、`**` 可视为受限正则），
  以及**内容的规范化与哈希一致性**（可与「编码一致性」类比）。
- 易错点辨析：
  - 「`.gitignore` 里写了就一定会忽略」——错，已跟踪文件不受约束，需 `git rm --cached`；
  - 「`build/keep.txt` 用 `!` 能救回来」——错，父目录被排除后 Git 不再递归；
  - 「`git rm` 能删掉大文件占的空间」——错，要重写历史才释放；
  - 「LFS 只是把文件放别处」——严格说是**指针入库 + 过滤器搬运**，仓库里保留的可 repo 部分是 ASCII 指针。
- 笔试问法示例：「如何彻底清理仓库中误提交的大文件/密钥」——答：轮换密钥 + `git filter-repo` 重写 + 强推 + 通知所有协作者克隆。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 落地与事故预防 | 策略按集成频率选型、PR 六步、commitlint/semantic-release、三份配置的职责边界与 CRLF/LFS 坑 |
| 🎓 博士生 | 原理与设计哲学 | 集成频率 vs 反馈延迟、feature flag 解耦部署与发布、机器可读历史、clean/smudge 过滤器、规范化保证 blob 唯一 |
| 📚 考研者 | 易错口径与迁移考点 | 三种策略选型依据、SemVer 推导、glob/自动机类比、ignore 三陷阱与大文件清理流程 |
