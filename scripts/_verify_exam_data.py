"""轻量级考研题库数据通路验证：不依赖 FastAPI/uvicorn，直接加载真实 exam_bank
服务，对照前端 exam.ts 契约断言字段。仅桩掉 app.core.config / app.core.responses。
"""
import importlib.util
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTENT_DIR = REPO / "content"

# ── 桩：app.core.config / app.core.responses ──
app = types.ModuleType("app")
app_core = types.ModuleType("app.core")
app_core_config = types.ModuleType("app.core.config")
app_core_responses = types.ModuleType("app.core.responses")

class _Settings:
    content_dir = str(CONTENT_DIR)

app_core_config.settings = _Settings()

class AppError(Exception):
    def __init__(self, code, message="", http_status=400, **kw):
        super().__init__(message)
        self.code = code
        self.http_status = http_status

app_core_responses.AppError = AppError
app_core_responses.NOT_FOUND = 404
app_core_responses.PARAM_ERROR = 400

sys.modules["app"] = app
sys.modules["app.core"] = app_core
sys.modules["app.core.config"] = app_core_config
sys.modules["app.core.responses"] = app_core_responses

# ── 加载真实 exam_bank（按文件路径，避免触发真实 app 包 __init__）──
spec = importlib.util.spec_from_file_location(
    "exam_bank_verify", REPO / "server" / "app" / "services" / "exam_bank.py"
)
eb = importlib.util.module_from_spec(spec)
sys.modules["exam_bank_verify"] = eb  # dataclass 内省会查 sys.modules[__module__]
spec.loader.exec_module(eb)

fails = []

def check(cond, msg):
    if cond:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        fails.append(msg)

print("== 1. catalog（考试目录）==")
cat = eb.catalog()
check(isinstance(cat, dict) and "items" in cat, "catalog 返回 dict 含 items")
items = cat.get("items", [])
check(len(items) >= 1, f"至少 1 场考试（实际 {len(items)}）")
check(all("subjects" in e and "counts" in e for e in items), "每项含 subjects 与 counts")
# 取第一个考试/科目做后续探测
exam0 = items[0]
ek = exam0["key"]
sk = exam0["subjects"][0]["key"] if exam0["subjects"] else None
print(f"  用 {ek} / {sk} 做样本")

print("== 2. frameworks（解题框架）==")
try:
    fw = eb.framework(ek, sk)
    check("topics" in fw and isinstance(fw["topics"], list), f"framework 含 topics（{len(fw.get('topics', []))} 个）")
except Exception as e:
    check(False, f"framework 抛异常: {e}")

print("== 3. knowledge（知识点）==")
try:
    kd = eb.knowledge(ek, sk)
    check("items" in kd, "knowledge 含 items")
except Exception as e:
    check(False, f"knowledge 抛异常: {e}")

print("== 4. summaries（分类总结 + 建议刷题顺序）==")
try:
    sm = eb.summaries(ek, sk)
    groups = sm.get("groups", [])
    check(len(groups) > 0, f"summaries 含 groups（{len(groups)} 个）")
    so = [g for g in groups if g.get("suggested_order")]
    check(len(so) > 0, f"存在 suggested_order 的专题（{len(so)}/{len(groups)}）")
    # 校验 suggested_order 与 question_ids 同集合（契约 §C）
    ok_order = all(set(g["suggested_order"]) == set(g["question_ids"]) for g in so)
    check(ok_order, "suggested_order 与 question_ids 同集合（字段透传正确）")
except Exception as e:
    check(False, f"summaries 抛异常: {e}")

print("== 5. questions（列表不下发答案）==")
try:
    ql = eb.list_questions(ek, sk, page=1, size=5)
    check("items" in ql and "total" in ql, "questions 含 items/total（分页）")
    sample = ql["items"][0] if ql["items"] else None
    if sample:
        check("stem" in sample and "type" in sample, "题目卡含 stem/type")
        check("answer" not in sample and "walkthrough" not in sample, "列表不含 answer/walkthrough（不剧透）")
        qid = sample["id"]
        print(f"  样本题 id={qid}")
        print("== 6. question_detail（含四层讲解 + 答案）==")
        det = eb.question_detail(ek, sk, qid)
        check("answer" in det, "详情含 answer")
        check("walkthrough" in det and "framework" in det["walkthrough"], "详情含四层 walkthrough.framework")
except Exception as e:
    check(False, f"questions/detail 抛异常: {e}")

print("== 7. papers（套卷）==")
try:
    pl = eb.list_papers(ek, page=1, size=5)
    check("items" in pl and "total" in pl, f"papers 含 items/total（{pl.get('total')} 套）")
    if pl["items"]:
        pid = pl["items"][0]["id"]
        pd = eb.paper_detail(pid)
        check("sections" in pd, "paper_detail 含 sections")
except Exception as e:
    check(False, f"papers 抛异常: {e}")

print("== 8. grade（无状态判分）==")
try:
    ql = eb.list_questions(ek, sk, page=1, size=3)
    if ql["items"]:
        q = ql["items"][0]
        qd = eb.question_detail(ek, sk, q["id"])
        ans = qd.get("answer", {})
        correct = ans.get("correct")
        payload = [{"question_id": q["id"], "choice": correct if isinstance(correct, int) else 0}]
        res = eb.grade(ek, sk, payload)
        check("items" in res and res["items"], "grade 返回 items")
        check(res["items"][0]["verdict"] in ("CORRECT", "INCORRECT", "UNGRADED"), "verdict 枚举合法")
        check("summary" in res and "accuracy" in res["summary"], "grade 含 summary.accuracy")
except Exception as e:
    check(False, f"grade 抛异常: {e}")

print()
if fails:
    print(f"结果：{len(fails)} 项失败")
    for f in fails:
        print("  -", f)
    sys.exit(1)
else:
    print("结果：全部通过 ✓ 考研题库数据通路与前端契约一致")
