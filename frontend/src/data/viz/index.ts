/**
 * index.ts —— 按学科懒加载图解数据
 *
 * 为什么拆成 16 个模块：167 章全量约 1.8MB，直接 import 会进主 chunk。
 * 这里每个学科一个 `import()`，Vite 会切成独立 chunk，只在真的打开某学科
 * 章节时才下载（最大单学科 fundamentals 248KB）。
 *
 * 注意：agent / ml 的数据按方案 A 并入 `ai` 学科，这里仍按 content 目录名
 * 单独切 chunk；discrete-math 自 2026-11-08 起是 SUBJECTS 的第 14 个正式
 * 学科，学习页可直接选中，也不再是「只走 408 专轨」（离散数学本就不属 408）。
 */
import type { VizChapter } from './types';

export type * from './types';

type Loader = () => Promise<VizChapter[]>;

const LOADERS: Record<string, Loader> = {
  cpp: () => import('./cpp').then((m) => m.default),
  clang: () => import('./clang').then((m) => m.default),
  java: () => import('./java').then((m) => m.default),
  spring: () => import('./spring').then((m) => m.default),
  python: () => import('./python').then((m) => m.default),
  fullstack: () => import('./fullstack').then((m) => m.default),
  database: () => import('./database').then((m) => m.default),
  middleware: () => import('./middleware').then((m) => m.default),
  ai: () => import('./ai').then((m) => m.default),
  agent: () => import('./agent').then((m) => m.default),
  bigdata: () => import('./bigdata').then((m) => m.default),
  data: () => import('./data').then((m) => m.default),
  ml: () => import('./ml').then((m) => m.default),
  fundamentals: () => import('./fundamentals').then((m) => m.default),
  'discrete-math': () => import('./discrete-math').then((m) => m.default),
  tooling: () => import('./tooling').then((m) => m.default),
};

const CACHE = new Map<string, VizChapter[]>();

/** 没有对应学科时返回空数组（页面据此显示「本章暂无图解」），不抛错 */
export function loadVizChapters(subject: string): Promise<VizChapter[]> {
  const hit = CACHE.get(subject);
  if (hit) return Promise.resolve(hit);
  const load = LOADERS[subject];
  if (!load) return Promise.resolve([]);
  return load().then((list) => {
    CACHE.set(subject, list);
    return list;
  });
}

/** 已经加载过就直接给（避免首帧闪「加载中」） */
export function peekVizChapters(subject: string): VizChapter[] | undefined {
  return CACHE.get(subject);
}
