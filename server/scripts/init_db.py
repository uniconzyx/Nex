"""开发环境快速建库：create_all + 种子数据（课程/章节/成就）。

用法：python -m scripts.init_db
生产环境请使用 Alembic 迁移（见 README）。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        cpp = Course(code="cpp", title="C++ 思维导图主线", sort=0)
        clang = Course(code="clang", title="C 语言单独模块", sort=1)
        db.add_all([cpp, clang])
        await db.flush()
        for i, title in enumerate(CPP_CHAPTERS):
            db.add(Chapter(
                course_id=cpp.id, idx=i, code=f"cpp-ch{i:02d}", title=title,
                goals=[], is_free=i < 3,  # 前 3 章游客可体验
            ))
        for i, title in enumerate(CLANG_UNITS):
            db.add(Chapter(
                course_id=clang.id, idx=i, code=f"clang-ch{i:02d}", title=f"C 语言 · {title}",
                goals=[], is_free=i == 0,
            ))
        for code, title, desc, icon in ACHIEVEMENTS:
            db.add(Achievement(code=code, title=title, description=desc, icon=icon))
        await db.commit()
    print(f"OK: courses=2, chapters={len(CPP_CHAPTERS) + len(CLANG_UNITS)}, achievements={len(ACHIEVEMENTS)}")


if __name__ == "__main__":
    asyncio.run(main())
