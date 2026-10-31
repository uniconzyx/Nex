/**
 * SettingsPage.tsx —— 冒险设置
 *
 * 这里改的每一项都真实生效：
 *   深色模式 → progress.theme，同时写 <html data-km-theme>
 *   玻璃质感 → localStorage["nex.lgMode"]，liquidglass.css 的 lg-a / lg-b
 *   玻璃强度 → localStorage["nex.lgIntensity"]，写 <html data-lg-intensity>，
 *              经 --lg-k / --lg-da 两个调制量缩放模糊半径与白底浓度
 *   减少动效 → localStorage["nex.motionPref"]，写 <html data-km-motion>，
 *              CSS 与粒子层读同一套判定（lib/motion.ts）
 *   内容服务地址 → localStorage["nex.apiBaseUrl"]，api.ts 立即读取
 *   判题服务地址 → localStorage["nex.judge.lanBaseUrl"]，GoJudgeClient 立即读取
 *   重置进度 → 清空本地进度（二次确认）
 *   导出 / 导入进度 → 下载或还原 JSON，方便换机迁移
 *   高性能 / 省电模式 → localStorage["nex.lgPowerSave"]，强制 A + 轻磨砂
 *
 * ⚠️ 两个地址不是一回事，别再混用：
 *   内容服务 = Nex 的 FastAPI 后端（默认 8000），提供题库 / 指南 / 账号 / 进度；
 *   判题服务 = 桌面端沙箱的局域网入口（默认 8080），只负责跑代码。
 *   桌面端判题走本机 invoke，通常不需要填；手机端才需要填电脑地址。
 */
import { useCallback, useEffect, useState, type ChangeEvent } from 'react';

import { BUNDLE } from '../data/bundle';
import { allChapters } from '../lib/graph';
import {
  applyStoredTheme,
  importProgress,
  parseProgressFile,
  previewOf,
  resetProgress,
  setTheme,
  useProgress,
  type ImportPreview,
} from '../lib/progress';
import { apiHealth, getApiBase, setApiBase, type ApiHealth } from '../lib/api';
import { checkConnection, describeCapabilities, useConnection } from '../lib/connection';
import { goJudgeClient, LAN_DEFAULT_PORT } from '../lib/GoJudgeClient';
import {
  getLgIntensity,
  getLgMode,
  LG_INTENSITY_LABEL,
  setLgIntensity,
  setLgMode,
  setPowerSave,
  type LgIntensity,
  type LgMode,
} from '../lib/liquidGlass';
import { getMotionPref, MOTION_LABEL, setMotionPref, type MotionPref } from '../lib/motion';
import { SUBJECTS } from '../lib/subject';
import type { KmPage } from '../lib/nav';
import {
  getAuthBackendId,
  getLocalAuthBase,
  LOCAL_AUTH_DEFAULT,
  setLocalAuthBase,
  type AuthBackendId,
} from '../lib/authBackend';
import { localHealth } from '../lib/authLocal';
import { changePassword, switchAuthBackend, useSession } from '../lib/session';

/**
 * 内容规模 —— 从数据实时算，不写字面量。
 * 之前这里硬编码「13 学科 · 107 章」，内容早已长到 160+ 章，写死就必然过期。
 *
 * 章节数必须走 `allChapters()`（依赖图）而不是 `BUNDLE.chapters`：
 * 后者漏掉 clang 的 7 个独立单元（157 vs 164），会和右栏「今日目标」显示两个不同的数字。
 * 同一件事在同一屏里有两个答案，比数字本身过时更糟。
 */
const CONTENT_SCALE = {
  subjects: SUBJECTS.length,
  chapters: allChapters().length,
  projects: BUNDLE.projects.items.length,
};

const INTENSITY_ORDER: LgIntensity[] = ['light', 'mid', 'heavy'];
const MOTION_ORDER: MotionPref[] = ['system', 'reduce', 'full'];
const MOTION_HINT: Record<MotionPref, string> = {
  system: '按操作系统的「减少动态效果」设置来',
  reduce: '关掉全部动画、过渡与平滑滚动',
  full: '即使系统要求减少动效，也照常播放',
};

