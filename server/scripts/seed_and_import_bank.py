"""把 content/<学科>/<章节>/exercises.json 全量导入 Postgres（覆盖 judge 链路的 exercises/test_cases）。

设计要点：
- DB 当前仅有 cpp/clang 两课程与 27 章节；content 下还有 java/spring/python/fullstack/
  database/middleware/ai/bigdata/data/fundamentals/tooling/agent/ml 等十余学科。
  脚本先按 content 目录前缀幂等补齐 Course/Chapter，再逐章导入 Exercise。
- 磁盘上的 exercises.json 缺 meta.format 字段，且含有 ExerciseType 枚举外的类型
  (judge/design/explain) 与整数 difficulty，直接喂 import_package 会被整包拒绝。
  故在导入前做逐题清洗：
    * 注入 meta.format = "cppmind-exercise-v1"
    * 类型归一：judge/design/explain -> output；choice/fix_error/output/coding 保留
    * difficulty 整数/非法串 -> easy/mid/hard
    * coding 无 test_cases -> 丢弃该项（即已知「之后补充」缺口）
    * choice 选项<2 或 answer.correct 非选项子集 -> 丢弃该项
- 缺 meta.chapter 的文件从目录名推导章节码（clang-u06 等）。

用法：
  python -m scripts.seed_and_import_bank            # 种子章节 + 导入
  python -m scripts.seed_and_import_bank --dry-run # 仅统计，不写库
  python -m scripts.seed_and_import_bank --force    # 清掉已导入章节后重导（幂等）
"""
import argparse
import asyncio
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select, text  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models.content import Chapter, Course  # noqa: E402
from app.models.exercise import Exercise  # noqa: E402
from app.services.sync.importer import import_package  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent  # 项目根 CppMind
CONTENT = ROOT / "content"

# content 顶级目录名 == 课程码（cpp/clang/java/spring/python/fullstack/database/
# middleware/ai/bigdata/data/fundamentals/tooling/agent/ml），一一对应。
_SUBJECTS = ["cpp", "clang", "java", "spring", "python", "fullstack", "database",
             "middleware", "ai", "bigdata", "data", "fundamentals", "tooling",
             "agent", "ml"]
SUBJECT_TO_COURSE = {s: s for s in _SUBJECTS}
COURSE_TITLES = {
    "cpp": "C++ 思维导图主线", "clang": "C 语言单独模块", "java": "Java 学习主线",
    "spring": "Spring 全家桶", "python": "Python 学习主线", "fullstack": "全栈开发",
    "database": "数据库", "middleware": "中间件", "ai": "AI 基础", "bigdata": "大数据",
    "data": "数据分析", "fundamentals": "计算机基础", "tooling": "工具链",
    "agent": "Agent 工程", "ml": "机器学习",
}
COURSE_SORT = {s: i for i, s in enumerate(_SUBJECTS)}

VALID_TYPES = {"choice", "fix_error", "output", "coding"}


def norm_type(t: str) -> str:
    if t in VALID_TYPES:
        return t
    # judge/design/explain 是概念型（非代码判题），统一落到 output 以保留内容
    return "output"


def norm_difficulty(d):
    if isinstance(d, int):
        return "easy" if d <= 2 else ("mid" if d <= 4 else "hard")
    if isinstance(d, str) and d in ("easy", "mid", "hard"):
        return d
    return "mid"


def norm_answer(a, t):
    if isinstance(a, dict):
        return a
    if isinstance(a, str):
        # choice 的字符串答案视为单选；其余类型包成 text 以保留内容
        return {"correct": [a]} if t == "choice" else {"text": a}
    return {}


def norm_options(opts):
    """选项可能是字符串列表（"A. 文本"）而非 {key,text} 字典，统一归一成字典。"""
    if not isinstance(opts, list):
        return None
    out = []
    for i, o in enumerate(opts):
        if isinstance(o, dict):
            out.append(o)
        elif isinstance(o, str):
            m = re.match(r"^([A-Za-z])\.?\s*(.*)$", o)
            if m:
                out.append({"key": m.group(1).upper(), "text": m.group(2)})
            else:
                out.append({"key": chr(ord("A") + i), "text": o})
    return out or None


def clean_items(items):
    kept, dropped = [], 0
    for it in items:
        t = norm_type(it.get("type"))
        it["type"] = t
        it["difficulty"] = norm_difficulty(it.get("difficulty"))
        ans = it.get("answer")
        if not isinstance(ans, dict):
            ans = norm_answer(ans, t)
            it["answer"] = ans
        if it.get("options") is not None:
            it["options"] = norm_options(it.get("options"))
        if t == "coding":
            if not (it.get("test_cases") or []):
                dropped += 1
                continue  # 无用例的 coding 属已知缺口，跳过
        if t == "choice":
            opts = it.get("options") or []
            keys = {o.get("key") for o in opts if isinstance(o, dict)}
            correct = ans.get("correct", [])
            correct = set(correct) if isinstance(correct, (list, tuple, set)) else {correct}
            if len(keys) < 2 or not correct or not correct.issubset(keys):
                dropped += 1
                continue
        kept.append(it)
    return kept, dropped


