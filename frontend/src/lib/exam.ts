/**
 * exam.ts —— 考研题库访问层
 *
 * 全部接口对齐 docs/API-Exam.md（v1 契约）。底层用 api.ts 的 apiGet / apiPost，
 * 自动走 localStorage["nex.apiBaseUrl"]（默认 http://127.0.0.1:8000）。
 *
 * 关键约束（来自契约）：
 *   - 题目列表不下发答案，答案/解析/四层讲解只在详情接口；
 *   - GET 天然幂等；grade 无状态（不写库），可安全重试；
 *   - 题型 type 取值随题库变化，不在此写死，渲染时给兜底文案；
 *   - 套卷 subject=null 表示整卷，scope="full"，会同时出现在各科目下。
 */

import { apiGet, apiPost } from './api';

const P = '/api/v1';

// ───────────────────────────── 目录 ─────────────────────────────

export interface Catalog {
  content_version: number;
  items: ExamSummary[];
}

export interface ExamSummary {
  key: string;
  label: string;
  short: string;
  duration: number | null;
  total_score: number | null;
  subjects: SubjectSummary[];
  counts: { questions: number; topics: number; summaries: number; papers: number };
}

export interface SubjectSummary {
  key: string;
  label: string;
  score: number;
  counts: {
    questions: number;
    topics: number;
    patterns: number;
    knowledge: number;
    summaries: number;
    papers: number;
  };
}

// ─────────────────────────── 解题框架 ───────────────────────────

export interface FrameworkDoc {
  exam: string;
  subject: string;
  label: string;
  score: number | null;
  pattern: string | null;
  intro: string | null;
  topics: FrameworkTopic[];
  totals: { topics: number; patterns: number };
}

export interface FrameworkTopic {
  id: string;
  title: string;
  order: number | null;
  heat: number | null;
  seen_in: number[];
  points: string[];
  patterns: Pattern[];
  question_count: number;
}

export interface Pattern {
  id: string;
  title: string;
  freq: string | null;
  ask: string | null;
  steps: string[];
  traps: string[];
}

// ─────────────────────────── 知识点 ─────────────────────────────

export interface KnowledgeDoc {
  exam: string;
  subject: string;
  book: string | null;
  items: KnowledgeBlock[];
  total: number;
}

export interface KnowledgeBlock {
  topic: string;
  topic_title: string;
  chapter: string | null;
  knowledge: KnowledgePoint[];
}

export interface KnowledgePoint {
  id: string;
  title: string;
  chapter: string | null;
  patterns: string[];
  core: string;
  tip: string | null;
}

// ─────────────────────────── 分类总结 ───────────────────────────

export interface SummaryDoc {
  exam: string;
  subject: string;
  groups: SummaryGroup[];
  total: number;
}

export interface SummaryGroup {
  topic: string;
  title: string;
  recognize: string;
  framework: string[];
  skills: { title: string; body: string }[];
  traps: string[];
  question_ids: string[];
  suggested_order: string[];
}

// ───────────────────────────── 题目 ─────────────────────────────

export interface QuestionCard {
  order: number;
  id: string;
  topic: string;
  topic_title: string;
  type: string;
  difficulty: number | null;
  stem: string;
  option_count: number;
  has_passage: boolean;
  knowledge_ids: string[];
}

export interface QuestionList {
  items: QuestionCard[];
  total: number;
  page: number;
  size: number;
}

export interface Walkthrough {
  framework: { title: string; pattern: string; steps: string[]; trap: string };
  approach: string;
  points: { id: string; title: string; core: string; note?: string; pitfall?: string }[];
  solution: string;
}

export interface QuestionDetail {
  id: string;
  exam: string;
  subject: string;
  topic: string;
  topic_title: string;
  type: string;
  difficulty: number | null;
  stem: string;
  options: string[];
  passage: string | null;
  ask: string[];
  answer: { correct?: number | number[]; text?: string };
  explain: { right?: string; wrong?: string; link?: string };
  walkthrough: Walkthrough;
}

// ───────────────────────────── 套卷 ─────────────────────────────

export interface PaperCard {
  id: string;
  exam: string;
  subject: string | null;
  scope: 'subject' | 'full';
  title: string;
  kind: string;
  duration: number | null;
  total_score: number | null;
  section_count: number;
  question_count: number;
  subjects: string[];
}

export interface PaperList {
  items: PaperCard[];
  total: number;
  page: number;
  size: number;
}

export interface PaperDetail extends PaperCard {
  disclaimer: string;
  blueprint: { subject: string; name: string; score: number }[];
  sections: PaperSection[];
  counts: { sections: number; questions: number };
}

export interface PaperSection {
  no: number;
  name: string;
  type: string;
  range: string | null;
  score: number;
  per_score: number | null;
  note: string | null;
  items: PaperItem[];
}

export interface PaperItem {
  id: string;
  order: number;
  type: string;
  topic: string | null;
  topic_title: string | null;
  difficulty: number | null;
  stem: string;
  options: string[];
  ask: string[];
  answer: { correct?: number | number[]; text?: string } | null;
  explain: object | null;
  walkthrough: Walkthrough | null;
  score: number | null;
  in_bank: boolean;
}

