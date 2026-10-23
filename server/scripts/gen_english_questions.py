#!/usr/bin/env python
"""生成英语一、英语二的题库（阶段16）。

每套专项卷 = 阅读 1 篇（3 题）+ 翻译 1 题 + 写作 1 题，8 套共 8 篇文章。
文章全部自编，不取自真题；题材对齐大纲常见话题（工作、科技、教育、环境、健康、文化）。
四层结构里 framework 从 frameworks/e1.json 回填，approach/solution 逐题写。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"


def load_patterns(subj: str) -> dict[str, dict]:
    data = json.loads((EXAM / "frameworks" / f"{subj}.json").read_text(encoding="utf-8"))
    return {p["id"]: p for t in data["topics"] for p in t["patterns"]}


def build(subj: str, data: list[dict]) -> dict:
    pats = load_patterns(subj)
    items = []

    def add(qid, topic, kid, pid, typ, stem, approach, note, solution, passage=None, **kw):
        item = {
            "id": qid,
            "topic": topic,
            "knowledge": kid,
            "type": typ,
            "diff": 3,
            "stem": stem,
            "answer": {"correct": kw["correct"]} if typ == "choice" else {"text": kw["text"]},
            "explain": {"right": approach, "wrong": "常见错误：" + note, "link": kid},
            "walkthrough": {
                "framework": {
                    "title": pats[pid]["title"],
                    "pattern": pid,
                    "steps": pats[pid]["steps"],
                    "trap": pats[pid]["traps"][0],
                },
                "approach": approach,
                "points": [{"id": kid, "note": note}],
                "solution": solution,
            },
        }
        if kw.get("options"):
            item["options"] = kw["options"]
        if passage:
            item["passage"] = passage
        items.append(item)

    for i, p in enumerate(data, 1):
        ref = f"{p['id']}"
        passage = {"id": ref, "title": p["title"], "text": p["text"]}
        for j, (stem, opts, correct, approach, note, solution) in enumerate(p["qs"], 1):
            kid = f"{subj}-reading-k{[1, 2, 3][(j - 1) % 3]}"
            pid = f"{subj}-reading-p{[1, 2, 3][(j - 1) % 3]}"
            add(f"q-{subj}-{p['id']}-q{j}", f"{subj}-reading", kid, pid, "choice",
                stem, approach, note, solution, passage=passage,
                options=opts, correct=correct)

        src, ref_t, note = p["trans"]
        add(f"q-{subj}-{p['id']}-tr", f"{subj}-translation", f"{subj}-translation-k1",
            f"{subj}-translation-p1", "calc", src, "先切分意群定主干，再按汉语习惯重排语序，最后检查术语与指代是否统一。",
            note,
            "参考译文：" + ref_t + "\n得分点：" + note + "\n检查清单：主干是否译出、修饰是否归位、指代是否还原。",
            text=ref_t)

        prompt, essay, wnote = p["write"]
        add(f"q-{subj}-{p['id']}-wr", f"{subj}-writing", f"{subj}-writing-k2",
            f"{subj}-writing-p2", "design", prompt,
            "先定三段骨架（描述—分析—结论），再把题目给出的信息逐条落进段落，最后检查字数与衔接词。",
            wnote, essay, text=essay)

    return {"subject": subj, "exam": "english", "items": items}


# ============================================================== 英语一 8 篇
E1 = [
    {
        "id": "e1-p1", "title": "Remote work and the junior employee",
        "text": (
            "When firms first sent employees home in 2020, many managers predicted a collapse in output. "
            "The collapse never came. Studies covering tens of thousands of workers found that routine tasks "
            "were completed slightly faster at home, largely because commutes disappeared and meetings shrank. "
            "Yet the same studies reported a quieter problem: employees in their first two years of work "
            "learned more slowly. Sitting near experienced colleagues, they had absorbed judgement by watching "
            "it being exercised. Video calls transmit information but not atmosphere, and a junior hire who does "
            "not know what to ask cannot ask it. Some firms now answer with hybrid weeks in which teams gather "
            "for the tasks that require judgement and disperse for the tasks that require concentration."
        ),
        "qs": [
            ("Studies of remote work found that routine tasks were completed",
             ["more slowly than in offices", "slightly faster than in offices",
              "at exactly the same speed", "only by senior employees"], 1,
             "题干关键词是 routine tasks 与 completed，回原文找同义表达，定位在第二句的 slightly faster。",
             "把 commutes disappeared 当成效率提高的唯一原因，忽略后面提到的会议减少；或凭常识选「更慢」。",
             "定位句：routine tasks were completed slightly faster at home。原因给出两条——通勤消失、会议缩短。"
             "选项 B 与原文同义；A、C 与 slightly faster 相反或不符；D 把范围缩小到 senior，原文无此限定。"),
            ("The learning problem for junior employees arose mainly because",
             ["they had too many video calls", "they lacked opportunities to observe how decisions are made",
              "they were given harder tasks than before", "their managers stopped assigning work"], 1,
             "问原因，定位到 learned more slowly 之后那句「靠旁观判断被行使来吸收」，把它译成选项。",
             "选「视频会议太多」——原文说视频会议传递信息但不传递氛围，重点在缺失的观察机会，不是会议数量。",
             "原文：they had absorbed judgement by watching it being exercised。即缺少「旁观判断如何行使」的机会。"
             "B 正是该句的同义改写。A 曲解 video calls 的作用；C、D 原文均未提及。"),
            ("The author's attitude towards hybrid weeks can best be described as",
             ["dismissive", "cautiously approving", "openly hostile", "completely neutral"], 1,
             "态度题看结尾段的评价：Some firms now answer with… 是正面回应问题的做法，语气克制。",
             "选 completely neutral——作者明确把 hybrid 当作对问题的回答，并非毫无立场。",
             "末句 Some firms now answer with hybrid weeks… 中 answer 一词表明作者认为这是有效回应；"
             "但用的是 some firms，没有绝对化，故为「谨慎赞同」。A、C 与 answer 相反；D 忽略了评价色彩。"),
        ],
        "trans": (
            "Sitting near experienced colleagues, they had absorbed judgement by watching it being exercised.",
            "坐在有经验的同事身边，他们通过观察判断力如何被运用而习得了这种判断力。",
            "现在分词状语前置译成「坐在……身边」；被动 being exercised 转成汉语主动「如何被运用」；"
            "absorb 译「习得」比「吸收」更贴切。"),
        "write": (
            "Write an essay of about 160 words based on the following idea: some companies now ask employees to "
            "return to the office for part of the week. Describe the trend, explain its reasons, and give your comment.",
            "A growing number of firms are asking staff to return to the office for two or three days a week. "
            "The shift is driven by two concerns. First, new employees learn judgement by observing experienced "
            "colleagues, and a screen transmits information far better than atmosphere. Second, some tasks, such as "
            "negotiating a contract or resolving a conflict, move faster when people share a room. Yet a full return "
            "would waste the hours that remote work has saved. The sensible arrangement is therefore deliberate: "
            "gather for the work that needs judgement, disperse for the work that needs concentration. Companies that "
            "treat the office as a tool rather than a habit are likely to keep both productivity and loyalty.",
            "没有点明「混合办公」这一核心概念，只泛泛谈效率；或只描述现象不分析原因。"),
    },
    {
        "id": "e1-p2", "title": "Why city trees are health infrastructure",
        "text": (
            "City trees are usually discussed as decoration. A growing body of medical evidence suggests they "
            "should be discussed as infrastructure. Researchers tracking thousands of residents found that people "
            "living within a short walk of mature trees reported lower stress and slept longer, even after income "
            "and noise were taken into account. The effect was strongest in the hottest months, when shade lowered "
            "surface temperatures by several degrees. None of this makes trees a substitute for clinics. It does "
            "mean that a decision to remove a row of trees for a wider road is a health decision, and should be "
            "costed as one. A few cities have begun to do exactly that, listing the medical savings alongside the "
            "construction costs in their planning documents."
        ),
        "qs": [
            ("The researchers found that the health benefit of trees was greatest",
             ["in winter", "during the hottest months", "in wealthy neighbourhoods", "near clinics"], 1,
             "细节题，关键词 greatest 对应原文 strongest，定位到 the hottest months。",
             "把 lower stress 当成全年恒定，忽略 the effect was strongest in the hottest months 这一限定。",
             "原文：The effect was strongest in the hottest months, when shade lowered surface temperatures by "
             "several degrees。B 为原文同义；A 与 hottest 相反；C、D 原文未提。"),
            ("By calling trees 'infrastructure', the author means that trees",
             ["are as expensive as roads", "produce measurable public benefits that should be costed",
              "should be planted by engineers", "can replace clinics in poor areas"], 1,
             "词义/态度题：看作者用 infrastructure 想强调什么——后文说「砍树是健康决策，应计入成本」。",
             "选 can replace clinics——原文明确说 None of this makes trees a substitute for clinics，正好相反。",
             "第三句起作者把树木与「成本核算」挂钩：a decision to remove a row of trees… is a health decision, "
             "and should be costed as one。故 infrastructure 指「产生可计量公共效益、应纳入成本」。"
             "B 与原文一致；D 与 None of this makes trees a substitute for clinics 直接冲突。"),
            ("The last sentence is used to show that",
             ["the idea is already being put into practice", "cities rarely listen to researchers",
              "construction costs are falling", "planning documents are too long"], 0,
             "末句作用题：A few cities have begun to do exactly that 中的 exactly that 指前一句的「把医疗节省计入成本」。",
             "把 do exactly that 理解成「种更多树」，忽略它回指的是上一句的成本核算做法。",
             "末句：A few cities have begun to do exactly that, listing the medical savings alongside the "
             "construction costs。do exactly that 回指「把砍树的健康代价计入成本」，说明理念已落地，选 A。"),
        ],
        "trans": (
            "It does mean that a decision to remove a row of trees for a wider road is a health decision, and should be costed as one.",
            "它确实意味着，为拓宽道路而砍掉一排树的决定是一个健康决策，并且应当按健康决策来核算成本。",
            "It 指代前句「树不能替代诊所」这一让步；a decision to remove… 的不定式作后置定语，译成「为……而砍树的决定」；"
            "cost as one 中的 one 指 a health decision，需还原。"),
        "write": (
            "Write an essay of about 160 words on the following topic: some cities are cutting down street trees to "
            "widen roads. State the problem, analyse its consequences, and suggest what city governments should do.",
            "Several cities have removed mature street trees to make room for extra lanes. The immediate gain is "
            "shorter queues at rush hour; the losses are less visible and last longer. Mature trees cool streets in "
            "summer, absorb noise, and, according to medical research, reduce stress among nearby residents. Once "
            "cut, they take decades to replace. The rational response is not to forbid road widening but to price "
            "what is being destroyed. Planners should publish the health and cooling benefits of a tree row beside "
            "the construction budget, and plant replacements before removal begins. When the trade-off is visible, "
            "citizens can judge whether a wider road is worth the shade it costs.",
            "只写「树很重要」的口号，没有把健康成本与工程预算联系起来；或提出「一律不修路」的极端主张。"),
    },
    {
        "id": "e1-p3", "title": "The reproducibility problem in science",
        "text": (
            "Science advances by repetition: a result becomes knowledge when other laboratories obtain it too. "
            "In several fields, however, large replication projects have found that a substantial share of "
            "published findings cannot be reproduced. The causes are mundane rather than scandalous. Samples are "
            "small, analysis choices are flexible, and journals reward novelty over confirmation. A researcher who "
            "tries twenty statistical models and reports the one that worked is not lying, but the reported result "
            "is no longer an unbiased estimate. Reformers propose three remedies: register the analysis plan "
            "before collecting data, publish negative results, and fund replication as a normal part of research "
            "rather than as a curiosity."
        ),
        "qs": [
            ("According to the passage, failed replications are mainly caused by",
             ["deliberate fraud", "ordinary research practices and incentives",
              "a shortage of laboratories", "government funding cuts"], 1,
             "细节题，关键词 causes 对应原文 The causes are mundane rather than scandalous，后面列举三点。",
             "选 deliberate fraud——原文明确说 mundane rather than scandalous，即平常做法而非学术不端。",
             "原文：The causes are mundane rather than scandalous. Samples are small, analysis choices are "
             "flexible, and journals reward novelty。B 概括了这三条；A 与 mundane rather than scandalous 相反；"
             "C、D 原文未提。"),
            ("The example of the researcher trying twenty models is used to show that",
             ["researchers are dishonest", "flexible analysis can make a result misleading without any intent to deceive",
              "statistics should not be used", "twenty models are always better than one"], 1,
             "例证题：例子服务于论点，看它前后一句——「不是撒谎，但结果不再是无偏估计」。",
             "选 researchers are dishonest，忽略了紧随其后的 is not lying。",
             "原文：A researcher who tries twenty statistical models… is not lying, but the reported result is no "
             "longer an unbiased estimate。例子说明「无主观造假也会产生误导性结果」，B 最准确；A 与 is not lying 冲突；"
             "C、D 过度推论。"),
            ("Which of the following is NOT among the proposed remedies?",
             ["Pre-registering the analysis plan", "Publishing negative results",
              "Increasing the number of journals", "Funding replication studies"], 2,
             "否定细节题：把三个 remedy 与选项逐一对照，找未提及的那一项。",
             "漏看 NOT，选了原文出现过的 remedy；或把 journals reward novelty 误当成「增加期刊数量」。",
             "原文列三条：register the analysis plan before collecting data（=A）、publish negative results（=B）、"
             "fund replication（=D）。C「增加期刊数量」原文未提，只提到期刊奖励新颖性，故为答案。"),
        ],
        "trans": (
            "A researcher who tries twenty statistical models and reports the one that worked is not lying, but the reported result is no longer an unbiased estimate.",
            "一位尝试二十种统计模型、只报告其中奏效那一种的研究者并没有撒谎，但其所报告的结果已不再是无偏估计。",
            "who 引导的定语从句较长，拆成「一位……的研究者」；the one that worked 译「其中奏效的那一种」；"
            "not lying 与 no longer 构成对比，译文要保留这层转折。"),
        "write": (
            "Write an essay of about 160 words on the following topic: many published scientific findings cannot be "
            "reproduced. Discuss the causes and propose how the research system should respond.",
            "The credibility of science rests on results that others can reproduce, yet large replication projects "
            "suggest that many published findings fail this test. The explanation is rarely fraud. Small samples, "
            "flexible analysis, and journals that reward novelty all push toward fragile results. Three reforms "
            "follow naturally. Researchers should register their analysis plan before collecting data, so that the "
            "reported model is not chosen after the fact. Journals should publish negative results, which currently "
            "disappear and force others to repeat the same dead ends. Funders should treat replication as ordinary "
            "research rather than as an admission of failure. None of these changes is dramatic, but together they "
            "restore the repetition on which science depends.",
            "把原因全部归为「学者造假」，与原文 mundane rather than scandalous 的定性冲突；或只列改革不解释原因。"),
    },
    {
        "id": "e1-p4", "title": "What AI can and cannot do in diagnosis",
        "text": (
            "Systems trained on medical images can now detect certain cancers at least as accurately as "
            "specialist radiologists. Headlines often stop there. In practice the interesting questions begin "
            "afterwards. A model is calibrated on the population it was trained on; move it to a hospital with "
            "different equipment and its accuracy may fall sharply. It also reports a probability, not a reason, "
            "and clinicians are understandably reluctant to act on a number they cannot interrogate. The most "
            "promising deployments therefore place the model beside the doctor rather than in place of the doctor, "
            "using it to sort urgent cases and to flag images that deserve a second look."
        ),
        "qs": [
            ("The passage suggests that the accuracy of an AI diagnostic system",
             ["is fixed once training is complete", "may decline when equipment changes",
              "is always higher than that of doctors", "improves automatically over time"], 1,
             "细节题，关键词 accuracy 与 equipment，定位到 move it to a hospital with different equipment。",
             "把 at least as accurately as 当成「永远更准」，忽略后面的条件与下降风险。",
             "原文：move it to a hospital with different equipment and its accuracy may fall sharply。B 为同义；"
             "A 与「换设备会掉点」矛盾；C 把 at least as 绝对化为 always higher；D 原文未提。"),
            ("Clinicians hesitate to rely on the model partly because",
             ["it is too slow", "it gives a probability without an explanation",
              "it cannot process images", "it is more expensive than doctors"], 1,
             "问原因，定位 clinicians are understandably reluctant 所在句：reports a probability, not a reason。",
             "选 it is too slow——原文谈的是「无法追问理由」，不是速度。",
             "原文：It also reports a probability, not a reason, and clinicians are understandably reluctant to act "
             "on a number they cannot interrogate。B 直接对应；A、C、D 均无原文依据。"),
            ("The author's preferred deployment strategy is to",
             ["replace radiologists with models", "use models as assistants to clinicians",
              "abandon AI diagnosis entirely", "let patients interpret model output"], 1,
             "态度/主旨题，看结尾 the most promising deployments… beside the doctor rather than in place of the doctor。",
             "选 replace radiologists——原文用 rather than in place of the doctor 明确否定替代。",
             "末句：place the model beside the doctor rather than in place of the doctor, using it to sort urgent "
             "cases and flag images。B 与 beside 一致；A 与 in place of 相反；C、D 无依据。"),
        ],
        "trans": (
            "The most promising deployments therefore place the model beside the doctor rather than in place of the doctor, using it to sort urgent cases and to flag images that deserve a second look.",
            "因此，最有前景的部署方式是把模型放在医生身边、而非取代医生，用它来分拣急症病例，并标记出值得复查的影像。",
            "rather than 连接两个介词短语，译成「而非」；using it 是伴随状语，另起一句更顺；"
            "flag 在此为动词「标记」，deserve a second look 译「值得复查」。"),
        "write": (
            "Write an essay of about 160 words on the following topic: AI systems can read medical images as "
            "accurately as specialists. Discuss what this can and cannot replace.",
            "AI systems now match specialist radiologists in detecting some cancers, and the temptation to describe "
            "this as a replacement is strong. It is also premature. A model's accuracy depends on the population and "
            "equipment it was trained on; move it to a different hospital and performance may drop. More "
            "importantly, a model outputs a probability, not a reason, and a clinician cannot interrogate a number. "
            "The sensible division of labour is therefore complementary. The model sorts urgent cases and flags "
            "images for review, while the doctor explains, decides, and takes responsibility. Used this way, AI "
            "shortens the queue without asking patients to trust a black box.",
            "写成「AI 将取代医生」或「AI 完全无用」的两极判断，缺少「辅助而非替代」的中间立场。"),
    },
    {
        "id": "e1-p5", "title": "Museums after the virtual tour",
        "text": (
            "When museums closed their doors, they put their collections online. Virtual tours attracted millions "
            "of visitors, and many institutions assumed they had found a new audience. The data tell a subtler "
            "story. Online visitors spend minutes, not hours, and rarely return; they behave like people browsing "
            "a shop window rather than like visitors. What the digital version does well is preparation and "
            "follow-up: a teacher can show a class a painting before a visit, and a visitor can look again at an "
            "object that caught the eye. Museums that treat the website as a substitute for the gallery are "
            "disappointed; those that treat it as a doorway are not."
        ),
        "qs": [
            ("The data on virtual tours show that online visitors",
             ["stay for hours", "usually come back many times", "behave like window-shoppers", "spend more than physical visitors"], 2,
             "细节题，关键词 online visitors，定位到 they behave like people browsing a shop window。",
             "被 attracted millions 误导，以为线上观众黏性很高；忽略 minutes, not hours 与 rarely return。",
             "原文：Online visitors spend minutes, not hours, and rarely return; they behave like people browsing a "
             "shop window。C 为原文同义；A、B 与 minutes、rarely return 相反；D 原文未比较花费。"),
            ("According to the author, the digital collection is most useful for",
             ["replacing the gallery visit", "preparing for and recalling a visit",
              "selling museum goods", "training professional curators"], 1,
             "细节题，关键词 most useful，定位 preparation and follow-up 一句，并注意冒号后的两个例子。",
             "选 replacing the gallery visit——末句明确说把它当替代品的博物馆会失望。",
             "原文：What the digital version does well is preparation and follow-up: a teacher can show a class a "
             "painting before a visit… B 概括了这两个场景；A 与 treat the website as a substitute… are disappointed 相反。"),
            ("The phrase 'a doorway' in the last sentence is closest in meaning to",
             ["an exit from the museum", "a route into a deeper experience", "a barrier to access", "a marketing tool"], 1,
             "词义题：doorway 与 substitute 对举，指「入口」——把人引向实体参观，而非取代它。",
             "按字面译成「出口」，与 preparation/follow-up 的定位矛盾。",
             "末句对比：treat the website as a substitute… are disappointed; those that treat it as a doorway are "
             "not。substitute（替代品）与 doorway（入口）相反，后者指通向更深体验的通道，选 B。"),
        ],
        "trans": (
            "Museums that treat the website as a substitute for the gallery are disappointed; those that treat it as a doorway are not.",
            "把网站当作展厅替代品的博物馆会失望；而把它当作入口的博物馆则不会。",
            "两个 that 定语从句并列，译文用「把……当作……」结构；those 指 those museums，需补出「博物馆」；"
            "分号保持两句对比关系。"),
        "write": (
            "Write an essay of about 160 words on the following topic: museums now offer virtual tours of their "
            "collections. Some believe this makes physical visits unnecessary. Discuss both views and give your opinion.",
            "Virtual tours have opened museum collections to anyone with a screen, and some commentators conclude "
            "that physical visits are becoming unnecessary. The evidence suggests otherwise. Online visitors stay "
            "for minutes and rarely return, treating the collection as a shop window rather than an experience. "
            "What the digital version does best is prepare and extend a visit: a class can study a painting before "
            "arriving, and a visitor can return to an object that caught the eye. A substitute competes with the "
            "gallery; a doorway leads into it. Museums should therefore design their websites as doorways, using "
            "high-quality images and clear context to make the physical visit more likely, not less.",
            "只谈「线上方便」或「线下不可替代」，没有指出两者是互补关系。"),
    },
    {
        "id": "e1-p6", "title": "Sleep, memory and the cost of a short night",
        "text": (
            "Students have long treated sleep as a reserve to be spent before examinations. Laboratory work "
            "suggests this is a poor bargain. During deep sleep the brain replays patterns formed during the day, "
            "consolidating them into longer-term memory; cut the night short and the replay is cut short with it. "
            "In one experiment, participants who learned a list of words in the evening recalled more after a full "
            "night than after a half night, although the total study time was identical. The finding has an "
            "uncomfortable implication for schools that schedule early starts after late-night revision. Sleep is "
            "not time away from study; it is part of the process."
        ),
        "qs": [
            ("The experiment described in the passage found that participants who slept a full night",
             ["studied longer", "recalled more words", "learned a harder list", "forgot the list faster"], 1,
             "细节题，关键词 experiment 与 full night，定位 recalled more after a full night than after a half night。",
             "把 total study time was identical 忽略掉，误以为睡得久的人学得更多。",
             "原文：participants who learned a list of words in the evening recalled more after a full night than "
             "after a half night, although the total study time was identical。B 为原文同义；A 与 identical 矛盾；"
             "C、D 无依据。"),
            ("The phrase 'a poor bargain' suggests that skipping sleep to study is",
             ["financially expensive", "a trade that gives less than it costs", "a necessary choice", "a modern invention"], 1,
             "词义题：bargain 是「交易」，poor bargain 指「不划算」，后文用实验说明记忆收益反而下降。",
             "按字面理解成「花钱多」，把 bargain 当纯经济词。",
             "首句把睡眠比作可支取的储备，随后说 this is a poor bargain——即「用睡眠换学习时间」这笔交易不划算。"
             "下文实验证明同样学习时间下睡整夜记得更多，正好支持 B。"),
            ("The author's main purpose is to",
             ["describe the stages of sleep", "argue that sleep contributes to learning",
              "criticise students for staying up late", "compare two memory experiments"], 1,
             "主旨题：首句提出「睡眠换学习不划算」，中间给机制与实验，末句点题 Sleep is not time away from study。",
             "选 criticise students——作者批评的是「把早课排在熬夜复习之后」的安排，不是学生本人。",
             "结构：现象（学生牺牲睡眠）→ 机制（深睡重放、巩固记忆）→ 实验（整夜睡者记得更多）→ 结论（睡眠是学习过程的一部分）。"
             "B 覆盖全文；A 只是机制细节；C 对象错；D 只提到一个实验。"),
        ],
        "trans": (
            "During deep sleep the brain replays patterns formed during the day, consolidating them into longer-term memory; cut the night short and the replay is cut short with it.",
            "在深度睡眠中，大脑会重放白天形成的活动模式，并将其巩固为长期记忆；若缩短夜间睡眠，这种重放也会随之被缩短。",
            "consolidating 是伴随状语，译成并列动作；cut the night short and… 是「祈使句 + and」表条件，译成「若……就……」；"
            "it 指 the night，需还原为「夜间睡眠」。"),
        "write": (
            "Write an essay of about 160 words on the following topic: many students reduce sleep before "
            "examinations. Explain why this is counterproductive and suggest better habits.",
            "Late-night revision feels productive because it is visible: the desk is occupied and the notes are "
            "open. Memory research suggests the feeling is misleading. During deep sleep the brain replays the "
            "patterns formed during the day and consolidates them, so a shortened night shortens the very process "
            "that turns study into recall. In controlled experiments, students who slept a full night remembered "
            "more than those who studied the same number of hours but slept half as long. The practical lesson is "
            "simple: review in the evening, sleep a full night, and test yourself in the morning. Schools can help "
            "by not scheduling early examinations immediately after late-night revision sessions.",
            "把「少睡」当成努力的象征，通篇鼓励熬夜；或只讲睡眠重要，不给可执行的替代方案。"),
    },
    {
        "id": "e1-p7", "title": "Carbon labels and the limits of consumer choice",
        "text": (
            "Carbon labels on products are attractive because they promise to turn every purchase into a "
            "climate decision. Trials in several countries show that labels do change behaviour, but modestly: "
            "shoppers shift a few percentage points toward lower-carbon options, and the effect fades when the "
            "label competes with price. The deeper problem is arithmetic. A label informs one choice at a time, "
            "while emissions are determined by systems: how food is produced, how goods are transported, how "
            "buildings are heated. Expecting labels to deliver large reductions is like expecting a menu to "
            "improve a restaurant's kitchen. Labels are worth having, but they work best alongside rules that "
            "change what is on offer."
        ),
        "qs": [
            ("Trials of carbon labels showed that the effect on shoppers was",
             ["large and permanent", "small and weakened by price", "none at all", "stronger for expensive goods"], 1,
             "细节题，关键词 trials，定位 modestly 与 the effect fades when the label competes with price。",
             "把 change behaviour 当成效果显著，忽略 modestly 与 fades。",
             "原文：labels do change behaviour, but modestly… and the effect fades when the label competes with "
             "price。B 概括了这两点；A 与 modestly/fades 相反；C 与 do change behaviour 矛盾；D 无依据。"),
            ("The comparison with a menu and a kitchen is intended to show that",
             ["labels cannot change what is produced", "restaurants waste more than shops",
              "menus are badly designed", "price is the only signal that matters"], 0,
             "类比题：menu 对应 label（信息），kitchen 对应 system（生产），菜单改不了厨房。",
             "把类比理解成「餐厅浪费更多」，脱离上下文的 emissions are determined by systems。",
             "原文先说排放由系统决定（生产、运输、供暖），再说「指望标签大幅减排，就像指望菜单改善厨房」。"
             "菜单只能选，不能改变厨房怎么做菜，对应 A。"),
            ("The author concludes that labels",
             ["should be abolished", "are useful but insufficient on their own",
              "are more effective than regulation", "should replace price signals"], 1,
             "结论题，看末句 Labels are worth having, but they work best alongside rules。",
             "选 should be abolished——末句明确说 worth having，只是需要配合规则。",
             "末句：Labels are worth having, but they work best alongside rules that change what is on offer。"
             "B 是「有用但不充分」的同义；A 与 worth having 相反；C、D 原文未主张。"),
        ],
        "trans": (
            "Expecting labels to deliver large reductions is like expecting a menu to improve a restaurant's kitchen.",
            "指望标签带来大幅减排，就像指望菜单去改善餐厅的厨房一样。",
            "动名词短语作主语，译成「指望……」；is like 保持比喻结构；deliver large reductions 译「带来大幅减排」，"
            "不要直译「交付减少」。"),
        "write": (
            "Write an essay of about 160 words on the following topic: some governments plan to require carbon "
            "labels on food and clothing. Discuss the benefits and limitations of this policy.",
            "Carbon labels promise to make climate impact visible at the moment of choice, and trials suggest they "
            "do shift purchases, if only by a few percentage points. That is a real gain: information is cheap and "
            "the label respects consumer judgement. Yet the policy has limits. Labels inform one decision at a "
            "time, while most emissions are fixed by production, transport and heating systems that no shopper can "
            "alter. The effect also fades when price pulls the other way, and poorer households can hardly be "
            "expected to pay more for a lower number. The sensible conclusion is to keep the label and pair it with "
            "rules that change what suppliers offer, so that the low-carbon option becomes the easy one.",
            "把标签说成万能或完全无用；没有指出「信息工具 + 规则」需要配合。"),
    },
    {
        "id": "e1-p8", "title": "Gig work and the price of flexibility",
        "text": (
            "Platform work is praised for its flexibility: a driver can start at noon and stop at four. The "
            "flexibility is real, but it is not free. Because gig workers are classified as independent "
            "contractors, the platform does not contribute to insurance or retirement, and the worker bears the "
            "cost of idle time. Surveys find that hourly earnings, once these costs are subtracted, are often "
            "below those of comparable salaried jobs. Defenders reply that workers value the freedom to choose "
            "hours, and the surveys support this too. The policy question is therefore not whether flexibility "
            "is good, but who pays for it. A system that lets workers keep the flexibility while sharing the "
            "insurance cost would be both fairer and more stable."
        ),
        "qs": [
            ("According to the passage, the flexibility of gig work",
             ["comes at a cost to the worker", "is exaggerated by platforms", "has no effect on earnings", "is valued only by defenders"], 0,
             "细节题，关键词 flexibility，定位 The flexibility is real, but it is not free，后文列出成本。",
             "只读到 flexibility is real 就选「被夸大」，忽略 but it is not free。",
             "原文：The flexibility is real, but it is not free… the worker bears the cost of idle time。A 与 not free "
             "同义；B 与 The flexibility is real 相反；C、D 无依据（后文说 surveys support 工人重视自由）。"),
            ("The author's policy suggestion is that",
             ["gig work should be banned", "workers should keep flexibility while costs are shared",
              "platforms should set fixed hours", "insurance should be abolished"], 1,
             "细节题，关键词 suggestion，定位末句 keep the flexibility while sharing the insurance cost。",
             "选 platforms should set fixed hours——这与「保留灵活性」直接冲突。",
             "末句：A system that lets workers keep the flexibility while sharing the insurance cost would be both "
             "fairer and more stable。B 为原文同义；A、C、D 均与原文主张相反或未提。"),
            ("The passage is mainly about",
             ["how platforms calculate wages", "who bears the hidden costs of flexible work",
              "why drivers prefer fixed schedules", "the history of labour classification"], 1,
             "主旨题：首句给灵活性，随后 but it is not free，末句落到「谁为灵活性付费」。",
             "选 how platforms calculate wages——文中没有算法或计价细节。",
             "结构：灵活性真实 → 但成本由工人承担（保险、养老、空等）→ 时薪对比 → 争议双方 → 政策问题是谁付费。"
             "B 概括主线；A 无细节支撑；C 与文意相反；D 未展开历史。"),
        ],
        "trans": (
            "The policy question is therefore not whether flexibility is good, but who pays for it.",
            "因此，政策问题不在于灵活性好不好，而在于由谁来为它买单。",
            "not… but… 结构译成「不在于……而在于……」；whether 从句译成「好不好」更符合汉语；"
            "pays for it 的 it 指 flexibility，需还原。"),
        "write": (
            "Write an essay of about 160 words on the following topic: gig workers enjoy flexible hours but often "
            "lack insurance and retirement benefits. Propose a fair arrangement.",
            "Platform work offers something salaried jobs rarely do: the freedom to choose when to work. It also "
            "transfers hidden costs to the worker. Independent contractors pay for their own insurance and "
            "retirement, and they absorb the cost of hours when no work arrives. Surveys that subtract these costs "
            "find hourly earnings below those of comparable salaried jobs. Banning platforms would remove the "
            "flexibility that workers say they value, so the better route is to separate the two issues. Platforms "
            "could contribute to a portable insurance account for every active hour, while workers keep control of "
            "their schedules. Flexibility would remain; the risk would be shared.",
            "只主张「加强监管」或「平台全责」，没有说明如何保留灵活性。"),
    },
]
