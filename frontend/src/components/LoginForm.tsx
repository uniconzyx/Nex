/**
 * LoginForm.tsx —— 登录 / 注册 表单（单一事实来源）
 *
 * 同时被「启动登录网关」(LoginGate) 与「账号抽屉」(AccountDrawer) 复用，
 * 避免两份表单逻辑漂移。登录 / 注册走 useSession 的 signIn / signUp；
 * 已登录时展示「退出登录」。
 *
 * 表单按**当前认证后端的能力**自适应（见 lib/authBackend.ts）：
 *   nex   → 邮箱 + 密码、有「注册」tab、有微信登录按钮；
 *   local → 用户名 + 密码、无注册（账号由管理员创建）、无微信。
 *   不把用不了的按钮摆出来再报错，是这一层唯一的存在理由。
 *
 * 微信登录：纯前端无法闭环（需微信开放平台 AppID + 原生 SDK + 后端 OAuth 回调）。
 * 但「无法闭环」和「点了没反应」是两回事——点按钮会真的去问后端
 * GET /api/v1/auth/wechat/config，把「缺资质 / 缺实现 / 连不上服务」分开告诉用户。
 */
import { useState } from 'react';

import { resolveApiBase } from '../lib/api';
import { authBackendInfo } from '../lib/authBackend';
import { useSession } from '../lib/session';

/** 后端 /auth/wechat/config 的返回；unreachable 是前端自己补的（请求失败） */
interface WechatState {
  enabled: boolean;
  stage: 'unconfigured' | 'not_implemented' | 'ready' | 'unreachable';
  missing: string[];
  reason: string;
}

interface Props {
  /** 登录 / 注册成功后回调（网关借此关闭自己） */
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: Props) {
  const s = useSession();
  const be = authBackendInfo();
  const [rawMode, setRawMode] = useState<'login' | 'register'>('login');
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [msg, setMsg] = useState('');
  const [wechatNote, setWechatNote] = useState(false);
  const [wx, setWx] = useState<WechatState | null>(null);
  const [wxBusy, setWxBusy] = useState(false);

  // 后端不支持注册时，即便状态里残留 'register' 也按登录处理
  const mode = be.supportsRegister ? rawMode : 'login';
  const isLocalAccount = be.id === 'local';

  /** 问后端要一份「微信登录到底卡在哪」的真实答案 */
  const checkWechat = async () => {
    setWechatNote(true);
    setWx(null);
    setWxBusy(true);
    try {
      const base = (await resolveApiBase()).replace(/\/+$/, '');
      const res = await fetch(`${base}/api/v1/auth/wechat/config`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as { data?: WechatState };
      setWx(body.data ?? null);
    } catch {
      setWx({
        enabled: false,
        stage: 'unreachable',
        missing: [],
        reason: '连不上内容服务，没法确认微信登录状态；本地学习与进度不受影响',
      });
    } finally {
      setWxBusy(false);
    }
  };

  const submit = async () => {
    setMsg('');
    if (!account.trim() || !password) {
      setMsg(isLocalAccount ? '请填写用户名与密码。' : '请填写账号与密码。');
      return;
    }
    const res =
      mode === 'login'
        ? await s.signIn(account.trim(), password)
        : await s.signUp(account.trim(), password, nickname.trim());
    if (res.ok) {
      setPassword('');
      setMsg('');
      onSuccess?.();
    } else {
      setMsg(res.error || '操作失败');
    }
  };

  if (s.status === 'online') {
    return (
      <div className="km-login-online">
        <div className="km-account-head">
          <img src="/assets/kaimao/mood-happy.png" alt="" />
          <div>
            <h3>{s.account?.profile.nickname || '本地游侠'}</h3>
            <span className="km-tag km-tag-ok">{s.account?.email ?? be.label}</span>
          </div>
        </div>
        <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={s.signOut}>
          退出登录
        </button>
      </div>
    );
  }

  return (
    <div className="km-login-form">
      {/*
        只有一个 tab 时整条隐藏。
        否则「登录」tab 和一个功能完全相同的「登录」提交按钮会上下叠着，
        看起来像两个提交键，用户得停下来判断该点哪个——这不是选择，是噪音。
      */}
      {be.supportsRegister && (
        <div className="km-login-tabs" role="tablist" aria-label="账号操作">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={`km-login-tab ${mode === 'login' ? 'on' : ''}`}
            onClick={() => {
              setRawMode('login');
              setMsg('');
            }}
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={`km-login-tab ${mode === 'register' ? 'on' : ''}`}
            onClick={() => {
              setRawMode('register');
              setMsg('');
            }}
          >
            注册
          </button>
        </div>
      )}

      <div className="km-login-fields">
        {mode === 'register' && (
          <label className="km-login-field">
            <span>昵称</span>
            <input
              className="km-input"
              type="text"
              placeholder="留空则取账号前缀"
              aria-label="昵称"
              value={nickname}
              maxLength={32}
              onChange={(e) => setNickname(e.target.value)}
            />
          </label>
        )}
        <label className="km-login-field">
          <span>{isLocalAccount ? '用户名' : '邮箱'}</span>
          <input
            className="km-input"
            // local 后端收的是用户名而不是邮箱。用 type="email" 会让部分移动端
            // 键盘只出邮箱符号，输入 "dev" 这种账号很别扭，也与语义不符。
            type={isLocalAccount ? 'text' : 'email'}
            placeholder={isLocalAccount ? '你的用户名' : 'you@example.com'}
            aria-label={isLocalAccount ? '用户名' : '邮箱'}
            value={account}
            autoComplete="username"
            onChange={(e) => setAccount(e.target.value)}
          />
        </label>
        <label className="km-login-field">
          <span>密码</span>
          <input
            className="km-input"
            type="password"
            placeholder={mode === 'register' ? '8–72 位' : '输入密码'}
            aria-label="密码"
            value={password}
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void submit();
            }}
          />
        </label>
      </div>

      <div className="km-login-actions">
        <button
          type="button"
          className="km-btn km-btn-primary km-btn-sm"
          disabled={s.pending || !account.trim() || !password}
          onClick={() => void submit()}
        >
          {s.pending ? '连接中…' : mode === 'login' ? '进入试炼塔' : '注册并进入'}
        </button>
        <span className={`km-login-hint ${msg ? 'is-error' : ''}`}>
          {msg ||
            (s.status === 'offline'
              ? isLocalAccount
                ? '连不上本地账号服务，登录暂不可用；本地进度不受影响。'
                : '没有检测到内容服务，登录暂不可用；本地进度不受影响。'
              : isLocalAccount
                ? '账号由管理员创建；令牌 7 天有效，到期需重新登录。'
                : '进度只存在本机，登录用于多设备同步。')}
        </span>
      </div>

      {be.supportsWechat && (
        <>
          <div className="km-login-divider"><span>或</span></div>
          <button
            type="button"
            className="km-btn km-btn-wechat km-btn-sm"
            onClick={() => void checkWechat()}
            disabled={wxBusy}
          >
            <span className="km-wechat-ico" aria-hidden="true">微</span>
            {wxBusy ? '检查中…' : '微信登录'}
          </button>
          {wechatNote && (
            <p className="km-login-hint km-wechat-note">
              {wxBusy
                ? '正在检查后端的微信登录配置…'
                : wx
                  ? wx.reason
                  : '微信登录需要微信开放平台的「网站应用」资质，并接入原生 SDK（Android / Tauri）。'}
            </p>
          )}
        </>
      )}
    </div>
  );
}
