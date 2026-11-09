"""开发环境快速建库：create_all + 种子数据（课程/章节/成就）。

用法：python -m scripts.init_db
生产环境请使用 Alembic 迁移（见 README）。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: F401, E402  确保所有模型注册到 metadata
from app.models.content import Chapter, Course  # noqa: E402
from app.models.progress import Achievement  # noqa: E402

CPP_CHAPTERS = [
    "工具链与环境", "C++ 基础语法", "面向对象", "内存与对象模型",
    "现代 C++：C++11/14/17/20/23", "STL 标准库", "模板与泛型编程", "并发与异步",
    "数据结构与算法", "系统与底层", "工程化", "高性能与优化",
    "深度学习基础：数学与模型", "C++ 深度学习生态", "深度学习 C++ 学习路径",
    "项目实战", "推荐资源", "面试准备", "推荐学习节奏", "一句话路线",
]

CLANG_UNITS = ["指针", "内存", "结构体", "文件", "预处理", "Makefile", "多文件编译"]

ACHIEVEMENTS = [
    ("first_ac", "首次 AC", "第一次通过编程题全部测试用例", "cat-celebrate"),
    ("streak_7", "七日坚持", "连续学习打卡 7 天", "cat-cheer"),
    ("first_project", "项目启航", "完成第一个项目实战的全部任务", "cat-jump"),
    ("wrong_slayer", "错题克星", "错题本清零一次", "cat-check"),
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        # 幂等：按自然键 upsert，重复执行只会补齐缺失项，不会撞 unique 约束。
        async def course(code: str, title: str, sort: int) -> Course:
            row = (await db.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
            if row is None:
                row = Course(code=code, title=title, sort=sort)
                db.add(row)
                await db.flush()
            return row

        cpp = await course("cpp", "C++ 思维导图主线", 0)
        clang = await course("clang", "C 语言单独模块", 1)

        existing_ch = set(
            (await db.execute(select(Chapter.code))).scalars().all()
        )
        # 章节 code 必须与 content/<subject>/<chapter>/ 对齐（内容体系是唯一事实源）。
        # 旧版从 00 起，会让 /chapters 返回的 code 和前端 BUNDLE 对不上，也会让
        # seed 把 cpp-ch20 误判成新章、留下孤儿 cpp-ch00。
        for i, title in enumerate(CPP_CHAPTERS):
            code = f"cpp-ch{i + 1:02d}"
            if code in existing_ch:
                continue
            db.add(Chapter(course_id=cpp.id, idx=i, code=code, title=title,
                           goals=[], is_free=i < 3))  # 前 3 章游客可体验
        for i, title in enumerate(CLANG_UNITS):
            code = f"clang-ch{i + 1:02d}"
            if code in existing_ch:
                continue
            db.add(Chapter(course_id=clang.id, idx=i, code=code, title=f"C 语言 · {title}",
                           goals=[], is_free=i == 0))

        existing_ach = set(
            (await db.execute(select(Achievement.code))).scalars().all()
        )
        for code, title, desc, icon in ACHIEVEMENTS:
            if code in existing_ach:
                continue
            db.add(Achievement(code=code, title=title, description=desc, icon=icon))
        await db.commit()

    # 内容侧一并播种：以前只建 2 门课 / 27 章，knowledge_points 恒 0 行，
    # /chapters 的掌握度、/mindmap、/search 全是空壳。seed 幂等、纯增量。
    from scripts.seed_knowledge_points import seed

    await seed()
    print(
        f"OK: courses=2, chapters={len(CPP_CHAPTERS) + len(CLANG_UNITS)}, "
        f"achievements={len(ACHIEVEMENTS)}；概念体系已播种"
    )


if __name__ == "__main__":
    asyncio.run(main())