export function SettingsPage({ onNavigate }: { onNavigate: (page: KmPage) => void }) {
  const p = useProgress();
  const conn = useConnection();
  const [base, setBase] = useState(getApiBase());
  const [saved, setSaved] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const [judgeBase, setJudgeBase] = useState(() => goJudgeClient.getLanBaseUrl());
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [checking, setChecking] = useState(false);
  const [powerSave, setPowerSaveLocal] = useState(() => {
    try {
      return localStorage.getItem('nex.lgPowerSave') === 'true';
    } catch {
      return false;
    }
  });
  const [lgMode, setLgModeLocal] = useState<LgMode>(() => getLgMode());
  const [lgIntensity, setLgIntensityLocal] = useState<LgIntensity>(() => getLgIntensity());
  const [motionPref, setMotionPrefLocal] = useState<MotionPref>(() => getMotionPref());
  /** 已选中但尚未执行的导入文件：先给人看清内容，再决定合并还是覆盖 */
  const [pendingImport, setPendingImport] = useState<{
    raw: unknown;
    preview: ImportPreview;
    name: string;
  } | null>(null);
  const [importMsg, setImportMsg] = useState('');
  const [importErr, setImportErr] = useState('');

  /* ── 账号服务：选哪套认证后端 + 本地服务地址 / 探活 / 改密 ── */
  const session = useSession();
  const [authBackend, setAuthBackendLocal] = useState<AuthBackendId>(() => getAuthBackendId());
  const [authBase, setAuthBase] = useState(() => getLocalAuthBase());
  const [authBusy, setAuthBusy] = useState(false);
  const [authMsg, setAuthMsg] = useState('');
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [pwdMsg, setPwdMsg] = useState('');
  const [pwdErr, setPwdErr] = useState('');

  const pickAuthBackend = (id: AuthBackendId) => {
    if (id === authBackend) return;
    setAuthBackendLocal(id);
    // 切换后端由 session 负责清令牌 + 重探测：两套令牌互不通用，
    // 留着旧令牌切过去，下一次请求会被误判成「登录已过期」
    switchAuthBackend(id);
    setAuthMsg('');
    setPwdMsg('');
    setPwdErr('');
  };

  const saveAuthBase = () => {
    setLocalAuthBase(authBase.trim());
    const next = getLocalAuthBase();
    setAuthBase(next);
    setAuthMsg(`已保存为 ${next}`);
  };

  const probeAuth = async () => {
    setAuthBusy(true);
    setAuthMsg('');
    const h = await localHealth();
    setAuthBusy(false);
    if (!h.ok) {
      setAuthMsg(`连不上 ${h.base}：${h.error ?? '未知原因'}`);
      return;
    }
    setAuthMsg(
      h.db?.ok
        ? `已连通 ${h.base}，数据库正常`
        : `服务在线（${h.base}），但数据库异常：${h.db?.error ?? '未知'}`,
    );
  };

  const submitPassword = async () => {
    setPwdMsg('');
    setPwdErr('');
    if (!oldPwd || !newPwd) {
      setPwdErr('请填写原密码与新密码。');
      return;
    }
    const r = await changePassword(oldPwd, newPwd);
    if (r.ok) {
      setOldPwd('');
      setNewPwd('');
      setPwdMsg('密码已修改，其他设备上的登录已失效。');
    } else {
      setPwdErr(r.error);
    }
  };

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
    // 浅探测同时同步全局状态：设置页是用户修完地址后的第一站，
    // 这里通了，顶栏指示灯与离线横幅必须**同一刻**跟着变绿/消失，
    // 否则会出现「横幅还挂着但其实已经通了」的割裂感（Phase18）。
    if (!deep) await checkConnection();
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

  /** 选文件后只做解析与预览，不动磁盘——覆盖是不可逆操作，不能藏进一次点击 */
  const pickImportFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // 立刻清空 input：否则同一个文件第二次选不会触发 change
    e.target.value = '';
    if (!file) return;
    setImportErr('');
    setImportMsg('');
    try {
      const text = await file.text();
      const json: unknown = JSON.parse(text);
      const parsed = parseProgressFile(json);
      if (!parsed.ok) {
        setPendingImport(null);
        setImportErr(parsed.error);
        return;
      }
      setPendingImport({ raw: json, preview: previewOf(parsed.state), name: file.name });
    } catch {
      setPendingImport(null);
      setImportErr('文件不是合法 JSON——可能下载被截断，或者选错了文件');
    }
  };

  const runImport = (mode: 'merge' | 'replace') => {
    if (!pendingImport) return;
    const r = importProgress(pendingImport.raw, mode);
    if (!r.ok) {
      setImportErr(r.error);
      return;
    }
    setPendingImport(null);
    setImportErr('');
    setImportMsg(
      mode === 'merge'
        ? '已合并导入：本机原有的记录一条没丢，备份里的记录也补上了'
        : '已覆盖导入：本机进度已替换为备份内容',
    );
    // 备份里带着 theme / outfit，导入后要立刻把外观应用上去，否则要等刷新才变
    applyStoredTheme();
    window.setTimeout(() => setImportMsg(''), 4000);
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
        <div className="km-kv km-kv-col">
          <span>玻璃质感</span>
          <div className="km-seg">
            <button
              type="button"
              className={`km-seg-btn${lgMode === 'a' ? ' on' : ''}`}
              aria-pressed={lgMode === 'a'}
              onClick={() => {
                setLgModeLocal('a');
                setLgMode('a');
              }}
            >
              冰蓝磨砂（A）
            </button>
            <button
              type="button"
              className={`km-seg-btn${lgMode === 'b' ? ' on' : ''}`}
              aria-pressed={lgMode === 'b'}
              onClick={() => {
                setLgModeLocal('b');
                setLgMode('b');
              }}
            >
              通透折射（B）
            </button>
          </div>
        </div>
        <div className="km-kv km-kv-col">
          <span>玻璃强度</span>
          <div className="km-seg" role="group" aria-label="玻璃强度">
            {INTENSITY_ORDER.map((k) => (
              <button
                key={k}
                type="button"
                className={`km-seg-btn${lgIntensity === k ? ' on' : ''}`}
                aria-pressed={lgIntensity === k}
                disabled={powerSave}
                onClick={() => {
                  setLgIntensityLocal(k);
                  setLgIntensity(k);
                  // 省电模式下 getLgIntensity() 会固定返回 light，
                  // 这里回读一次，保证 UI 显示的是真正生效的档位
                  setLgIntensityLocal(getLgIntensity());
                }}
              >
                {LG_INTENSITY_LABEL[k]}
              </button>
            ))}
          </div>
        </div>
        <p className="km-hint" style={{ marginTop: 0 }}>
          {powerSave
            ? '省电模式已开启，强度锁定在「轻磨砂」——模糊半径才是 GPU 开销的大头，只换配色省不下电。'
            : '强度只改模糊半径与白底浓度：越往右越通透，也越吃 GPU。低端设备卡顿时往左调。'}
        </p>

        <div className="km-kv km-kv-col">
          <span>减少动效</span>
          <div className="km-seg" role="group" aria-label="减少动效">
            {MOTION_ORDER.map((k) => (
              <button
                key={k}
                type="button"
                className={`km-seg-btn${motionPref === k ? ' on' : ''}`}
                aria-pressed={motionPref === k}
                onClick={() => {
                  setMotionPrefLocal(k);
                  setMotionPref(k);
                }}
              >
                {MOTION_LABEL[k]}
              </button>
            ))}
          </div>
        </div>
        <p className="km-hint" style={{ marginTop: 0 }}>
          {MOTION_HINT[motionPref]}。影响关卡动画、粒子与玻璃流光；改完立即生效。
        </p>

        <div className="km-kv">
          <span>高性能 / 省电模式</span>
          <button
            type="button"
            className={`km-switch${powerSave ? ' on' : ''}`}
            aria-label="切换高性能省电模式"
            aria-pressed={powerSave}
            onClick={() => {
              const next = !powerSave;
              setPowerSaveLocal(next);
              setPowerSave(next);
              // 省电会同时覆盖方案与强度，回读让两个控件立刻反映真实状态
              setLgModeLocal(getLgMode());
              setLgIntensityLocal(getLgIntensity());
            }}
          />
        </div>
        <p className="km-hint">
          开启后强制「冰蓝磨砂（A）+ 轻磨砂」，糊得最少、最省电；关闭则回到您上面选的
          方案与强度（未选过则按设备默认：桌面通透折射 B / 移动端磨砂 A）。
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
        <h3>账号服务</h3>
        <p className="km-hint" style={{ marginTop: 0 }}>
          登录默认走 <b>Nex 内容服务</b>（支持注册与自动续期）。也可切换到独立的
          <b>本地账号服务</b>（auth-server，Node + MySQL）：不开放注册、账号由管理员创建、
          令牌 7 天有效。两套后端的令牌<b>互不通用</b>，切换会清空当前登录状态。
        </p>

        <div className="km-seg" role="group" aria-label="账号服务来源">
          <button
            type="button"
            className={`km-seg-btn ${authBackend === 'nex' ? 'on' : ''}`}
            aria-pressed={authBackend === 'nex'}
            onClick={() => pickAuthBackend('nex')}
          >
            Nex 内容服务
          </button>
          <button
            type="button"
            className={`km-seg-btn ${authBackend === 'local' ? 'on' : ''}`}
            aria-pressed={authBackend === 'local'}
            onClick={() => pickAuthBackend('local')}
          >
            本地账号服务
          </button>
        </div>

        <div className="km-kv">
          <span>登录状态</span>
          <b>
            {session.status === 'online'
              ? `已登录 · ${session.account?.profile.nickname ?? '—'}`
              : session.status === 'offline'
                ? '未连接服务'
                : '未登录'}
          </b>
        </div>

        {authBackend === 'local' && (
          <>
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <input
                className="km-input"
                value={authBase}
                onChange={(e) => setAuthBase(e.target.value)}
                placeholder={LOCAL_AUTH_DEFAULT}
                aria-label="本地账号服务地址"
              />
              <button type="button" className="km-btn km-btn-primary km-btn-sm" onClick={saveAuthBase}>
                保存
              </button>
              <button
                type="button"
                className="km-btn km-btn-ghost km-btn-sm"
                onClick={() => void probeAuth()}
                disabled={authBusy}
              >
                {authBusy ? '检测中…' : '检测'}
              </button>
            </div>
            {authMsg && <p className="km-hint">{authMsg}</p>}
            <p className="km-hint">
              该服务不提供注册与自动续期：令牌到期需重新登录，登出会让当前令牌立即作废。
            </p>

            {session.status === 'online' && (
              <div style={{ marginTop: 14 }}>
                <p className="km-hint" style={{ marginBottom: 6 }}>
                  <b>修改密码</b>（改完其他设备全部下线）
                </p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <input
                    className="km-input"
                    type="password"
                    value={oldPwd}
                    onChange={(e) => setOldPwd(e.target.value)}
                    placeholder="原密码"
                    aria-label="原密码"
                    autoComplete="current-password"
                    style={{ flex: '1 1 140px' }}
                  />
                  <input
                    className="km-input"
                    type="password"
                    value={newPwd}
                    onChange={(e) => setNewPwd(e.target.value)}
                    placeholder="新密码（8–72 字节）"
                    aria-label="新密码"
                    autoComplete="new-password"
                    style={{ flex: '1 1 160px' }}
                  />
                  <button
                    type="button"
                    className="km-btn km-btn-ghost km-btn-sm"
                    onClick={() => void submitPassword()}
                    disabled={session.pending}
                  >
                    修改
                  </button>
                </div>
                {pwdErr && (
                  <p className="km-hint" style={{ color: 'var(--km-bad)' }}>
                    {pwdErr}
                  </p>
                )}
                {pwdMsg && (
                  <p className="km-hint" style={{ color: 'var(--km-ok)' }}>
                    {pwdMsg}
                  </p>
                )}
              </div>
            )}
          </>
        )}
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
        <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={exportJson}>
            导出进度 JSON
          </button>
          <label className="km-btn km-btn-ghost km-btn-sm" style={{ cursor: 'pointer', margin: 0 }}>
            导入进度 JSON
            <input
              type="file"
              accept="application/json,.json"
              onChange={(e) => void pickImportFile(e)}
              style={{ display: 'none' }}
            />
          </label>
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

        {importErr && (
          <p className="km-hint" style={{ color: 'var(--km-bad)' }}>
            导入失败：{importErr}
          </p>
        )}
        {importMsg && (
          <p className="km-hint" style={{ color: 'var(--km-ok)' }}>
            {importMsg}
          </p>
        )}

        {pendingImport && (
          <div
            style={{
              marginTop: 12,
              padding: '12px 14px',
              borderRadius: 12,
              border: '1px solid var(--km-line)',
              background: 'var(--km-sunk, rgba(15, 23, 42, 0.04))',
            }}
          >
            <b style={{ fontSize: 13 }}>{pendingImport.name}</b>
            <p className="km-hint" style={{ margin: '6px 0 10px' }}>
              备份里有 {pendingImport.preview.chapters} 章 · {pendingImport.preview.projects} 项目 ·{' '}
              {pendingImport.preview.checkins} 次打卡 · {pendingImport.preview.answers} 条作答 ·{' '}
              {pendingImport.preview.monsters} 只图鉴 · {pendingImport.preview.coins} 金币
            </p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="km-btn km-btn-primary km-btn-sm"
                onClick={() => runImport('merge')}
              >
                合并导入（推荐）
              </button>
              <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => runImport('replace')}>
                覆盖导入
              </button>
              <button
                type="button"
                className="km-btn km-btn-ghost km-btn-sm"
                onClick={() => setPendingImport(null)}
              >
                取消
              </button>
            </div>
            <p className="km-hint" style={{ marginBottom: 0 }}>
              合并 = 两边取并集，本机已有的记录一条不丢；覆盖 = 完全用备份替换本机进度，不可撤销。
            </p>
          </div>
        )}

        <p className="km-hint">
          进度只存在本机（localStorage）。换设备：先在旧设备「导出进度 JSON」，再到新设备「导入」即可。
          导入的备份只会写进本机，不会自动推上云端——后续任意一次答题会走正常同步把差异并上去。
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
          <b>
            {CONTENT_SCALE.subjects} 学科 · {CONTENT_SCALE.chapters} 章 · {CONTENT_SCALE.projects} 项目
          </b>
        </div>
        <div className="km-kv">
          <span>开源许可</span>
          <b>MIT</b>
        </div>
      </section>
    </div>
  );
}
