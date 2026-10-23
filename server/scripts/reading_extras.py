#!/usr/bin/env python
"""阅读读后复盘数据（阶段16）。

每篇文章固定三块：
  takeaway      读完的总结：主旨、命题手法、最容易错在哪
  falseFriends  熟词生义：常见义 → 文中义，配原句
  synonyms      同义替换：原文表达 ↔ 选项/题干表达

这三块是「做完题之后真正留下来的东西」。只刷题不复盘，下次遇到同样的替换仍然认不出。
"""

from __future__ import annotations

EXTRA = {
    "e1": {
        "e1-p1": {
            "takeaway": [
                "主旨：远程办公保住了常规产出，却削弱了新人「旁观学习」的机会，混合办公是对这一取舍的回应。",
                "命题手法：用 studies found 引结论、用 although/but 设限定，正确项多是限定后的版本。",
                "易错点：把「远程效率略高」扩大成「远程全面更好」，忽略 junior 这一段的反例。",
            ],
            "falseFriends": [
                ("shrink", "收缩、缩水", "（会议）缩短", "meetings shrank：不是「会议缩水」，而是时长变短"),
                ("hire", "雇佣（动词）", "新员工（名词）", "a junior hire：此处 hire 指被雇用的人"),
                ("absorb", "吸收（液体、知识）", "习得（判断力）", "absorb judgement：靠观察养成判断力，不是「吸收判断」"),
            ],
            "synonyms": [
                ("routine tasks", "everyday work / repetitive duties"),
                ("slightly faster", "a modest speed-up"),
                ("learn more slowly", "absorb less / develop more slowly"),
                ("atmosphere", "the feel of a workplace"),
                ("judgement", "the ability to make sound decisions"),
            ],
        },
        "e1-p2": {
            "takeaway": [
                "主旨：树木不是装饰而是健康基础设施，砍树修路应按健康决策核算成本。",
                "命题手法：先让步（不能替代诊所）再推进（但应计入成本），答案落在让步之后。",
                "易错点：把 infrastructure 当成修辞，忽略作者「计入预算」的具体主张。",
            ],
            "falseFriends": [
                ("cost", "成本（名词）", "核算成本（动词）", "should be costed as one：按健康决策来计价"),
                ("mature", "成熟的（人）", "成年的（树）", "mature trees：树冠已成、遮荫能力最强的树"),
                ("row", "一排、一行", "一排（树）", "a row of trees：注意不是「争吵」"),
            ],
            "synonyms": [
                ("infrastructure", "public assets / essential facilities"),
                ("lower stress", "less anxiety"),
                ("taken into account", "allowed for / controlled for"),
                ("medical savings", "health-care cost reductions"),
            ],
        },
        "e1-p3": {
            "takeaway": [
                "主旨：大量结果无法复现，原因多是平常的研究做法与激励，而非造假；对策是预注册、发阴性结果、资助重复。",
                "命题手法：定性句（mundane rather than scandalous）+ 三条并列措施，NOT 题就从这里出。",
                "易错点：把「无法复现」直接等同于「学术不端」。",
            ],
            "falseFriends": [
                ("negative results", "负面结果（直觉）", "阴性结果 / 未获支持的结果", "publish negative results：指没做出显著差异的结果"),
                ("scandalous", "丑闻性的", "（学术）造假的", "mundane rather than scandalous：平常做法而非造假"),
                ("curiosity", "好奇心", "猎奇之物、边缘兴趣", "rather than as a curiosity：不是可有可无的猎奇研究"),
            ],
            "synonyms": [
                ("reproduce", "obtain the same result again"),
                ("mundane", "ordinary / unremarkable"),
                ("remedies", "fixes / correctives"),
                ("flexible analysis", "freedom to choose among statistical models"),
            ],
        },
        "e1-p4": {
            "takeaway": [
                "主旨：AI 读片精度已达专家水平，但换设备会掉点、只给概率不给理由，故应辅助而非替代医生。",
                "命题手法：先承认优势，再用 in practice / however 转折列局限，主旨题考转折后的立场。",
                "易错点：把 at least as accurately as 读成「永远更准」。",
            ],
            "falseFriends": [
                ("flag", "旗帜（名词）", "标记（动词）", "flag images：把影像标出来待复查"),
                ("interrogate", "审问、审讯", "追问（数据、结论）", "a number they cannot interrogate：无法追问依据的数字"),
                ("sort", "分类、排序", "分诊", "sort urgent cases：按紧急程度分流"),
            ],
            "synonyms": [
                ("accuracy", "hit rate / precision"),
                ("fall sharply", "drop dramatically"),
                ("beside the doctor", "alongside clinicians"),
                ("in place of", "instead of / as a replacement for"),
            ],
        },
        "e1-p5": {
            "takeaway": [
                "主旨：线上展览不是实体参观的替代品，而是行前准备与行后回看的入口。",
                "命题手法：数据（minutes, rarely return）+ 对比（substitute vs doorway），词义题就考这个对比。",
                "易错点：被「数百万访问量」带走，忽视停留时长与回访率。",
            ],
            "falseFriends": [
                ("subtle", "微妙的、不易察觉的", "更复杂的、另有隐情的", "a subtler story：数据讲的是另一回事"),
                ("browse", "浏览（网页）", "闲逛式观看", "browsing a shop window：只看不买式的观看"),
                ("doorway", "门口", "入口、通道（隐喻）", "treat it as a doorway：把它当作进入实体体验的通道"),
            ],
            "synonyms": [
                ("substitute", "replacement"),
                ("rarely return", "low repeat visits"),
                ("caught the eye", "attracted attention"),
                ("preparation and follow-up", "before and after the visit"),
            ],
        },
        "e1-p6": {
            "takeaway": [
                "主旨：深睡重放并巩固记忆，缩短睡眠会缩短这一过程，睡眠是学习的一部分。",
                "命题手法：机制句 + 控制变量的实验（although total study time was identical），结论句收束。",
                "易错点：把「睡整夜记得多」解释成「他们学得更久」，忽略 although 从句。",
            ],
            "falseFriends": [
                ("reserve", "储备、预留", "可支取的本钱", "a reserve to be spent：把睡眠当可透支的储备"),
                ("replay", "重播（录像）", "（大脑）重放", "the brain replays patterns：神经活动模式的重放"),
                ("identical", "完全相同的", "（时长）一模一样", "the total study time was identical：总学习时长相同"),
            ],
            "synonyms": [
                ("consolidate", "stabilize / fix in memory"),
                ("cut short", "interrupt / shorten"),
                ("recalled more", "remembered a greater number"),
                ("part of the process", "integral to learning"),
            ],
        },
        "e1-p7": {
            "takeaway": [
                "主旨：碳标签能改变行为但幅度有限，排放由系统决定，标签需与改变供给的规则配合。",
                "命题手法：让步（do change behaviour）+ 限定（but modestly）+ 类比（menu/kitchen）+ 结论（alongside rules）。",
                "易错点：把「有效果」当成「效果显著」，忽略 modestly 与 fades。",
            ],
            "falseFriends": [
                ("arithmetic", "算术", "算总账、总量问题", "The deeper problem is arithmetic：单次选择加起来仍不够"),
                ("deliver", "交付、递送", "带来、实现", "deliver large reductions：实现大幅减排"),
                ("on offer", "在售、提供中", "（商家）供给的内容", "what is on offer：货架上有什么"),
            ],
            "synonyms": [
                ("modestly", "slightly / to a limited degree"),
                ("fade", "weaken / disappear"),
                ("rules", "regulation / mandatory standards"),
                ("large reductions", "big cuts in emissions"),
            ],
        },
        "e1-p8": {
            "takeaway": [
                "主旨：零工的灵活性真实但非免费，保险与空等成本由工人承担；应保留灵活、分摊成本。",
                "命题手法：先立（flexibility is real）后破（but not free），末句给政策主张。",
                "易错点：把「工人重视自由」当成「零工没有问题」，两者在文中并存。",
            ],
            "falseFriends": [
                ("bear", "熊（名词）", "承担（动词）", "the worker bears the cost：工人承担成本"),
                ("contractor", "承包商", "独立承包人（无雇员福利）", "independent contractors：不享受平台缴纳的保险"),
                ("portable", "便携的", "可随人转移的", "portable insurance account：换个平台也带得走的账户"),
            ],
            "synonyms": [
                ("flexibility", "freedom to choose hours"),
                ("idle time", "hours when no work arrives"),
                ("fairer", "more equitable"),
                ("sharing the cost", "spreading the burden"),
            ],
        },
    },
    "e2": {
        "e2-p1": {
            "takeaway": [
                "主旨：比起增加设施，让人看见自己与同伴的差距更能改变行为。",
                "命题手法：先给失败数据（one third），再给低成本做法，末句点题。",
                "易错点：把「不是加桶」误读成「桶不重要」，忽略 instead of 只是否定该方案。",
            ],
            "falseFriends": [
                ("sort", "分类", "把……分类投放", "sorted correctly：分类正确"),
                ("rate", "比率", "正确率", "the rate rose to nearly three quarters：比例升到近四分之三"),
                ("chart", "图表", "周榜", "a weekly chart：每周公布的成绩表"),
            ],
            "synonyms": [
                ("feedback", "seeing how they are doing"),
                ("instructions", "guidance / leaflets"),
                ("rose to", "increased to"),
            ],
        },
        "e2-p2": {
            "takeaway": [
                "主旨：老年人线上课完成率低，卡点在操作而非态度；短期人工陪伴能显著提升完成率。",
                "命题手法：先破常识（gift for older learners），再给数据，最后用 not… but… 定性。",
                "易错点：把「完成率低」归因于「不愿学」，与 practical rather than attitudinal 冲突。",
            ],
            "falseFriends": [
                ("navigate", "航行、导航", "操作（界面）", "navigate menus：在菜单里操作"),
                ("pilot", "飞行员", "试点的", "a pilot programme：试点项目"),
                ("alone", "孤独的", "独自、无协助", "learning the technology alone：没人陪着自己摸索"),
            ],
            "synonyms": [
                ("barrier", "obstacle"),
                ("completion", "finishing the course"),
                ("pair with", "match with"),
            ],
        },
        "e2-p3": {
            "takeaway": [
                "主旨：共享单车第一年后使用趋平，存活靠投放位置与停车规则，而不是铺量。",
                "命题手法：数据趋势（peaks then flattens）+ 对比（marked areas vs anywhere）。",
                "易错点：把「规则变严」等同于「使用减少」，原文结论相反。",
            ],
            "falseFriends": [
                ("flatten", "使变平", "（增长）走平", "then flattens：不再增长但也没崩"),
                ("estate", "庄园、遗产", "住宅区", "housing estates：居民小区"),
                ("marked", "显著的、标记过的", "划定的", "marked areas：指定停车区"),
            ],
            "synonyms": [
                ("ridership", "number of riders"),
                ("level off", "stop growing"),
                ("scatter", "spread randomly"),
            ],
        },
        "e2-p4": {
            "takeaway": [
                "主旨：志愿经历不是硬性要求，但它提供的协作与坚持证据，正是面试要问的。",
                "命题手法：让步（rarely a requirement）+ 转折（yet frequently asked）+ 结论（evidence）。",
                "易错点：把 half right 理解成「一半学生是对的」，它是「学生只对了一半」。",
            ],
            "falseFriends": [
                ("shift", "转变、轮班", "一班岗", "a food bank shift：食物银行的一班志愿服务"),
                ("count", "计数", "算数、有分量", "only internships count：只有实习才算数"),
                ("half right", "一半正确（字面）", "对了一半、另一半错了", "the students are half right：判断对、理由错"),
            ],
            "synonyms": [
                ("evidence", "proof / demonstration"),
                ("persistence", "sticking with a task"),
                ("reliability", "being dependable"),
            ],
        },
        "e2-p5": {
            "takeaway": [
                "主旨：超市丢弃可食用食物，主因是外观与日期规则；障碍是订货习惯而非顾客抵触。",
                "命题手法：little to do with… everything to do with… 的强对比，末句 not… but… 收束。",
                "易错点：把「顾客不愿买」当成主因，原文明确否定。",
            ],
            "falseFriends": [
                ("edible", "可食用的", "（虽不好看但）能吃", "all are edible：都能吃"),
                ("aisle", "过道", "货架通道", "a separate aisle：单独一个货架区"),
                ("discard", "丢弃", "下架处理", "discard food：把食物处理掉"),
            ],
            "synonyms": [
                ("throw away", "discard"),
                ("appearance", "looks / cosmetic standards"),
                ("resistance", "refusal / opposition"),
            ],
        },
        "e2-p6": {
            "takeaway": [
                "主旨：无现金支付有效率优势，却排斥部分人群；好系统的标准是「多少人能用」。",
                "命题手法：收益—代价并列（save time / exclude），末句给评判标准。",
                "易错点：把「技术进步」当成「所有人都受益」。",
            ],
            "falseFriends": [
                ("keypad", "键盘", "（密码）按键区", "large-print keypads：大字按键"),
                ("nostalgia", "怀旧", "守旧、留恋过去", "progress versus nostalgia：进步与守旧之争"),
                ("exclude", "排除", "把……挡在服务之外", "exclude older customers：让老年顾客用不了"),
            ],
            "synonyms": [
                ("cashless", "digital payment"),
                ("only as good as", "depends on"),
                ("exclude", "leave out"),
            ],
        },
        "e2-p7": {
            "takeaway": [
                "主旨：企业健康项目效果有限，真正影响健康的是工时、掌控感与期望清晰度。",
                "命题手法：现象（gym discounts）→ 数据（participation highest among healthy）→ 归因（work organisation）。",
                "易错点：把「参与率高」当成「项目有效」，原文说参与者本就健康。",
            ],
            "falseFriends": [
                ("wellness", "健康", "员工健康项目", "wellness programmes：健身折扣、计步 App 这类项目"),
                ("offset", "抵消", "弥补", "no step counter can offset：计步器弥补不了"),
                ("shift", "转变", "轮班", "notice of shifts：提前告知班次"),
            ],
            "synonyms": [
                ("stress", "pressure / strain"),
                ("scheduling", "timing of work"),
                ("redirect", "move / reallocate"),
            ],
        },
        "e2-p8": {
            "takeaway": [
                "主旨：旅游的收益被看见、成本被隐藏；收费与限流是为了保住「宜居」这一前提。",
                "命题手法：短句转折（hides a cost）+ 例证（门票、限流）+ 格言式结论。",
                "易错点：把「收费」理解成「不欢迎游客」，原文说是保护旅游的基础。",
            ],
            "falseFriends": [
                ("export", "出口（货物）", "出口型产业", "an export industry：把旅游当作向外销售的服务"),
                ("liveable", "可居住的", "宜居的", "pleasant to live in：居民住得舒服"),
                ("hide", "躲藏", "掩盖", "hides a cost：把成本遮住了"),
            ],
            "synonyms": [
                ("cost", "burden"),
                ("residents moving away", "local population leaving"),
                ("limit", "cap"),
            ],
        },
    },
}
