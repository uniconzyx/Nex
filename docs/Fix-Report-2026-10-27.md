# 修复验收报告 — 2026-10-27

按「① 选择题 → ② 判题用例 → ③ agent/ml 并入 ai → ④ 覆盖率与文档」的顺序执行完毕。
本报告只写**实跑能复现的数字**，每个数字都注明用哪个脚本验证、怎么回滚。

---

## 0. 一句话结论

| 项 | 修复前 | 修复后 |
|---|---|---|
| 选择题缺陷（缺选项 / 答案不在选项里） | **111 道** | **0 道**（321 题全通过） |
| 编程题「名义可判」 | 39 道（其中**只有 2 道是真能判的**） | 30 道（**全部实跑验证**） |
| agent/ml 章节在 UI 里可见 | **不可见**（24 章 / 144 题无入口） | 全部并入 `ai`，`ai` 共 **207 题** |
| `_coverage.json` | 过期：136 章 / 130 完整 / 8 个「缺失单元」 | 重算：138 章 / **138 完整** / **0 缺失** |
| 前端类型检查 | — | `tsc --noEmit` **exit 0** |

**最重要的一条不是"数字变好了"，而是"发现原来的可判率是假的"。** 详见第 2 节。

---

## 1. 选择题：111 道缺陷 → 0

### 三种真实病因（不是同一种）

| 病因 | 数量 | 例子 |
|---|---|---|
| 选项**内联写在 `content_md` 正文里**，没有 `options` 数组 | 83 | `"…正确的是：\n\nA. 引用可以不初始化\nB. …"` |
| 答案用字符串 / 别的键名，不是 `["A"]` | 103 | `{"correct": "A"}`、`{"value": "C"}`、`{"choice": "C"}`、`{"correct": [1]}` |
| 选项**从来没写过**（只有题干 + 答案） | 29 | `python/py-ch05` 那批；`cpp/cpp-ch20` 整章 |
| 一题塞两问、答案列了 5 个字母但只有 4 个选项 | 1 | `tooling/tool-ch05` CMD/ENTRYPOINT |

### 处理方式

- `scripts/fix_choice_options.py`：自动解析正文里的选项行（**跳过 ``` 围栏代码块**，
  否则 makefile 里的 `C := $(D)` 会被误认成选项 C）、规范化答案键名与字母大小写。
  - 结果：解析出 81 道选项、规范化 103 道答案
- `scripts/patch_missing_options.py`：29 道**逐题手写 4 个干扰项**（AI 写不了的部分，
  按题意人工编写，正确答案字母与原 `answer.correct` 保持一致）。
  - `tooling q3` 拆成 `q3`（第一问）+ `q3b`（第二问），内容不丢、答案干净
- 两个脚本都 `--restore` 可还原，备份在 `content/_backup_choice_fix/`、`content/_backup_missing_options/`

### 验收

```
选择题 321 道，不合格 0 道（每道都有 >=2 个选项，且答案字母都在选项集合内）
```

---

## 2. 判题用例：从「假可判」到「真可判」——本轮最关键的发现

### 2.1 先说结论

原来看起来有 **39 道**题带 `test_cases`，实测**只有 2 道**能真判。剩下的 37 道是这样的：

```jsonc
// database/db-ch01，LeetCode 175
{"input": "schema 与样例数据见 external_url",
 "expected_output": "见 external_url（Person LEFT JOIN Address 结果）"}