def iter_files():
    for fp in sorted(glob.glob(str(CONTENT / "*" / "*" / "exercises.json"))):
        p = Path(fp)
        sub, ch = p.parent.parent.name, p.parent.name
        if sub.startswith("_"):  # 跳过 _exam/_guides 等非学科目录
            continue
        yield fp, sub, ch


async def seed_courses_chapters(db):
    course_cache: dict[str, Course] = {c.code: c for c in (await db.execute(select(Course))).scalars()}
    chapter_cache: set[str] = {c.code for c in (await db.execute(select(Chapter))).scalars()}

    async def get_course(code: str) -> Course:
        if code not in course_cache:
            c = Course(code=code, title=COURSE_TITLES[code], sort=COURSE_SORT[code])
            db.add(c)
            await db.flush()
            course_cache[code] = c
        return course_cache[code]

    added = 0
    for fp, sub, ch in iter_files():
        try:
            raw = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue
        chapter_code = (raw.get("meta") or {}).get("chapter") or ch
        if chapter_code in chapter_cache:
            continue
        course = await get_course(SUBJECT_TO_COURSE[sub])
        m = re.search(r"\d+", chapter_code)
        idx = int(m.group()) if m else 0
        db.add(Chapter(course_id=course.id, idx=idx, code=chapter_code,
                       title=f"{COURSE_TITLES[SUBJECT_TO_COURSE[sub]]} · {chapter_code}",
                       goals=[], is_free=False))
        chapter_cache.add(chapter_code)
        added += 1
    await db.commit()
    return added


async def main(dry_run: bool, force: bool):
    async with SessionLocal() as db:
        # 幂等确保 bundle_id 列存在（兼容已建表的老库；新库由 create_all 自带）。
        try:
            await db.execute(text("ALTER TABLE exercises ADD COLUMN IF NOT EXISTS bundle_id TEXT"))
            await db.commit()
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] 确保 bundle_id 列失败（可忽略，若已存在）: {e}")
        if not dry_run:
            added = await seed_courses_chapters(db)
            print(f"[seed] 新增章节 {added} 个（课程/章节均幂等）")
        else:
            print("[dry-run] 跳过种子与写入，仅统计")

        total_files = 0
        total_ex = 0
        total_dropped = 0
        ok_ch = 0
        skip_ch = 0
        err_ch = 0
        # 全局去重集合，与 gen_exercise_bundle.build() 的 seen 完全同源：
        # 保证同一显式 id 在多处出现时，后端 bundle_id 与前端 BankExercise.id 改名规则一致（如 ex1-1 -> ex1-1-2）。
        seen: set[str] = set()
        for fp, sub, ch in iter_files():
            total_files += 1
            try:
                raw = json.loads(Path(fp).read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  [SKIP] 解析失败 {fp}: {e}")
                skip_ch += 1
                continue
            chapter_code = (raw.get("meta") or {}).get("chapter") or ch
            items = raw.get("items", [])
            # 与 gen_exercise_bundle.py 完全一致的 id 规则 + 全局去重：
            # 优先用 item 自带 id，否则「章节目录名-序号」(ch=目录名)，同名则按全局序号改名，
            # 保证云端 bundle_id 与前端 BankExercise.id 1:1。
            for i, it in enumerate(items):
                if isinstance(it, dict) and "bundle_id" not in it:
                    bid = it.get("id") or f"{ch}-{i + 1:02d}"
                    if bid in seen:
                        # 全局递增计数，保证跨章节唯一（同一显式 id 出现在多个章节时不会撞车）
                        _c = 1
                        while f"{bid}-{_c}" in seen:
                            _c += 1
                        bid = f"{bid}-{_c}"
                    seen.add(bid)
                    it["bundle_id"] = bid
            kept, dropped = clean_items(items)
            total_dropped += dropped
            if not kept:
                skip_ch += 1
                continue
            pkg = {"meta": {"format": "cppmind-exercise-v1", "chapter": chapter_code},
                   "items": kept}
            if dry_run:
                ok_ch += 1
                total_ex += len(kept)
                continue
            if force:
                chapter = (await db.execute(
                    select(Chapter).where(Chapter.code == chapter_code))).scalar_one_or_none()
                if chapter is not None:
                    await db.execute(delete(Exercise).where(Exercise.chapter_id == chapter.id))
                    await db.commit()
            try:
                res = await import_package(db, json.dumps(pkg, ensure_ascii=False))
                ok_ch += 1
                total_ex += res.get("created", 0)
            except ValueError as e:
                err_ch += 1
                print(f"  [ERR] {chapter_code}: {e}")

        print(f"\n=== 汇总 ===")
        print(f"文件总数: {total_files}")
        if not dry_run:
            print(f"导入成功章节: {ok_ch}  失败: {err_ch}  跳过(无有效题): {skip_ch}")
        else:
            print(f"可导入章节(预览): {ok_ch}  跳过(无有效题): {skip_ch}")
        print(f"导入题目数: {total_ex}")
        print(f"清洗丢弃题数(无用例coding/非法choice等): {total_dropped}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="仅统计不写库")
    ap.add_argument("--force", action="store_true", help="清掉已导入章节后重导")
    args = ap.parse_args()
    asyncio.run(main(args.dry_run, args.force))
