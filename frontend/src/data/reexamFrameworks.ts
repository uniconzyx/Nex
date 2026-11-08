/**
 * reexamFrameworks.ts —— 复试面试「框架问答」+「英文口语面试框架」
 * ============================================================================
 * 手写维护层（不进 gen_tracks.py 生成链）：data/reexam.ts 是生成产物勿手改，
 * 这里独立成文件，按 category 名与 REEXAM.interview.categories 对齐。
 *
 * 两块内容：
 *   1. ANSWER_FRAMEWORKS：每类面试问题一个答题框架（结构步骤 + 示范回答 + 避坑），
 *      键与 ReexamInterviewCategory.category 一致；「英语口语」类由 ENGLISH_FRAMEWORK 接管。
 *   2. ENGLISH_FRAMEWORK：英文口语专项——自我介绍四段模板（en/zh 对照）、
 *      高频问答句式库、卡壳救场句、训练提示。
 * ============================================================================
 */

export interface FrameworkStep {
  /** 步骤名：越短越好，方便考场回忆 */
  name: string;
  /** 这一步说什么、怎么说 */
  detail: string;
}

export interface AnswerFramework {
  /** 与 ReexamInterviewCategory.category 对齐 */
  category: string;
  /** 框架名，如「定位 → 痛点 → 准备 → 契合」 */
  name: string;
  /** 一句话说明这个框架解决什么 */
  applies: string;
  steps: FrameworkStep[];
  /** 填好的示范回答（中文） */
  example: string;
  pitfalls: string[];
}

export interface EnglishLine {
  en: string;
  zh: string;
}

export interface EnglishIntroPara {
  label: string;
  /** 这一段的写作要点（中文） */
  point: string;
  line: EnglishLine;
}

export interface EnglishPattern {
  /** 题型场景，如「Why 动机类」 */
  scene: string;
  en: string;
  zh: string;
}

export interface EnglishFramework {
  title: string;
  desc: string;
  /** 自我介绍四段模板 */
  intro: EnglishIntroPara[];
  /** 高频问答句式库 */
  patterns: EnglishPattern[];
  /** 卡壳救场句 */
  rescue: EnglishLine[];
  /** 训练提示 */
  tips: string[];
}

/* ── 一、各类面试问题的答题框架（中文五类；英语口语走专项） ────────── */

