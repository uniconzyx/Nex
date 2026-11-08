# 贡献指南（Nex）

感谢参与 Nex 多学科学习内容的建设。本仓库内容由**脚本化门禁**保障质量，提交前请确保通过
`server/scripts/` 下的校验工具。以下规则为**硬性约束**，违反会被 CI / 门禁拦截。

## 1. 学科与章节结构

- 13 个学科目录：`content/<subject>/`，其中 `subject ∈`
  `cpp, clang, java, python, database, fullstack, spring, middleware, bigdata,
  fundamentals, tooling, data, ai`。
- 章节目录：`content/<subject>/<id>/`，其中 C/C++/clang 用 `cpp-chNN` / `clang-uNN`，
  其余用 `<subject>-chNN`。
- `clang` 的元数据挂在 `content/cpp/_manifest.json` 的 `clang_module.units[]`，**无独立 manifest**。
- 母清单：`content/cpp/_manifest.json`（含 `clang_module.units`）。其余学科各有
  `<subject>_manifest.json`。门禁以 manifest 的 `chapters[]` 作为"规划单元"分母。

## 2. 每章 7 类文件（缺一不可）

```
content/<subject>/<id>/
├── goals.md            # 学习目标 + 软前置 + 【GitHub 资源】+【B 站教程】双来源段
├── concept/*.md        # ≥3 个概念文件，每个内嵌三视角
├── pitfalls.md         # ≥3 条（行首必须是编号 1. / - ）
├── exercises.json      # ≥5 道（choice / fix_error / output / coding 混合）
├── examples/*.json     # ≥10 条，字段见下
├── interview.json      # ≥3 条面试题
└── project.json        # ≥1 个项目任务
```

规范详见 `content/_template/README.md`。

### examples/*.json 字段
`code_lang` / `code_std` / `stdin` / `expected_output` / `code` 必填；`expected_output`
必须是**真实编译器/解释器实测产物，禁止编造**。

### exercises.json 真题字段
```json
{
  "source": "self | leetcode | nowcoder",
  "source_ref": "LC-1 / NC-101",
  "external_url": "https://leetcode.cn/problems/two-sum/"
}
```
`source_ref` 与 `external_url` **必须写在题项顶层**（写在 `answer` 里会被门禁判缺失）。

## 3. 三视角（每个 concept/*.md 必含）

每个概念文件必须内嵌三段，三者**互补不重复**：

- `### 🧑‍💻 程序员视角`：工程决策树与排查顺序。
- `### 🎓 博士生视角`：第一性原理与形式化依据。
- `### 📚 考研者视角`：408 考点记忆锚点。

> **标记码点必须带零宽连接符（ZWJ）**：程序员 `🧑‍💻` = `\U0001F9D1\u200D\U0001F4BB`，
> 博士生 `🎓`、考研者 `📚` 同理。脚本里一律用**显式码点构造**，不要手打 emoji
> （不带 ZWJ 的变体渲染几乎一样但字节不同，会长期掩盖"三视角缺失"）。
> 新章节一次写到位，勿事后 retrofit。

## 4. 学习来源：GitHub（star 最高）+ B 站 双来源（强制）

**每章 `goals.md` 必须同时包含 GitHub 真实代码源与 B 站真实教程源两段。**

- **GitHub 资源**：所有 `resources` 必须指向 GitHub **star 最高**仓库，star 用 API 实时抓取，
  刷新用 `server/scripts/sync_github_resources.py`（幂等）。**勿手写 star、勿凭记忆填 repo**。
- **B 站教程**：每条必须是真实 UP 主 + 真实 BV 号 / 视频链接（不要用占位链接）。
- `goals.md` 注入锚点：优先插在 `## 软前置` / `## 学习路径建议` / `## 学习路径` 之前，否则追加文件尾。

门禁会扫描每章 `goals.md` 是否含「GitHub 资源」与「bilibili / B站」两段。

## 5. 学习线独立性与三元服务

- 每学科「独立且完整」，同时服务**考研 / 学习 / 就业**三类用户。
- 首章 `prerequisites` **必须为空**；跨学科先修只写 `soft_prerequisites`
  （如 `[{"id":"py-ch01","note":"若已掌握可跳过"}]`），并在 `goals.md` 加
  「## 软前置（可选，不阻断学习）」。`prerequisites` 只引用本线章节。
