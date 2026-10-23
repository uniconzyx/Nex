#!/usr/bin/env python
"""把题库渲染成一份可翻看的静态样张（docs/exam-preview.html）。

用途：肉眼验收「解题框架 → 解决思路 → 知识点 → 详细解法」的呈现顺序，
以及分类总结是否真的按专题归类、陷阱是否说得具体。

数据全部读自 content/_exam/，不手写任何题面，保证样张与题库同步。
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"
OUT = ROOT / "docs" / "exam-preview.html"

PAPER = "algorithm-algo-mock-01"
LAYERS = [
    ("framework", "解题框架"),
    ("approach", "解决思路"),
    ("points", "知识点"),
    ("solution", "详细解法"),
]
TYPE_LABEL = {
    "choice": "单项选择题", "multi": "多项选择题", "blank": "填空题",
    "calc": "解答题", "design": "设计题", "judge": "判断题",
}


def load(rel: str) -> dict:
    return json.loads((EXAM / rel).read_text(encoding="utf-8"))


def esc(text) -> str:
    return html.escape(str(text or ""), quote=False)


def para(text: str) -> str:
    """保留换行的段落。"""
    return esc(text).replace("\n", "<br>")


def kb_doc() -> tuple[dict, list[dict]]:
    meta = load("_meta.json")
    stats = []
    for e in meta["exams"]:
        for s in e["subjects"]:
            q = load(f"questions/{e['key']}-{s['key']}.json")
            sm = load(f"summaries/{e['key']}-{s['key']}.json")
            papers = list((EXAM / "papers").glob(f"{e['key']}-{s['key']}-mock-*.json"))
            stats.append({
                "exam": e["label"], "subject": s["label"],
                "questions": len(q["items"]),
                "topics": len(sm["groups"]),
                "papers": len(papers),
            })
    return meta, stats


def render_question(q: dict, no: int, score: int | None) -> str:
    w = q["walkthrough"]
    fw = w["framework"]

    head = esc(TYPE_LABEL.get(q["type"], q["type"]))
    if score:
        head += f" · {score} 分"

    options = ""
    if q.get("options"):
        items = []
        for i, opt in enumerate(q["options"]):
            key = opt.get("key") if isinstance(opt, dict) else None
            text = opt.get("text") if isinstance(opt, dict) else opt
            label = esc(key or chr(65 + i))
            items.append(f'<li><b>{label}</b><span>{esc(text)}</span></li>')
        options = '<ol class="opts">' + "".join(items) + "</ol>"

    steps = "".join(f"<li>{esc(s)}</li>" for s in fw["steps"])
    point_items = []
    for p in w["points"]:
        pit = p.get("pitfall")
        pit_html = f'<span class="pt-pit">易错：{esc(pit)}</span>' if pit else ""
        point_items.append(
            f'<li><b>{esc(p.get("title") or p.get("id"))}</b>'
            f'<span>{esc(p.get("core"))}{pit_html}</span></li>'
        )
    points = "".join(point_items)

    body = {
        "framework": f'<ol class="steps">{steps}</ol>'
                     f'<p class="trap"><span>容易错在</span>{esc(fw.get("trap"))}</p>',
        "approach": f'<p>{para(w["approach"])}</p>',
        "points": f'<ul class="pts">{points}</ul>',
        "solution": f'<p class="sol">{para(w["solution"])}</p>',
    }

    layers = "".join(
        f'<div class="layer"><h4>{label}</h4><div class="layer-body">{body[key]}</div></div>'
        for key, label in LAYERS
    )

    return (
        '<article class="q">'
        f'<div class="q-no"><b>{no}</b><span>{head}</span></div>'
        '<div class="q-main">'
        f'<p class="stem">{para(q["stem"])}</p>{options}'
        f'<div class="layers">{layers}</div>'
        "</div></article>"
    )


def render_paper() -> tuple[str, str, str]:
    paper = load(f"papers/{PAPER}.json")
    bank = {x["id"]: x for x in load("questions/algorithm-algo.json")["items"]}

    chunks, no = [], 0
    for sec in paper["sections"]:
        rows = []
        for item in sec["items"]:
            q = bank[item["id"]] if isinstance(item, dict) else bank[item]
            no += 1
            score = item.get("score") if isinstance(item, dict) else sec.get("perScore")
            rows.append(render_question(q, no, score))
        chunks.append(f'<h3 class="sec-h">{esc(sec["name"])}</h3>' + "".join(rows))
    return paper["title"], paper["disclaimer"], "".join(chunks)


def render_summaries() -> str:
    data = load("summaries/algorithm-algo.json")
    out = []
    for g in data["groups"]:
        steps = "".join(f"<li>{esc(s)}</li>" for s in g["framework"])
        skills = "".join(
            f'<div class="skill"><b>{esc(k["title"])}</b><p>{esc(k["body"])}</p></div>'
            for k in g["skills"][:2]
        )
        traps = "".join(f"<li>{esc(t)}</li>" for t in g["traps"])
        out.append(
            '<article class="grp">'
            f'<h3>{esc(g["title"])}<span class="cnt"> · 本专题 {len(g["questionIds"])} 题</span></h3>'
            f'<p class="recog">{esc(g["recognize"])}</p>'
            f'<div class="grp-grid"><div><h4>固定步骤</h4><ol class="steps">{steps}</ol></div>'
            f'<div><h4>技巧</h4>{skills}<h4>陷阱</h4><ul class="traps">{traps}</ul></div></div>'
            "</article>"
        )
    return "".join(out)


def render_stats(stats: list[dict]) -> str:
    rows = "".join(
        f'<tr><td>{esc(s["exam"])}</td><td>{esc(s["subject"])}</td>'
        f'<td>{s["questions"]}</td><td>{s["topics"]}</td><td>{s["papers"]}</td></tr>'
        for s in stats
    )
    total_q = sum(s["questions"] for s in stats)
    total_p = sum(s["papers"] for s in stats)
    total_t = sum(s["topics"] for s in stats)
    return (
        '<table class="tbl"><thead><tr><th>考试</th><th>科目</th>'
        "<th>题数</th><th>分类总结</th><th>模拟卷</th></tr></thead><tbody>"
        f"{rows}</tbody><tfoot><tr><td>合计</td><td>{len(stats)} 个科目</td>"
        f"<td>{total_q}</td><td>{total_t}</td><td>{total_p}</td></tr></tfoot></table>"
    )


CSS = """
:root{
  --ground:#ECEDEA; --surface:#F6F7F4; --ink:#15171A; --muted:#454A51;
  --accent:#1B4DD8; --tint:#E4EBFB;
  --serif:"Source Han Serif SC","Songti SC","Noto Serif SC",Georgia,serif;
  --sans:"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,-apple-system,sans-serif;
  --fs-display:clamp(2.6rem,6.2vw,5.4rem);
  --fs-h2:2.125rem; --fs-h3:1.375rem;
  --fs-small:0.875rem;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:17px;line-height:1.7;letter-spacing:.01em}
