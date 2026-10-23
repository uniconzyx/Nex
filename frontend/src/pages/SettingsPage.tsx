/**
 * SettingsPage.tsx —— 冒险设置
 *
 * 这里改的每一项都真实生效：
 *   深色模式 → progress.theme，同时写 <html data-km-theme>
 *   内容服务地址 → localStorage["nex.apiBaseUrl"]，api.ts 立即读取
 *   判题服务地址 → localStorage["nex.judge.lanBaseUrl"]，GoJudgeClient 立即读取
 *   重置进度 → 清空本地进度（二次确认）
 *   导出进度 → 下载 JSON，方便换机迁移
 *
 * ⚠️ 两个地址不是一回事，别再混用：
 *   内容服务 = Nex 的 FastAPI 后端（默认 8000），提供题库 / 指南 / 账号 / 进度；
 *   判题服务 = 桌面端沙箱的局域网入口（默认 8080），只负责跑代码。
 *   桌面端判题走本机 invoke，通常不需要填；手机端才需要填电脑地址。
 */
import { useCallback, useEffect, useState } from 'react';

import { applyStoredTheme, resetProgress, setTheme, useProgress } from '../lib/progress';
import { apiHealth, getApiBase, setApiBase, type ApiHealth } from '../lib/api';
import { describeCapabilities, useConnection } from '../lib/connection';
import { goJudgeClient, LAN_DEFAULT_PORT } from '../lib/GoJudgeClient';
import type { KmPage } from '../lib/nav';