- 考研 = 三视角 + 八股 ≥10；学习 = goals/concept/pitfalls/examples 齐全；
  就业 = 八股 + interview ≥3 + project ≥1 + GitHub 资源。

## 6. 合规红线

- **LeetCode / 牛客：只存元数据 + 链接，不存题面正文**（`source` / `source_ref` / `external_url`）。
- 示例禁止机器相关量进 `expected_output`：墙钟时间、纳秒耗时、内存地址。性能类改用操作计数 /
  指针跳转次数 / 布尔判据（如 `加速比>100: True`）。
- Python 示例禁用 `hash(str)`（PYTHONHASHSEED 随机化）→ 用 `zlib.crc32`。
- C 示例禁止把「有副作用的调用」与「它写入的变量」放进同一 `printf` 参数列表
  （求值顺序未定义 → 假通过）。先算后打印。
- 含 `timeit` 的示例只输出布尔判据，绝不写具体毫秒。

## 7. 密钥与本地环境安全

- `server/.env` 含 `DEEPSEEK_API_KEY` 等敏感信息，**已被 `.gitignore` 排除，绝不提交**。
- 贡献者请复制 `server/.env.example` 为 `server/.env` 并填入自己的密钥。
- CI / 发布构建通过 GitHub Secrets 注入，不在仓库内留明文密钥。
- `scratch/`、`build/`、`dist/`、发布二进制（`*.exe` / `*.apk`）均在 `.gitignore` 中。

## 8. 提交流程

```bash
# 0) 一次性准备审计环境（新建 venv / 换机器时必须做）
#    审计会把 examples 里的代码真正跑一遍；内容侧大量示例用 numpy/pandas，
#    漏装会在 audit_correctness 里堆出成片「缺 Python 依赖」，那是环境问题不是内容问题。
python -m pip install -r server/requirements-audit.txt

# 1) 校验（必须全绿）
python server/scripts/validate_content.py      # 门禁：章节结构 / 三视角 / 八股模块
python scripts/audit_sources.py                # 来源门禁：GitHub+B站 双来源与章节级锚点
python scripts/audit_source_anchor.py          # 锚点门禁：§x.y 编号不越界 + 锚点标题须与真实 ## 标题重合
python scripts/audit_repo_align.py              # 仓库-笔记错位门禁：github_notes 代码路径须命中本章登记仓库（行与仓库错配）
python scripts/audit_correctness.py --all --skip-net   # 实跑 examples/习题，stdout 逐字节比对
python scripts/check_md_outputs.py             # 正文 ```text 输出块必须在 examples 里有出处
python scripts/audit_depth.py --min-grade C    # 深度分级（A/B/C），C 级不阻塞但要记账
python server/scripts/verify_examples.py       # 示例真实回放
python server/scripts/verify_exercises.py      # 题集健康度
python server/scripts/audit_learning_lines.py  # 学习线审计（可选）

# 2) 刷新 GitHub star（如改动 resources）
python server/scripts/sync_github_resources.py

# 3) 更新 manifest 状态
python server/scripts/sync_manifest_status.py
python server/scripts/sync_dart_manifest.py    # 同步前端 content_manifest.dart
python server/scripts/gen_exercise_bundle.py   # 改过 exercises.json 必须重跑，产出 exercises.ts / clangUnits.ts
python scripts/gen_chapter_content.py          # 改过 pitfalls.md 必须重跑，产出 chapterContent.ts
python scripts/gen_concept_viz.py              # 改过 concept/exercises/pitfalls/interview 必重跑，产出 frontend/src/data/viz/*.ts