export const ANSWER_FRAMEWORKS: AnswerFramework[] = [
  {
    category: '研究计划',
    name: '定位 → 痛点 → 准备 → 契合（四步）',
    applies: '适用于「想研究什么 / 为什么选它 / 和导师方向怎么契合」这一组问题。',
    steps: [
      {
        name: '① 定位',
        detail: '一句话说出方向，具体到「技术 × 场景」（如「图神经网络解决推荐冷启动」）。忌「我对 AI 感兴趣」——导师听到这句就知道你没想过。',
      },
      {
        name: '② 痛点',
        detail: '说清这个问题现在为什么没被解决好：现有方法哪一步贵、不准或不可扩展。有痛点，动机才成立。',
      },
      {
        name: '③ 准备',
        detail: '你已有什么：精读过的论文、跑通过的代码/数据集、相关课程。用事实背书动机，不靠热情宣言。',
      },
      {
        name: '④ 契合 + 里程碑',
        detail: '锚到导师近 3 年的工作线（点过他哪篇论文），再给一个可判定的小目标，如「第一学期复现组里 XX 论文并汇报」。',
      },
    ],
    example:
      '我想做图神经网络在推荐系统冷启动上的应用（定位）。现有方法对新用户几乎拿不到交互信号，主流做法靠内容特征硬凑，精度掉得厉害（痛点）。我精读过 GraphSAGE 和 LightGCN，并用 MovieLens 复现过 LightGCN（准备）。读过您组 2024 年那篇 XX，我的计划是第一学期先复现它，再尝试把内容特征引入消息传递（契合 + 里程碑）。',
    pitfalls: [
      '空泛兴趣宣言（「我对 AI 很感兴趣」= 没准备）',
      '「听老师安排」——导师要的是你有判断，不是没判断',
      '没读过导师论文硬套契合，一问就穿',
    ],
  },
  {
    category: '项目陈述',
    name: 'STAR-R 五步（背景-任务-行动-结果-反思）',
    applies: '适用于「讲一个项目 / 最大难点 / 怎么攻克」这一组问题；故障题在 STAR 后追加六环。',
    steps: [
      { name: '① 背景 S', detail: '一句话交代项目规模：并发量、数据量、团队人数。让导师快速校准难度。' },
      { name: '② 任务 T', detail: '你个人负责哪一块，边界说清楚——「我们」糊掉个人贡献是面试大忌。' },
      { name: '③ 行动 A', detail: '讲决策点：「为什么选 A 不选 B」，展示权衡；不要罗列技术栈名词。' },
      { name: '④ 结果 R', detail: '量化：QPS 提升 X%、P99 降 Y ms、错误率降 Z%。没有数字的结果不算结果。' },
      { name: '⑤ 反思 R', detail: '重做会改什么——先说不改什么（知道边界），再说一处最有杠杆的改动。' },
      {
        name: '故障题追加：六环',
        detail: '现象 → 假设 → 验证 → 根因 → 修复 → 防复发（加了什么监控/单测让同类问题不再发生）。',
      },
    ],
    example:
      '项目是一个课设级别的短链服务，峰值 500 QPS（背景）。我负责缓存与存储层（任务）。当时在「本地缓存 + Redis 两级」和「只上 Redis」之间选了前者，因为热点 key 占 20% 却贡献 80% 读量（行动）。上线后 P99 从 85ms 降到 22ms（结果）。重做我会保留两级结构，但给本地缓存加容量上限与淘汰率监控——当时它差点吃满容器内存（反思）。',
    pitfalls: [
      '流水账式讲过程，没有决策点',
      '「我们我们」——导师只想知道你做了什么',
      '编一个讲不深的坑，被追问两层就露底',
    ],
  },
  {
    category: '专业素养',
    name: '观点 → 边界 → 例子（三段式）',
    applies: '适用于「你怎么看 X / 最重要的特质 / 失败经历」这类发散、批判性问题。',
    steps: [
      { name: '① 先给结论', detail: '一句话亮观点，不和稀泥。「两边都有道理」等于没有观点。' },
      { name: '② 讲边界', detail: '这个观点在哪里成立、哪里不成立——边界感是技术判断力的最直接证据。' },
      { name: '③ 落例子', detail: '用你亲历的一个小例子收尾，观点就有了证据；没有例子的观点是背来的。' },
    ],
    example:
      '我认为大模型消失的是「调包式实现」，不是问题建模能力（结论）。因为门槛上移了：数据质量、评测体系、延迟成本这些约束反而更重要——模型能写出来，但评测指标设计错，结果全错（边界）。我给一个学习项目配评测时就踩过：盲目用准确率，类别不平衡下高准确率其实毫无意义，后来改成按类别看 F1 才发现模型漏掉整个少数类（例子）。',
    pitfalls: [
      '两边讨好、没有结论',
      '只背新闻热词（AGI、颠覆），没有技术细节',
      '观点是观点、例子是例子，两者对不上',
    ],
  },
  {
    category: '选导与联系导师',
    name: '邮件五要素 + 沟通三原则',
    applies: '适用于「联系导师的邮件怎么写 / 名额满了怎么办」这一组实操问题。',
    steps: [
      { name: '① 标题', detail: '「姓名-本科学校-报考方向-初试分数」。导师平均 30 秒扫一封邮件，标题先给全部关键信息。' },
      { name: '② 我是谁 + 分数', detail: '正文两行内说清身份与初试成绩，不铺垫不抒情。' },
      { name: '③ 读过哪篇', detail: '点名导师某篇论文 + 一句具体评价（方法或局限）。这是与群发邮件拉开差距的关键一行。' },
      { name: '④ 我能做什么', detail: '工程/数据/代码能力与组里需求的匹配点，一到两条即可。' },
      { name: '⑤ 附件 + 不施压', detail: '附简历与成绩单；不问「能不能收我」这种只能被拒的问题，结尾留自然接口（「期待有机会进一步交流」）。' },
    ],
    example:
      '标题：张三-XX大学-计算机-初试 385。正文：老师好，我是 XX 大学计算机 2022 级张三，初试 385 分。拜读过您 2024 年关于 XX 的论文，其中用 XX 解决 XX 的思路对我启发很大。我本科做过 XX（GitHub 链接），熟悉 C++ 与系统编程。简历与成绩单见附件，期待有机会向您进一步请教。',
    pitfalls: [
      '群发痕迹（称呼与内容对不上）',
      '长篇抒情、简历附件缺失',
      '同时联系同组多位老师又不说明，被导师间一聊就尴尬',
    ],
  },
  {
    category: '科研潜质与读博',
    name: '判断依据 + 具体问题域',
    applies: '适用于「读研和本科的区别 / 有没有读博打算」这类考察长期投入的问题。',
    steps: [
      { name: '① 给判断依据', detail: '不说「读/不读」的裸结论，说依据：什么信号会让你想读博（对某类问题的持续兴趣、能否忍受长期无反馈）。' },
      { name: '② 说得出问题域', detail: '若说想读，必须能说出一个具体问题域 + 为什么现在没被解决；讲不出就是假话。' },
      { name: '③ 诚实', detail: '不想读就给理由（更想做工程落地），不要为加分假装想读博——入学后转硕博会很尴尬。' },
    ],
    example:
      '本科是「把已知问题解对」，研究生是「把未知问题定义清楚」——这是我理解的最大的区别（区别）。目前没有定论，但判断依据是：如果一年后我仍然对 XX 这类问题保持持续投入、并且能忍受几个月没有正反馈，我会考虑读博；目前我更倾向先在工程里验证这些方法能不能落地（依据 + 诚实）。',
    pitfalls: [
      '为加分假装想读博，入学后转硕博很尴尬',
      '说想读却讲不出具体问题域',
      '把读研说成「缓冲就业」，导师听到会扣分',
    ],
  },
  {
    category: '英语口语',
    name: '（由英文口语专项框架接管）',
    applies: '见下方「英文口语面试框架」：自我介绍四段模板 + 句式库 + 救场句。',
    steps: [],
    example: '',
    pitfalls: [],
  },
];

