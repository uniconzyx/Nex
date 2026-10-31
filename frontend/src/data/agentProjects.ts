/**
 * agentProjects.ts —— 就业「项目」轻量入口的内容数据（离线可用）
 * ============================================================================
 * 聚焦「全栈开发 agent 开发」：每个卡片都是一名全栈工程师能独立落地的 Agent 项目，
 * 既能写前端对话界面、也能写后端编排与工具调用，是求职项目经历的高含金量素材。
 * 卡片的「去实战」按钮跳转到完整 BOSS 项目实战库（onNavigate('projects')）。
 *
 * 每张卡片支持展开详情：目标 / 技术选型 / 验收标准；并带 audience 标签供校招/社招筛选。
 * ============================================================================
 */

export type AgentLevel = '入门' | '进阶' | '挑战';
export type AgentAudience = '校招' | '社招' | '通用';

export interface AgentProject {
  id: string;
  title: string;
  /** 一句话：做完你会交付出什么 */
  tagline: string;
  level: AgentLevel;
  /** 面向人群：校招 / 社招 / 通用 */
  audience: AgentAudience;
  /** 技术栈标签 */
  stack: string[];
  /** 最终产出物（可写进简历） */
  outcome: string;
  /** 为什么值得做（一句话，戳中求职价值） */
  why: string;
  /** 项目目标：解决什么痛点、达成什么效果 */
  target: string;
  /** 技术选型要点：为什么这么选 */
  techDetail: string;
  /** 验收标准：做到哪几条算「能写进简历」 */
  acceptance: string[];
}

