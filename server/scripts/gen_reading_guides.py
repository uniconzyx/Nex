#!/usr/bin/env python
"""生成英语阅读精读与长难句拆解（阶段16）。

数据来源分两层：
  - 原文与题目在 questions/english-*.json 里（唯一事实来源，避免两处文本不一致）
  - 精读内容（段意、词伙、长难句主干/修饰/译文/命题点）写在本文件

输出 reading/english-e1.json / english-e2.json，前端可按段落折叠展示。
长难句的「主干」只留主谓宾，「修饰」逐条列出成分与作用，这是拆句最有效的两步。
"""

from __future__ import annotations

import json
from pathlib import Path

from reading_extras import EXTRA

ROOT = Path(__file__).resolve().parents[2]
EXAM = ROOT / "content" / "_exam"

DATA = {
    "e1": {
        "e1-p1": {
            "para": [
                "现象：远程办公没有让产出崩塌，常规任务反而略快。",
                "转折：但入职两年内的员工学得更慢，因为缺少「旁观判断」的机会。",
                "应对：混合办公——需要判断的事聚在一起，需要专注的事各自分散。",
            ],
            "vocab": [
                ("collapse", "n.", "崩塌、骤降", "The collapse never came：预言中的下滑并未出现"),
                ("absorb", "v.", "吸收、习得", "absorb judgement 译「习得判断力」，不是「吸收判断」"),
                ("transmit", "v.", "传递", "transmit information but not atmosphere：传递信息但不传递氛围"),
                ("hybrid", "adj.", "混合的", "hybrid weeks 指部分到岗、部分远程的工作周"),
                ("disperse", "v.", "分散", "与 gather 对举，指团队各自散开"),
            ],
            "sentences": [
                ("Studies covering tens of thousands of workers found that routine tasks were completed slightly faster at home, largely because commutes disappeared and meetings shrank.",
                 "Studies found that routine tasks were completed slightly faster.",
                 "covering… 现在分词作后置定语修饰 Studies；that 引导宾语从句；largely because… 原因状语从句，说明「为什么略快」。",
                 "覆盖数万名员工的研究发现，常规任务在家完成得略快，主要原因是通勤消失、会议缩短。",
                 "细节题定位句。found that 后是结论，because 后是原因，命题常把两者拆开，问「原因是什么」。"),
                ("Sitting near experienced colleagues, they had absorbed judgement by watching it being exercised.",
                 "they had absorbed judgement.",
                 "Sitting… 现在分词作方式状语；by watching… 方式状语；being exercised 现在分词被动，作 watching 的宾补。",
                 "坐在有经验的同事身边，他们通过观察判断力如何被运用而习得了这种判断力。",
                 "翻译题原句。分词状语要译成「坐在……身边」，being exercised 要转成主动「如何被运用」。"),
                ("Video calls transmit information but not atmosphere, and a junior hire who does not know what to ask cannot ask it.",
                 "Video calls transmit information but not atmosphere, and a junior hire cannot ask it.",
                 "who 引导定语从句修饰 hire；what to ask 作 know 的宾语；it 指 the question。",
                 "视频通话传递信息，却不传递氛围；而一个不知道该问什么的初级员工，也无从问起。",
                 "推断题依据。but not 是显性对比，cannot ask it 是隐性结果，二者合起来说明「氛围缺失导致学得慢」。"),
            ],
        },
        "e1-p2": {
            "para": [
                "立论：城市树木常被当作装饰，医学证据支持把它当作基础设施。",
                "证据：住得离成熟树木近的人压力更低、睡得更长，在最热的月份效果最强。",
                "结论：砍树修路是健康决策，应把医疗节省计入工程成本；已有城市这么做。",
            ],
            "vocab": [
                ("infrastructure", "n.", "基础设施", "作者用它强调「应纳入公共成本核算」"),
                ("mature", "adj.", "成熟的（树）", "mature trees 指成年大树，遮荫能力最强"),
                ("shade", "n.", "树荫", "shade lowered surface temperatures：树荫降低地表温度"),
                ("substitute", "n.", "替代品", "a substitute for clinics：不能替代诊所"),
                ("cost", "v.", "核算成本", "should be costed as one：按健康决策来核算"),
            ],
            "sentences": [
                ("Researchers tracking thousands of residents found that people living within a short walk of mature trees reported lower stress and slept longer, even after income and noise were taken into account.",
                 "Researchers found that people reported lower stress and slept longer.",
                 "tracking… 现在分词定语；living… 现在分词定语；even after… 让步状语从句，表示「排除混杂因素后仍成立」。",
                 "追踪数千名居民的研究者发现，住在离成熟树木几步之遥的人压力更低、睡眠更长，即便把收入和噪音因素考虑在内也是如此。",
                 "细节题定位句。even after 是「结论可靠」的标志，选项若说「因为富人区树多」即被此句排除。"),
                ("It does mean that a decision to remove a row of trees for a wider road is a health decision, and should be costed as one.",
                 "It does mean that a decision is a health decision and should be costed as one.",
                 "does 表强调；to remove… 不定式作定语修饰 decision；for a wider road 目的状语；as one 中的 one 指 a health decision。",
                 "它确实意味着，为拓宽道路而砍掉一排树的决定是一个健康决策，并且应当按健康决策来核算成本。",
                 "词义/态度题依据。作者用 infrastructure 不是比喻，而是主张「计入成本」，这句是直接证据。"),
                ("A few cities have begun to do exactly that, listing the medical savings alongside the construction costs in their planning documents.",
                 "A few cities have begun to do that.",
                 "listing… 现在分词作伴随状语；alongside… 介词短语说明并列关系。",
                 "少数城市已经开始这样做：在规划文件中把医疗节省与建设成本并列列出。",
                 "末句作用题。exactly that 回指上一句的「按健康决策核算成本」，说明理念已落地。"),
            ],
        },
        "e1-p3": {
            "para": [
                "背景：科学靠重复确立知识，但多个领域的大规模重复实验发现大量结果无法复现。",
                "原因：样本小、分析选择多、期刊奖励新颖性——是平常做法，不是学术不端。",
                "对策：预注册分析方案、发表阴性结果、把重复研究当作常规投入。",
            ],
            "vocab": [
                ("replication", "n.", "重复实验", "replication projects 重复性研究项目"),
                ("reproduce", "v.", "复现", "findings cannot be reproduced 结果无法复现"),
                ("mundane", "adj.", "平常的、乏味的", "mundane rather than scandalous：平常而非丑闻"),
                ("unbiased", "adj.", "无偏的", "an unbiased estimate 无偏估计"),
                ("novelty", "n.", "新颖性", "journals reward novelty over confirmation：重新颖轻验证"),
            ],
            "sentences": [
                ("A researcher who tries twenty statistical models and reports the one that worked is not lying, but the reported result is no longer an unbiased estimate.",
                 "A researcher is not lying, but the result is no longer an unbiased estimate.",
                 "who… 定语从句；that worked 定语从句修饰 the one；not… but… 构成转折。",
                 "一位尝试二十种统计模型、只报告其中奏效那一种的研究者并没有撒谎，但其所报告的结果已不再是无偏估计。",
                 "例证题核心句。is not lying 排除「造假」选项，but 后才是作者真正的判断。"),
                ("Reformers propose three remedies: register the analysis plan before collecting data, publish negative results, and fund replication as a normal part of research rather than as a curiosity.",
                 "Reformers propose three remedies.",
                 "冒号后三个并列动词短语作同位解释；rather than 对比「常规投入」与「猎奇」。",
                 "改革者提出三条补救措施：在收集数据前登记分析方案、发表阴性结果，以及把重复研究当作科研的常规部分而非猎奇之举。",
                 "否定细节题出处。三条措施与选项一一对应，未出现的那一项才是答案。"),
                ("The causes are mundane rather than scandalous.",
                 "The causes are mundane.",
                 "rather than 引导对比成分，否定 scandalous。",
                 "这些原因是平常的，而非丑闻性的。",
                 "定性句。凡是把原因归为「学者造假」的选项，都与这句直接冲突。"),
            ],
        },
        "e1-p4": {
            "para": [
                "现状：图像模型在部分癌症识别上已达专家水平，但新闻往往到此为止。",
                "局限：换设备精度会掉；只给概率不给理由，医生不敢贸然采用。",
                "出路：把模型放在医生身边做分诊与复核提示，而不是取代医生。",
            ],
            "vocab": [
                ("calibrate", "v.", "校准", "calibrated on the population 在特定人群上校准"),
                ("accuracy", "n.", "准确率", "accuracy may fall sharply 精度可能骤降"),
                ("interrogate", "v.", "追问、质询", "a number they cannot interrogate 无法追问的数字"),
                ("deployment", "n.", "部署、应用", "the most promising deployments 最有前景的应用方式"),
                ("flag", "v.", "标记", "flag images 标记影像"),
            ],
            "sentences": [
                ("A model is calibrated on the population it was trained on; move it to a hospital with different equipment and its accuracy may fall sharply.",
                 "A model is calibrated; its accuracy may fall.",
                 "it was trained on 是省略 which 的定语从句；move… and… 为「祈使句 + and」表条件。",
                 "模型是在它所训练的人群上校准的；把它搬到设备不同的医院，精度可能骤降。",
                 "细节题依据。分号前后是「前提—后果」，选项若说「精度固定」即与此句矛盾。"),
                ("It also reports a probability, not a reason, and clinicians are understandably reluctant to act on a number they cannot interrogate.",
                 "It reports a probability, and clinicians are reluctant.",
                 "not a reason 对比；they cannot interrogate 是省略 which 的定语从句。",
                 "它给出的还是概率而非理由，临床医生不愿依据一个无法追问的数字行事，也在情理之中。",
                 "因果链：只给概率 → 无法追问 → 不愿采纳。问「医生为何犹豫」时定位此句。"),
                ("The most promising deployments therefore place the model beside the doctor rather than in place of the doctor, using it to sort urgent cases and to flag images that deserve a second look.",
                 "Deployments place the model beside the doctor.",
                 "rather than 对比；using it 伴随状语；that deserve… 定语从句。",
                 "因此最有前景的部署方式，是把模型放在医生身边而非取代医生，用它分诊急症、标记值得复查的影像。",
                 "主旨题依据。beside 与 in place of 的对立，就是「辅助」与「替代」的分界。"),
            ],
        },
        "e1-p5": {
            "para": [
                "现象：闭馆期间博物馆把藏品搬上网，虚拟参观吸引数百万人。",
                "数据：线上访客只停留几分钟、很少回访，像逛橱窗而不是参观。",
                "定位：数字版的优势在「参观前准备」和「参观后回看」，它是门口不是替代品。",
            ],
            "vocab": [
                ("subtle", "adj.", "微妙的", "a subtler story 更微妙的情况"),
                ("browse", "v.", "浏览", "browsing a shop window 逛橱窗"),
                ("substitute", "n.", "替代品", "a substitute for the gallery 展厅的替代品"),
                ("doorway", "n.", "门口、入口", "treat it as a doorway 把它当作入口"),
                ("follow-up", "n.", "后续跟进", "preparation and follow-up 行前准备与行后回看"),
            ],
            "sentences": [
                ("Online visitors spend minutes, not hours, and rarely return; they behave like people browsing a shop window rather than like visitors.",
                 "Online visitors spend minutes and rarely return.",
                 "not hours 对比；browsing… 现在分词定语；rather than 对比两种身份。",
                 "线上访客只停留几分钟而非几小时，且很少回访；他们的行为更像逛橱窗的人，而不像参观者。",
                 "细节题依据。minutes / rarely return 是量化证据，直接否掉「黏性高」的选项。"),
                ("What the digital version does well is preparation and follow-up: a teacher can show a class a painting before a visit, and a visitor can look again at an object that caught the eye.",
                 "What the digital version does well is preparation and follow-up.",
                 "What 引导主语从句；冒号后两个例子分别对应 preparation 与 follow-up；that caught the eye 定语从句。",
                 "数字版真正擅长的是行前准备与行后回看：教师可以在参观前给班级展示一幅画，访客也可以再次端详一件曾吸引他的展品。",
                 "细节题依据。冒号后是举例，答题时要能判断哪个选项属于「准备」、哪个属于「回看」。"),
                ("Museums that treat the website as a substitute for the gallery are disappointed; those that treat it as a doorway are not.",
                 "Museums are disappointed; those are not.",
                 "两个 that 定语从句；those 指代 museums；it 指 the website。",
                 "把网站当作展厅替代品的博物馆会失望；把它当作入口的博物馆则不会。",
                 "词义题依据。substitute 与 doorway 的对立，决定 doorway 应理解为「通向实体体验的入口」。"),
            ],
        },
        "e1-p6": {
            "para": [
                "现象：学生把睡眠当作考前可透支的储备。",
                "机制与实验：深睡重放白天的模式并巩固记忆；同样学习时间下，睡整夜者记得更多。",
                "结论：睡眠不是学习之外的时间，而是学习过程的一部分。",
            ],
            "vocab": [
                ("reserve", "n.", "储备", "a reserve to be spent 可支取的储备"),
                ("consolidate", "v.", "巩固", "consolidating them into longer-term memory 巩固为长期记忆"),
                ("replay", "v./n.", "重放", "the brain replays patterns 大脑重放模式"),
                ("identical", "adj.", "完全相同的", "the total study time was identical 学习总时长相同"),
                ("implication", "n.", "含义、推论", "an uncomfortable implication 令人不安的推论"),
            ],
            "sentences": [
                ("During deep sleep the brain replays patterns formed during the day, consolidating them into longer-term memory; cut the night short and the replay is cut short with it.",
                 "The brain replays patterns; the replay is cut short.",
                 "formed… 过去分词定语；consolidating… 伴随状语；cut… and… 条件句；with it 中的 it 指 the night。",
                 "在深度睡眠中，大脑会重放白天形成的模式，并将其巩固为长期记忆；若缩短夜间睡眠，重放也会随之缩短。",
                 "机制句，也是翻译题原句。consolidating 要译成并列动作，不能译成定语。"),
                ("In one experiment, participants who learned a list of words in the evening recalled more after a full night than after a half night, although the total study time was identical.",
                 "Participants recalled more.",
                 "who 定语从句；than 比较结构；although 让步状语从句。",
                 "在一项实验中，晚上学习词表的参与者在睡满一夜后比只睡半夜后回忆得更多，尽管学习总时长完全相同。",
                 "细节题依据。although 从句排除「他们学得更久」这一解释，是选项设置的分水岭。"),
                ("Sleep is not time away from study; it is part of the process.",
                 "Sleep is not time away; it is part of the process.",
                 "分号连接两个并列分句，形成否定—肯定的定义式表达。",
                 "睡眠不是从学习中抽走的时间，它就是学习过程的一部分。",
                 "主旨句。观点明确、无绝对化，适合作为 main idea 的答案依据。"),
            ],
        },
        "e1-p7": {
            "para": [
                "吸引力：碳标签让每次购买都像一次气候选择。",
                "效果有限：只能让购买偏移几个百分点，遇到价格竞争就失效。",
                "深层问题：排放由生产、运输、供暖等系统决定，标签只能影响单次选择，需与规则配合。",
            ],
            "vocab": [
                ("modestly", "adv.", "幅度不大地", "change behaviour, but modestly 有改变但幅度小"),
                ("fade", "v.", "减弱、消退", "the effect fades 效果消退"),
                ("arithmetic", "n.", "算术；此处指「算总账」", "The deeper problem is arithmetic 更深层是总量问题"),
                ("reduction", "n.", "削减", "deliver large reductions 带来大幅减排"),
                ("alongside", "prep.", "与……一起", "work best alongside rules 与规则配合效果最好"),
            ],
            "sentences": [
                ("Trials in several countries show that labels do change behaviour, but modestly: shoppers shift a few percentage points toward lower-carbon options, and the effect fades when the label competes with price.",
                 "Trials show that labels do change behaviour, but modestly.",
                 "that 宾语从句；do 表强调；冒号后解释 modestly；when 时间/条件状语从句。",
                 "多国试验表明，标签确实改变了行为，但幅度有限：消费者会向低碳选项偏移几个百分点，而一旦标签与价格竞争，效果便消退。",
                 "细节题依据。modestly 与 fades 是两个限定词，选项若说「效果显著且持久」即错。"),
                ("Expecting labels to deliver large reductions is like expecting a menu to improve a restaurant's kitchen.",
                 "Expecting labels to deliver reductions is like expecting a menu to improve a kitchen.",
                 "两个动名词短语分别作主语和宾语；is like 构成明喻。",
                 "指望标签带来大幅减排，就像指望菜单去改善餐厅的厨房一样。",
                 "类比题。menu 对应 label（信息），kitchen 对应 system（生产），类比的方向不能颠倒。"),
                ("Labels are worth having, but they work best alongside rules that change what is on offer.",
                 "Labels are worth having, but they work best alongside rules.",
                 "that 定语从句修饰 rules；what is on offer 宾语从句。",
                 "标签值得拥有，但它与「改变供给内容」的规则配合时效果最好。",
                 "结论句。既肯定标签（worth having）又指出不足（alongside rules），答案应是「有用但不充分」。"),
            ],
        },
        "e1-p8": {
            "para": [
                "说法：平台工作以灵活著称，司机可以中午开工、四点收工。",
                "代价：按独立承包商归类，平台不缴保险与养老，空等成本由工人承担，折算时薪偏低。",
                "政策问题：不是灵活好不好，而是谁为灵活付费；应保留灵活、分摊保险。",
            ],
            "vocab": [
                ("contractor", "n.", "承包商", "independent contractors 独立承包商"),
                ("contribute", "v.", "缴纳、贡献", "does not contribute to insurance 不缴保险"),
                ("idle", "adj.", "空闲的", "the cost of idle time 空等时间的成本"),
                ("subtract", "v.", "扣除", "once these costs are subtracted 扣除这些成本后"),
                ("portable", "adj.", "可携带的", "portable insurance account 可随人转移的保险账户"),
            ],
            "sentences": [
                ("Because gig workers are classified as independent contractors, the platform does not contribute to insurance or retirement, and the worker bears the cost of idle time.",
                 "The platform does not contribute, and the worker bears the cost.",
                 "Because 原因状语从句；or 连接 insurance 与 retirement；bear the cost 为「承担成本」。",
                 "由于零工劳动者被归类为独立承包商，平台不为他们缴纳保险或养老，空等时间的成本也由劳动者自己承担。",
                 "细节题依据。这句是「灵活不免费」的具体机制，成本转移的两个方向都在这里。"),
                ("Surveys find that hourly earnings, once these costs are subtracted, are often below those of comparable salaried jobs.",
                 "Hourly earnings are often below those of salaried jobs.",
                 "once… 条件状语从句作插入语；those 指 earnings。",
                 "调查发现，扣除这些成本后，小时收入往往低于可比的全职受薪岗位。",
                 "数据依据。比较对象是 comparable salaried jobs，选项若扩大为「所有工作」即偷换范围。"),
                ("A system that lets workers keep the flexibility while sharing the insurance cost would be both fairer and more stable.",
                 "A system would be both fairer and more stable.",
                 "that 定语从句；while 表对比；both… and… 并列两个形容词比较级。",
                 "一种既让劳动者保留灵活性、又共同分摊保险成本的制度，会更公平也更稳定。",
                 "政策建议句。问「作者建议什么」时，答案必须同时包含「保留灵活」和「分摊成本」两半。"),
            ],
        },
    },
    "e2": {
        "e2-p1": {
            "para": [
                "问题：宿舍装了回收桶，但第一次调查只有三分之一瓶子投对。",
                "做法：不加桶，改为每周公布各楼正确率，并让保洁把分错的袋子留在桶边附短说明。",
                "结果与启示：一学期升到近四分之三；人需要的不是更多说明，而是看见自己做得怎样。",
            ],
            "vocab": [
                ("disappointing", "adj.", "令人失望的", "The first survey was disappointing"),
                ("sort", "v.", "分类", "sorted correctly 分类正确"),
                ("chart", "n.", "图表", "a weekly chart 每周图表"),
                ("rate", "n.", "比率", "the rate rose to nearly three quarters"),
                ("neighbour", "n.", "邻居", "compared with their neighbours 与邻楼相比"),
            ],
            "sentences": [
                ("Instead of adding more bins, the housing office tried something cheaper.",
                 "The housing office tried something cheaper.",
                 "Instead of… 介词短语作状语，表示「而不是」。",
                 "宿管部门没有增加垃圾桶，而是尝试了更省钱的办法。",
                 "转折句。Instead of 直接否掉「多买桶」的选项，是细节题的分界。"),
                ("The lesson is that people do not need more instructions; they need to see how they are doing compared with their neighbours.",
                 "The lesson is that people need to see how they are doing.",
                 "that 表语从句；how 宾语从句；compared with… 过去分词短语作状语。",
                 "这一做法的启示是：人们并不需要更多说明，他们需要看到自己与邻居相比做得如何。",
                 "主旨句。not… 与分号后的肯定形成对照，答案应落在「可见的反馈」。"),
            ],
        },
        "e2-p2": {
            "para": [
                "反差：线上课本该方便老年人，报名人数多但完成率远低于年轻人。",
                "原因：不是态度问题，而是操作门槛——菜单、上传、进会议，一步卡住就放弃。",
                "办法：前两周配学生助手，完成率大幅上升；技术不是障碍，独自学技术才是。",
            ],
            "vocab": [
                ("attitudinal", "adj.", "态度上的", "practical rather than attitudinal 是操作而非态度问题"),
                ("navigate", "v.", "操作、浏览（界面）", "navigate menus 操作菜单"),
                ("pilot", "adj./n.", "试点的", "a pilot programme 试点项目"),
                ("completion", "n.", "完成率", "raised completion sharply 大幅提高完成率"),
                ("barrier", "n.", "障碍", "The technology was not the barrier"),
            ],
            "sentences": [
                ("The reasons are practical rather than attitudinal: platforms assume users can navigate menus, upload files and join video calls, and a single confusing step can end the attempt.",
                 "The reasons are practical.",
                 "rather than 对比；冒号后解释 practical 的具体内容；assume 后接省略 that 的宾语从句。",
                 "原因是操作层面的，而非态度层面的：平台假定用户会操作菜单、上传文件、加入视频通话，而一个令人困惑的步骤就可能让尝试中断。",
                 "细节题依据。practical rather than attitudinal 一句排除「不愿学」的选项。"),
                ("The technology was not the barrier; learning the technology alone was.",
                 "The technology was not the barrier; learning it alone was the barrier.",
                 "分号连接两个分句；alone 修饰 learning；句末 was 后省略 the barrier。",
                 "技术本身并不是障碍；真正的障碍在于要独自学会使用这项技术。",
                 "结论句。省略结构是翻译与理解难点，答题时要补出省略成分。"),
            ],
        },
        "e2-p3": {
            "para": [
                "预期与现实：共享单车承诺绿色出行，多城却出现「第一年火热、随后趋平」。",
                "存活关键：把车投到真正有需求的地方（地铁口、住宅区），而非撒在市中心。",
                "规则：指定停车区让街道整洁、使用率更高；随意停放则相反。",
            ],
            "vocab": [
                ("ridership", "n.", "骑行量", "Ridership peaks in the first year"),
                ("flatten", "v.", "趋于平缓", "then flattens 随后走平"),
                ("estate", "n.", "住宅区", "housing estates 住宅小区"),
                ("scatter", "v.", "散布", "scattering them across the centre 撒在市中心"),
                ("marked", "adj.", "划定的", "marked areas 指定区域"),
            ],
            "sentences": [
                ("The companies that survive tend to be those that moved bikes to where people actually need them, near metro exits and housing estates, instead of scattering them across the centre.",
                 "The companies tend to be those.",
                 "两个 that 定语从句；where 宾语从句作 to 的宾语；instead of 对比。",
                 "存活下来的公司往往是那些把车投放到人们真正需要之处——地铁口和住宅区——而不是撒在市中心的公司。",
                 "细节题依据。instead of 否掉「撒在市中心」，near… 给出正确投放点。"),
                ("Where bikes may be left only in marked areas, streets stay tidy and the service is used more; where they may be left anywhere, the opposite happens.",
                 "Streets stay tidy and the service is used more; the opposite happens.",
                 "Where 引导地点状语从句（两处）；the opposite 指「街道乱、使用少」。",
                 "在只允许停放在指定区域的地方，街道保持整洁、服务使用率更高；而在可随意停放的地方，情况正好相反。",
                 "细节题依据。两个 where 形成对照，答案必须体现「规则严→使用多」这一反直觉结论。"),
            ],
        },
        "e2-p4": {
            "para": [
                "学生认知：认为只有亮眼实习才算数。",
                "调查结果：志愿经历很少被列为硬性要求，但面试官常问「合作解决问题」的经历。",
                "原因：价值不在活动本身，而在它提供的可靠、协作、坚持的证据。",
            ],
            "vocab": [
                ("recruiter", "n.", "招聘人员", "graduate recruiters 校招招聘官"),
                ("requirement", "n.", "要求", "rarely listed as a requirement"),
                ("shift", "n.", "班次", "a food bank shift 食物银行的一班岗"),
                ("coordination", "n.", "协作", "evidence of coordination 协作的证据"),
                ("persistence", "n.", "坚持", "reliability, coordination and persistence"),
            ],
            "sentences": [
                ("Volunteering was rarely listed as a requirement, yet interviewers frequently asked candidates to describe a situation where they had worked with others to solve a problem.",
                 "Volunteering was rarely a requirement, yet interviewers asked candidates to describe a situation.",
                 "yet 表转折；where 定语从句修饰 situation；ask sb to do 结构。",
                 "志愿经历很少被列为硬性要求，但面试官常请候选人描述一个与他人合作解决问题的情境。",
                 "细节题依据。「不是要求」与「常被追问」并存，正是 half right 的第一半。"),
                ("The value lies less in the activity itself than in the evidence it provides of reliability, coordination and persistence.",
                 "The value lies in the evidence.",
                 "less… than… 比较结构；it provides 是省略 which 的定语从句。",
                 "其价值与其说在于活动本身，不如说在于它所提供的、关于可靠、协作与坚持的证据。",
                 "例证题结论句。活动标签不重要，提供的证据才重要，这是选项辨析的核心。"),
            ],
        },
        "e2-p5": {
            "para": [
                "现象：超市丢弃食物，原因多与外观和日期规则有关，而非不能吃。",
                "做法：设折扣货架、取消部分果蔬的保质期标签，效果是浪费减少、成本下降。",
                "障碍：不是顾客抵触，而是按外观订货的习惯。",
            ],
            "vocab": [
                ("edible", "adj.", "可食用的", "all are edible 都可食用"),
                ("sellable", "adj.", "可销售的", "none is sellable by the usual rules"),
                ("aisle", "n.", "货架通道", "a separate aisle 单独的货架区"),
                ("discard", "v.", "丢弃", "supermarkets discard food"),
                ("resistance", "n.", "抵触", "not customer resistance"),
            ],
            "sentences": [
                ("A supermarket throws away food for reasons that have little to do with hunger and everything to do with appearance.",
                 "A supermarket throws away food for reasons.",
                 "that 定语从句；have little to do with… and everything to do with… 对比结构。",
                 "超市丢弃食物，其原因与饥饿几乎无关，而完全与外观有关。",
                 "主旨句。little… everything… 的对比直接锁定「外观规则」这一成因。"),
                ("The obstacle is not customer resistance but the habit of ordering by appearance.",
                 "The obstacle is the habit.",
                 "not… but… 结构；ordering by appearance 动名词短语作 of 的宾语。",
                 "障碍并不在于顾客的抵触，而在于按外观订货的习惯。",
                 "结论句。否定顾客责任，指向商家订货习惯，是推断题的依据。"),
            ],
        },
        "e2-p6": {
            "para": [
                "两面性：无现金支付对有机者方便，对无机者构成排斥。",
                "应对：部分城市要求商户收现金，部分银行推出大字键盘、单键确认的卡。",
                "结论：这不是进步与怀旧之争，而是设计问题——好系统取决于有多少人能用。",
            ],
            "vocab": [
                ("cashless", "adj.", "无现金的", "Cashless payment 无现金支付"),
                ("exclude", "v.", "排斥", "exclude older customers 把老年顾客排除在外"),
                ("retailer", "n.", "零售商", "requiring retailers to accept cash"),
                ("keypad", "n.", "键盘", "large-print keypads 大字键盘"),
                ("nostalgia", "n.", "怀旧", "progress versus nostalgia 进步与怀旧之争"),
            ],
            "sentences": [
                ("Shops that stop accepting cash save time at the counter, but they also exclude older customers and people without a bank account.",
                 "Shops save time, but they exclude customers.",
                 "that 定语从句；but 转折；介词短语 without a bank account 作定语。",
                 "停止收现金的商店节省了柜台时间，但也把老年顾客和没有银行账户的人排除在外。",
                 "细节题依据。saves… but excludes… 是典型的「收益—代价」结构，选项只取一半即为片面。"),
                ("A payment system is only as good as the number of people who can use it.",
                 "A payment system is only as good as the number of people.",
                 "only as good as 比较结构；who 定语从句。",
                 "一个支付系统的好坏，取决于有多少人能够使用它。",
                 "结论句。评判标准是「可用人数」，不是速度或新颖度。"),
            ],
        },
        "e2-p7": {
            "para": [
                "现状：企业健康项目多是健身折扣、水果、计步 App。",
                "效果有限：参与者本就是健康人群，改善幅度小。",
                "真正的成因：工时长且不可预测、缺乏掌控感、期望不清；改排班比改 App 更有效。",
            ],
            "vocab": [
                ("wellness", "n.", "健康（项目）", "wellness programmes 员工健康项目"),
                ("participation", "n.", "参与率", "Participation is highest among…"),
                ("offset", "v.", "抵消", "no step counter can offset 计步器无法抵消"),
                ("schedule", "n./v.", "排班", "redirected the budget from apps to scheduling"),
                ("shift", "n.", "轮班", "notice of shifts 提前告知班次"),
            ],
            "sentences": [
                ("Participation is highest among employees who are already healthy, and the measured improvements are small.",
                 "Participation is highest and improvements are small.",
                 "who 定语从句；两个并列分句。",
                 "参与率最高的恰恰是本来就很健康的员工，而测得的改善幅度很小。",
                 "细节题依据。「本来健康 + 改善小」两句并列，共同否定健康项目的效果。"),
                ("Long and unpredictable hours, low control over tasks and unclear expectations produce stress that no step counter can offset.",
                 "Hours, control and expectations produce stress.",
                 "三个并列主语；that 定语从句修饰 stress；no… can offset 否定结构。",
                 "漫长且不可预测的工时、对任务缺乏掌控感、以及不明确的期望，会带来任何计步器都无法抵消的压力。",
                 "因果句。压力来源是工作组织方式，这正是作者主张改排班的依据。"),
            ],
        },
        "e2-p8": {
            "para": [
                "说法与代价：旅游被说成出口产业，但这个说法掩盖了居民承担的成本。",
                "做法：收门票维护街道、限制每日游轮数量。",
                "理念：宜游之地必先宜居。",
            ],
            "vocab": [
                ("export", "n.", "出口（产业）", "an export industry 出口型产业"),
                ("rent", "n.", "租金", "its rents rising 租金上涨"),
                ("souvenir", "n.", "纪念品", "souvenir stalls 纪念品摊"),
                ("cruise", "n.", "游轮", "cruise ships 游轮"),
                ("liveable", "adj.", "宜居的", "pleasant to live in 宜居"),
            ],
            "sentences": [
                ("The description hides a cost.",
                 "The description hides a cost.",
                 "主谓宾结构，短句承担转折功能。",
                 "这一说法掩盖了一项成本。",
                 "转折句。它否定了「旅游纯属收益」的前提，是推断题「作者为何不满」的依据。"),
                ("A place that is pleasant to visit must first be pleasant to live in.",
                 "A place must first be pleasant to live in.",
                 "that 定语从句；first 强调先后条件。",
                 "一个宜游的地方，首先必须宜居。",
                 "结论句。宜居是宜游的前提，对应「可持续发展」的立场。"),
            ],
        },
    },
}