// ───────────────────────────── 精读 ─────────────────────────────

export interface ReadingIndex {
  exam: string;
  subject: string;
  items: {
    id: string;
    title: string;
    word_count: number;
    paragraph_count: number;
    vocab_count: number;
    sentence_count: number;
    question_ids: string[];
  }[];
  total: number;
}

export interface Passage {
  id: string;
  exam: string;
  subject: string;
  title: string;
  text: string;
  word_count: number;
  paragraphs: { no: number; zh: string }[];
  vocab: { word: string; pos: string; cn: string; note: string }[];
  sentences: { en: string; main: string; mods: string; zh: string; point: string }[];
  question_map: { qid: string; type: string; locate: string }[];
  takeaway: string[];
  false_friends: { word: string; usual: string; here: string; note: string }[];
  synonyms: { from: string; to: string }[];
}

// ───────────────────────────── 判分 ─────────────────────────────

export interface GradeAnswer {
  question_id: string;
  choice?: number;
  choices?: number[];
  text?: string;
}

export interface GradeRequest {
  answers: GradeAnswer[];
}

export type Verdict = 'CORRECT' | 'INCORRECT' | 'UNGRADED';

export interface GradeItem {
  question_id: string;
  type: string;
  verdict: Verdict;
  your_answer: number | number[] | string | null;
  expected: object;
  explain: object;
  walkthrough: Walkthrough;
}

export interface GradeResult {
  exam: string;
  subject: string;
  items: GradeItem[];
  summary: {
    total: number;
    correct: number;
    incorrect: number;
    ungraded: number;
    accuracy: number | null;
  };
}

// ─────────────────────────── 封装函数 ───────────────────────────

export function getCatalog(): Promise<Catalog> {
  return apiGet<Catalog>(`${P}/exams`);
}

export function getExam(exam: string): Promise<ExamSummary> {
  return apiGet<ExamSummary>(`${P}/exams/${encodeURIComponent(exam)}`);
}

export function getFrameworks(exam: string, subject: string): Promise<FrameworkDoc> {
  return apiGet<FrameworkDoc>(`${P}/exams/${exam}/subjects/${subject}/frameworks`);
}

export function getKnowledge(exam: string, subject: string): Promise<KnowledgeDoc> {
  return apiGet<KnowledgeDoc>(`${P}/exams/${exam}/subjects/${subject}/knowledge`);
}

export function getSummaries(exam: string, subject: string): Promise<SummaryDoc> {
  return apiGet<SummaryDoc>(`${P}/exams/${exam}/subjects/${subject}/summaries`);
}

export interface QuestionQuery {
  topic?: string;
  type?: string;
  difficulty?: number;
  q?: string;
  sort?: 'order' | 'difficulty';
  page?: number;
  size?: number;
}

export function getQuestions(
  exam: string,
  subject: string,
  opts: QuestionQuery = {},
): Promise<QuestionList> {
  const params = new URLSearchParams();
  if (opts.topic) params.set('topic', opts.topic);
  if (opts.type) params.set('type', opts.type);
  if (opts.difficulty != null) params.set('difficulty', String(opts.difficulty));
  if (opts.q) params.set('q', opts.q);
  if (opts.sort) params.set('sort', opts.sort);
  if (opts.page != null) params.set('page', String(opts.page));
  if (opts.size != null) params.set('size', String(opts.size));
  const qs = params.toString();
  return apiGet<QuestionList>(
    `${P}/exams/${exam}/subjects/${subject}/questions${qs ? `?${qs}` : ''}`,
  );
}

export function getQuestion(exam: string, subject: string, id: string): Promise<QuestionDetail> {
  return apiGet<QuestionDetail>(`${P}/exams/${exam}/subjects/${subject}/questions/${id}`);
}

export function getReading(exam: string, subject: string): Promise<ReadingIndex> {
  return apiGet<ReadingIndex>(`${P}/exams/${exam}/subjects/${subject}/reading`);
}

export function getPassage(exam: string, subject: string, id: string): Promise<Passage> {
  return apiGet<Passage>(`${P}/exams/${exam}/subjects/${subject}/reading/${id}`);
}

export interface PaperQuery {
  subject?: string | null;
  kind?: string;
  page?: number;
  size?: number;
}

export function getPapers(exam: string, opts: PaperQuery = {}): Promise<PaperList> {
  const params = new URLSearchParams();
  if (opts.subject) params.set('subject', opts.subject);
  if (opts.kind) params.set('kind', opts.kind);
  if (opts.page != null) params.set('page', String(opts.page));
  if (opts.size != null) params.set('size', String(opts.size));
  const qs = params.toString();
  return apiGet<PaperList>(`${P}/exams/${exam}/papers${qs ? `?${qs}` : ''}`);
}

export function getPaper(exam: string, id: string): Promise<PaperDetail> {
  return apiGet<PaperDetail>(`${P}/exams/${exam}/papers/${id}`);
}

export function grade(
  exam: string,
  subject: string,
  answers: GradeAnswer[],
): Promise<GradeResult> {
  return apiPost<GradeResult>(`${P}/exams/${exam}/subjects/${subject}/grade`, { answers });
}
