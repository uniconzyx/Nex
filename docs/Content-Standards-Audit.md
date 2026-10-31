# CppMind 内容标准审计（两条标准 × 深度）

> 生成方式：`python scripts/audit_sources.py && python scripts/audit_depth.py && python scripts/report_standards.py`
> 所有数字都来自这两个审计器的 JSON 输出，不是估算。

## 一句话结论

- **标准一（体系完善）**：141/141 章七类内容齐备；三视角 519/519 篇规范（标记漂移 0 处）。**这一条真的过了。**
- **标准二（来源完整）**：结构门槛 141/141 章达标（每章 ≥3 个真实 GitHub 仓库 + ≥2 条真实 B 站直链 + 论文）。**但只有 35/141 章是「章节级路线」**，其余 106 章的读法在同科目内重复，属于「学科级复制」——这是目前最大的实质缺口。
- **深度（深入/完整/透彻）**：A 8 章、B 53 章、**C（偏薄）80 章**。薄在「概念里没有可运行代码」（48 章）、「知识点粒度粗」（30 章）、「陷阱太少」（24 章）。

## 标准二：结构达标 ≠ 颗粒度达标

| 学科 | 章数 | 来源结构达标 | 章节级路线 | 被复制的章 |
|---|---|---|---|---|
| agent | 16 | 16/16 | 16 | 0 |
| ai | 10 | 10/10 | 2 | 8 |
| bigdata | 6 | 6/6 | 0 | 6 |
| clang | 7 | 7/7 | 7 | 0 |
| cpp | 20 | 20/20 | 0 | 20 |
| data | 6 | 6/6 | 0 | 6 |
| database | 8 | 8/8 | 0 | 8 |
| fullstack | 8 | 8/8 | 1 | 7 |
| fundamentals | 12 | 12/12 | 0 | 12 |
| java | 9 | 9/9 | 0 | 9 |
| middleware | 8 | 8/8 | 0 | 8 |
| ml | 9 | 9/9 | 9 | 0 |
| python | 8 | 8/8 | 0 | 8 |
| spring | 8 | 8/8 | 0 | 8 |
| tooling | 6 | 6/6 | 0 | 6 |
| **合计** | **141** | **141** | **35** | **106** |

判据：同一学科内两章如果 `github_notes` 完全相同，就判定为「学科级复制」。它可能带了 § 锚点、也可能有 star，但那份路线不是为这一章写的。

## 深度：C 级清单（按字数升序，前 30）

