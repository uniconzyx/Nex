"""临时脚本：将 dev 库初始化为干净种子状态。

删除验证过程中污染的全部测试账号及其级联数据（进度 / 错题 / 笔记 / 收藏 /
会话 / 计划 / 打卡 / 成就 / OAuth 绑定 / 学习状态快照等），保留内容种子
（courses/chapters/exercises 等）。

安全前提：dev 库 19 个账号全部位于保留测试域名（example.com / test.com /
nex.dev 测试前缀），无任何真实个人账号。删除前会打印计数，便于核对。
"""
from __future__ import annotations
import asyncio, asyncpg
from app.core.config import settings

url = str(settings.database_url).replace("postgresql+asyncpg://", "postgresql://")

# 仅删测试域名账号；真实个人账号绝不在此列。
TEST_DOMAINS = ("@example.com", "@test.com")
TEST_PREFIXES = ("e2e", "judge_e2e", "pubby_", "verify", "ai-check", "plan-chk")

USER_ID_TABLES = [
    "ai_conversations", "career_step_progress", "checkins", "favorites", "notes",
    "progress", "project_task_progress", "study_plans", "study_state",
    "submissions", "user_achievements", "user_oauth_identities",
    "user_profiles", "wrong_questions",
]


def is_test_email(email: str) -> bool:
    if any(email.endswith(d) for d in TEST_DOMAINS):
        return True
    local = email.split("@", 1)[0]
    return any(local.startswith(p) for p in TEST_PREFIXES)


async def main() -> None:
    c = await asyncpg.connect(url, timeout=10)
    try:
        users = await c.fetch("select id, email from users order by id")
        targets = [(u["id"], u["email"]) for u in users if is_test_email(u["email"])]
        ids = [t[0] for t in targets]
        print(f"全部账号数: {len(users)}，判定为测试账号: {len(targets)}")
        for tid, em in targets:
            print(f"  -> 删除 id={tid} email={em}")

        if not ids:
            print("无可清理的测试账号，已是干净状态。")
            return

        # 1) ai_messages（conversation_id 间接关联）
        n = await c.execute(
            "delete from ai_messages where conversation_id in (select id from ai_conversations where user_id = any($1))",
            ids,
        )
        # 2) daily_tasks（plan_id 间接关联）
        await c.execute(
            "delete from daily_tasks where plan_id in (select id from study_plans where user_id = any($1))",
            ids,
        )
        # 3) 直连 user_id 的子表
        for t in USER_ID_TABLES:
            await c.execute(f"delete from {t} where user_id = any($1)", ids)
        # 4) 最后删用户
        await c.execute("delete from users where id = any($1)", ids)

        # 复核
        remain = await c.fetchval("select count(*) from users")
        print(f"\n清理完成。剩余账号数: {remain}")
        # 关键内容表不应受影响
        for t in ("courses", "chapters", "exercises", "knowledge_points"):
            cnt = await c.fetchval(f"select count(*) from {t}")
            print(f"  内容表 {t} 行数: {cnt}")
    finally:
        await c.close()


if __name__ == "__main__":
    asyncio.run(main())
