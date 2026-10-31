/* 就业 · 简历打磨 区块的纯数据层（由 EmploymentPage 渲染）
 * 内容面向计算机/技术岗求职者，离线可用，不依赖后端。
 * 结构：自检清单 + STAR 框架 + 分模块写法 + 常见雷区 + 模板/ATS。
 */
export interface ResumeCheckItem {
  id: string;
  text: string;
  why?: string;
}

export interface ResumeModule {
  id: string;
  title: string;
  summary: string;
  good: string[];
  bad: string[];
  example?: string;
}

export interface ResumePitfall {
  id: string;
  title: string;
  fix: string;
}

export interface ResumeTemplate {
  id: string;
  title: string;
  points: string[];
}

export const RESUME_LEDIT = '从「写了什么」到「能过筛」：自检清单 + 分模块写法 + 雷区，按 STAR 把经历讲成结果。';

export const RESUME_CHECKLIST: ResumeCheckItem[] = [
  { id: 'one-page', text: '校招一页纸 / 社招（5 年+）两页内', why: 'HR 平均 6–10 秒扫一份简历，越长被读到越靠后。' },
  { id: 'contact', text: '至少一个可达联系方式（手机 / 邮箱 / GitHub）', why: '联系不上 = 石沉大海，GitHub 比「熟悉 Git」更有说服力。' },
  { id: 'file', text: '文件名规范：姓名_岗位_电话.pdf', why: 'HR 收几十份「简历.pdf」，你的会被埋。' },
  { id: 'pdf', text: '导出为 PDF，不用 Word 直发', why: 'Word 在不同机器上排版会乱，PDF 锁定版式。' },
  { id: 'skill-tier', text: '技能分级（熟练 / 了解），不写「精通全部」', why: '「精通 C++/Java/Python/Go」一眼假，面试会被按最高档拷打。' },
  { id: 'jd-align', text: '技术栈对齐目标岗位 JD', why: 'ATS 与用人部门都靠关键词匹配，照抄 JD 术语能过初筛。' },
  { id: 'verb', text: '每段经历动词开头（设计 / 实现 / 优化 / 主导）', why: '名词开头像岗位职责，动词开头像你做过的事。' },
  { id: 'quantify', text: '有量化结果（性能 / 规模 / 收益）', why: '「提升性能」是空话，「800ms→120ms」才是结果。' },
  { id: 'role', text: '项目写清你的角色与个人贡献边界', why: '「我们」看不出你干了啥，面试官专问「你具体做了哪块」。' },
  { id: 'no-fluff', text: '无错别字、无中英文标点混用', why: '细节翻车 = 态度翻车，这是成本最低的扣分项。' },
  { id: 'no-private', text: '不写照片 / 年龄 / 婚育等冗余信息', why: '与岗位无关的信息既占空间又招歧视风险。' },
  { id: 'tailor', text: '每投一家公司微调一次', why: '一稿多投命中率低，按 JD 调前三条能明显提筛。' },
];

export const RESUME_STAR = {
  intro: 'STAR 把「我做了 X」变成「我为 Y 带来了 Z」——面试官买的不是动作，是结果。',
  cells: [
    { k: 'S', name: '情境 Situation', d: '背景与约束：什么业务、什么规模、什么痛点。' },
    { k: 'T', name: '任务 Task', d: '你要解决的具体问题，最好带指标。' },
    { k: 'A', name: '行动 Action', d: '你做了什么、怎么做的、技术选型与难点。' },
    { k: 'R', name: '结果 Result', d: '可量化的收益：性能、成本、规模、用户。' },
  ],
  before: '负责后端开发，参与了订单系统的优化。',
  after: '主导订单服务重构（S/T），用缓存 + 异步削峰替换同步链路（A），平均响应 800ms→120ms、错误率降 60%（R），支撑双十一 3 倍峰值无降级。',
};