/* ── 二、英文口语面试框架（专项） ─────────────────────────────────── */

export const ENGLISH_FRAMEWORK: EnglishFramework = {
  title: '英文口语面试框架',
  desc: '自我介绍四段模板 + 高频问答句式库 + 卡壳救场句。原则：句子短（15 词以内）、错误少，比华丽长句得分；每天出声朗读 15 分钟，用提纲不逐字背。',
  intro: [
    {
      label: '① Opening · 开场身份',
      point: '一句话：身份 + 学校 + 专业。不背长开场白，稳住语速就是赢。',
      line: {
        en: 'Good morning, professors. It is a great honor to be here. My name is Li Ming, from XX University, majoring in Computer Science.',
        zh: '各位老师好，很荣幸参加面试。我叫李明，来自 XX 大学计算机专业。',
      },
    },
    {
      label: '② Academic · 学业亮点',
      point: '挑两项最有把握的（GPA/排名/核心课），别堆数字。',
      line: {
        en: 'During my undergraduate years, I kept a GPA of 3.8 out of 4.0, ranking in the top five percent, and built a solid foundation in data structures and operating systems.',
        zh: '本科期间我的 GPA 3.8/4.0，排名前 5%，在数据结构与操作系统上打下了扎实基础。',
      },
    },
    {
      label: '③ Project · 项目亮点',
      point: '只讲一个项目：角色 + 一个量化结果。专有名词读音提前练准。',
      line: {
        en: 'The project I am most proud of is a short-URL service. I was responsible for the caching layer, and reduced the p99 latency from 85 to 22 milliseconds.',
        zh: '我最自豪的项目是一个短链服务。我负责缓存层，把 P99 延迟从 85 毫秒降到 22 毫秒。',
      },
    },
    {
      label: '④ Motivation · 读研动机',
      point: 'research-oriented：锚到导师方向，收尾致谢。忌「好就业」。',
      line: {
        en: "I am applying for this program because I want to dig deeper into recommender systems. I have read Professor Wang's recent paper on graph neural networks, and I would love to continue this line of research here. Thank you.",
        zh: '我报考是因为想在推荐系统方向深入下去。读过王老师关于图神经网络的近期论文，希望能在这里继续这条研究线。谢谢。',
      },
    },
  ],
  patterns: [
    {
      scene: 'Why 动机类（为什么读研 / 选我们学校 / 选这个方向）',
      en: 'The main reason is that... What attracts me most is...',
      zh: '句式：主要原因是……最吸引我的是……。答「资源匹配」：具体到某实验室/某门课/某位老师，再补一句你能带来什么。',
    },
    {
      scene: '描述类（家乡 / 最喜欢的课 / 你的项目）',
      en: 'There are three things worth mentioning. First... Second... Finally...',
      zh: '三段式万能结构，任何描述题都能套；每段一句话，说到第三点自然收尾。',
    },
    {
      scene: '观点类（专业话题：怎么看大模型 / 某技术趋势）',
      en: 'In my view, ... Although I also recognize that...',
      zh: '先观点后让步，显批判性；观点 + 边界 + 一个小例子，与中文专业素养框架同构。',
    },
    {
      scene: '毕业设计 / 论文摘要（一分钟版）',
      en: 'The goal of my thesis is to... I implemented... We achieved... by...',
      zh: '一分钟结构 What → How → Result：目标一句、实现一句、结果带数字一句。',
    },
    {
      scene: '收尾句（任何回答的最后一句）',
      en: 'That is why I believe this direction suits me.',
      zh: '把话题拉回「我适合」，给回答一个落点，避免戛然而止。',
    },
  ],
  rescue: [
    { en: "That's a good question. Let me think for a second.", zh: '争取 3 秒思考时间，比沉默或「嗯…啊…」好得多。' },
    { en: 'If I understand correctly, you are asking about...', zh: '复述确认问题，同时给自己组织语言的时间；确认错了老师还会纠正你。' },
    { en: 'I may not have the exact term in English, but the idea is...', zh: '词穷兜底：意思先行，术语丢了不扣大分，卡壳才扣分。' },
    { en: 'Sorry, could you please say that again?', zh: '真没听清就礼貌重问，别硬猜问题答非所问。' },
  ],
  tips: [
    '语速稳 > 词藻华丽；每句 15 词以内，错误少比长句更得分',
    '专有名词读音提前练准：自己项目名、论文术语、导师学校名',
    '准备 5 个万能话题（家乡/课程/项目/榜样/爱好），现场灵活组合',
    '每天出声朗读 15 分钟；用提纲练不逐字背，逐字背一紧张就断片',
  ],
};