# 4) 提交（不要提交 .env / 大二进制）
git add content/<subject>/<id> ...
git commit -m "content(<subject>): 新增 <id> 三视角 + 双来源"
```

> 门禁报错先怀疑门禁自己。历史上 `audit_correctness` 的 72 条「运行失败」全是 venv 缺 numpy，
> 13 条「输出不一致」全是 `expected_output` 里残留的孤立 `\r`（CRLF 被截断），
> 内容本身没有一处错。排查顺序：先确认依赖与数据形态，再改内容。

> 凡要经 Bash 执行的生成脚本，请先 `Write` 落 `.py` 再执行（避免反引号命令替换吞掉内容）。
> 跑完务必人眼核对关键数字，不能只看退出码 0。

**非 Python 示例的四层验证**（`scripts/verify_softlang.py`，由 `audit_correctness.py`
的 else 分支调用）：`executed` = SQL 真在 sqlite3 执行，且代码与声明输出有关联；
`structural` = 声明式 / 说明型示例做语法结构校验（YAML 解析、HTML 标签闭合、
CSS / CMake 括号、SQL 分词配对）；`env_blocked` = 本机安全策略禁止启动 bash
（Python 调 bash 会拉起 WSL 启动器被拦），只做 heredoc / 引号静态配对；
`unverified` = 确实无法验证。**这三层都不冒充 stdout 逐字符比对** —— 历史
`expected_output` 格式并不统一（DDL 回显有无、分隔符、小数位都不一致），
强行逐字符只会制造假失败。仅在 POSIX 且显式 `NEX_SOFTLANG_ALLOW_BASH=1`
时 bash 才实跑并逐字符比对。审计输出按四层分别计数，别把「已结构校验」
读成「已实跑通过」。YAML 结构校验依赖 `PyYAML`（已列入
`server/requirements-audit.txt`）；换机器漏装时，该示例会明确落到
`unverified` 并在汇总里点名，既不误报 FAIL，也不冒充「已结构校验」。

**concept 结构速览图**：`scripts/add_concept_diagrams.py`（幂等）给缺 `text`
围栏代码块的 concept 文件补图，节点取自文件自身真实的三级标题与该节代码语言。
它不新增任何 #/##/### 标题、不写「输出 / 运行结果 / stdout」字样，因此不影响
`audit_depth` 的 h3 计数、`audit_source_anchor` 的标题锚点，也不会被
`check_md_outputs.py` 当成「正文抄录的程序输出」。

**输出卫生判据（弱信号不猜字符串，读实跑证据）**：`audit_correctness.py` 里
`BAD_OUTPUT_FAIL = ['Traceback', 'bash:', 'command not found']` 是强信号，直接
FAIL；`BAD_OUTPUT_WARN = ['error:', 'Error:']` 原先是**无条件 warn**。但它是子串
匹配，命中的几乎全是 `TypeError:` / `ValueError:` / `MergeError:` 这类**异常类名**。
2026-11-08 逐条核过全量审计剩下的 22 条 warn：20 个 Python + 2 个 JS，全部是
try/except 捕获异常后正常打印、或 argparse / git / docker 报错文案样例；`code`
里 18 条含该字样，另 4 条是异常类名由 pandas / argparse 动态生成（不在源码字面
里）；**没有一条是「把程序崩溃输出抄进 expected_output」**。

判据因此改为**后置判定**：能实跑的示例（C/C++/Python/Java/JS）在 stdout 逐字符
比对通过 + 退出码符合声明后，`error:` 必是程序正常打印，只计入
`[info] 输出卫生：N 个…` 统计，不占 warn 名额；只有走 `verify_softlang` 分层
验证、**没有 stdout 实跑证据**的示例（bash / sql / css / …）才保留 warn 要求
人工复核。既不再制造 22 条噪声 warn 让人麻木，也不是「凡含 Error: 一律放行」。
回归用例 `scripts/verify_output_hygiene.py` 直接调 `check_examples`，七个用例
锁死两类判据（实跑反例静默 / 无实跑证据仍 warn / Traceback 仍 FAIL /
干净示例无记录 / 末尾换行两侧省略均按口径通过 / **中间行不同仍 FAIL**），8/8。

**输出口径：末尾换行不参与判定（254 条 info 不是待办）**：全量审计汇总里的
「N 个示例末尾换行写法不同」曾被当成历史噪声想批量统一。2026-11-08 抽样实跑
查明它**不是数据缺陷**：`expected_output` 写的是「人在终端看到的内容」，而末尾
换行由语言运行时决定 —— Python `print` / Java `println` / JS `console.log` 必带
一个 `\n`，C `printf("a=2 b=1")` / `System.out.print` 则完全不带。全库 1842 个
示例里 1410 个写 1 个末尾换行、431 个不写、1 个写 2 个。`verify_examples.py`
本就是「按行包含匹配、忽略空行」，`scripts/audit_reexam_code.py` 也明写
「行尾空白不计，末尾换行不计」，`docs/Unfinished-Backlog-2026-10-31.md` 早已把
它定性为「主动降级为 info 的噪声治理」。

因此处理方式是把**口径显式化**，不是改 254 个文件：比对前先剥掉两侧末尾换行，
剩余内容仍**严格逐字符比对**，中间任何一行不同照样 FAIL；汇总按方向拆成
「声明侧省略 N / 运行侧省略 M」，只作可观测性统计。**不要为了把数字清零去批量
补 `expected_output` 的末尾换行** —— 既覆盖不全所有运行时，也会让声明与
`verify_examples.py` 的口径脱节。`verify_output_hygiene.py` 的 E/F/G 三个用例
就是用来锁死这条边界的（尤其 G：防止有人把归一写成「一律放行」）。

另修 `--warn-out`：原先 `rep.warns` 为空时**不写文件**，判据修好后旧清单还留在
磁盘上（实测残留着上一轮 4 条旧措辞），会让人误以为告警还在。现在无条件写，
归零时清空并在汇总打印「本次为空」。

---

## 9. 交互微游戏（sandbox / debug）管线

`content/_handmade/labs.json` 是唯一数据源，但**由两类脚本分别维护**：

| 生产者 | 拥有章节 | 语义 |
|---|---|---|
| `scripts/_author_labs.py` | cpp / fundamentals / ml / ai / database 共 68 章 | 作者源，`--check` 只比对自己拥有的章节 |
| `scripts/inject_batch{3,4,5,6,7,8,9,10,11,12,13}_sandbox.py` | 其余章节（tooling / middleware / bigdata / data / ai / ml / fundamentals / agent / fullstack / discrete-math / python / cpp / spring / clang / java …） | 幂等合并：只替换本章 sandbox，保留 debug 等其它玩法 |

> ⚠️ 不要用「整份重写」的方式改 labs.json。`_author_labs.py` 现在只覆盖自己拥有的章、
> 其余原样保留；在此之前的版本会静默抹掉外部批次的几十章手工模块。
>
> ⚠️ 注入脚本也**不能**直接 `chapters[key] = [mod]`：那会抹掉同章里其它 kind 的模块
> （cpp 那 11 章原本各带一个 debug，batch7 首版就这么吞掉过 11 个）。正确写法是
> `kept = [m for m in chapters.get(key, []) if m["kind"] != "sandbox"]; chapters[key] = [mod] + kept`。
> 守门里的 `audit_handmade_labs` 只统计模块总数，**不会因为丢模块而报错**——所以
> 每批注入后必须核对自己的「保留其它模块 N 个」输出，别只看 `通过`。

改完按顺序跑（每一步都必须绿）：

```bash
python scripts/inject_batchN_sandbox.py        # 或 scripts/_author_labs.py（改了作者源）
python scripts/audit_handmade_labs.py -v       # 结构 + 「这一关真能通关」穷举验证
python scripts/solve_sandbox.py --all          # 产出 frontend/scripts/sandbox_solutions.json
python scripts/gen_interactive.py              # 并入 interactive.json + 前端 TS
./frontend/node_modules/.bin/tsc --noEmit -p frontend/tsconfig.json
node frontend/scripts/verify_labs_sandbox13.mjs http://localhost:5230   # 真机把旋钮拖到通关
```

四条写法纪律（违反任一条都会变成「假游戏」）：

1. **判据必须带下限**（`nodes >= 10000`、`clauses >= 100`）。只有上限时，穷举求解读会退化成
   「所有旋钮拉到最小值」，玩家一拖就通关，等于没玩。
2. **既定事实用 `==` 锁死**，且该值必须落在参数网格上（`min + i*step`）；网格取不到会让判据
   恒假，报成「这一关不可能通关」。
3. **默认值要写成「真实事故配置」**：一打开就红，但红得有道理（如 10 万顶点用邻接矩阵 = 38GB）。
4. `if(c,a,b)` 在两套求值器里都是**急切求值**（两个分支都先算），除法要么保证除数恒非零，
   要么不要放进 `if` 分支；`fmt` 只认 `int` / `fix2` / `pct`。

## 10. 双端原生封装与图标

`deploy/package/` 把 `web-preview/` 的两套 UI 封成 EXE / APK；默认
`tauri.conf.json`、`dist/`、`frontend/` 一律不动（`--config` 增量合并）。

```bash
python deploy/package/design_icons.py   # 设计/生成全套图标（需 Pillow）
python deploy/package/prepare.py        # 制备 staging + 同步 Android 图标 + 生成构建脚本
deploy/package/build-exe.cmd            # Windows EXE
deploy/package/build-apk.cmd            # Android arm64 APK
```

图标唯一色源是 `frontend/src/styles/liquidglass.css` 的 `.km-app{}`；设计母题为
**冰晶六边形 + 凯喵头像 + 掌握度圆弧**。`design_icons.py` 同时产出 `src-tauri/icons/`、
`web-preview/favicon-64.png`、`deploy/launcher/nex.ico` 与 Android 五档 mipmap，
并把 Android 资源**镜像到 `deploy/package/icons/android/`**——因为 `src-tauri/gen/`
整目录被 `.gitignore` 忽略，`prepare.py` 每次会从镜像同步回去，保证 clone 后重编
不会变回 Tauri 默认图标。`prepare.py` 末尾有自检，防止构建脚本模板被改坏。

三个已踩过的坑（改封装前先读）：

1. `build.rs` 必须保留 `cargo:rerun-if-changed=icons/icon.ico`：否则只换图标不重跑
   Windows 资源编译，Cargo 复用旧 `libresource.a`，EXE 提取出来仍是旧占位图。
2. Windows 未开开发者模式时，Tauri CLI 写进 `jniLibs` 的 `libnex.so` 是 **0 字节**，
   照此打出的 APK 会白屏；必须手动拷真 `.so` 并用
   `gradlew assembleRelease -x rustBuild*` 重打包。
3. 签名用 `java -jar apksigner.jar`，不要从 Git Bash 调 `.bat` 包装脚本（被安全策略拦）。

以下四项是**本机封装验收脚本**（`scratch/` 整体 gitignore，不在版本库里），
由主人在打出 EXE / APK 后本机执行；CI 只做源级校验，不假装验过二进制：
`scratch/verify_nex_package.cjs`（内嵌站点 14/14）、
`scratch/verify_nex_csp.cjs`（等效 CSP 7/7）、
`scratch/verify_conn_dialog.cjs`（连接设置两端 25/25）、
`scratch/verify_nex_package.py`（产物静态与签名 20/20）、
`deploy/package/verify_icons.py`（图标真进包 + so 非 0 字节，10/10）。

**CI 与源级防回归**：`.github/workflows/ci.yml` 的 `package-assets` job 跑
`deploy/package/verify_icon_sources.py`（10/10）：重跑 `design_icons.py` 后与库内
资产做**像素级**幂等比对（不用字节比对 —— Pillow / zlib 版本会改 PNG 编码字节，
但像素不该变），再核对三处 Windows 图标同源、非旧占位图、`build.rs` 的
`rerun-if-changed` 声明与 `prepare.py` 模板关键串；比对后会把库内资产原样恢复，
不留 diff。`design_icons.py::write_vectors()` 会自建 `drawable*/` 目录，保证
干净 checkout（无 `gen/`）也能重跑。

EXE / APK 是 `.gitignore` 的本机产物，CI 上**没有二进制**，所以 job 只在产物
确实存在时才条件执行完整的 `verify_icons.py`；否则明确打印「由本机守门」，
不假装验过。EXE 图标色差、APK 启动图标逐像素、arm64 `libnex.so` 非 0 字节
这三项，永远以本机 `verify_icons.py` 为准。

## 10.1 真应用封装路线（与设计稿包并存，2026-11-08 新增）

`prepare.py` 封的是 `web-preview/` 两套静态设计稿（页面 title 自带「UI 设计稿」，
进度数字写死、交互多为 toast 提示），**不是功能完整的学习应用**。功能完整的 App
在 `frontend/`（章节 / 题库 / 判题 / 实验 / 9 大学科 / 进度同步），默认
`tauri.conf.json` 的 `frontendDist: ../dist` 本来就是为它准备的。现另开一条独立
路线，两条路线产物名不同、互不覆盖，**现有设计稿包与其验收结论原样保留**：

```bash
python deploy/package/prepare_app.py   # 生成 staging + 两份增量配置 + 两个构建脚本
deploy/package/build-app-exe.cmd       # -> release/nex-shell/Nex-App-Desktop-1.0.exe
deploy/package/build-app-apk.cmd       # -> release/nex-shell/Nex-App-Mobile-1.0-arm64.apk
```

`prepare_app.py` 让 vite 把当前构建输出到干净的 `deploy/package/app/`（gitignore）。
不能直接把 `frontendDist` 指回 `../dist`：`vite.config.ts` 的 `emptyOutDir=false`
让 dist/ 累积了历次哈希产物（实测 207 文件 / 195MB），整目录塞进 Tauri 会把包
撑爆。生成器从 `index.html` 沿 JS/CSS 引用走闭包体检，并用「>120 文件或 >40MB」
挡住误拷；Pyodide 那几个文件不在 HTML 引用图上，另按白名单单独验。增量配置覆盖
`build.frontendDist` / 构建钩子 / 窗口标题 / `app.security.csp`。`beforeBuildCommand`
置空，避免再跑一次 `npm run build` 去重写 dist/。

**判题运行时是这条路最容易漏的两件事**（都曾在封装后静默失效，别删）：

1. CSP 必须比默认多一条 `'wasm-unsafe-eval'`。判题用 Pyodide（WASM），
   Chromium 在 `script-src 'self'` 下拒绝 `WebAssembly.instantiateStreaming`，
   现象是点「提交判题」后永远停在「准备解释器…」，控制台**不报** CSP 违规、
   静态资源也不 404，极难定位。该 source 只放开 wasm 编译，不等于
   `unsafe-eval`，不引入 JS eval。
2. 解释器不能走 CDN。`frontend/public/pyodide/`（5 文件 / 11.7MB，由
   `scripts/fetch_pyodide.py` 从 npm tarball 取，版本与 `protocol.ts` 的
   `PYODIDE_VERSION` 对齐）由 vite 原样拷进包根，`DEFAULT_INDEX_URL` 指同源
   `/pyodide/`。原先指 `cdn.jsdelivr.net`，封装后既被 CSP 拦、离线又必然失败。
   桌面端另需 `src-tauri/binaries/go-judge.exe` 随 EXE 落到同级 `binaries/`
   （`build-app-exe.cmd` 已自动拷）；Rust `detect_go_judge()` 只认这个位置，
   漏了会静默降级成 mock 直跑，而不是真编译。

冷启动会显示登录网关，点「先逛逛 · 本地模式」即可离线使用（进度存本机）。
**离线能用的边界**：章节 / 题库 / 实验沙箱 / 图表 / 装扮 / 签到 / 成就 /
每日试炼 / 本地进度 / 双端判题都自洽；AI 对话、Agent 陪练的模型洞察、账号注册
登录与云端进度同步仍需 FastAPI 后端（页面会明确提示「未登录」「未连接」）。

出包前验收：`verify_app_staging.cjs` 以真实 CSP + 无后端实跑两端（12/12）、
`audit_app_features.cjs` 遍历两端 23 个路由（46 页 0 白屏 / 0 报错）、
`verify_app_judge.cjs` 点真「提交判题」跑 `print(6*7)` 拿 2/2 通过（7/7，
同时断言 0 外部 CDN 请求）。源级门禁 `scripts/verify_app_package_sources.py`
11/11 会守住「Pyodide 同源 / SDK 版本一致 / 五件资源齐备 / go-judge 落盘 /
双端 CSP / 生成器幂等」；`prepare_app.py` 末尾自检还会断言两个构建脚本的输出名
**不含**设计稿包文件名，防止误覆盖已验收产物。

**内容防回归（`content-health` job）**：跑 `server/scripts/verify_exercises.py`
（字段 / 平台链接 / Python 参考代码 `compile()` / `meta` 自洽），再重跑三个生成器
—— `server/scripts/gen_exercise_bundle.py`、`scripts/gen_chapter_content.py`、
`scripts/gen_concept_viz.py` —— 并核四类入库产物
（`exercises.ts` / `clangUnits.ts` / `chapterContent.ts` / `viz/*.ts`）未漂移。
两层缺一不可：检查器只读 `content/`，2026-11-07 前入库的 `exercises.ts` 一度比
`content/` **少 25 道题**（加题后漏跑生成器）、`discrete-math.ts` 只含 dm-ch01
一章，`verify_exercises.py` 对此完全无感，全部 167 章照样报「通过」。

判据用 `git status --porcelain -- <产物路径>` 而非 `git diff --exit-code`：
后者只看 tracked 文件的**修改**，抓不到「新增学科生成了新 `.ts` 却没入库」这种
untracked 情况。三个生成器均零第三方依赖，CI 干净 checkout 即可直接跑。

跨平台换行前提（2026-11-08 用干净 clone 实测）：`.gitattributes` 是
`* text=auto eol=lf`，CI 是 Linux，`os.linesep` 为 `\n`，生成器写出与 checkout
同为 LF，天然一致；本机 Windows 的 `Path.write_text()` 写 CRLF，主仓库因工作区
本来就是 CRLF 且 `autocrlf=true` 也判为一致。但**在刚 clone 出来的目录里**直接
重跑生成器会看到三个产物变 `M` —— 字节级比对证明归一成 LF 后内容完全相同，
纯粹是换行差异，不是内容漂移。本地模拟 CI 时须按 `eol=lf` 归一再判 status，
否则是 Windows 特有的假红。`viz/data.js` 是 `.gitignore` 的本机产物，不参与比对。

**判据自测（第 2 个 step）**：门禁逻辑自己也会被改坏，所以新加一层反向验证，
三个脚本纯标准库、零第三方依赖，且排在「生成物同步」之前（要求基线干净）：
`scripts/verify_output_hygiene.py`（输出判据 8/8）、
`scripts/verify_ci_idempotency_gate.py`（临时制造 modified 与 untracked 两类漂移，
确认都被拦下，2/2，跑完自动恢复无残留）、
`scripts/verify_exercise_meta_checker.py`（自造 5 类 meta 漂移 + 真实章节对照，
11/11）。已用 `git clone` 出的干净 checkout 完整模拟过该 job 的全部 step，均 rc=0。

同批还收掉 13 章历史欠账：11 处 `meta.note` 的**总题数与「基础题 N」分解同时滞后**
（加题只改 items 没改 note）、2 处参考代码语法错误（`clang-u07-q7` 把换行写成
字面量 `/n`；`ml-ch04` 生成器表达式少一个右括号）。改 `exercises.json` 后记得
重跑生成器，`git diff` 里应只出现预期字段。

**检查器盲区（同批补上）**：`verify_exercises.py` 原先只查 `meta.note` 里的
「N 题」，全库复核又查出 **17 处 `meta.count` 漂移**（写 6 实为 7，多在
agent / ml 线）、**5 处 note 分解漂移**（ai-ch09 / cpp-ch10 / fund-ch17），
另有 5 章无 `note`。`validate_content.py`、`audit_correctness.py`、
`gen_exercise_bundle.py` **都不读** `meta.count` / 分解数，所以这些漂移能长期
躲过全部门禁。现已把 `meta.count` 与「基础题 N / 算法题 M」分解纳入第 ⑤ 类
检查（`meta 自洽`），并修平 21 处客观数字；`scripts/verify_exercise_meta_checker.py`
在临时目录自造 5 类漂移（count / 总题数 / 基础题分解 / 算法题分解 / 非数字）做
反向验证，并用真实章节对照防误报，11/11。该脚本零外部依赖，已随判据自测进 CI。
无 `note` 的 5 章属正常（非必填），不强行编造描述文字。`ml-ch04` 的描述性
题数（「3 道概念题 + 3 道算法实践题」）按实际 4 基础 + 3 算法同步为 4 道。
