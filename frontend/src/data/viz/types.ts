/**
 * types.ts —— 概念图解的数据契约
 *
 * 生成端在 scripts/gen_concept_viz.py，消费端是 components/ConceptViz.tsx。
 * 这里刻意保持「薄」：只有渲染需要的字段，没有原文全文、没有 HTML。
 *
 * 一条铁律：exams / works / asks 都是**只读引用**，来源分别是本章的
 * exercises.json / pitfalls.md / interview.json。前端只负责展示与跳转，
 * 永远不回写——题面、答案、解析的唯一真相在那三个文件里。
 */

/** 图的形态，由小标题语义决定（见生成器的 pick_kind） */
export type VizKind = 'flow' | 'stack' | 'timeline' | 'compare';

/** 场景灯：考试真题 / 线上事故 / 面试追问 */
export type VizMode = 'exam' | 'work' | 'ask';

export interface VizCode {
  lang: string;
  code: string;
}

/** 一个「节」= concept 文件里的一个 `##` 小节，也就是图上的一个节点 */
export interface VizSec {
  /** 小节标题（生成时截到 46 字） */
  h: string;
  /** 首段正文（截到 118 字） */
  s: string;
  /** 该节第一个代码块；没有则为 null */
  c: VizCode | null;
}

export interface VizConcept {
  /** 章节 id + 文件名，例如 cpp-ch03/01-c-array-vs-pointer */
  id: string;
  file: string;
  title: string;
  kind: VizKind;
  secs: VizSec[];
}

export interface VizExamOption {
  k: string;
  t: string;
}

/** 本章的一道真题（只读，答案默认折叠） */
export interface VizExam {
  kind: string;
  q: string;
  stem: string;
  opts: VizExamOption[];
  ans: string;
  why: string;
}

/** 本章的一个工程坑（pitfalls.md 的一条） */
export interface VizWork {
  h: string;
  d: string;
}

/** 本章的一条面试追问（interview.json 的一条） */
export interface VizAsk {
  q: string;
  a: string;
  fu: string[];
  tag: string;
}

export interface VizChapter {
  id: string;
  subj: string;
  title: string;
  summary: string;
  concepts: VizConcept[];
  exams: VizExam[];
  works: VizWork[];
  asks: VizAsk[];
}
