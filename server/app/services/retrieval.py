"""课程知识检索（RAG-lite）。

Phase 6「AI 深化」的核心补课：阶段 5 的 CppCat 只有 6 个 prompt 模板，**完全不认识
真实课程资料**，回答无法锚定到 20 章内容与题库。本模块用离线 BM25 倒排索引把课程
Markdown 与题库建成可检索语料，供 `ai_provider.build_messages` 注入"相关资料"片段，
落实架构文档 §8.2 的「当前章节(目标+知识点摘要)」上下文注入——且零外部向量库依赖、
可在无网络/无 DB 环境下对纯语料检索并单测。

设计要点：
- 中英文混合分词：英文/数字按词；中文按「单字 + 二元」切分（轻量、无需分词器）。
- BM25 评分（k1=1.5, b=0.75），idf 带平滑。
- 支持 subject / chapter_id 过滤（章节上下文优先）。
- 题库语料每条带 source_ref（真题依据），检索命中即把依据回传给模型与前端。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

# 轻量停用词（中英文常见虚词/标点残渣），降低噪声、提升相关性。
_STOP = {
    "的", "了", "和", "与", "及", "在", "是", "我", "你", "他", "她", "它", "们",
    "这", "那", "有", "个", "不", "也", "都", "就", "而", "或", "中", "为", "对",
    "a", "an", "the", "of", "to", "in", "is", "are", "and", "or", "for", "with",
    "this", "that", "it", "we", "you", "they", "on", "at", "by",
}


@dataclass
class Doc:
    """一条可检索文档。"""

    id: str
    title: str
    text: str
    subject: str = ""
    chapter_id: int | None = None
    meta: dict = field(default_factory=dict)  # 额外信息，如 source_ref / difficulty / type


@dataclass
class Hit:
    doc: Doc
    score: float
    snippet: str


_CJK = re.compile(r"[一-鿿]+")
_ASCII = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens: list[str] = list(_ASCII.findall(text))
    for run in _CJK.findall(text):
        for i, ch in enumerate(run):
            tokens.append(ch)  # 单字
            if i + 1 < len(run):
                tokens.append(run[i : i + 2])  # 二元
    return [t for t in tokens if t not in _STOP and len(t) > 0]


def _snippet(text: str, terms: list[str], width: int = 80) -> str:
    """取首个命中词附近的片段，用于向前端/模型展示依据摘要。"""
    if not text:
        return ""
    for t in terms:
        if len(t) >= 2:  # 仅用中文二元/英文词定位，避免单字噪声
            idx = text.find(t)
            if idx >= 0:
                start = max(0, idx - width // 3)
                end = min(len(text), start + width)
                return text[start:end].strip().replace("\n", " ")
    return text[:width].strip().replace("\n", " ")


class KnowledgeIndex:
    """BM25 倒排索引，纯内存、可单测。"""

    def __init__(self, docs: list[Doc]) -> None:
        self.docs = docs
        # 标题参与检索（如「智能指针」标题贡献"指针"词），正文用于摘要片段。
        self._terms: list[list[str]] = [_tokenize(f"{d.title}\n{d.text}") for d in docs]
        self._df: dict[str, int] = {}
        for terms in self._terms:
            for t in set(terms):
                self._df[t] = self._df.get(t, 0) + 1
        self._n = len(docs)
        self._avgdl = (sum(len(t) for t in self._terms) / self._n) if self._n else 0.0
        self._idf_cache: dict[str, float] = {}

    def _idf(self, term: str) -> float:
        if term not in self._idf_cache:
            df = self._df.get(term, 0)
            # BM25 idf（带 +0.5 平滑，避免 df=0 时出现负无穷）
            self._idf_cache[term] = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
        return self._idf_cache[term]

    def retrieve(
        self,
        query: str,
        k: int = 4,
        subject: str | None = None,
        chapter_id: int | None = None,
    ) -> list[Hit]:
        q_terms = _tokenize(query)
        if not q_terms or self._n == 0:
            return []
        k1, b = 1.5, 0.75
        scores = [0.0] * self._n
        for qt in q_terms:
            idf = self._idf(qt)
            for i, terms in enumerate(self._terms):
                f = terms.count(qt)
                if f == 0:
                    continue
                dl = len(terms)
                denom = f + k1 * (1 - b + b * dl / (self._avgdl or 1))
                scores[i] += idf * (f * (k1 + 1)) / denom

        ranked = sorted(range(self._n), key=lambda i: scores[i], reverse=True)
        hits: list[Hit] = []
        for i in ranked:
            if scores[i] <= 0:
                break
            d = self.docs[i]
            if subject and d.subject and d.subject != subject:
                continue
            if chapter_id is not None and d.chapter_id is not None and d.chapter_id != chapter_id:
                continue
            hits.append(Hit(doc=d, score=round(scores[i], 4), snippet=_snippet(d.text, q_terms)))
            if len(hits) >= k:
                break
        return hits


def build_corpus_from_content(content_dir: str | Path) -> list[Doc]:
    """扫描 content/ 下所有 Markdown，按路径推断 subject 与 chapter_id。"""
    docs: list[Doc] = []
    base = Path(content_dir)
    if not base.exists():
        return docs
    for md in sorted(base.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(base)
        parts = rel.parts
        subject = parts[0] if parts else ""
        chapter_id: int | None = None
        m = re.search(r"ch(\d+)", str(rel))
        if m:
            chapter_id = int(m.group(1))
        docs.append(
            Doc(
                id=f"content:{rel.as_posix()}",
                title=md.stem,
                text=text,
                subject=subject,
                chapter_id=chapter_id,
                meta={"kind": "lesson"},
            )
        )
    return docs


_SOURCE_LABEL = {
    "self": "CppMind 自编",
    "leetcode": "LeetCode 真题",
    "nowcoder": "牛客真题",
}


def build_corpus_from_exercises(rows: list[dict]) -> list[Doc]:
    """把题库行转为检索文档。rows 字段：id/chapter_id/type/difficulty/title/
    content_md/explanation/source/external_url/external_id/tags(list[str])。"""
    docs: list[Doc] = []
    for r in rows:
        title = r.get("title") or f"题 {r.get('id')}"
        body = "\n".join(
            x for x in (r.get("content_md") or "", r.get("explanation") or "") if x
        )
        src = r.get("source") or "self"
        source_ref = _SOURCE_LABEL.get(src, "CppMind 自编")
        if r.get("external_url"):
            source_ref += f"（{r['external_url']}）"
        elif r.get("external_id"):
            source_ref += f"（编号 {r['external_id']}）"
        tags = r.get("tags") or []
        text = f"{title}\n{body}\n标签：{' '.join(tags)}"
        docs.append(
            Doc(
                id=f"exercise:{r.get('id')}",
                title=title,
                text=text,
                subject=r.get("subject", ""),
                chapter_id=r.get("chapter_id"),
                meta={
                    "kind": "exercise",
                    "type": r.get("type"),
                    "difficulty": r.get("difficulty"),
                    "source_ref": source_ref,
                    "tags": tags,
                },
            )
        )
    return docs


# ---------------------------------------------------------------------------
# 进程内索引缓存：内容目录语料只在磁盘变化时重建；题库语料由端点按 TTL 刷新。
# ---------------------------------------------------------------------------
_INDEX_CACHE: dict[str, tuple[float, KnowledgeIndex]] = {}
_EXERCISE_DOCS: list[Doc] = []
_TTL_S = 300.0


def set_exercise_docs(docs: list[Doc]) -> None:
    """端点每次从 DB 拉到题库后注入，供 get_index 合并。"""
    global _EXERCISE_DOCS
    _EXERCISE_DOCS = docs


def get_index(content_dir: str | Path, now: float | None = None) -> KnowledgeIndex:
    """返回合并「课程内容 + 题库」的索引，5 分钟缓存避免重复建索引。"""
    import time

    now = now or time.time()
    key = str(Path(content_dir))
    cached = _INDEX_CACHE.get(key)
    if cached and now - cached[0] < _TTL_S:
        return cached[1]
    lesson_docs = build_corpus_from_content(content_dir)
    idx = KnowledgeIndex(lesson_docs + _EXERCISE_DOCS)
    _INDEX_CACHE[key] = (now, idx)
    return idx
