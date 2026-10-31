# 题库文件 → Postgres 全量导入（2026-10-26）

## 目标
让前端判题页「有题可做」：把 `content/<学科>/<章节>/exercises.json` 全量导入 Postgres 的 `exercises` / `test_cases` 表，使判题链路（B 选项已验证）跑在真实数据上。

## 结果
- 课程 **15** 门、章节 **146** 个、题目 **699** 道、test_cases **193** 条、tags 1319 / exercise_tags 1902。
- 138 个 `exercises.json` 全部导入成功（0 失败）。
- 端到端验证：用真实导入的 coding 题 `id=1548「读取 n 个数求和」`（3 个用例）提交 C++ 正确解 → `ac/passed=3`；错误解 → `wa/passed=0`。

## 导入前暴露并修复的 4 个真实 bug
1. **`judge.py` 访问 `exercise.test_cases` 关系惰性加载 → `MissingGreenlet`**（exercise_id 提交 500）。改用 `selectinload(Exercise.test_cases)` 预加载。
2. **`importer.py` 用 `exercise.tags.append(...)` 触发 tags 关系惰性加载 → `MissingGreenlet`**。改为直接往关联表 `exercise_tags` 插行（不再碰 `tags` 关系集合）。
3. **`system.py` 的 `features.judge` 硬编码 `None`**。改为实时探测 `judge0_url/languages`，`/system/health` 如实返回 `judge.ok`。
4. **`judge0.py` 的 `LANG_MAP[lang]` 越界 KeyError**。改为 `.get(lang, 54)` 回退 cpp。

## 磁盘文件 → 导入器之间的格式/类型鸿沟（已在脚本内归一化）
磁盘 `exercises.json` 与 `ExercisePackage` 校验schema 存在多处不一致，导入脚本 `server/scripts/seed_and_import_bank.py` 在落库前逐题清洗：
- 缺 `meta.format` 字段 → 注入 `cppmind-exercise-v1`。
- 含枚举外类型 `judge`(24)/`design`(32)/`explain`(9) → 归一为 `output`（保留内容；这些非代码判题型，不进判题）。
- `difficulty` 用整数(如 5)或非法串 → 映射到 easy/mid/hard。
- `choice` 题 `options` 为字符串列表（"A. 文本"）→ 解析成 `{key,text}` 字典。
- `answer` 为字符串或 None → 包成 `{correct:[...]}`(choice) 或 `{text:...}`/空 dict。
- `coding` 无 `test_cases` → 丢弃该项（即「之后补充」缺口，共 263 题被清洗丢弃）。
- 4 个文件缺 `meta.chapter` → 从目录名推导章节码。

## 运行方式
```bash
cd server
# 仅预览统计
python -m scripts.seed_and_import_bank --dry-run
# 真实导入（会先幂等补齐课程/章节，再逐章导入）
python -m scripts.seed_and_import_bank --force
```
- `--force`：导入前清空该章节已存在的 exercises 后重导（幂等，便于重复执行；依赖 submissions 表为空，目前为空）。
- 课程/章节种子逻辑幂等（按 `code` upsert），重复执行只补缺失项。

## 端到端判题验证脚本
`scripts/test_judge_real_exercise.py`：注册/登录 → 提交真实 exercise_id → 轮询结果，断言正确解 AC/错误解 WA。

## 仍待办（非本次范围，主人已点明「之后补充」）
- Java 判题（`LANG_MAP`/`CodeStd` 无 java）、纯函数片段题（无 main）、文件 IO 题、无 reference_code 题。
- 159 道无用例 coding 题 + 部分字符串选项/异常结构题被清洗丢弃，属已知缺口，需补参考实现与用例。
- 生产应换回 go-judge 侧车，仅校准 `GET /languages`。
- 前端判题页需对接 `/judge/submissions` 与 `exercises` 列表接口（fetch 真实题库）。