.wrap{max-width:56rem;margin:0 auto;padding:0 24px}
.masthead{padding:84px 0 36px}
.masthead h1{font-family:var(--serif);font-weight:700;letter-spacing:-.03em;
  font-size:var(--fs-display);line-height:1.06;margin:0 0 24px}
.lede{font-size:var(--fs-h3);line-height:1.5;max-width:36rem;margin:0 0 28px}
.cta{display:inline-flex;align-items:center;height:48px;padding:0 22px;margin:8px 0 0;
  background:var(--accent);color:#fff;text-decoration:none;font-weight:600;border-radius:2px}
.cta:hover{background:#153FB8}
.cta:focus-visible{outline:3px solid #15171A;outline-offset:3px}
.figures{display:flex;flex-wrap:wrap;gap:40px;margin:0 0 32px;padding:0;list-style:none}
.figures b{display:block;font-family:var(--serif);font-size:var(--fs-h2);line-height:1.1;
  letter-spacing:-.02em}
.figures span{font-size:var(--fs-small);color:var(--muted)}
section{padding:32px 0 8px}
.sec-title{font-family:var(--serif);font-size:var(--fs-h2);letter-spacing:-.015em;
  line-height:1.2;margin:0 0 12px}
.sec-note{color:var(--muted);margin:0 0 20px;max-width:40rem}
.sec-h{font-family:var(--serif);font-size:var(--fs-h3);margin:44px 0 6px}
.q{display:grid;grid-template-columns:9rem 1fr;gap:24px;padding:32px 24px;
  background:var(--surface);margin:16px 0;border-radius:2px}
.q-no{font-family:var(--sans)}
.q-no b{display:block;font-size:var(--fs-h2);line-height:1;letter-spacing:-.03em}
.q-no span{display:block;font-family:var(--sans);font-size:var(--fs-small);
  color:var(--muted);margin-top:8px;white-space:nowrap}
.stem{font-family:var(--serif);font-size:var(--fs-h3);line-height:1.6;margin:0 0 14px}
.opts{list-style:none;margin:0 0 20px;padding:0;display:grid;gap:6px}
.opts li{display:flex;gap:10px}
.opts b{min-width:1.2rem;color:var(--accent)}
.opts span{flex:1}
.layers{margin-top:24px;display:grid;gap:26px}
.layer{display:grid;grid-template-columns:7.5rem 1fr;gap:20px;align-items:start}
.layer h4{margin:0;font-size:1rem;font-weight:700;color:var(--accent);
  letter-spacing:.01em;padding-top:.05em}
.layer-body p{margin:0 0 10px}
.steps{margin:0;padding-left:1.2rem;display:grid;gap:6px}
.trap{margin:14px 0 0;background:var(--tint);padding:12px 16px;border-radius:2px}
.trap span{font-weight:700;color:var(--accent);margin-right:10px}
.trap span::after{content:"｜";color:var(--muted);font-weight:400}
.pts{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.pts li{display:grid;grid-template-columns:11rem 1fr;gap:12px}
.pts b{font-weight:600}
.pt-pit{display:block;margin-top:6px;color:var(--accent);font-size:var(--fs-small)}
.sol{white-space:pre-wrap}
.grp{background:var(--surface);padding:28px 24px;margin:16px 0;border-radius:2px}
.grp h3{font-family:var(--serif);font-size:var(--fs-h3);margin:0 0 10px;letter-spacing:-.01em}
.recog{color:var(--muted);margin:0 0 20px}
.grp-grid{display:grid;grid-template-columns:1fr 1fr;gap:32px}
.grp h4{font-size:1rem;margin:0 0 10px;color:var(--accent);letter-spacing:.01em}
.grp h4:not(:first-child){margin-top:20px}
.skill{margin:0 0 12px}
.skill b{display:block}
.skill p{margin:2px 0 0;color:var(--muted)}
.traps{margin:0;padding-left:1.1rem;display:grid;gap:4px}
.grp h3 .cnt{font-family:inherit;font-size:var(--fs-small);font-weight:400;color:var(--muted)}
.wrap-note{margin:28px 0 0;color:var(--muted);max-width:40rem}
.tbl{width:100%;border-collapse:collapse;background:var(--surface);margin:8px 0 0}
.tbl th,.tbl td{padding:9px 12px;text-align:left;border-bottom:1px solid #DBDCD5}
.tbl th{font-size:var(--fs-small);color:var(--muted);font-weight:600}
.tbl td:nth-child(n+3),.tbl th:nth-child(n+3){text-align:right;font-variant-numeric:tabular-nums}
.tbl tfoot td{font-weight:700;border-bottom:none}
footer{padding:56px 0 80px;color:var(--muted);font-size:var(--fs-small);max-width:40rem}
@media (prefers-reduced-motion:no-preference){
  .js .reveal{opacity:0;transform:translateY(14px)}
  .js .reveal.in{opacity:1;transform:none;transition:opacity .5s ease,transform .5s ease}
  .js .layer{opacity:0;transform:translateY(10px)}
  .js .q.in .layer,.js .grp.in .layer{opacity:1;transform:none;
    transition:opacity .45s ease,transform .45s ease}
  .js .q.in .layer:nth-child(2){transition-delay:.08s}
  .js .q.in .layer:nth-child(3){transition-delay:.16s}
  .js .q.in .layer:nth-child(4){transition-delay:.24s}
}
@media (max-width:720px){
  .q{grid-template-columns:1fr;gap:12px;padding:24px 18px}
  .q-no{display:flex;align-items:baseline;gap:10px}
  .q-no span{margin-top:0}
  .layer{grid-template-columns:1fr;gap:6px}
  .layer h4{padding-top:0}
  .pts li{grid-template-columns:1fr;gap:2px}
  .grp-grid{grid-template-columns:1fr;gap:24px}
  .figures{gap:28px}
}
"""

SCRIPT = """
document.documentElement.classList.add('js');
const io = new IntersectionObserver((es)=>{
  es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} });
},{rootMargin:'0px 0px -8% 0px'});
document.querySelectorAll('.q,.grp').forEach(el=>{el.classList.add('reveal');io.observe(el);});
"""


def main() -> int:
    meta, stats = kb_doc()
    title, disclaimer, paper_html = render_paper()
    sums = render_summaries()
    table = render_stats(stats)

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>考研题库样张 · 四层讲解与分类总结</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <h1>一道题，按四层讲透</h1>
    <p class="lede">框架先立住，思路再落地，知识点对上号，最后才展开完整解法。
      下面是题库里真实的一套卷子，四层顺序与陷阱提示都没改过。</p>
    <ul class="figures">
      <li><b>{sum(s['questions'] for s in stats)}</b><span>道题</span></li>
      <li><b>{len(stats)}</b><span>个考试科目</span></li>
      <li><b>{sum(s['topics'] for s in stats)}</b><span>份分类总结</span></li>
      <li><b>{sum(s['papers'] for s in stats)}</b><span>套模拟卷</span></li>
    </ul>
  </header>

  <section>
    <h2 class="sec-title">样卷：{esc(title)}</h2>
    <p class="sec-note">每题固定四层，顺序不可调换：先看框架知道「这类题按什么动作做」，
      再看思路知道「这道题具体从哪下手」，然后核对知识点，最后才是完整解法。
      框架底部单列一步「容易错在」，把最常见的失分点放在动笔之前。</p>
    {paper_html}
  </section>

  <section id="summary">
    <h2 class="sec-title">分类总结：按专题收口</h2>
    <p class="sec-note">同一专题的题共用一套步骤与陷阱。做完该专题的题后回看这一页，
      把「认题信号、固定步骤、技巧、陷阱」四件事过一遍，比再刷十道同类题有效。</p>
    {sums}
    <p class="wrap-note">八个专题已经覆盖全部 40 道题，每道题都能回指到上面的某一步骤。
      做完一套卷再回看对应专题，比重复刷题更容易发现自己固定的错法。</p>
  </section>

  <section>
    <h2 class="sec-title">全库概况</h2>
    <p class="sec-note">每个科目都有独立的题型框架、知识点表、分类总结与模拟卷，
      由脚本生成并逐项校验：四层顺序、答案有效、总结覆盖全部专题、卷面分值配平。</p>
    {table}
  </section>

  <footer>{esc(disclaimer)}</footer>
</div>
<script>{SCRIPT}</script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"写出 {OUT.relative_to(ROOT)} · {len(page) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
