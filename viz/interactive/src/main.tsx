/**
 * 预览台入口
 *   #/                     索引：16 学科 × 165 章
 *   #/mw-ch04              手写精修版（四个模块，含物理拖拽 + 延迟双删时序）
 *   #/middleware/mw-ch04   通用数据驱动版（同一章的 interactive.json）
 *   #/database/db-ch02     任意章节（按需 import，首页只加载 27KB 索引）
 */
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import CacheDesignLab from '../mw-ch04/CacheDesignLab';
import { InteractiveLab } from '../lab/InteractiveLab';
import type { LabData } from '../lab/types';
import { LAB_INDEX } from './data/index';

const SUBJECT_NAME: Record<string, string> = {
  agent: 'AI Agent', ai: '人工智能 / 深度学习', bigdata: '大数据',
  clang: 'C 语言', cpp: 'C++', data: '数据分析', database: '数据库',
  'discrete-math': '离散数学', fullstack: '全栈开发', fundamentals: '计算机基础',
  java: 'Java', middleware: '中间件', ml: '机器学习', python: 'Python',
  spring: 'Spring', tooling: '工具链',
};

/** 每章一个 json，Vite 会把它们切成独立 chunk —— 首页只下载索引 */
const FILES = import.meta.glob('./data/labs/*.json') as Record<
  string,
  () => Promise<{ default: LabData }>
>;

function load(key: string) {
  return FILES[`./data/labs/${key.replace('/', '__')}.json`];
}

function Index() {
  const groups = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const it of LAB_INDEX) (m[it.subject] ||= []).push(it.key);
    return m;
  }, []);
  const meta = useMemo(() => Object.fromEntries(LAB_INDEX.map((x) => [x.key, x])), []);
  const [q, setQ] = useState('');
  const norm = q.trim().toLowerCase();

  return (
    <div data-page="index">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0, fontSize: 21, fontWeight: 600, color: '#2B3E50' }}>
          凯喵 Code 试炼录 · 交互模块台
        </h1>
        <span style={{ fontSize: 12.5, color: '#7A93A8' }}>
          {LAB_INDEX.length} 章 · 数据由 scripts/gen_interactive.py 从真题 / 易错点 / 代码块抽取
        </span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜章节 / 学科…"
          data-index-search
          style={{
            marginLeft: 'auto',
            border: '1px solid rgba(255,255,255,0.9)',
            background: 'rgba(255,255,255,0.7)',
            borderRadius: 10,
            padding: '7px 12px',
            fontSize: 12.5,
            color: '#2B3E50',
            outline: 'none',
            width: 220,
          }}
        />
      </div>

      {Object.keys(groups).sort().map((s) => {
        const keys = groups[s].filter(
          (k) => !norm || k.includes(norm) || meta[k].title.toLowerCase().includes(norm),
        );
        if (!keys.length) return null;
        return (
          <section key={s} style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600, color: '#2E7FB0' }}>
                {SUBJECT_NAME[s] || s}
              </span>
              <span style={{ fontSize: 11, color: '#7A93A8' }}>{keys.length} 章</span>
              <span style={{ flex: 1, height: 1, background: 'rgba(207,226,239,0.7)' }} />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
              {keys.map((k) => (
                <a
                  key={k}
                  href={`#/${k}`}
                  data-index-card={k}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 2,
                    minWidth: 208,
                    maxWidth: 268,
                    height: 78,
                    padding: '8px 11px',
                    borderRadius: 12,
                    border: '1px solid rgba(255,255,255,0.9)',
                    background: 'rgba(255,255,255,0.62)',
                    boxShadow: '0 8px 24px rgba(160,190,220,0.12)',
                    textDecoration: 'none',
                    overflow: 'hidden',
                  }}
                >
                  <span style={{ fontSize: 10, color: '#7A93A8', fontFamily: 'monospace' }}>{k}</span>
                  <span
                    style={{
                      fontSize: 12.5,
                      color: '#2B3E50',
                      lineHeight: 1.4,
                      height: '2.8em',
                      overflow: 'hidden',
                    }}
                  >
                    {meta[k].title}
                  </span>
                  <span style={{ fontSize: 10.5, color: '#5DB4E5', marginTop: 'auto' }}>
                    {meta[k].kinds.join(' · ')}
                  </span>
                </a>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function Chapter({ chapKey }: { chapKey: string }) {
  const [data, setData] = useState<LabData | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    const f = load(chapKey);
    if (!f) {
      setErr(`没有 ${chapKey} 的数据，先跑 scripts/gen_interactive.py`);
      return;
    }
    f()
      .then((m) => alive && setData(m.default))
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [chapKey]);

  return (
    <div data-page="chapter" data-chapter={chapKey}>
      <div style={{ marginBottom: 10 }}>
        <a href="#/" style={{ fontSize: 12, color: '#2E7FB0', textDecoration: 'none' }}>
          ← 返回索引
        </a>
        {chapKey === 'middleware/mw-ch04' && (
          <a
            href="#/mw-ch04"
            data-switch-refined
            style={{ marginLeft: 14, fontSize: 12, color: '#0F8A6C', textDecoration: 'none' }}
          >
            看手写精修版 →
          </a>
        )}
      </div>
      {err ? (
        <div style={{ fontSize: 13, color: '#C2413C' }}>{err}</div>
      ) : data ? (
        <InteractiveLab data={data} />
      ) : (
        <div data-loading style={{ fontSize: 13, color: '#7A93A8' }}>
          载入本章数据…
        </div>
      )}
    </div>
  );
}

function App() {
  const [route, setRoute] = useState(() =>
    decodeURIComponent(window.location.hash.replace(/^#\/?/, '')).replace(/\/$/, ''),
  );
  useEffect(() => {
    const on = () =>
      setRoute(decodeURIComponent(window.location.hash.replace(/^#\/?/, '')).replace(/\/$/, ''));
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);

  if (!route) return <Index />;
  if (route === 'mw-ch04') {
    return (
      <div data-page="refined">
        <div style={{ marginBottom: 10 }}>
          <a href="#/" style={{ fontSize: 12, color: '#2E7FB0', textDecoration: 'none' }}>
            ← 返回索引
          </a>
          <a
            href="#/middleware/mw-ch04"
            data-switch-generic
            style={{ marginLeft: 14, fontSize: 12, color: '#0F8A6C', textDecoration: 'none' }}
          >
            看通用驱动版 →
          </a>
        </div>
        <CacheDesignLab />
      </div>
    );
  }
  return <Chapter chapKey={route} />;
}

const root = createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <div
      style={{
        maxWidth: 1180,
        margin: '0 auto',
        padding: '22px 18px 60px',
        fontFamily: "'Microsoft YaHei', -apple-system, 'PingFang SC', system-ui, sans-serif",
      }}
    >
      <App />
    </div>
  </React.StrictMode>,
);