```

```java
// java/java-ch01，两数之和的 reference_code
public static void main(String[] args) {
    int[] r = twoSum(new int[]{2, 7, 11, 15}, 9);  // 参数写死，从不读 args
    System.out.println(r[0] + " " + r[1]);
}
```

判题契约是「完整程序 + stdin → 比对 stdout」（`server/app/services/judge0.py:62`）。
学生提交代码后，判题器会把 `schema 与样例数据见 external_url` 这串**中文文本**
当作 stdin 喂进去 —— 程序要么忽略它（永远同一行输出，判成假通过），
要么解析失败（假失败）。**这比没有用例更糟：它给出错误的反馈。**

### 2.2 硬判据核查（不看描述，只看代码）

对每道带用例的题，检查 `answer.reference_code` 里有没有真正读 stdin 的调用：

| 语言 | 判据 |
|---|---|
| python | `sys.stdin` / `input(` |
| c | `scanf` / `fgets(..., stdin)` / `getchar` / `read(0` |
| cpp | `scanf` / `std::cin` / `cin >>` / `getline(cin` |
| java | `Scanner` / `System.in` / `BufferedReader` |
| sql | 恒为否（SQL 要连真库执行，本来就不走 stdin） |

结果：**67 道带用例里 30 道读 stdin，37 道不读。**

### 2.3 处理

- `scripts/purge_fake_cases.py`：37 道伪用例的 `test_cases` 移入 `samples`
  （保留作为题面样例阅读，不参与判题），并写入 `judge_note` 说明为什么不能自动判分。
- `scripts/add_judge_cases.py`：新补 **28 道**真可判题，做法是
  1. 把参考实现改写成「读 stdin / 写 stdout 的完整程序」；
  2. 题面追加统一的「判题 I/O 约定」段落；
  3. **用本机 gcc 15.2 / g++ 15.2 / Python 3.13 真实运行**这份参考程序，
     用它的输出作为 `expected_output` —— 期望值是跑出来的，不是人抄的。

### 2.4 真实可判能力：2 道 → 30 道

| 学科 | 真可判 | 代表性题目 |
|---|---|---|
| C/C++ | 10 | 字符串反转、有效括号、字符串相加、STL 词频 Top3、stringstream 解析、inline square、二分查找 |
| 计算机基础（C） | 10 | 原地去重、有效括号、每日温度、二分查找、查找首尾位置、两数之和、搜索旋转数组、位 1 个数、矩阵置零、LRU 缺页次数 |
| Python | 10 | 字符串反转、二分查找、旋转数组、two-sum、字母异位词、集合交集保序、路径简化、CSV 解析、正则 DP、空白压缩 |

`选择题 321 / 编程题 344 / 真可判 30（8.7%）`

> **数字变小了，但能力变强了。** 修复前的"39 道"里有 37 道会让学生的正确代码被判错；
> 现在是 30 道，每一道都经过「参考程序实跑 → 期望值比对」的闭环。

---

## 3. 方案 A：agent + ml 并入 ai

### 3.1 ml 是什么

`content/ml/` 是**机器学习（Machine Learning）的 8 章课程**，对应吴恩达课程体系：

| 章 | 标题 |
|---|---|
| ml-ch01 | 学习范式与数学基础：从「拟合」到「泛化」 |
| ml-ch02 | 线性模型：最小二乘、正则化与逻辑回归 |
| ml-ch03 | 神经网络：推理、训练与多分类 |
| ml-ch04 | 应用机器学习：评估、偏差方差与误差分析 |
| ml-ch05 | 决策树与集成学习：从信息增益到 XGBoost |
| ml-ch06 | 无监督学习与降维：聚类、谱方法与 PCA |
| ml-ch07 | 推荐系统：协同过滤与矩阵分解 |
| ml-ch08 | 强化学习：马尔可夫决策过程与 Q-learning |

它和 `ai`（深度学习 / 大模型 / RAG / Agent 工程化）是**上下游关系**：
ml 讲"模型怎么训练出来"，ai 讲"模型怎么被用起来、包成产品"。
`agent`（16 章）则是 AI 应用开发主线：行业认知 → Prompt → 模型接入 → RAG →
私有化部署 → LoRA 微调 → Transformer → 多模态 → Agent 系统 → 商业化 → 求职。

### 3.2 实际改动

- `scripts/merge_agent_ml_into_ai.py`：把 24 章挂到 `ai` 下，**13 学科口径不变**
  - ai 原有分组 A1–A4（深度学习 / 大模型 / 提示与知识增强 / Agent 工程化）
  - agent 的 6 组 → A5–A10（Agent · 认知与基座 / 知识与部署 / 原理与多模态 / 产品与系统 / 前沿与职业 / 交付与求职）
  - ml 的 3 组 → A11–A13（机器学习 · 监督学习 / 高级算法 / 无监督与强化）
  - 章节 order 从 9 续到 32
- `server/scripts/gen_exercise_bundle.py`：新增 `SUBJ_ALIAS = {"agent": "ai", "ml": "ai"}`，
  在打题时就把 `subj` 归一 —— 否则前端按 13 学科过滤题库时，这 144 道题**永远筛不出来**
  （这才是"有内容无入口"的真正机制）

### 3.3 验收

```
bundle.ts: ai 章节 8 -> 32（agent 16 + ml 8 全部就位）
exercises.ts: ai 题数 63 -> 207；无 "subj":"agent" / "subj":"ml" 残留
13 学科题数：cpp130 clang46 java66 spring56 python60 fullstack64 database58
             middleware58 ai207 bigdata42 data42 fundamentals87 tooling47 = 963
```

---

## 4. 覆盖率重算与文档更正

### 4.1 `_coverage.json` 严重过期

原生成脚本（`gen_bundle_data.py` 等）已丢失，文件停在某个旧快照：

| 字段 | 旧记录 | 磁盘实测 |
|---|---|---|
| total_chapters | 136 | **138** |
| complete | 130 | **138** |
| incomplete | 6 | **0** |
| missing_units（manifest 计划缺口） | 8（agent-ch01/02/04 + ml-ch04~08） | **0** |
| orphan_dirs（不被 manifest 收录的孤儿目录） | 2（ml-ch04、ml-ch08） | **0** |

它甚至记录 `agent-ch01` 的 `interview=0 / project=0`，而磁盘实际是 **4 条面试题 + 1 个项目**。

`scripts/recalc_coverage.py` 按旧文件的阈值（goals 1 / concept 3 / pitfalls 3 /
exercises 5 / examples 10 / interview 3 / project 1）重算，并把计数口径写进脚本 docstring。

### 4.2 口径声明（重要，防止再一次"虚报"）

**100% 是「结构完整性」，不是「知识正确性」。** 它只说明每章 7 类文件齐备且过阈值，
不代表内容没有事实错误、没有过时结论。体量与论证深度的审计见
`docs/Content-Audit-2026-10-27.md`，知识正确性需要独立的人工/专家复核。

### 4.3 文档更正

`docs/JUDGE-COVERAGE-2026-10-26.md` 顶部已加警示，并把表格更正为四行：

| 阶段 | 含 test_cases | coding 总数 | 可判率 |
|---|---|---|---|
| 17 轮（仅 Python 成果） | 163 | 344 | 47.4% |
| 该文声称修复后 | 185 | 344 | 53.8% |
| **2026-10-27 磁盘实测** | **39** | 344 | **11.3%** |
| **2026-10-27 本轮补完（真可判）** | **30** | 344 | **8.7%** |

保留那份文档是为了记住教训：**声称的 185 从未落在工作区（`git status` 干净），
脚本崩了却以为成功，没有校验写盘结果就报了数字。**

---

## 5. 产物与回滚

新增脚本（都可 `--restore`）：

| 脚本 | 作用 | 备份目录 |
|---|---|---|
| `scripts/fix_choice_options.py` | 解析内联选项 + 规范化答案 | `content/_backup_choice_fix/` |
| `scripts/patch_missing_options.py` | 29 道手写选项 + tooling q3 拆题 | `content/_backup_missing_options/` |
| `scripts/add_judge_cases.py` | 28 道真可判用例（实跑生成期望值） | `content/_backup_judge_cases/` |
| `scripts/purge_fake_cases.py` | 37 道伪用例转 samples | `content/_backup_purge_fake/` |
| `scripts/merge_agent_ml_into_ai.py` | agent/ml 并入 ai | `frontend/src/data/_backup_bundle/` |
| `scripts/recalc_coverage.py` | 重算 `_coverage.json` | `content/_backup_coverage/` |

---

## 6. 遗留（下一轮该做什么）

1. **fundamentals 还剩 22 道**编程题没做（链表 / 树 / 图 / LRU / 银行家算法），
   java 20 道全部待重写（现有 10 道是伪用例，已清）。
   这两批合计 42 道，做完后真可判可到 ~72 道。
2. **database 的 18 道 SQL 题**需要「建 schema + 灌数据 + 跑 SQL 比对结果」的判题器，
   不能用 stdin 模式。这是独立工程。
3. **`clang` 缺 `_manifest.json`**，所以它的 7 章没进 manifest 对账（planning 只统计 131 个单元）。
4. 判题链路的真机验证：go-judge（:2358）本次没启动，30 道用例的「期望值」是用
   本机 gcc/g++/python 跑出来的，语义等价但沙箱内路径/编码仍需在真机跑一次 e2e。
