/**
 * ProfilePage.tsx —— 个人闯关档案（纯本机进度 + 成就）
 *
 * 合规改造（2026-10-29）：
 *   登录 / 注册不再内联在此页，而是收口到顶部常驻账号 chip → AccountDrawer。
 *   本页只保留「只读账号状态 + 账号管理按钮」，不再散落表单。
 *
 * 进度全部来自本机（progress.ts），账号来自内容服务（session.ts）。
 * 设计上把"登录"当成可选增强而不是入口闸门：连不上后端时页面照常完整，
 * 只是账号卡显示"未连接服务 · 本地模式"，并给出重试用账号抽屉。
 */
import { useMemo, useState } from 'react';

import { BUNDLE } from '../data/bundle';
import { SUBJECTS } from '../lib/subject';
import { streakOf, useProgress } from '../lib/progress';
import { updateNickname, useSession } from '../lib/session';
import { authBackendInfo } from '../lib/authBackend';
import type { KmPage } from '../lib/nav';

export function ProfilePage({
  onNavigate,
  onOpenAccount,
}: {
  onNavigate: (page: KmPage) => void;
  onOpenAccount?: () => void;
}) {
  const p = useProgress();
  const s = useSession();

  /* 改昵称：就地编辑，不弹窗 —— 只改一个字段不值得再开一层遮罩 */
  const [editingName, setEditingName] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [nameMsg, setNameMsg] = useState('');

  const beginEditName = () => {
    setDraftName(s.account?.profile.nickname ?? '');
    setNameMsg('');
    setEditingName(true);
  };

  const commitName = async () => {
    setNameMsg('保存中…');
    const r = await updateNickname(draftName);
    if (r.ok) {
      setEditingName(false);
      setNameMsg('');
    } else {
      setNameMsg(r.error);
    }
  };

  const exp = p.doneChapters.length * 20 + p.doneProjects.length * 30 + p.checkins.length * 50;
  const level = 1 + Math.floor(exp / 300);
  const streak = streakOf(p.checkins);

  const bySubject = useMemo(
    () =>
      SUBJECTS.map((s) => {
        const pack = BUNDLE.chapters[s.key as keyof typeof BUNDLE.chapters];
        const total = pack?.chapters.length ?? 0;
        const done = (pack?.chapters ?? []).filter((c) => p.doneChapters.includes(c.id)).length;
        return { ...s, total, done };
      }),
    [p.doneChapters],
  );

  const byTier = useMemo(() => {
    const tiers = ['t1', 't2', 't3', 't4'];
    return tiers.map((t) => {
      const all = BUNDLE.projects.items.filter((i) => i.tier === t);
      return { tier: t, total: all.length, done: all.filter((i) => p.doneProjects.includes(i.slug)).length };
    });
  }, [p.doneProjects]);

  return (
    <div className="km-view">
      <section className="km-card">
        <h3>个人闯关档案</h3>
        <div className="km-stat-row" style={{ marginTop: 0 }}>
          <div className="km-stat">
            <b>Lv.{level}</b>
            <span>当前等级</span>
          </div>
          <div className="km-stat">
            <b>{exp}</b>
            <span>累计经验</span>
          </div>
          <div className="km-stat">
            <b>{streak} 天</b>
            <span>连续打卡</span>
          </div>
          <div className="km-stat">
            <b>{p.coins.toLocaleString('zh-CN')}</b>
            <span>经验结晶</span>
          </div>
        </div>
      </section>

      <section className="km-card km-account">
        <div className="km-account-head">
          <img src="/assets/kaimao/mood-idle.png" alt="" />
          <div>
            <h3>{s.account?.profile.nickname || '本地游侠'}</h3>
            <span className={`km-tag ${s.status === 'online' ? 'km-tag-ok' : 'km-tag-gray'}`}>
              {s.status === 'online'
                // 本地账号服务没有邮箱字段，回落到后端名称，避免显示成"已登录 · "的空尾巴
                ? `已登录 · ${s.account?.email ?? authBackendInfo().label}`
                : s.status === 'offline'
                  ? '未连接服务 · 本地模式'
                  : '未登录 · 本地模式'}
            </span>
          </div>
        </div>
        {s.status === 'online' && (
          <div className="km-name-edit">
            {editingName ? (
              <>
                <input
                  className="km-input"
                  value={draftName}
                  maxLength={24}
                  autoFocus
                  placeholder="给自己起个名字（24 字以内）"
                  onChange={(e) => setDraftName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void commitName();
                    if (e.key === 'Escape') setEditingName(false);
                  }}
                />
                <button type="button" className="km-btn km-btn-sm" onClick={() => void commitName()}>
                  保存
                </button>
                <button
                  type="button"
                  className="km-btn km-btn-ghost km-btn-sm"
                  onClick={() => setEditingName(false)}
                >
                  取消
                </button>
              </>
            ) : (
              <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={beginEditName}>
                改昵称
              </button>
            )}
            {nameMsg && <span className="km-hint km-name-msg">{nameMsg}</span>}
          </div>
        )}
        <p className="km-hint" style={{ marginTop: 10 }}>
          {s.status === 'online'
            ? '进度仍以本机为准，账号只用于身份与将来的多设备同步。断网时全部功能照常可用。'
            : '进度只存在这台设备，不上传。登录用于多设备同步，不登录也能用全部功能。'}
        </p>
        {/*
          方向 / 计划 / 每日学习 是 Nex 内容服务的账号画像字段。
          本地账号服务（auth-server）只有 id / username / nickname，
          这三项会一律显示成「—」「free」「0 分钟」——不是"信息不全"，
          而是这个后端根本不提供，摆出来只会让人以为数据丢了。
        */}
        {s.status === 'online' && s.account && authBackendInfo().id !== 'local' && (
          <div className="km-account-fields">
            <div>
              <span>方向</span>
              <b>{s.account.profile.direction || '—'}</b>
            </div>
            <div>
              <span>计划</span>
              <b>{s.account.profile.plan || '—'}</b>
            </div>
            <div>
              <span>每日学习</span>
              <b>{s.account.profile.daily_minutes} 分钟</b>
            </div>
          </div>
        )}
        <div className="help-actions">
          <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={onOpenAccount}>
            {s.status === 'online' ? '账号管理' : '登录 / 注册'}
          </button>
          <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => onNavigate('help')}>
            查看用法
          </button>
        </div>
      </section>

      <section className="km-card">
        <h3>章节掌握 · 按学科</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          {bySubject.map((s) => {
            const pct = s.total ? Math.round((s.done / s.total) * 100) : 0;
            return (
              <div key={s.key} className="km-weak">
                <span className="km-weak-name">{s.short}</span>
                <span className="km-weak-bar">
                  <i style={{ width: `${pct}%` }} />
                </span>
                <span className="km-weak-n">
                  {s.done}/{s.total}
                </span>
              </div>
            );
          })}
        </div>
        <p className="km-hint">共 {bySubject.reduce((n, s) => n + s.total, 0)} 章；进度来自「标记已掌握」。</p>
      </section>

      <section className="km-card">
        <h3>项目通关 · 按梯度</h3>
        <div className="km-stat-row" style={{ marginTop: 0 }}>
          {byTier.map((t) => (
            <div className="km-stat" key={t.tier}>
              <b>
                {t.done}/{t.total}
              </b>
              <span>{t.tier.toUpperCase()}</span>
            </div>
          ))}
        </div>
        <p className="km-hint">
          项目库共 {BUNDLE.projects.total} 个、{BUNDLE.projects.hours} 小时；T4 是能写进简历的深度。
        </p>
      </section>

      <section className="km-card">
        <h3>最近打卡</h3>
        {p.checkins.length === 0 ? (
          <div className="km-empty">
            <b>还没有打卡记录</b>
            <span>去「签到祭坛」点一下，连续天数会从这里开始算。</span>
          </div>
        ) : (
          <div className="km-chips">
            {[...p.checkins]
              .sort()
              .slice(-21)
              .map((d) => (
                <span key={d} className="km-tag km-tag-ok">
                  {d}
                </span>
              ))}
          </div>
        )}
      </section>
    </div>
  );
}