def build(subj: str) -> dict:
    qdata = json.loads((EXAM / "questions" / f"english-{subj}.json").read_text(encoding="utf-8"))
    passages: dict[str, dict] = {}
    for q in qdata["items"]:
        p = q.get("passage")
        if not p:
            continue
        key = p["id"]
        if key not in passages:
            passages[key] = {"id": key, "title": p["title"], "text": p["text"],
                             "paragraphs": [], "vocab": [], "sentences": [], "questionMap": []}
        passages[key]["questionMap"].append({
            "qid": q["id"],
            "type": q["type"],
            "locate": q["walkthrough"]["approach"].split("。")[0],
        })

    for pid, extra in DATA[subj].items():
        if pid not in passages:
            raise SystemExit(f"{pid} 不在题库的 passage 中")
        g = passages[pid]
        g["paragraphs"] = [{"no": i, "zh": t} for i, t in enumerate(extra["para"], 1)]
        g["vocab"] = [{"word": w, "pos": pos, "cn": cn, "note": note}
                      for w, pos, cn, note in extra["vocab"]]
        g["sentences"] = [{"en": en, "main": main, "mods": mods, "zh": zh, "point": point}
                          for en, main, mods, zh, point in extra["sentences"]]
        ex = EXTRA.get(subj, {}).get(pid, {})
        g["takeaway"] = ex.get("takeaway", [])
        g["falseFriends"] = [{"word": w, "usual": u, "here": h, "note": n}
                             for w, u, h, n in ex.get("falseFriends", [])]
        g["synonyms"] = [{"from": a, "to": b} for a, b in ex.get("synonyms", [])]

    return {"subject": subj, "exam": "english",
            "passages": [passages[k] for k in DATA[subj] if k in passages]}


if __name__ == "__main__":
    out_dir = EXAM / "reading"
    out_dir.mkdir(exist_ok=True)
    for subj in ("e1", "e2"):
        data = build(subj)
        (out_dir / f"english-{subj}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        n_s = sum(len(p["sentences"]) for p in data["passages"])
        n_w = sum(len(p["vocab"]) for p in data["passages"])
        print(f"english-{subj}: {len(data['passages'])} 篇 / 长难句 {n_s} / 词伙 {n_w}")