| 章节 | 讲解字数 | 公式 | 代码块 | H3 | 陷阱 | 短板 |
|---|---|---|---|---|---|---|
| java-ch01 | 1414 | 0 | 5 | 9 | 5 | concept_chars/h3/pitfalls |
| py-ch01 | 1419 | 0 | 3 | 9 | 6 | concept_chars/code_blocks/h3/pitfalls |
| cpp-ch03 | 1545 | 0 | 3 | 9 | 4 | concept_chars/code_blocks/h3/pitfalls |
| db-ch01 | 1548 | 0 | 6 | 9 | 6 | concept_chars/h3/pitfalls |
| cpp-ch01 | 1616 | 0 | 3 | 9 | 4 | concept_chars/code_blocks/h3/pitfalls |
| cpp-ch04 | 1661 | 0 | 3 | 9 | 5 | concept_chars/code_blocks/h3/pitfalls |
| cpp-ch02 | 1679 | 0 | 4 | 9 | 5 | concept_chars/code_blocks/h3/pitfalls |
| clang-u01 | 2934 | 0 | 24 | 12 | 10 | concept_chars |
| clang-u02 | 3050 | 0 | 14 | 9 | 11 | concept_chars/h3 |
| ai-ch03 | 3096 | 39 | 0 | 28 | 13 | concept_chars/code_blocks |
| fund-ch01 | 3129 | 0 | 14 | 12 | 10 | concept_chars |
| fs-ch03 | 3134 | 0 | 0 | 12 | 14 | concept_chars/code_blocks |
| clang-u04 | 3282 | 0 | 10 | 9 | 8 | h3 |
| ai-ch06 | 3322 | 0 | 0 | 24 | 15 | code_blocks |
| cpp-ch09 | 3380 | 0 | 3 | 12 | 6 | code_blocks/pitfalls |
| spring-ch04 | 3464 | 0 | 9 | 9 | 6 | h3/pitfalls |
| spring-ch06 | 3535 | 3 | 0 | 24 | 14 | code_blocks |
| cpp-ch17 | 3561 | 0 | 9 | 24 | 7 | pitfalls |
| cpp-ch20 | 3595 | 0 | 0 | 33 | 15 | code_blocks |
| fs-ch04 | 3611 | 0 | 0 | 24 | 14 | code_blocks |
| spring-ch05 | 3687 | 0 | 0 | 24 | 14 | code_blocks |
| cpp-ch05 | 3796 | 0 | 11 | 9 | 8 | h3 |
| tool-ch03 | 3846 | 0 | 0 | 24 | 14 | code_blocks |
| ai-ch02 | 3858 | 0 | 0 | 24 | 12 | code_blocks |
| py-ch02 | 3949 | 0 | 3 | 15 | 9 | code_blocks |
| mw-ch01 | 3978 | 0 | 0 | 24 | 6 | code_blocks/pitfalls |
| cpp-ch14 | 4017 | 0 | 16 | 15 | 7 | pitfalls |
| cpp-ch15 | 4039 | 0 | 10 | 12 | 6 | pitfalls |
| fund-ch03 | 4076 | 0 | 6 | 9 | 9 | h3 |
| cpp-ch16 | 4123 | 0 | 8 | 15 | 7 | pitfalls |

## 阈值（可复核）

| 指标 | B 级（合格） | A 级（扎实） |
|---|---|---|
| concept_chars | 3200 | 6000 |
| code_blocks | 5 | 12 |
| h3 | 10 | 20 |
| pitfalls | 8 | 15 |
| example_real_pct | 100 | 100 |
| exercise_types | 3 | 4 |

> 公式数只报告不评级：cpp/java/python 这类工程学科本来就少公式。

## 本轮已修

1. **失效链接**：8 条 B 站链接（cpp 的侯捷/黑马整列、fundamentals 1 条、java 1 条）已换为站内 API 核验通过的真实 BV；62 个唯一 BV、566 处引用，复核失效 0 条。
2. **占位句**："建议结合本章示例与习题观看" 这类模板话已全量清除，审计器会把它们判成未达标。
3. **星数**：GitHub 未认证 API 每小时 60 次，批量核验必被限流；被限流的 `null` 曾把真实星数抹成空值。现在改为三级取值（本轮 API → manifest 旧值 → 历史快照），515 行全部有星数。
4. **假精确**：原先 99.8% 的 GitHub 行都写着「全章通用」，等于没有锚点。现在读法里写 `§x.y` 的按 § 采信，`要点/三视角解析` 这类模板标题不再被当作锚点。
5. **章节级路线（试点）**：clang 7 个单元原先共用 3 个学科级仓库，已逐单元换成`c4` / `kilo` / `cJSON` / `redis` 的具体入口文件（21 条读法全部带 § 与文件名），clang 从 0/7 变成 7/7 章节级。

## 下一步（按 ROI 排序）

| 批次 | 范围 | 做什么 |
|---|---|---|
| 1 | 106 章仍是学科级路线 | 按 clang 的做法逐章换仓库 + 写入口文件读法 |
| 2 | 80 章偏薄 | 优先补「概念里没有可运行代码」的 48 章：每节加一段可跑代码 + 真实输出 |
| 3 | 30 章粒度粗 | 把大节拆成可检索的小节（H3 ≥ 20） |
| 4 | 24 章陷阱少 | 补齐到 ≥15 条，且每条给「症状 → 原因 → 修法」 |

