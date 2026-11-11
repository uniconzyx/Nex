"""考研题库的只读数据服务（content/_exam → API 契约对象）。

三条职责，全部集中在这里，路由层只做参数校验与响应包装：
  1. 索引：按 (exam, subject) 建框架 / 知识点 / 分类总结 / 题库；按 id 建套卷与题目。
  2. 标准化：套卷里的题目可能是「字符串 id」也可能是「内嵌快照」（408 整卷的设计题
     只存在于卷子里）。对外一律返回同一种形状，客户端不需要分支。
  3. 判分：只对客观题（选择/多选/填空）给结论；主观题标记 UNGRADED 并回放参考解法。

为什么按内容字段索引而不是按文件名：
  文件名是构建脚本的实现细节（`408-ds.json` vs `math-m1.json` vs `algorithm-algo.json`），
  一旦客户端或路由跟着文件名走，改一次生成规则就得改三处。这里只认 JSON 里的
  exam / subject / key 字段，文件名随便改。

缓存策略：题库是构建产物（`build_exam.py` 生成），进程启动后不再变化，因此首次访问
时整库载入并常驻内存。重新构建题库后必须重启服务，这一点写进了 API 文档。
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from app.core.config import settings
from app.core.responses import AppError, NOT_FOUND, PARAM_ERROR

# 与 app/models/enums.py 无关：题库是纯内容，不落库，题型就是数据里的字符串
CHOICE, MULTI, BLANK = "choice", "multi", "blank"

MAX_PAGE_SIZE = 100


def _exam_dir() -> Path:
    """题库目录。优先跟着 settings.content_dir，失败再回落到仓库路径。"""
    configured = Path(settings.content_dir) / "_exam"
    if configured.is_dir():
        return configured
    return Path(__file__).resolve().parents[3] / "content" / "_exam"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"考试数据缺失：{path}（先跑 server/scripts/build_exam.py）") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"考试数据损坏：{path}: {exc}") from exc


@dataclass
class Bank:
    meta: dict
    exams: dict[str, dict] = field(default_factory=dict)
    frameworks: dict[tuple[str, str], dict] = field(default_factory=dict)
    knowledge: dict[tuple[str, str], dict] = field(default_factory=dict)
    summaries: dict[tuple[str, str], dict] = field(default_factory=dict)
    questions: dict[tuple[str, str], list[dict]] = field(default_factory=dict)
    reading: dict[tuple[str, str], dict] = field(default_factory=dict)
    vocab: dict[tuple[str, str], dict] = field(default_factory=dict)
    listening: dict[tuple[str, str], dict] = field(default_factory=dict)
    formulas: dict[tuple[str, str], dict] = field(default_factory=dict)
    papers: dict[str, dict] = field(default_factory=dict)
    questions_by_id: dict[str, dict] = field(default_factory=dict)
    question_scope: dict[str, tuple[str, str]] = field(default_factory=dict)
    topics: dict[tuple[str, str, str], dict] = field(default_factory=dict)

    # ---- 作用域 ----------------------------------------------------------
    def subjects(self, exam: str) -> list[dict]:
        return self.exams[exam]["subjects"]

    def scope(self, exam: str, subject: str) -> tuple[dict, dict]:
        """校验 exam/subject 存在，返回 (exam_meta, subject_meta)。

        未知值时把合法取值放进 data，客户端可以直接渲染候选，而不是猜。
        """
        e = self.exams.get(exam)
        if e is None:
            raise AppError(
                NOT_FOUND, f"考试不存在：{exam}", http_status=404,
                data={"allowed": sorted(self.exams)},
            )
        for s in e["subjects"]:
            if s["key"] == subject:
                return e, s
        raise AppError(
            NOT_FOUND, f"{e['label']} 下没有科目：{subject}", http_status=404,
            data={"allowed": [s["key"] for s in e["subjects"]]},
        )

    def subject_questions(self, exam: str, subject: str) -> list[dict]:
        return self.questions.get((exam, subject), [])

    def topic_title(self, exam: str, subject: str, topic: str) -> str:
        t = self.topics.get((exam, subject, topic))
        return t["title"] if t else topic

    # ---- 计数 ------------------------------------------------------------
    def subject_counts(self, exam: str, subject: str) -> dict:
        fw = self.frameworks.get((exam, subject), {})
        topics = fw.get("topics") or []
        kn = self.knowledge.get((exam, subject), {})
        sm = self.summaries.get((exam, subject), {})
        return {
            "questions": len(self.subject_questions(exam, subject)),
            "topics": len(topics),
            "patterns": sum(len(t.get("patterns") or []) for t in topics),
            "knowledge": sum(len(b.get("knowledge") or []) for b in kn.get("items") or []),
            "summaries": len(sm.get("groups") or []),
            "papers": len(self.subject_papers(exam, subject)),
        }

    def papers_of_exam(self, exam: str) -> list[dict]:
        return [p for p in self.papers.values() if p.get("exam") == exam]

    def subject_papers(self, exam: str, subject: str) -> list[dict]:
        out = []
        for p in self.papers_of_exam(exam):
            if p.get("subject") == subject:
                out.append(p)
            elif p.get("subject") is None and _covers(p, subject):
                # 整卷（如 408-mock-01）覆盖多个科目，出现在每个科目的卷包里
                out.append(p)
        return out


def _covers(paper: dict, subject: str) -> bool:
    return any(b.get("subject") == subject for b in paper.get("blueprint") or [])


def _scan(directory: Path) -> Iterable[dict]:
    if not directory.is_dir():
        return []
    return (_load(p) for p in sorted(directory.glob("*.json")))


def _build() -> Bank:
    root = _exam_dir()
    meta = _load(root / "_meta.json")
    bank = Bank(meta=meta)

    for e in meta.get("exams") or []:
        bank.exams[e["key"]] = e

    for doc in _scan(root / "frameworks"):
        exam, key = doc.get("exam"), doc.get("key")
        if not exam or not key:
            continue
        bank.frameworks[(exam, key)] = doc
        for t in doc.get("topics") or []:
            bank.topics[(exam, key, t["id"])] = t

    for name, target in (
        ("knowledge", bank.knowledge),
        ("summaries", bank.summaries),
    ):
        for doc in _scan(root / name):
            exam, subject = doc.get("exam"), doc.get("subject")
            if exam and subject:
                target[(exam, subject)] = doc

    for doc in _scan(root / "questions"):
        exam, subject = doc.get("exam"), doc.get("subject")
        if not exam or not subject:
            continue
        items = doc.get("items") or []
        bank.questions[(exam, subject)] = items
        for q in items:
            bank.questions_by_id[q["id"]] = q
            bank.question_scope[q["id"]] = (exam, subject)

    for doc in _scan(root / "reading"):
        exam, subject = doc.get("exam"), doc.get("subject")
        if exam and subject:
            bank.reading[(exam, subject)] = doc

    # 词表单独一个目录：reading/ 下的文件按 (exam, subject) 互相覆盖，
    # 把高频词塞进 reading/ 会把精读篇目顶掉。
    for doc in _scan(root / "vocab"):
        exam, subject = doc.get("exam"), doc.get("subject")
        if exam and subject:
            bank.vocab[(exam, subject)] = doc

    for doc in _scan(root / "listening"):
        exam, subject = doc.get("exam"), doc.get("subject")
        if exam and subject:
            bank.listening[(exam, subject)] = doc

    # 公式表同样独立成目录：它是「速查」而非「精读/框架」，混进去会互相覆盖
    for doc in _scan(root / "formulas"):
        exam, subject = doc.get("exam"), doc.get("subject")
        if exam and subject:
            bank.formulas[(exam, subject)] = doc

    for doc in _scan(root / "papers"):
        if doc.get("id"):
            bank.papers[doc["id"]] = doc

    return bank


_bank: Bank | None = None
_lock = threading.Lock()


def bank() -> Bank:
    global _bank
    if _bank is None:
        with _lock:
            if _bank is None:
                _bank = _build()
    return _bank


def reset() -> None:
    """测试用：丢弃缓存，下次访问重新读盘。"""
    global _bank
    with _lock:
        _bank = None


# ---------------------------------------------------------------- 目录 ----

def catalog() -> dict:
    b = bank()
    items = []
    for e in b.meta.get("exams") or []:
        subjects = []
        totals = {"questions": 0, "topics": 0, "summaries": 0, "papers": 0}
        for s in e["subjects"]:
            c = b.subject_counts(e["key"], s["key"])
            subjects.append({**s, "counts": c})
            for k in totals:
                totals[k] += c[k]
        items.append({
            "key": e["key"],
            "label": e["label"],
            "short": e.get("short", e["label"]),
            "duration": e.get("duration"),
            "total_score": e.get("total"),
            "subjects": subjects,
            "counts": {**totals, "papers": len(b.papers_of_exam(e["key"]))},
        })
    return {"content_version": b.meta.get("version", 1), "items": items}


def exam_detail(exam: str) -> dict:
    b = bank()
    for item in catalog()["items"]:
        if item["key"] == exam:
            return item
    raise AppError(
        NOT_FOUND, f"考试不存在：{exam}", http_status=404,
        data={"allowed": sorted(b.exams)},
    )


# ------------------------------------------------------------ 框架/知识 ----

def framework(exam: str, subject: str) -> dict:
    b = bank()
    _, s = b.scope(exam, subject)
    fw = b.frameworks.get((exam, subject)) or {}
    topics = []
    for t in fw.get("topics") or []:
        topics.append({
            "id": t["id"],
            "title": t["title"],
            "order": t.get("order"),
            "heat": t.get("heat"),
            "seen_in": t.get("seenIn") or [],
            "points": t.get("points") or [],
            "patterns": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "freq": p.get("freq"),
                    "ask": p.get("ask"),
                    "steps": p.get("steps") or [],
                    "traps": p.get("traps") or [],
                }
                for p in t.get("patterns") or []
            ],
            "question_count": sum(
                1 for q in b.subject_questions(exam, subject) if q.get("topic") == t["id"]
            ),
        })
    return {
        "exam": exam,
        "subject": subject,
        "label": fw.get("label") or s["label"],
        "score": fw.get("score"),
        "pattern": fw.get("pattern"),
        "intro": fw.get("intro"),
        "topics": topics,
        "totals": {
            "topics": len(topics),
            "patterns": sum(len(t["patterns"]) for t in topics),
        },
    }


def knowledge(exam: str, subject: str) -> dict:
    b = bank()
    b.scope(exam, subject)
    doc = b.knowledge.get((exam, subject)) or {}
    items = []
    total = 0
    for block in doc.get("items") or []:
        ks = []
        for k in block.get("knowledge") or []:
            total += 1
            ks.append({
                "id": k["id"],
                "title": k.get("title"),
                "chapter": k.get("chapter"),
                "patterns": k.get("patterns") or [],
                "core": k.get("core"),
                "tip": k.get("tip"),
            })
        items.append({
            "topic": block.get("topic"),
            "topic_title": b.topic_title(exam, subject, block.get("topic") or ""),
            "chapter": block.get("chapter"),
            "knowledge": ks,
        })
    return {
        "exam": exam,
        "subject": subject,
        "book": doc.get("book"),
        "items": items,
        "total": total,
    }


def summaries(exam: str, subject: str) -> dict:
    b = bank()
    b.scope(exam, subject)
    doc = b.summaries.get((exam, subject)) or {}
    groups = [
        {
            "topic": g.get("topic"),
                "title": g.get("title"),
                "recognize": g.get("recognize"),
                "framework": g.get("framework") or [],
                "skills": g.get("skills") or [],
                "traps": g.get("traps") or [],
                "question_ids": g.get("questionIds") or [],
                "suggested_order": g.get("suggestedOrder") or [],
            }
        for g in doc.get("groups") or []
    ]
    return {"exam": exam, "subject": subject, "groups": groups, "total": len(groups)}


# ---------------------------------------------------------------- 题库 ----

def question_card(b: Bank, exam: str, subject: str, q: dict) -> dict:
    return {
        "id": q["id"],
        "topic": q.get("topic"),
        "topic_title": b.topic_title(exam, subject, q.get("topic") or ""),
        "type": q.get("type"),
        "difficulty": q.get("diff"),
        "stem": q.get("stem"),
        "option_count": len(q.get("options") or []),
        "has_passage": bool(q.get("passage")),
        "knowledge_ids": [p.get("id") for p in (q.get("walkthrough") or {}).get("points") or []],
    }


def question_detail(exam: str, subject: str, question_id: str) -> dict:
    b = bank()
    b.scope(exam, subject)
    q = b.questions_by_id.get(question_id)
    if q is None or b.question_scope.get(question_id) != (exam, subject):
        raise AppError(
            NOT_FOUND, f"题目不存在：{question_id}", http_status=404,
            data={"exam": exam, "subject": subject},
        )
    return {
        "id": q["id"],
        "exam": exam,
        "subject": subject,
        "topic": q.get("topic"),
        "topic_title": b.topic_title(exam, subject, q.get("topic") or ""),
        "type": q.get("type"),
        "difficulty": q.get("diff"),
        "stem": q.get("stem"),
        "options": q.get("options") or [],
        "passage": q.get("passage"),
        "ask": q.get("ask") or [],
        "answer": q.get("answer") or {},
        "explain": q.get("explain") or {},
        # 四层讲解：framework → approach → points → solution，顺序即呈现顺序
        "walkthrough": q.get("walkthrough") or {},
    }


def list_questions(
    exam: str,
    subject: str,
    *,
    topic: str | None = None,
    qtype: str | None = None,
    difficulty: int | None = None,
    keyword: str | None = None,
    sort: str = "order",
    page: int = 1,
    size: int = 20,
) -> dict:
    b = bank()
    b.scope(exam, subject)
    rows = b.subject_questions(exam, subject)

    allowed_topics = [t["id"] for t in (b.frameworks.get((exam, subject)) or {}).get("topics") or []]
    if topic and topic not in allowed_topics:
        raise AppError(
            PARAM_ERROR, f"未知专题：{topic}", http_status=400,
            data={"allowed": allowed_topics},
        )

    allowed_types = sorted({q.get("type") for q in rows if q.get("type")})
    if qtype and qtype not in allowed_types:
        raise AppError(
            PARAM_ERROR, f"未知题型：{qtype}", http_status=400,
            data={"allowed": allowed_types},
        )

    kw = keyword.strip().casefold() if keyword else None

    # 在原始顺序上过滤，顺手保留题库下标作为 order，避免同一道题因内容相同被误匹配
    indexed = [
        (i, q)
        for i, q in enumerate(rows)
        if (not topic or q.get("topic") == topic)
        and (not qtype or q.get("type") == qtype)
        and (difficulty is None or q.get("diff") == difficulty)
        and (kw is None or kw in (q.get("stem") or "").casefold())
    ]
    if sort == "difficulty":
        indexed.sort(key=lambda x: (x[1].get("diff") or 0, x[0]))
    # order：保持题库生成顺序（与框架专题顺序一致）

    total = len(indexed)
    start = (page - 1) * size
    window = indexed[start:start + size]
    return {
        "items": [
            {"order": i + 1, **question_card(b, exam, subject, q)} for i, q in window
        ],
        "total": total,
        "page": page,
        "size": size,
    }


# ---------------------------------------------------------------- 套卷 ----

def paper_card(b: Bank, p: dict) -> dict:
    subject = p.get("subject")
    return {
        "id": p["id"],
        "exam": p.get("exam"),
        "subject": subject,
        "scope": "subject" if subject else "full",
        "title": p.get("title"),
        "kind": p.get("kind"),
        "duration": p.get("duration"),
        "total_score": p.get("totalScore"),
        "section_count": len(p.get("sections") or []),
        "question_count": sum(len(s.get("items") or []) for s in p.get("sections") or []),
        "subjects": [x.get("subject") for x in p.get("blueprint") or []],
    }


def list_papers(
    exam: str,
    *,
    subject: str | None = None,
    kind: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    b = bank()
    if exam not in b.exams:
        raise AppError(
            NOT_FOUND, f"考试不存在：{exam}", http_status=404,
            data={"allowed": sorted(b.exams)},
        )
    if subject:
        b.scope(exam, subject)
        rows = b.subject_papers(exam, subject)
    else:
        rows = b.papers_of_exam(exam)
    if kind:
        rows = [p for p in rows if p.get("kind") == kind]
    rows.sort(key=lambda p: p["id"])
    total = len(rows)
    start = (page - 1) * size
    return {
        "items": [paper_card(b, p) for p in rows[start:start + size]],
        "total": total,
        "page": page,
        "size": size,
    }


def _paper_item(b: Bank, section: dict, item: Any) -> dict:
    """把「字符串 id」与「内嵌快照」统一成一种形状。

    - 字符串：题库里的题，回查完整字段；
    - dict：套卷内嵌快照。408 的设计题现在按「先单科后组合」进单科题库，
      整卷/专项卷里的快照都带单科库 id，因此 in_bank 应为 true；
      若 id 不在题库（历史游离快照）则只输出快照字段并标 in_bank=false。
    """
    if isinstance(item, str):
        qid, snapshot = item, {}
    else:
        qid, snapshot = item.get("id"), item
    q = b.questions_by_id.get(qid)
    base = q or snapshot
    walkthrough = base.get("walkthrough") or {}
    scope = b.question_scope.get(qid)
    topic_title = (
        b.topic_title(scope[0], scope[1], base.get("topic") or "")
        if scope else (base.get("topic") or "")
    )
    return {
        "id": qid,
        "order": None,  # 由调用方按分区内顺序填
        "type": base.get("type") or section.get("type"),
        "topic": base.get("topic"),
        "topic_title": topic_title,
        "difficulty": base.get("diff"),
        "stem": base.get("stem"),
        "options": base.get("options") or [],
        "ask": base.get("ask") or [],
        "answer": base.get("answer"),
        "explain": base.get("explain"),
        "walkthrough": walkthrough or None,
        "score": (item.get("score") if isinstance(item, dict) else None)
        or section.get("perScore"),
        "in_bank": q is not None,
    }


def paper_detail(paper_id: str) -> dict:
    b = bank()
    p = b.papers.get(paper_id)
    if p is None:
        raise AppError(
            NOT_FOUND, f"套卷不存在：{paper_id}", http_status=404,
        )
    sections = []
    for sec in p.get("sections") or []:
        items = [_paper_item(b, sec, it) for it in sec.get("items") or []]
        for i, it in enumerate(items, start=1):
            it["order"] = i
        sections.append({
            "no": sec.get("no"),
            "name": sec.get("name"),
            "type": sec.get("type"),
            "range": sec.get("range"),
            "score": sec.get("score"),
            "per_score": sec.get("perScore"),
            "note": sec.get("note"),
            "items": items,
        })
    return {
        "id": p["id"],
        "exam": p.get("exam"),
        "subject": p.get("subject"),
        "scope": "subject" if p.get("subject") else "full",
        "title": p.get("title"),
        "kind": p.get("kind"),
        "duration": p.get("duration"),
        "total_score": p.get("totalScore"),
        "disclaimer": p.get("disclaimer"),
        "blueprint": p.get("blueprint") or [],
        "sections": sections,
        "counts": {
            "sections": len(sections),
            "questions": sum(len(s["items"]) for s in sections),
        },
    }


# ---------------------------------------------------------------- 精读 ----

def reading_index(exam: str, subject: str) -> dict:
    b = bank()
    b.scope(exam, subject)
    doc = b.reading.get((exam, subject)) or {}
    items = []
    for p in doc.get("passages") or []:
        items.append({
            "id": p["id"],
            "title": p.get("title"),
            "word_count": len((p.get("text") or "").split()),
            "paragraph_count": len(p.get("paragraphs") or []),
            "vocab_count": len(p.get("vocab") or []),
            "sentence_count": len(p.get("sentences") or []),
            "question_ids": [m.get("qid") for m in p.get("questionMap") or []],
        })
    return {"exam": exam, "subject": subject, "items": items, "total": len(items)}


def reading_passage(exam: str, subject: str, passage_id: str) -> dict:
    b = bank()
    b.scope(exam, subject)
    doc = b.reading.get((exam, subject)) or {}
    for p in doc.get("passages") or []:
        if p["id"] == passage_id:
            # 显式列出字段而不是 `**p`：数据文件里是 questionMap / falseFriends，
            # 对外统一 snake_case，避免同一个响应里两种命名风格并存。
            return {
                "id": p["id"],
                "exam": exam,
                "subject": subject,
                "title": p.get("title"),
                "text": p.get("text"),
                "word_count": len((p.get("text") or "").split()),
                "paragraphs": p.get("paragraphs") or [],
                "vocab": p.get("vocab") or [],
                "sentences": p.get("sentences") or [],
                "question_map": p.get("questionMap") or [],
                "takeaway": p.get("takeaway") or [],
                "false_friends": p.get("falseFriends") or [],
                "synonyms": p.get("synonyms") or [],
            }
    raise AppError(
        NOT_FOUND, f"精读文章不存在：{passage_id}", http_status=404,
        data={"exam": exam, "subject": subject},
    )


# ---------------------------------------------------------------- 词表 ----

def vocab_index(exam: str, subject: str) -> dict:
    """阅读高频词表：按「态度 / 论证 / 题材 / 熟词僻义 / 动词」分组。

    没有词表的科目返回空列表而不是 404 —— 与 reading_index 同一约定：
    集合存在但为空，和资源不存在是两件事。
    """
    b = bank()
    b.scope(exam, subject)
    doc = b.vocab.get((exam, subject)) or {}
    groups = []
    total = 0
    for g in doc.get("groups") or []:
        words = g.get("words") or []
        total += len(words)
        groups.append({
            "id": g.get("id"),
            "title": g.get("title"),
            "desc": g.get("desc"),
            "words": words,
            "count": len(words),
        })
    return {
        "exam": exam,
        "subject": subject,
        "note": doc.get("note"),
        "groups": groups,
        "total": total,
    }


# ---------------------------------------------------------------- 听力 ----

def listening_index(exam: str, subject: str) -> dict:
    """听力训练单元：场景词 / 同义替换 / 速记 / 复述。

    考研英语初试不考听力，这里的单元服务复试与四六级，
    因此数据里不含音频，练的是「听辨要点」而不是「听音频答题」。
    """
    b = bank()
    b.scope(exam, subject)
    doc = b.listening.get((exam, subject)) or {}
    units = doc.get("units") or []
    return {
        "exam": exam,
        "subject": subject,
        "note": doc.get("note"),
        "units": units,
        "total": len(units),
    }


def formulas_index(exam: str, subject: str) -> dict:
    """公式与二级结论速查：按章 → 分组 → 条目三级组织。

    条目里 tex 是 KaTeX 源码，前端渲染；note 用来说明「什么时候用」，
    比公式本身更容易被忘掉，所以必须一起返回。
    """
    b = bank()
    b.scope(exam, subject)
    doc = b.formulas.get((exam, subject)) or {}
    chapters = []
    total = 0
    for ch in doc.get("chapters") or []:
        groups = []
        for g in ch.get("groups") or []:
            items = g.get("items") or []
            total += len(items)
            groups.append({
                "title": g.get("title"),
                "items": items,
                "count": len(items),
            })
        chapters.append({
            "id": ch.get("id"),
            "title": ch.get("title"),
            "note": ch.get("note"),
            "groups": groups,
        })
    return {
        "exam": exam,
        "subject": subject,
        "note": doc.get("note"),
        "chapters": chapters,
        "total": total,
    }


# ---------------------------------------------------------------- 判分 ----

_WS = re.compile(r"[\s\u3000]+")
_TRAILING = "。．.,，;；:："


def _norm_text(s: str) -> str:
    return _WS.sub("", s).strip().casefold().rstrip(_TRAILING)


def grade(exam: str, subject: str, answers: list[dict]) -> dict:
    """批量判分。整批要么全通过，要么整批拒绝——不做「部分判分」。

    calc / design / analysis 一律 UNGRADED：接口回声参考解法，不给「对不对」，
    避免把主观题当成字符串比对（那会训练出错误的答题习惯）。
    """
    b = bank()
    b.scope(exam, subject)

    ids = [a["question_id"] for a in answers]
    duplicated = sorted({i for i in ids if ids.count(i) > 1})
    if duplicated:
        raise AppError(
            PARAM_ERROR, "同一题在本次提交里出现多次", http_status=400,
            data={"duplicate_ids": duplicated},
        )

    unknown = [i for i in ids if b.question_scope.get(i) != (exam, subject)]
    if unknown:
        raise AppError(
            PARAM_ERROR, f"题目不属于 {exam}/{subject}：{', '.join(unknown[:5])}",
            http_status=400, data={"unknown_ids": unknown},
        )

    items = []
    for a in answers:
        q = b.questions_by_id[a["question_id"]]
        qtype = q.get("type")
        expected = q.get("answer") or {}
        entry = {
            "question_id": q["id"],
            "type": qtype,
            "verdict": "UNGRADED",
            "your_answer": None,
            "expected": expected,
            "explain": q.get("explain") or {},
            "walkthrough": q.get("walkthrough") or {},
        }

        if qtype == CHOICE:
            choice = a.get("choice")
            if choice is None:
                raise AppError(
                    PARAM_ERROR, f"{q['id']} 是单选题，需要 choice", http_status=400,
                    data={"question_id": q["id"], "expected_field": "choice"},
                )
            options = q.get("options") or []
            if not 0 <= choice < len(options):
                raise AppError(
                    PARAM_ERROR, f"{q['id']} 的 choice 越界", http_status=400,
                    data={"question_id": q["id"], "option_count": len(options)},
                )
            entry["your_answer"] = choice
            entry["verdict"] = "CORRECT" if choice == expected.get("correct") else "INCORRECT"

        elif qtype == MULTI:
            choices = a.get("choices")
            if not choices:
                raise AppError(
                    PARAM_ERROR, f"{q['id']} 是多选题，需要 choices 非空数组", http_status=400,
                    data={"question_id": q["id"], "expected_field": "choices"},
                )
            options = q.get("options") or []
            if any(not isinstance(c, int) or not 0 <= c < len(options) for c in choices):
                raise AppError(
                    PARAM_ERROR, f"{q['id']} 的 choices 含越界下标", http_status=400,
                    data={"question_id": q["id"], "option_count": len(options)},
                )
            picked = sorted(set(choices))
            entry["your_answer"] = picked
            entry["verdict"] = (
                "CORRECT" if picked == sorted(expected.get("correct") or []) else "INCORRECT"
            )

        elif qtype == BLANK:
            text = a.get("text")
            if text is None or not str(text).strip():
                raise AppError(
                    PARAM_ERROR, f"{q['id']} 是填空题，需要 text", http_status=400,
                    data={"question_id": q["id"], "expected_field": "text"},
                )
            entry["your_answer"] = text
            entry["verdict"] = (
                "CORRECT" if _norm_text(str(text)) == _norm_text(str(expected.get("text", "")))
                else "INCORRECT"
            )

        items.append(entry)

    correct = sum(1 for i in items if i["verdict"] == "CORRECT")
    incorrect = sum(1 for i in items if i["verdict"] == "INCORRECT")
    return {
        "exam": exam,
        "subject": subject,
        "items": items,
        "summary": {
            "total": len(items),
            "correct": correct,
            "incorrect": incorrect,
            "ungraded": len(items) - correct - incorrect,
            "accuracy": round(correct / (correct + incorrect), 4) if correct + incorrect else None,
        },
    }