export function SettingsPage({ onNavigate }: { onNavigate: (page: KmPage) => void }) {
  const p = useProgress();
  const conn = useConnection();
  const [base, setBase] = useState(getApiBase());
  const [saved, setSaved] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const [judgeBase, setJudgeBase] = useState(() => goJudgeClient.getLanBaseUrl());
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [checking, setChecking] = useState(false);

  const saveBase = () => {
    setApiBase(base.trim());
    setSaved(base.trim() ? '已保存，下次请求使用新地址' : '已清空，恢复默认地址');
    window.setTimeout(() => setSaved(''), 2400);
  };

  const saveJudgeBase = () => {
    goJudgeClient.setLanBaseUrl(judgeBase.trim());
    setJudgeBase(goJudgeClient.getLanBaseUrl());
    setSaved(judgeBase.trim() ? '判题服务地址已保存' : '已清除判题服务地址');
    window.setTimeout(() => setSaved(''), 2400);
  };

  const checkNow = useCallback(async (deep = false) => {
    setChecking(true);
    const h = await apiHealth(deep);
    setHealth(h);
    setChecking(false);
  }, []);

  // 打开设置页时自动浅探一次（毫秒级），用户不用点按钮才知道通没通。
  // 深探测（连数据库）只在点「检测连接」时做——数据库没起时会等 1.5s 超时。
  useEffect(() => {
    void checkNow(false);
  }, [checkNow]);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kaimao-progress-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="km-view">
      <section className="km-card">
        <h3>第一次用？</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          三步就能开始：选学科 → 学一章并标记掌握 → 到试炼实验室判一道题。
          不用注册、不用联网，进度自动存在本机。
        </p>
        <div className="help-actions">
          <button
            type="button"
            className="km-btn km-btn-primary km-btn-sm"
            onClick={() => onNavigate('help')}
          >
            打开使用说明
          </button>
          <button
            type="button"
            className="km-btn km-btn-ghost km-btn-sm"
            onClick={() => onNavigate('learn')}
          >
            去学习
          </button>
        </div>
      </section>

      <section className="km-card">
        <h3>外观</h3>
        <div className="km-kv">
          <span>深色模式</span>
          <button
            type="button"
            className={`km-switch${p.theme === 'dark' ? ' on' : ''}`}
            aria-label="切换深色模式"
            aria-pressed={p.theme === 'dark'}
            onClick={() => {
              const next = p.theme === 'dark' ? 'light' : 'dark';
              setTheme(next);
              applyStoredTheme();
            }}
          />
        </div>
        <div className="km-kv">
          <span>减少动效</span>
          <span className="km-tag km-tag-gray">跟随系统</span>
        </div>
        <p className="km-hint">
          深色模式对桌面端与手机端同时生效；系统开启「减少动效」时，凯喵的浮动动画会自动停下。
        </p>
      </section>

      <section className="km-card">
        <h3>内容服务</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          题库、指南、账号与进度都来自 Nex 后端（FastAPI），默认{' '}
          <code>http://127.0.0.1:8000</code>。桌面端由客户端自动探测本机地址；
          手机端或跨机调试时手动填写。
        </p>
        <div className="km-kv">
          <span>连接状态</span>
          <b
            style={{
              color:
                conn.status === 'online'
                  ? 'var(--km-ok)'
                  : conn.status === 'offline'
                    ? 'var(--km-bad)'
                    : 'var(--km-ink-faint)',
            }}
          >
            {conn.status === 'online' ? '● 已连接' : conn.status === 'offline' ? '● 未连接' : '○ 检测中'}
          </b>
        </div>
        {health?.ok && (
          <>
            <div className="km-kv">
              <span>后端版本</span>
              <b>
                {health.backend?.name} v{health.backend?.version}
              </b>
            </div>
            <div className="km-kv">
              <span>可用能力</span>
              <b>{describeCapabilities(health)}</b>
            </div>
            {health.exam?.ok && (
              <div className="km-kv">
                <span>题库规模</span>
                <b>
                  {health.exam.exams} 考试 · {health.exam.questions} 题 · {health.exam.summaries} 总结 ·{' '}
                  {health.exam.papers} 套卷
                </b>
              </div>
            )}
            <div className="km-kv">
              <span>数据库</span>
              <b>
                {health.database?.checked
                  ? health.database.ok
                    ? '已连接'
                    : `未连接（${health.database.error ?? '未知'}）`
                  : '未检测'}
              </b>
            </div>
          </>
        )}
        {health && !health.ok && (
          <p className="km-hint" style={{ color: 'var(--km-bad)' }}>
            {health.error}
          </p>
        )}
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <input
            className="km-input"
            value={base}
            onChange={(e) => setBase(e.target.value)}
            placeholder="http://127.0.0.1:8000"
            aria-label="内容服务地址"
          />
          <button type="button" className="km-btn km-btn-primary km-btn-sm" onClick={saveBase}>
            保存
          </button>
          <button
            type="button"
            className="km-btn km-btn-ghost km-btn-sm"
            onClick={() => void checkNow(true)}
            disabled={checking}
          >
            {checking ? '检测中…' : '检测连接'}
          </button>
        </div>
        {saved && <p className="km-hint" style={{ color: 'var(--km-ok)' }}>{saved}</p>}
      </section>

      <section className="km-card">
        <h3>判题服务</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          判题沙箱跑在<b>电脑端</b>（go-judge），默认端口 {LAN_DEFAULT_PORT}。
          桌面端走本机通道，无需填写；<b>手机端</b>才要填电脑的局域网地址，例如{' '}
          <code>http://192.168.1.5:{LAN_DEFAULT_PORT}</code>。留空则恢复默认。
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <input
            className="km-input"
            value={judgeBase}
            onChange={(e) => setJudgeBase(e.target.value)}
            placeholder={`http://192.168.1.5:${LAN_DEFAULT_PORT}`}
            aria-label="判题服务地址"
          />
          <button type="button" className="km-btn km-btn-primary km-btn-sm" onClick={saveJudgeBase}>
            保存
          </button>
        </div>
      </section>

      <section className="km-card">
        <h3>数据</h3>
        <div className="km-kv">
          <span>本地进度</span>
          <b>
            {p.doneChapters.length} 章 · {p.doneProjects.length} 项目 · {p.checkins.length} 次打卡
          </b>
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
          <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={exportJson}>
            导出进度 JSON
          </button>
          {!confirmReset ? (
            <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => setConfirmReset(true)}>
              重置进度
            </button>
          ) : (
            <>
              <button
                type="button"
                className="km-btn km-btn-primary km-btn-sm"
                onClick={() => {
                  resetProgress();
                  setConfirmReset(false);
                }}
              >
                确认清空（不可恢复）
              </button>
              <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => setConfirmReset(false)}>
                取消
              </button>
            </>
          )}
        </div>
        <p className="km-hint">
          进度只存在本机（localStorage）。换设备请先导出，再在设置里手动恢复（后续版本提供导入）。
        </p>
      </section>

      <section className="km-card">
        <h3>关于</h3>
        <div className="km-kv">
          <span>客户端版本</span>
          <b>v2.0.0 · Tauri 2</b>
        </div>
        <div className="km-kv">
          <span>判题沙箱</span>
          <b>go-judge v1.13.3</b>
        </div>
        <div className="km-kv">
          <span>内容规模</span>
          <b>13 学科 · 107 章 · 110 项目</b>
        </div>
        <div className="km-kv">
          <span>开源许可</span>
          <b>MIT</b>
        </div>
      </section>
    </div>
  );
}