export const AGENT_PROJECTS: AgentProject[] = [
  {
    id: 'kb-agent',
    title: '个人知识库问答 Agent',
    tagline: '接自己的笔记 / 文档，做一个能「问一句、精准答」的 RAG 助手。',
    level: '入门',
    audience: '校招',
    stack: ['React', 'FastAPI', 'pgvector', 'OpenAI / 本地 LLM'],
    outcome: '一个可部署的检索增强问答站，支持文档上传、向量化、流式回答。',
    why: '覆盖「前端对话 UI + 后端检索 + 向量库」全链路，是 Agent 入门最稳的简历项目。',
    target: '把散落的笔记变成「随问随答」的知识助手：用户上传文档后，能基于文档内容做带引用的精准回答，而不是泛泛而谈。',
    techDetail: '前端用 React 做流式对话；后端 FastAPI 暴露上传/问答接口；pgvector 存 embedding 并做相似度检索；模型可用云端 API 或本地 Ollama，降低上线成本。',
    acceptance: [
      '文档上传后能被切片、向量化并入库',
      '回答严格基于检索片段，并标注引用来源',
      '前端支持流式输出与多轮上下文',
      '本地 docker-compose 一键起服务',
    ],
  },
  {
    id: 'pr-reviewer',
    title: 'GitHub PR 自动评审 Agent',
    tagline: '监听 PR Webhook，自动 diff 审查并回写评论与建议。',
    level: '进阶',
    audience: '社招',
    stack: ['Next.js', 'GitHub App', 'LLM 工具调用', 'Webhook'],
    outcome: '一个能接入真实仓库、在 PR 下自动评论的评审机器人。',
    why: '展示「事件驱动 + 工具调用 + 平台集成」的工程能力，后端岗极加分。',
    target: '在开发者提 PR 后自动跑评审：读懂 diff、定位风险点、给出可执行的修改建议，并把结论回写到 PR 评论区，减少人工 review 负担。',
    techDetail: '用 GitHub App + Webhook 接收事件；Next.js Route Handler 做回调入口；Agent 调用 diff 解析与代码检索工具，最后用 GitHub API 回写评论。注意鉴权与幂等，避免重复评论。',
    acceptance: [
      '开 PR 后自动触发评审并回写评论',
      '能区分「建议」与「必须修改」两类级别',
      '同一 PR 重复推送不重复刷屏（幂等）',
      '支持白名单仓库与跳过标签',
    ],
  },
  {
    id: 'ops-healer',
    title: '智能运维自愈 Agent',
    tagline: '拉监控告警 → 自动诊断根因 → 执行受限自愈脚本。',
    level: '挑战',
    audience: '社招',
    stack: ['Node 后端', 'Prometheus', 'Agent 编排', '沙箱执行'],
    outcome: '一个告警分流 + 诊断建议 + 安全自愈的运维助手（带人工确认闸）。',
    why: '把「可观测性 + 编排 + 安全边界」打包，是高并发 / 平台岗的硬通货。',
    target: '把值班同学从「看到告警→翻仪表盘→手工重启」的循环中解放：Agent 收到告警后自动拉指标、定位根因、给出修复方案，危险操作先交人工确认再执行。',
    techDetail: 'Node 后端对接 Prometheus 拉指标与告警；Agent 用「诊断工具集」做根因推理；自愈动作放进受限沙箱，破坏性操作必须经人工确认闸。重点在可观测接入与安全边界。',
    acceptance: [
      '告警进来后能自动拉取相关指标并归因',
      '给出可解释的处置建议（非黑盒）',
      '危险操作默认拦截，需人工确认才执行',
      '执行结果回写工单并有完整审计日志',
    ],
  },
  {
    id: 'support-agent',
    title: '多轮客服 + 工单 Agent',
    tagline: '用状态机管多轮会话，并把意图打通到工单系统。',
    level: '进阶',
    audience: '通用',
    stack: ['全栈 TS', '状态机', 'RAG 知识库', 'REST 集成'],
    outcome: '一个能多轮追问、自动建单、回写处理结果的客服工作台。',
    why: '证明你能把「对话状态 + 业务系统」连起来，而非只会调一次接口。',
    target: '让客服从「重复问答」升级为「能办事」：多轮澄清用户意图后，自动查知识库、建工单、并跟踪处理结果回执，减少人工转接。',
    techDetail: '用状态机管理会话阶段（问候→澄清→查询→建单→回访）；RAG 接产品知识库；工单系统走 REST。关键在于状态不丢、能打断、能回退。',
    acceptance: [
      '多轮对话能正确维护上下文与阶段',
      '命中知识库无果时自动建工单',
      '工单状态变化能回写并主动通知用户',
      '异常输入（脏话/跑题）有兜底话术',
    ],
  },
  {
    id: 'flow-studio',
    title: 'Agent 工作流编排台',
    tagline: '可视化拖拽节点，串起 LLM / Tool / Condition 成一条 DAG。',
    level: '挑战',
    audience: '通用',
    stack: ['React Flow', '后端 DAG 引擎', 'TypeScript', '队列'],
    outcome: '一个可保存 / 调试 / 运行 Agent 流程的可视化编辑器。',
    why: '同时秀出「复杂前端交互 + 后端任务编排」，全栈辨识度极高。',
    target: '把「写 Agent 流程」从改代码变成「拖节点」：用户在画布上连出 LLM/工具/分支，后端把图编译成 DAG 并调度执行，支持断点调试与运行回放。',
    techDetail: '前端 React Flow 做画布与连线校验；后端把图转成 DAG，用队列逐节点执行并收集中间结果；节点失败可重试。难点在前端协同编辑与后端并发调度。',
    acceptance: [
      '画布能拖拽、连线并校验成合法 DAG',
      '后端能按拓扑序执行并收集每节点输出',
      '支持节点失败重试与断点续跑',
      '流程可保存/加载，多人编辑不互相覆盖',
    ],
  },
  {
    id: 'code-completer',
    title: '代码补全 + 单测生成 Agent',
    tagline: '编辑器内联触发，生成实现并跑通单元测试。',
    level: '进阶',
    audience: '校招',
    stack: ['Monaco Editor', '后端执行沙箱', 'LLM', 'CI 钩子'],
    outcome: '一个内联补全 + 自动补单测、并在沙箱里验证通过率的小工具。',
    why: '贴近「AI 提效工具」赛道，能讲清「生成 → 验证」闭环最打动面试官。',
    target: '让写代码自带「质检」：在编辑器里触发后，Agent 先生成实现，再补一组单元测试，并在沙箱里真实跑一遍，只交付通过的那版。',
    techDetail: 'Monaco Editor 做内联触发与 diff 展示；后端起隔离执行沙箱跑测试；LLM 负责生成实现与用例。核心是「生成即验证」，用通过率回退差的解。',
    acceptance: [
      '编辑器内可触发补全并展示 diff',
      '自动生成的单测能在沙箱真实执行',
      '只保留跑通的实现（通过率门槛可调）',
      '可接入 CI，PR 阶段自动补测并评论',
    ],
  },
];

/** 上手路径：三步从 0 到能写进简历 */
export const AGENT_PATH: { step: string; title: string; note: string }[] = [
  {
    step: '01',
    title: '吃透一条链路',
    note: '从「知识库问答」入手，跑通 前端 UI → 后端 API → 模型/向量 的全链路调用。',
  },
  {
    step: '02',
    title: '加一层工具',
    note: '给 Agent 接一个真实外部能力（GitHub、监控、工单），学会 Function Calling / 工具编排。',
  },
  {
    step: '03',
    title: '补安全与闭环',
    note: '加人工确认闸、执行沙箱与失败回滚，让项目从「能跑」变成「敢上线」。',
  },
];

/** 人群筛选标签（含「全部」） */
export const AGENT_AUDIENCES: ('全部' | AgentAudience)[] = ['全部', '校招', '社招', '通用'];
