#!/usr/bin/env python
"""英语二题库（阶段16）。

英语二的文章比英语一短、句子更平实，题目偏细节与词义；翻译考整段而非单句。
8 套 = 8 篇文章 + 8 段翻译 + 8 篇写作。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_english_questions import build, load_patterns  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"

E2 = [
    {
        "id": "e2-p1", "title": "A recycling scheme that worked",
        "text": (
            "Two years ago the university installed recycling bins in every dormitory. The first survey was "
            "disappointing: only a third of bottles reached the correct bin. Instead of adding more bins, the "
            "housing office tried something cheaper. It published a weekly chart in each building showing how much "
            "waste had been sorted correctly, and it asked the cleaners to leave one wrongly sorted bag beside the "
            "bin with a short note. Within a term the rate rose to nearly three quarters. The lesson is that "
            "people do not need more instructions; they need to see how they are doing compared with their "
            "neighbours."
        ),
        "qs": [
            ("The first survey showed that",
             ["most bottles were recycled correctly", "only about one third of bottles were sorted correctly",
              "students refused to use the bins", "the bins were too small"], 1,
             "细节题，关键词 first survey，定位 only a third of bottles reached the correct bin。",
             "把 installed bins in every dormitory 当成效果好，忽略 disappointing 与 only a third。",
             "原文：The first survey was disappointing: only a third of bottles reached the correct bin。B 与之一致；"
             "A 与 one third 矛盾；C、D 原文未提。"),
            ("The housing office improved the rate mainly by",
             ["buying more bins", "giving students feedback on their performance",
              "hiring more cleaners", "fining students who sorted wrongly"], 1,
             "细节题，关键词 improved，定位「每周图表 + 把分错的袋子放在桶边」这两种反馈方式。",
             "选 buying more bins——原文明确说 Instead of adding more bins，正好相反。",
             "原文：It published a weekly chart… and asked the cleaners to leave one wrongly sorted bag beside the "
             "bin with a short note。两者都是「让人看到自己做得怎样」，即反馈，选 B；A 与 Instead of adding more bins 相反。"),
            ("The main point of the passage is that",
             ["recycling is difficult for students", "visible feedback changes behaviour more than instructions",
              "cleaners should sort the waste", "charts are expensive to produce"], 1,
             "主旨题，看末句 people do not need more instructions; they need to see how they are doing。",
             "选 recycling is difficult——文章讲的是「怎么让人做对」，不是难度本身。",
             "末句点题：people do not need more instructions; they need to see how they are doing compared with "
             "their neighbours。B 与之同义；A 只是开头现象；C、D 是细节或未提。"),
        ],
        "trans": (
            "The lesson is that people do not need more instructions; they need to see how they are doing compared with their neighbours.",
            "这一做法带来的启示是：人们并不需要更多说明，他们需要的是看到自己与邻居相比做得如何。",
            "that 引导表语从句，用冒号处理更简洁；compared with 译「与……相比」；"
            "they are doing 是进行时，译「做得如何」而非「正在做」。"),
        "write": (
            "Write an essay of about 150 words on the following topic: your university wants to increase the "
            "recycling rate in dormitories. Suggest one practical measure and explain why it should work.",
            "Instead of printing more instructions, the university should publish a weekly ranking of dormitory "
            "buildings by recycling rate. Each building would see its own figure and its position among neighbours. "
            "The measure is cheap, since the data are already collected when the waste is weighed, and it works on a "
            "well-documented principle: people adjust their behaviour when they can see how it compares with that of "
            "people around them. To avoid resentment, the ranking should praise improvement rather than shame the "
            "bottom building, and the top three could receive a small fund for a floor party. Visible progress, "
            "rather than another leaflet, is what changes habits.",
            "只写「加强宣传」这类空泛建议，没有说明具体做法与生效机制。"),
    },
    {
        "id": "e2-p2", "title": "Older learners and online courses",
        "text": (
            "Online courses were expected to be a gift for older learners, who often find it hard to travel to "
            "a campus. Participation tells a different story. Adults over sixty enroll in large numbers but "
            "complete far fewer courses than younger students. The reasons are practical rather than attitudinal: "
            "platforms assume users can navigate menus, upload files and join video calls, and a single confusing "
            "step can end the attempt. A pilot programme that paired each learner with a student helper for the "
            "first two weeks raised completion sharply. The technology was not the barrier; learning the "
            "technology alone was."
        ),
        "qs": [
            ("Older learners are described as",
             ["unwilling to study online", "enrolling in large numbers but completing fewer courses",
              "better at online study than younger students", "unable to afford courses"], 1,
             "细节题，关键词 older learners，定位 enroll in large numbers but complete far fewer courses。",
             "选 unwilling to study online——原文说 enroll in large numbers，意愿并不低。",
             "原文：Adults over sixty enroll in large numbers but complete far fewer courses than younger students。"
             "B 为原文同义；A 与 enroll in large numbers 矛盾；C 与 complete far fewer 矛盾；D 未提。"),
            ("The main obstacle for older learners was",
             ["the cost of courses", "the lack of interesting subjects",
              "navigating the platform without help", "the length of the courses"], 2,
             "细节题，关键词 obstacle，定位 platforms assume users can navigate menus… a single confusing step can end the attempt。",
             "选 the cost——原文明确说 reasons are practical rather than attitudinal，且列举的都是操作步骤。",
             "原文：platforms assume users can navigate menus, upload files and join video calls, and a single "
             "confusing step can end the attempt。C 概括了这一障碍；A、B、D 均无原文依据。"),
            ("The pilot programme showed that",
             ["older learners need easier content", "short-term human support can make technology usable",
              "video calls should be removed", "student helpers should teach the subjects"], 1,
             "细节题，关键词 pilot programme，定位 raised completion sharply 及其条件「前两周配学生助手」。",
             "选 older learners need easier content——原文说 technology was not the barrier，内容难度不是问题。",
             "原文：A pilot programme that paired each learner with a student helper for the first two weeks raised "
             "completion sharply… The technology was not the barrier; learning the technology alone was。"
             "B 与「短期人工支持」一致；A 与 content 无关；C、D 过度推论。"),
        ],
        "trans": (
            "The technology was not the barrier; learning the technology alone was.",
            "技术本身并不是障碍；真正的障碍在于要独自学会使用这项技术。",
            "分号保持对比；alone 修饰 learning，译「独自」而非「仅仅」；句末 was 后省略了 the barrier，"
            "汉语需补出「真正的障碍」。"),
        "write": (
            "Write an essay of about 150 words on the following topic: many older adults sign up for online courses "
            "but few finish them. Suggest how platforms or universities could help.",
            "Older adults are not short of motivation: they enroll in online courses in large numbers. What they "
            "lack is support in the first hours, when a confusing menu or a failed upload can end the attempt. "
            "Universities could therefore offer a short induction, either in person or by phone, in which a student "
            "helper sits beside the learner and completes one real task together. Platforms could simplify "
            "registration and keep a telephone line open during the first week. Neither measure is expensive, and "
            "both attack the real barrier, which is learning the technology alone rather than learning the subject. "
            "Completion, not enrolment, is the number that matters.",
            "把原因归为「老年人不愿学」或「课程太难」，与原文 attitudinal / content 无关的判断相反。"),
    },
    {
        "id": "e2-p3", "title": "Bike-sharing after the novelty",
        "text": (
            "Bike-sharing arrived with promises of clean transport and crowded streets full of bicycles. Several "
            "cities now report a quieter outcome. Ridership peaks in the first year and then flattens, while "
            "maintenance costs keep rising. The companies that survive tend to be those that moved bikes to where "
            "people actually need them, near metro exits and housing estates, instead of scattering them across "
            "the centre. Parking rules matter as much as price. Where bikes may be left only in marked areas, "
            "streets stay tidy and the service is used more; where they may be left anywhere, the opposite "
            "happens."
        ),
        "qs": [
            ("According to the passage, ridership in several cities",
             ["keeps rising every year", "peaks in the first year and then levels off",
              "falls to zero after a year", "is highest in the city centre"], 1,
             "细节题，关键词 ridership，定位 peaks in the first year and then flattens。",
             "把 peaks 当成持续增长；或把 falls to zero 夸大，原文是 flattens（趋平）。",
             "原文：Ridership peaks in the first year and then flattens, while maintenance costs keep rising。"
             "B 为原文同义；A 与 flattens 矛盾；C 过度；D 原文说的是把车放在地铁口与住宅区，而非「市中心骑行最多」。"),
            ("Surviving companies are those that",
             ["charge the lowest prices", "put bikes where demand actually is",
              "advertise most heavily", "avoid parking rules"], 1,
             "细节题，关键词 survive，定位 moved bikes to where people actually need them。",
             "选 charge the lowest prices——原文说 Parking rules matter as much as price，价格不是唯一因素。",
             "原文：The companies that survive tend to be those that moved bikes to where people actually need them, "
             "near metro exits and housing estates。B 为同义；A 把 as much as price 误读为「价格最重要」；C、D 无依据。"),
            ("The passage suggests that marked parking areas",
             ["reduce the number of users", "keep streets tidy and increase use",
              "are opposed by companies", "are more expensive to build"], 1,
             "细节题，关键词 marked areas，定位末句 Where bikes may be left only in marked areas, streets stay tidy and the service is used more。",
             "只读到规则变严就以为会减少使用，忽略 the service is used more。",
             "原文：Where bikes may be left only in marked areas, streets stay tidy and the service is used more。"
             "B 与原文一致；A 与 used more 相反；C、D 未提。"),
        ],
        "trans": (
            "Where bikes may be left only in marked areas, streets stay tidy and the service is used more; where they may be left anywhere, the opposite happens.",
            "在只允许把车停放在指定区域的地方，街道保持整洁，服务的使用率也更高；而在可以随意停放的地方，情况正好相反。",
            "Where 引导地点状语从句，译「在……的地方」；the opposite happens 译「情况正好相反」，不要直译「相反发生」；"
            "两个分句保持对照。"),
        "write": (
            "Write an essay of about 150 words on the following topic: bike-sharing schemes often lose users after "
            "the first year. Explain the reasons and suggest improvements.",
            "Bike-sharing schemes usually start with crowded streets and end with rows of broken bicycles. The "
            "novelty explains the early peak; the flat line afterwards has more ordinary causes. Bikes are placed "
            "where they are easy to park rather than where trips begin and end, maintenance is deferred until "
            "vehicles fail, and casual parking leaves pavements messy, which turns public opinion against the "
            "service. The fixes are practical. Operators should station bikes near metro exits and housing estates, "
            "set marked parking zones, and publish repair response times. Cities should treat the scheme as public "
            "transport, not as advertising space. Reliability, more than novelty, keeps riders.",
            "只描述「共享单车很方便」，没有分析第一年后使用量停滞的原因。"),
    },
    {
        "id": "e2-p4", "title": "Volunteering and the first job",
        "text": (
            "Employers say they value volunteering, but students often suspect that only impressive internships "
            "count. A survey of graduate recruiters suggests the students are half right. Volunteering was rarely "
            "listed as a requirement, yet interviewers frequently asked candidates to describe a situation where "
            "they had worked with others to solve a problem. A term spent organising a food bank shift supplied "
            "better answers than a month of photocopying in an office. The value lies less in the activity itself "
            "than in the evidence it provides of reliability, coordination and persistence."
        ),
        "qs": [
            ("The survey suggests that volunteering",
             ["is a formal requirement for most jobs", "rarely appears as a requirement but provides useful examples",
              "is less useful than any internship", "is only valued by charities"], 1,
             "细节题，关键词 survey，定位 Volunteers was rarely listed as a requirement, yet interviewers frequently asked…",
             "选 is a formal requirement——原文明确说 rarely listed as a requirement。",
             "原文：Volunteering was rarely listed as a requirement, yet interviewers frequently asked candidates to "
             "describe a situation… B 准确概括「不是硬性要求，但能提供素材」；A 与 rarely 相反；C、D 无依据。"),
            ("The food bank example is used to show that",
             ["charity work is harder than office work", "relevant evidence matters more than the label of the activity",
              "photocopying is useless", "students should avoid internships"], 1,
             "例证题：例子服务于「价值不在活动本身，而在它提供的证据」这一论点。",
             "把例子理解成「慈善工作更难」或「实习无用」，都超出了原文范围。",
             "原文在例子后立刻总结：The value lies less in the activity itself than in the evidence it provides of "
             "reliability, coordination and persistence。B 正是该句的同义；A、C、D 都是对例子的过度引申。"),
            ("The phrase 'half right' implies that students",
             ["completely misunderstood employers", "were correct about requirements but wrong about what counts",
              "were wrong about everything", "had not read the survey"], 1,
             "词义题：half right 指学生「对了一半」——要求判断对，价值判断错，后文分别说明。",
             "按字面理解成「一半学生对」，脱离上下文对 survey 结果的解释。",
             "后文结构：rarely a requirement（学生以为只有实习才算，这点被证实）→ 但面试官常问合作解决问题的经历"
             "（志愿活动同样算）。故 half right = 对要求判断正确、对「什么算数」判断错误，选 B。"),
        ],
        "trans": (
            "The value lies less in the activity itself than in the evidence it provides of reliability, coordination and persistence.",
            "其价值与其说在于活动本身，不如说在于它所提供的、关于可靠、协作与坚持的证据。",
            "less… than… 译「与其说……不如说……」；it provides 是省略 that 的定语从句，修饰 evidence；"
            "三个抽象名词并列，译文保留并列节奏。"),
        "write": (
            "Write an essay of about 150 words on the following topic: some students believe only internships matter "
            "for finding a job. Give your view with examples.",
            "Students often assume that only internships count when employers read a CV. Recruiters tell a more "
            "nuanced story. Volunteering is seldom a formal requirement, but interviews are built around questions "
            "about teamwork and problem solving, and a term spent running a food bank shift answers those questions "
            "better than a month of photocopying. What matters is not the label of the activity but the evidence it "
            "supplies: reliability, coordination, persistence. Students should therefore choose activities by the "
            "responsibilities they involve rather than by the prestige of the organisation. A well-documented "
            "volunteering role can be worth more than a famous name on a certificate.",
            "把实习与志愿对立起来，或只强调「志愿活动加分」而不说明原因。"),
    },
    {
        "id": "e2-p5", "title": "The food supermarkets throw away",
        "text": (
            "A supermarket throws away food for reasons that have little to do with hunger and everything to do "
            "with appearance. A banana with a brown spot, a loaf past its display date, a carton dented in "
            "delivery: all are edible, none is sellable by the usual rules. Some chains now sell such items at a "
            "discount in a separate aisle, and a few have changed the rules themselves, removing best-before dates "
            "from fruit and vegetables. The results are modest but consistent: less waste, lower costs, and "
            "customers who say they prefer shops that do it. The obstacle is not customer resistance but the "
            "habit of ordering by appearance."
        ),
        "qs": [
            ("According to the passage, supermarkets discard food mainly because",
             ["customers refuse to buy it", "it does not meet appearance or date rules",
              "it is unsafe to eat", "storage space is limited"], 1,
             "细节题，关键词 throw away 与 reasons，定位 have little to do with hunger and everything to do with appearance。",
             "选 customers refuse to buy it——末句明确说 The obstacle is not customer resistance。",
             "原文：throws away food for reasons that have little to do with hunger and everything to do with "
             "appearance，随后举例（褐斑香蕉、过期面包、凹陷纸盒）都是外观或日期规则。B 概括准确；A 与末句相反；"
             "C 与 all are edible 矛盾；D 未提。"),
            ("Some chains have removed best-before dates from fruit and vegetables in order to",
             ["raise prices", "reduce waste caused by date rules",
              "comply with new laws", "attract younger customers"], 1,
             "细节题，关键词 best-before dates，回到 removal 所在句，并联系上一句的 edible but not sellable。",
             "选 comply with new laws——原文没提法规，改动是商家自己做的（changed the rules themselves）。",
             "原文：a few have changed the rules themselves, removing best-before dates from fruit and vegetables，"
             "目的承前：这些食物 edible 却因规则不可售。故为减少由日期规则造成的浪费，选 B。"),
            ("The passage suggests that reducing food waste depends mainly on",
             ["customer education", "changing ordering and display habits",
              "building more warehouses", "lowering food prices"], 1,
             "主旨/推断题，看末句 The obstacle is not customer resistance but the habit of ordering by appearance。",
             "选 customer education——原文说障碍不是顾客抵触，教育顾客并非关键。",
             "末句：The obstacle is not customer resistance but the habit of ordering by appearance。"
             "B 与「按外观订货的习惯」同义；A 与 not customer resistance 相反；C、D 无依据。"),
        ],
        "trans": (
            "The obstacle is not customer resistance but the habit of ordering by appearance.",
            "障碍并不在于顾客的抵触，而在于按外观订货的习惯。",
            "not… but… 译「不在于……而在于……」；ordering by appearance 是动名词短语，译「按外观订货」；"
            "resistance 译「抵触」比「抵抗」更贴切。"),
        "write": (
            "Write an essay of about 150 words on the following topic: supermarkets waste large amounts of edible "
            "food. Discuss the causes and suggest what shops and customers can do.",
            "Supermarkets discard edible food for reasons that are commercial rather than biological. A spotted "
            "banana or a dented carton breaks the rules of display, and ordering systems reward full shelves over "
            "empty ones. The waste is therefore built into habits, not into customer preference. Shops can change "
            "the habits: sell imperfect produce in a designated aisle, drop best-before dates where they carry no "
            "safety meaning, and order by observed demand rather than by appearance. Customers can help by buying "
            "the discounted items and by treating a brown spot as a sign of ripeness rather than a defect. Neither "
            "change is dramatic, but together they keep good food in kitchens instead of bins.",
            "只强调「顾客应该买丑蔬果」，忽略订货与陈列规则这一主要成因。"),
    },
    {
        "id": "e2-p6", "title": "Paying without a smartphone",
        "text": (
            "Cashless payment is convenient for anyone who owns a smartphone and frustrating for anyone who does "
            "not. Shops that stop accepting cash save time at the counter, but they also exclude older customers "
            "and people without a bank account. Several cities have responded with rules requiring retailers to "
            "accept cash, and some banks now issue cards with large-print keypads and a single confirmation "
            "button. The debate is often framed as progress versus nostalgia. In practice it is a question of "
            "design: a payment system is only as good as the number of people who can use it."
        ),
        "qs": [
            ("Shops that refuse cash are criticised because they",
             ["charge higher prices", "exclude some groups of customers",
              "slow down the queue", "break international rules"], 1,
             "细节题，关键词 refuse cash 的后果，定位 they also exclude older customers and people without a bank account。",
             "选 slow down the queue——原文说 stop accepting cash save time at the counter，正好相反。",
             "原文：they also exclude older customers and people without a bank account。B 为同义；A、D 未提；"
             "C 与 save time 相反。"),
            ("The cards described in the passage are designed to",
             ["replace smartphones entirely", "make payment easier for people who struggle with small screens",
              "increase bank profits", "track customer spending"], 1,
             "细节题，关键词 cards，定位 large-print keypads and a single confirmation button。",
             "选 replace smartphones entirely——这类卡是补充手段，原文没有主张取消手机支付。",
             "原文：some banks now issue cards with large-print keypads and a single confirmation button。"
             "大字键盘与单一确认键都是为「看不清、操作困难」的人设计，B 最贴切；A、C、D 无依据。"),
            ("The author's conclusion is that a payment system should be judged by",
             ["its speed", "how many people can use it", "its novelty", "its cost to banks"], 1,
             "结论题，看末句 a payment system is only as good as the number of people who can use it。",
             "选 its speed——速度只是商家的收益，不是作者的评判标准。",
             "末句：a payment system is only as good as the number of people who can use it。B 为原文同义；"
             "A 是商家视角；C、D 未提。"),
        ],
        "trans": (
            "The debate is often framed as progress versus nostalgia. In practice it is a question of design: a payment system is only as good as the number of people who can use it.",
            "这场争论常被描述为进步与怀旧之争。而实际上，这是一个设计问题：一个支付系统的好坏，取决于有多少人能够使用它。",
            "is framed as 译「被描述为」；versus 译「与……之争」；only as good as 是固定表达，译「取决于」；"
            "冒号后的解释句保持独立。"),
        "write": (
            "Write an essay of about 150 words on the following topic: some shops no longer accept cash. Discuss the "
            "advantages and disadvantages, and give your opinion.",
            "Cashless payment saves time at the counter and reduces the cost of handling notes and coins. For a "
            "small shop, those savings are real. The disadvantage is equally real: customers without a smartphone or "
            "a bank account are excluded from ordinary shopping, and the exclusion falls hardest on older people. "
            "The choice is not between efficiency and nostalgia. It is a design question. Shops can keep fast "
            "digital payment while accepting cash at one counter, and banks can issue cards with large print and a "
            "single confirmation button. A payment system should be judged by how many people can use it, not by "
            "how modern it looks.",
            "只写「无现金很方便」或「老人可怜」，没有给出兼顾效率与包容的具体做法。"),
    },
    {
        "id": "e2-p7", "title": "Wellness programmes at work",
        "text": (
            "Company wellness programmes usually offer gym discounts, fruit in the kitchen and an app that counts "
            "steps. Reviews of their effects are mixed. Participation is highest among employees who are already "
            "healthy, and the measured improvements are small. Meanwhile the strongest influence on employee "
            "health is rarely mentioned: how work is organised. Long and unpredictable hours, low control over "
            "tasks and unclear expectations produce stress that no step counter can offset. A few employers have "
            "redirected the budget from apps to scheduling, giving teams notice of shifts and a voice in how work "
            "is divided. Reported stress fell further than in any of the fitness schemes."
        ),
        "qs": [
            ("Reviews of wellness programmes found that",
             ["they improved health substantially", "they mainly attracted already healthy employees",
              "they reduced stress more than scheduling changes", "they were too expensive"], 1,
             "细节题，关键词 reviews，定位 Participation is highest among employees who are already healthy。",
             "把 offer gym discounts 当成有效，忽略 measured improvements are small。",
             "原文：Participation is highest among employees who are already healthy, and the measured improvements "
             "are small。B 为同义；A 与 small 矛盾；C 与最后一句「降幅大于任何健身方案」相反；D 未提。"),
            ("The passage says the strongest influence on employee health is",
             ["diet", "exercise", "how work is organised", "the weather"], 2,
             "细节题，关键词 strongest influence，定位 the strongest influence on employee health is rarely mentioned: how work is organised。",
             "选 exercise——原文说锻炼类项目效果有限，真正影响大的是工作组织方式。",
             "原文：the strongest influence on employee health is rarely mentioned: how work is organised，后文列举"
             "长工时、低控制感、期望不清。C 为原文原词；A、B 是 wellness 项目的内容而非最强因素；D 无关。"),
            ("The employers who redirected their budget found that",
             ["fitness apps were more effective", "changing scheduling reduced stress more",
              "employees stopped exercising", "the budget was wasted"], 1,
             "细节题，关键词 redirected，定位末句 Reported stress fell further than in any of the fitness schemes。",
             "选 fitness apps were more effective——与末句「降幅超过任何健身方案」相反。",
             "末句：Reported stress fell further than in any of the fitness schemes。B 为同义；A、C、D 均与原文相反或无据。"),
        ],
        "trans": (
            "Long and unpredictable hours, low control over tasks and unclear expectations produce stress that no step counter can offset.",
            "漫长且不可预测的工时、对任务缺乏掌控感，以及不明确的期望，会带来任何计步器都无法抵消的压力。",
            "三个并列主语较长，译文用顿号分隔；that 引导定语从句修饰 stress；offset 译「抵消」，"
            "no step counter 前置为「任何计步器都无法……」。"),
        "write": (
            "Write an essay of about 150 words on the following topic: many companies offer wellness programmes. "
            "Do they address the real causes of workplace stress?",
            "Wellness programmes are popular because they are visible and inexpensive. A gym discount and a step "
            "counter signal that the company cares, yet the evidence suggests they reach the wrong people: "
            "participation is highest among employees who are already fit, and the measured gains are small. The "
            "main sources of stress lie elsewhere, in long and unpredictable hours, low control over tasks and "
            "unclear expectations. No app offsets a schedule that changes without notice. The more effective "
            "investment is therefore organisational: publish shifts in advance, let teams influence how work is "
            "divided, and make priorities explicit. Health programmes can supplement such changes, but they cannot "
            "substitute for them.",
            "把健康项目说成完全无用，或只呼吁「员工多运动」，回避工作组织方式这一成因。"),
    },
    {
        "id": "e2-p8", "title": "Tourism that pays for the place",
        "text": (
            "Tourism is often described as an export industry: visitors arrive, spend, and leave. The description "
            "hides a cost. A small town that attracts a million visitors a year may find its rents rising, its "
            "shops turning into souvenir stalls, and its residents moving away. Some destinations now charge an "
            "entry fee and use the money to maintain the very streets that visitors come to see. Others limit the "
            "number of cruise ships per day. The measures are unpopular with parts of the industry, but they rest "
            "on a simple idea: a place that is pleasant to visit must first be pleasant to live in."
        ),
        "qs": [
            ("The passage says the 'export industry' description",
             ["explains the full benefit of tourism", "ignores the costs borne by local residents",
              "is accepted by all economists", "applies only to small towns"], 1,
             "细节题，关键词 export industry，定位 The description hides a cost，后面列举租金上涨、商店变纪念品店、居民外迁。",
             "选 explains the full benefit——原文用 hides a cost 明确否定其完整性。",
             "原文：The description hides a cost，随后举例说明居民承担的成本。B 为同义；A 与 hides 相反；C、D 未提。"),
            ("The entry fee mentioned in the passage is used to",
             ["subsidise hotels", "maintain the streets visitors come to see",
              "advertise the town abroad", "reduce the number of residents"], 1,
             "细节题，关键词 entry fee，定位 use the money to maintain the very streets that visitors come to see。",
             "选 advertise the town——费用用途在原文已明确，是维护街道。",
             "原文：charge an entry fee and use the money to maintain the very streets that visitors come to see。"
             "B 为原文同义；A、C、D 无依据。"),
            ("The last sentence suggests that",
             ["tourism should be banned", "local liveability is a condition for sustainable tourism",
              "visitors should not pay fees", "cruise ships are the main problem"], 1,
             "主旨句题：must first be pleasant to live in 说明「宜居是宜游的前提」。",
             "选 tourism should be banned——原文主张管理，不是禁止。",
             "末句：a place that is pleasant to visit must first be pleasant to live in。B 正是该句的抽象概括；"
             "A 过度；C、D 是细节。"),
        ],
        "trans": (
            "The measures are unpopular with parts of the industry, but they rest on a simple idea: a place that is pleasant to visit must first be pleasant to live in.",
            "这些措施遭到了部分业内人士的反对，但它们基于一个简单的理念：一个宜游的地方，首先必须宜居。",
            "be unpopular with 译「遭到……反对」；rest on 译「基于」；冒号引出同位解释；"
            "pleasant to visit / to live in 对举，译「宜游」「宜居」最简洁。"),
        "write": (
            "Write an essay of about 150 words on the following topic: some tourist towns now charge an entry fee or "
            "limit visitor numbers. Discuss whether such measures are justified.",
            "Tourism brings income, but it also raises rents, replaces local shops with souvenir stalls and pushes "
            "residents out. An entry fee or a daily limit on visitors looks unwelcoming, yet it addresses a real "
            "problem: the town must remain liveable for the people who work there. The revenue can be used to "
            "maintain the streets and facilities that visitors come to see, which is precisely what a crowded "
            "destination struggles to fund. Such measures are not against tourism; they protect its foundation. The "
            "design matters, however: fees should be modest, revenue should be visible in local upkeep, and "
            "residents should not be charged for their own town.",
            "只表态「收费不合理」或「游客太多」，没有讨论费用用途与宜居前提。"),
    },
]


if __name__ == "__main__":
    for subj, data in (("e1", __import__("gen_english_questions").E1), ("e2", E2)):
        out = build(subj, data)
        (EXAM / "questions" / f"english-{subj}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"english-{subj}: {len(out['items'])} 题（{len(data)} 篇）")
