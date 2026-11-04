# -*- coding: utf-8 -*-
"""收尾：最后 7 条锚点漂移的精确修正（agent 5 章 6 条 + ml-ch05 1 条）。

这批不是整章虚构，而是「锚点措辞与真实小节对不齐」：
  · agent-ch02#2  §2.结构化输出的三种机制 → 真实标题是「1. 三种机制：能力不同，别混着用」
  · agent-ch03#2  §3.推理能力从哪来 → 该章无此小节，改指真实的小节
  · agent-ch05#1/2 「§数据·主题…」这种写法没有任何编号与标题原文
  · agent-ch11#6  §03 多智能体：SOP 如何被编码进角色 → 真实是「3. 多智能体：角色分工、handoff、共享黑板与成本爆炸」
  · agent-ch12#4  §01 毛利率不是净利率 → 真实是「2. 毛利结构诊断」「1. 三种计费模式」
  · ml-ch05#4     §1 类别特征处理 → 该章无此小节，真实是「3. 特征抽样与去相关」
"""
import json
import os
import re

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

# (学科, 章 id, 第几条 1-based) -> 新 note
FIX: dict[tuple[str, str, int], str] = {
    ("agent", "agent-ch02", 2):
        "§2.1 1. 三种机制：能力不同，别混着用 · §2.2 2. 输出契约：Schema 怎么写才不容易坏："
        "`examples/` 下 function calling / structured outputs 的 notebook 直接可跑，"
        "照它的 schema 写一遍，就看懂「JSON mode / 函数调用 / 严格 schema」三者的差别——"
        "第一节讲能力边界，第二节讲为什么宽松 schema 一定会坏；"
        "两节合起来才是本章「把自然语言当接口」的完整答案",

    ("agent", "agent-ch03", 2):
        "§2.5 5. 单位成本的三个杠杆 · §3.2 2. 成本对比：算「每百万 token 的边际成本」"
        "而不是「显卡多少钱」："
        "`inference/` 目录下的推理代码与技术报告里的训练/推理成本拆分，"
        "是「MoE 为何能把成本压下来」的第一手依据，别只看二手解读；"
        "§2.5 讲的是同一笔钱怎么在输入/缓存/输出三处压，"
        "§3.2 讲的是自建时该怎么折算——"
        "两者口径必须一致（都算边际成本），否则「本地便宜」只是摊错了分母",

    ("agent", "agent-ch05", 1):
        "§1.2 主题二：切块策略——固定长度、语义块、父子块与重叠的代价 · "
        "§2.2 主题二：RRF 融合与 cross-encoder 重排的性价比："
        "`libs/text-splitters/` 里每种切块器都是独立类且带参数说明，"
        "把它和 `libs/retrievers/` 的 ensemble retriever（RRF）接起来跑，"
        "就能实测「重叠多少、块多大」对召回的影响；"
        "第一节决定候选池的质量上限，第二节决定从池里捞出来的精度——"
        "召回差要先回头查切块，而不是先换重排模型",

    ("agent", "agent-ch05", 2):
        "§1.1 主题一：文档解析——版面、表格、扫描件是三道坎 · "
        "§2.3 主题三：查询改写与多跳，补召回的最后一公里："
        "`llama-index-core/` 的 node parser 与 query transform 是分开的两层，"
        "读这两层的接口边界，就看懂「解析/切块」与「改写/召回」为什么不该耦合；"
        "本章 §3.1「Recall@K、MRR、nDCG」量的正是这两层各自的贡献——"
        "分开量，才知道该修解析还是该修改写",

    ("agent", "agent-ch11", 6):
        "§3.3 3. 多智能体：角色分工、handoff、共享黑板与成本爆炸 · "
        "§3.2 2. 终止条件与死循环防护：三个检测器的分工："
        "`metagpt/roles/` 每个角色类都带 `_observe` / `_think` / `_act` 三段，"
        "把本章「角色 = 职责 + 可用动作 + 终止条件」落成了类结构；"
        "注意它同时给了「成本随角色数超线性增长」的反面——"
        "角色越多，黑板越大，handoff 越频繁，"
        "所以终止条件不是保险丝，而是成本控制的第一道开关",

    ("agent", "agent-ch12", 4):
        "§1.2 2. 毛利结构诊断：亏损从哪里来、怎么修 · §1.3 3. 毛利诊断的三个常见误判："
        "`azd up` 脚本把 RAG 应用从数据到部署全链路串了一遍，"
        "跟着算一遍自己的账单，就会发现本章「按 token 计价的幻觉」；"
        "第二节给出「毛利 = 收入 − 直接成本」的正确拆法，"
        "第三节列的三个误判里第一个就是「把毛利率当净利率」——"
        "前者只扣直接成本，后者还要扣人力与摊销",

    ("ml", "ml-ch05", 4):
        "§2.3 3. 特征抽样与去相关：随机森林比 Bagging 多了什么 · "
        "§3.3 3. LightGBM：三板斧——直方图、leaf-wise、GOSS："
        "`catboost/` 的 ordered target statistics 解决的是目标泄漏，"
        "正好对照本章「普通 target encoding 会把标签漏进特征」；"
        "第二节讲的是「怎么让树之间不那么像」（特征抽样），"
        "第三节讲的是「怎么让每棵树长得更快」（直方图 + leaf-wise），"
        "而 CatBoost 的 ordered 统计补的是第三条：「类别特征怎么进树而不漏标签」",
}


def split_note(note: str) -> tuple[str, str]:
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals(subj: str, cid: str, idx: int, note: str) -> None:
    path = os.path.join("content", subj, cid, "goals.md")
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    rows = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    line_i = rows[idx - 1]
    m = RE_GH_ROW.match(lines[line_i])
    head, tail = split_note(note)
    lines[line_i] = (
        f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
        f"| {head} | {tail} |"
    )
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


def main() -> None:
    by_subj: dict[str, dict[str, dict[int, str]]] = {}
    for (subj, cid, idx), note in FIX.items():
        by_subj.setdefault(subj, {}).setdefault(cid, {})[idx] = note

    for subj, chapters in by_subj.items():
        mpath = f"content/{subj}/_manifest.json"
        with open(mpath, "rb") as fb:
            raw = fb.read()
        nl = "\r\n" if b"\r\n" in raw else "\n"
        data = json.loads(raw.decode("utf-8"))
        for ch in data["chapters"]:
            cid = ch["id"]
            fixes = chapters.get(cid)
            if not fixes:
                continue
            notes = ch["resources"]["github_notes"]
            for idx, note in fixes.items():
                old = notes[idx - 1]
                notes[idx - 1] = note
                rewrite_goals(subj, cid, idx, note)
                print(f"ok {subj}/{cid}#{idx}")
                print(f"   旧: {old[:56]}")
                print(f"   新: {note[:56]}")
        out = json.dumps(data, ensure_ascii=False, indent=2)
        if nl == "\r\n":
            out = out.replace("\n", "\r\n")
        with open(mpath, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    print(f"\n共修 {len(FIX)} 条")


if __name__ == "__main__":
    main()
