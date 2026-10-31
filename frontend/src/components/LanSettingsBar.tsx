/**
 * LanSettingsBar.tsx
 * ---------------------------------------------------------------------------
 * 局域网判题设置条（移动端瘦客户端的入口）。
 *
 * 桌面端默认走 invoke，不需要配置；Android APK / 浏览器必须在第一次使用前
 * 填入「电脑端」的局域网地址，否则判题请求不知道发给谁。
 *
 * 设计取舍：做成独立组件而不是塞进 JudgePanel —— JudgePanel 是纯判题 UI，
 * 混进网络配置会让它的职责变糊；这里只依赖 GoJudgeClient 的公开 API。
 */
import { useCallback, useEffect, useState } from 'react';

import {
  LAN_DEFAULT_PORT,
  goJudgeClient,
  normalizeLanBaseUrl,
  type LanPing,
  type TransportMode,
} from '../lib/GoJudgeClient';

/** 是否桌面 Tauri（决定要不要显示「填地址」这个入口）。 */
function isDesktopTauri(): boolean {
  if (typeof window === 'undefined') return false;
  if (!('__TAURI_INTERNALS__' in window)) return false;
  return !/android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent);
}

export function LanSettingsBar() {
  const [url, setUrl] = useState<string>('');
  const [mode, setMode] = useState<TransportMode>('auto');
  const [msg, setMsg] = useState<string>('');
  const [msgTone, setMsgTone] = useState<'ok' | 'err' | 'info'>('info');
  const [probing, setProbing] = useState(false);

  // 挂载时把 localStorage 里的现值同步回输入框
  useEffect(() => {
    setUrl(goJudgeClient.getLanBaseUrl());
    setMode(goJudgeClient.getMode());
  }, []);

  const onSave = useCallback(() => {
    const norm = normalizeLanBaseUrl(url);
    goJudgeClient.setLanBaseUrl(norm);
    setUrl(norm);
    if (!norm) {
      setMsgTone('info');
      setMsg('已清除电脑端地址（桌面端不受影响，仍走本机 invoke）');
      return;
    }
    setMsgTone('ok');
    setMsg(`已保存：${norm}（此后判题会自动走局域网通道）`);
  }, [url]);

  const onProbe = useCallback(async () => {
    const norm = normalizeLanBaseUrl(url);
    if (!norm) {
      setMsgTone('err');
      setMsg(`请先填写电脑端地址，例如 192.168.1.5:${LAN_DEFAULT_PORT}`);
      return;
    }
    goJudgeClient.setLanBaseUrl(norm);
    setProbing(true);
    setMsgTone('info');
    setMsg('正在连接电脑端…');
    try {
      const ping: LanPing = await goJudgeClient.probeLan();
      if (!ping.accepting) {
        setMsgTone('err');
        setMsg(
          `能连上电脑（${ping.service} v${ping.version}），但沙箱未启用，暂不能判题。\n` +
            '请在电脑端把 go-judge.exe 放到 resources/binaries/ 后重启 Nex。',
        );
        return;
      }
      setMsgTone('ok');
      setMsg(`连接成功：${ping.service} v${ping.version}，沙箱已就绪，可以开始判题。`);
    } catch (e) {
      setMsgTone('err');
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setProbing(false);
    }
  }, [url]);

  const onModeChange = useCallback((m: TransportMode) => {
    setMode(m);
    goJudgeClient.setMode(m);
    setMsgTone('info');
    setMsg(
      m === 'lan'
        ? '已强制走局域网通道（忽略桌面 invoke）'
        : m === 'invoke'
          ? '已强制走本机 invoke（移动端会失败，仅桌面调试用）'
          : '自动模式：桌面走 invoke，移动端/浏览器走局域网',
    );
  }, []);

  // 桌面端：给一行状态说明就够了，不挡画面
  if (isDesktopTauri()) {
    return (
      <div className="lan-bar">
        <span className="lan-label">判题沙箱：本机运行，无需联网，也无需安装 Docker</span>
        {goJudgeClient.getLanBaseUrl() ? (
          <span className="lan-label lan-label--warn">
            （已存局域网地址，自动模式下不会使用）
          </span>
        ) : null}
      </div>
    );
  }

  // 移动端 / 浏览器：完整配置入口
  // 注意：@types/react 18 把 autoCorrect 定为 string（不是 boolean），必须写 "off"
  return (
    <div className="lan-bar">
      <span className="lan-label">电脑地址</span>
      <input
        className="lan-input"
        value={url}
        placeholder={`192.168.1.5:${LAN_DEFAULT_PORT}（看电脑端启动日志）`}
        inputMode="url"
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onSave();
        }}
      />
      <select
        className="lan-select"
        value={mode}
        onChange={(e) => onModeChange(e.target.value as TransportMode)}
        aria-label="通道模式"
      >
        <option value="auto">自动</option>
        <option value="lan">强制局域网</option>
        <option value="invoke">强制本机</option>
      </select>
      <button className="lan-btn" onClick={onSave} type="button">
        保存
      </button>
      <button
        className="lan-btn lan-btn--ghost"
        onClick={onProbe}
        disabled={probing}
        type="button"
      >
        {probing ? '连接中…' : '测试连接'}
      </button>
      {msg ? <span className={`lan-msg lan-msg--${msgTone}`}>{msg}</span> : null}
    </div>
  );
}

export default LanSettingsBar;