export const RESUME_MODULES: ResumeModule[] = [
  {
    id: 'contact',
    title: '个人信息',
    summary: '只留「能联系你 + 能证明你」的信息。',
    good: ['手机、邮箱放最显眼处', 'GitHub / 技术博客 / 竞赛主页放一行', '求职意向写清岗位方向'],
    bad: ['塞照片、身高、政治面貌', '留 QQ 邮箱（显得不专业）', '写一堆与岗位无关的社交账号'],
    example: '邮箱用姓名拼音 + 数字，别用「happyboy123@xxx」。',
  },
  {
    id: 'edu',
    title: '教育背景',
    summary: '学校 / 专业 / 时间 + 一个亮点就够。',
    good: ['GPA / 专业排名（若前 30%）', '核心课程挑 3–5 门对口写', '奖学金、ACM/数学建模等硬荣誉'],
    bad: ['罗列全部课程', '把高中经历也写进来', 'GPA 不好还硬写'],
    example: 'GPA 3.8/4.0（专业前 10%）· 操作系统 / 计网 / 数据库 95+。',
  },
  {
    id: 'skill',
    title: '专业技能',
    summary: '分级 + 对齐 JD，宁缺毋滥。',
    good: ['熟练：日常能写生产代码的', '了解：读过源码 / 跑过 demo 的', '按 JD 顺序排，前几条最重要'],
    bad: ['「精通」一切', '列一堆没碰过的框架凑数', '中英文混排无统一'],
    example: '熟练 C++ / STL / 多线程；了解 Redis / Kafka。',
  },
  {
    id: 'project',
    title: '项目经历',
    summary: '简历的灵魂，按 STAR + 个人贡献写。',
    good: ['一句话说清项目解决什么问题', '你的角色 + 个人贡献边界', '技术难点 + 你怎么解的', '量化收益（性能 / 用户 / 指标）'],
    bad: ['整段「我们团队」看不出你', '只写技术名词没有上下文', '把课程大作业吹成工业级'],
    example: '个人贡献：独立设计索引层，把查询从全表扫改成 B+ 树，P99 从 2s 降到 80ms。',
  },
  {
    id: 'work',
    title: '实习 / 工作',
    summary: '量化成果优先于职责描述。',
    good: ['用「动词 + 量化结果」句式', '写清楚业务影响（营收 / 成本 / 效率）', '带团队就写带了几人、交付了啥'],
    bad: ['只抄 JD 的职责列表', '「协助」「参与」满天飞没有产出', '把公司 KPI 当个人成果'],
    example: '优化推荐召回链路，CTR +4.2%，日均曝光收益 +12 万。',
  },
  {
    id: 'award',
    title: '竞赛 / 获奖',
    summary: '名称 + 级别 + 你做了什么。',
    good: ['写清赛事级别（国赛 / 省赛 / 企业赛）', '一句话你的贡献', 'ACM、Kaggle、数学建模含金量高'],
    bad: ['只写「获奖」不写级别', '把参与奖和一等奖并列', '罗列几十个水赛'],
    example: 'ICPC 区域赛银奖（团队第 2，负责图论与搜索模块）。',
  },
];

export const RESUME_PITFALLS: ResumePitfall[] = [
  { id: 'p1', title: '把「参与」写成「主导」', fix: '面试官一追问就露馅；写真实角色，反而更经得起深挖。' },
  { id: 'p2', title: '只有职责，没有成果', fix: '每段都补一个「所以呢」：带来了什么可量化的改变。' },
  { id: 'p3', title: '技术名词堆砌无上下文', fix: '「熟练微服务」不如「用 gRPC 拆单体，部署耗时 -70%」。' },
  { id: 'p4', title: '一稿多投不调 JD', fix: '投前把 JD 高频词对齐到简历前三条，初筛命中率明显更高。' },
  { id: 'p5', title: '花哨模板 / 照片影响 ATS', fix: 'ATS 靠文本解析，分栏、图表、图片会被拆乱，用干净单栏。' },
  { id: 'p6', title: 'GitHub / 博客是空壳', fix: '放链接前确保有真实 commit 和内容，空仓库比不放更减分。' },
];

export const RESUME_TEMPLATES: ResumeTemplate[] = [
  {
    id: 't1',
    title: '一页纸原则',
    points: ['校招严格一页，社招可两页', '删掉与岗位无关的社团 / 兴趣', '行距紧凑但留白清晰，别塞满'],
  },
  {
    id: 't2',
    title: 'ATS 友好排版',
    points: ['用标准 section 标题：教育 / 项目 / 实习', '单栏、无表格 / 图片 / 分栏', '字体用常见无衬线，别用艺术字', '关键词用纯文本，别做成图片'],
  },
  {
    id: 't3',
    title: '导出与命名',
    points: ['导出 PDF，文件名「姓名_岗位_电话.pdf」', '打印预览确认无截断、无乱码', '邮件正文别只发「见附件」，写一句自荐'],
  },
];
