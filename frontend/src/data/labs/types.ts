/**
 * 交互模块数据契约 · interactive.json
 * ─────────────────────────────────────────────────────────────
 * 由 `python scripts/gen_interactive.py` 生成，组件层只读这份数据。
 * 新增学科 / 章节不需要改组件 —— 填数据即可。
 *
 * 六种玩法（kind）：
 *   sandbox  连续参数推演（手工精修，如 TTL 抖动）
 *   debug    代码块拼装（手工精修，如 singleflight 补全）
 *   sequence 时序连线（拖事件卡到时间轴，按时序回放）  ← 玩法 B
 *   match    现象 ↔ 正解 配对连线                       ← 玩法 B
 *   boss     真题打靶（答对削护甲）
 *   fill     代码关键标识符挖空（拖 token 回位）
 */

export interface Scenario {
  /** 场景标签，如「工作现场」「考场视角」 */
  tag: string;
  /** 一句话情境 */
  head: string;
  /** 具体数字或追问，让场景落地 */
  body: string;
}

export interface DualScenario {
  work: Scenario;
  exam: Scenario;
}

export interface BossQuestion {
  id: string;
  stem: string;
  title: string;
  options: { key: string; text: string }[];
  /** 正确选项的字母键（数组，单/多选皆可） */
  correct: string[];
  explain: string;
}

export interface MatchPair {
  id: number;
  /** 左栏：出事的写法 / 现象 */
  left: string;
  /** 右栏：正确做法 */
  right: string;
}

export interface SequenceModule {
  kind: 'sequence';
  /** 来源小节标题，作为题目提示 */
  heading: string;
  steps: string[];
  file?: string;
  scenario?: DualScenario;
}

export interface MatchModule {
  kind: 'match';
  pairs: MatchPair[];
  tip?: string;
  scenario?: DualScenario;
}

export interface BossModule {
  kind: 'boss';
  questions: BossQuestion[];
  scenario?: DualScenario;
}

export interface FillBlank {
  id: string;
  answer: string;
  line: number;
}

export interface FillModule {
  kind: 'fill';
  lang: string;
  file?: string;
  /** 含 ‹1› ‹2› … 占位符的代码 */
  code: string;
  marker: string;
  blanks: FillBlank[];
  distractors: string[];
  tip?: string;
  scenario?: DualScenario;
}

/** 沙盒参数：一个可拖的旋钮 */
export interface SandboxParam {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  unit?: string;
  /** 离散档位的文字名（如 0=顺序表 / 1=链表），有它就不显示裸数字 */
  labels?: string[];
}

/** 沙盒指标：`expr` 里可引用参数与前面已算出的指标 key */
export interface SandboxMetric {
  key: string;
  label: string;
  expr: string;
  unit?: string;
  /** int = 取整显示；fix2 = 两位小数；默认按量级自动 */
  fmt?: 'int' | 'fix2' | 'pct';
}

export interface SandboxCheck {
  label: string;
  /** 布尔表达式，全部为真即通关 */
  expr: string;
}

export interface SandboxModule {
  kind: 'sandbox';
  title: string;
  brief: string;
  params: SandboxParam[];
  metrics: SandboxMetric[];
  checks: SandboxCheck[];
  /** 通关后给的一句话（为什么这么调） */
  insight: string;
  scenario?: DualScenario;
}

/** 拼装块：`for` 指向唯一正确的槽位，错了用它自己的 why 说清是哪类 bug */
export interface DebugBlock {
  id: string;
  text: string;
  for: string;
  why?: string;
}

export interface DebugSlot {
  id: string;
  hint: string;
}

export interface DebugModule {
  kind: 'debug';
  title: string;
  lang: string;
  file?: string;
  /** 线上症状：先说清"出什么事"，才谈怎么补 */
  symptom: string;
  /** 骨架代码，缺口处写 ‹1› ‹2› */
  code: string;
  marker: string;
  slots: DebugSlot[];
  blocks: DebugBlock[];
  /** 补全后应当看到的输出 */
  expect: string;
  pass: string;
  scenario?: DualScenario;
}

export type LabModule =
  | SequenceModule
  | MatchModule
  | BossModule
  | FillModule
  | SandboxModule
  | DebugModule;

export interface LabData {
  chapter: string;
  subject: string;
  title: string;
  /** 素材指纹：素材变了这个值才变，用来判断是否需要重跑生成器 */
  fingerprint: string;
  /** 双场景文案（工作现场 / 考场视角），章节级共享一份 */
  scenario?: DualScenario;
  modules: LabModule[];
}
