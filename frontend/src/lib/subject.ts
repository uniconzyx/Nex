/**
 * subject.ts —— 全局「当前学科」状态
 *
 * 为什么需要它：
 *   项目页把 13 个学科平铺成一排胶囊，切走再切回就丢状态；学习/练习页又各自写死 C++。
 *   用户真实的心智是「我现在在学哪一科」，这个状态应该跨页面存活。
 *
 * 设计：
 *   - 单一模块级 store（不是 Context），避免为了一个字符串给整棵树包 Provider；
 *   - 订阅用 Set 维护，任何组件 useSubject() 都能拿到同一份值并即时同步；
 *   - 落 localStorage，刷新/重启后仍在原学科。
 */
import { useEffect, useState } from 'react';

export interface Subject {
  /** 与后端 CareerTrack 枚举一致 */
  key: string;
  label: string;
  /** 窄屏与标签里用的短名 */
  short: string;
}

export const SUBJECTS: Subject[] = [
  { key: 'cpp', label: 'C / C++', short: 'C++' },
  { key: 'clang', label: 'C 语言', short: 'C' },
  { key: 'java', label: 'Java', short: 'Java' },
  { key: 'spring', label: 'Spring 生态', short: 'Spring' },
  { key: 'python', label: 'Python', short: 'Python' },
  { key: 'fullstack', label: '全栈开发', short: '全栈' },
  { key: 'database', label: '数据库', short: '数据库' },
  { key: 'middleware', label: '中间件', short: '中间件' },
  { key: 'ai', label: 'AI / Agent 开发', short: 'AI' },
  { key: 'bigdata', label: '大数据', short: '大数据' },
  { key: 'data', label: '数据分析', short: '数据分析' },
  { key: 'fundamentals', label: '计算机基础', short: '基础' },
  { key: 'tooling', label: '工具链', short: '工具链' },
];

const STORAGE_KEY = 'nex.subject';
const DEFAULT_SUBJECT = 'cpp';

export function subjectLabel(key: string): string {
  return SUBJECTS.find((s) => s.key === key)?.label ?? key;
}

function read(): string {
  if (typeof localStorage === 'undefined') return DEFAULT_SUBJECT;
  const v = localStorage.getItem(STORAGE_KEY);
  return v && SUBJECTS.some((s) => s.key === v) ? v : DEFAULT_SUBJECT;
}

let current = read();
const listeners = new Set<(key: string) => void>();

export function setSubject(key: string): void {
  if (!SUBJECTS.some((s) => s.key === key) || key === current) return;
  current = key;
  if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, key);
  for (const fn of listeners) fn(key);
}

/** 只在当前组件内监听（不写存储），供项目页与全局切换器双向同步 */
export function useSubject(): [string, (key: string) => void] {
  const [value, setValue] = useState(current);

  useEffect(() => {
    const fn = (k: string) => setValue(k);
    listeners.add(fn);
    // 挂载时补一次，避免模块级 current 与首次渲染之间被别处改过
    setValue(current);
    return () => {
      listeners.delete(fn);
    };
  }, []);

  return [value, setSubject];
}
