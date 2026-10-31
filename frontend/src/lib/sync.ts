/**
 * sync.ts —— 本机进度 ↔ 账号快照（离线优先）
 *
 * 规则（写清楚，免得以后有人改坏）：
 *   1. localStorage 是事实源。任何进度变更先本地生效，UI 立即更新。
 *   2. 登录后拉一次云端快照，与本地做**并集**合并（不删除任何记录）。
 *   3. 合并结果只在"确实有差异"时回推，避免与上传形成回环。
 *   4. 推送是节流 + 尽力而为：500ms 合并窗口，失败静默重试到下次操作。
 *
 * 不做的事：不做字段级冲突解决（没有并发编辑同一个字段的场景）、
 * 不做删除同步（用户清空进度视为本机行为，不应影响其它设备的记录）。
 *
 * ── 两套后端（2026-10-30 补，2026-10-31 对齐）────────────────────────
 *   nex   ：/api/v1/progress/state，现已存储**整份 ProgressState** 快照
 *           （与 auth-server 同能力），GET 返回 snapshot 字段时走 mergeRemoteSnapshot。
 *   local ：/api/auth/progress，同样存整份 ProgressState 快照。
 * 两者现在能力对齐：换设备都能全量恢复 answers / bestiary / chapterRuns /
 * weekly 等，不再丢掌握度。无 snapshot 的旧 nex 后端会回退到 5 字段并集合并。
 */
import { apiGet, apiPut } from './api';
import { getAuthBackendId } from './authBackend';
import { localGetProgress, localPutProgress } from './authLocal';
import {
  getProgressSnapshot,
  mergeRemote,
  mergeRemoteSnapshot,
  setProgressSyncHook,
  type ProgressState,
} from './progress';
import { getAccessToken, getSession } from './session';

interface RemoteState {
  done_chapters: string[];
  done_projects: string[];
  checkins: string[];
  coins: number;
  outfit: string;
  theme: string;
  client_rev: number;
  updated_at: string | null;
  /** 整份进度快照（Nex 后端升级后返回，与 auth-server 对齐）。存在时优先走 mergeRemoteSnapshot 全量恢复 */
  snapshot?: unknown;
}

let rev = 0;
let timer: ReturnType<typeof setTimeout> | null = null;
let inflight = false;
let installed = false;

async function push(snapshot: ProgressState): Promise<void> {
  if (getSession().status !== 'online') return;
  if (inflight) return;
  inflight = true;
  rev += 1;
  try {
    if (getAuthBackendId() === 'local') {
      const token = getAccessToken();
      // 没有令牌说明刚被登出，直接放弃：下一次登录会重新 pull
      if (token) await localPutProgress(token, snapshot, rev);
    } else {
      // nex 后端：与 auth-server 对齐，直接传整份快照（含 answers / bestiary /
      // chapterRuns / weekly 等），服务端按整份存；同时也带上 5 个扁平字段
      // 供旧接口/看板复用。后端优先用 snapshot 路径。
      await apiPut<RemoteState>('/api/v1/progress/state', {
        snapshot,
        done_chapters: snapshot.doneChapters,
        done_projects: snapshot.doneProjects,
        checkins: snapshot.checkins,
        coins: snapshot.coins,
        outfit: snapshot.outfit,
        theme: snapshot.theme,
        client_rev: rev,
      });
    }
  } catch {
    /* 离线/服务未启动：下次 commit 会再试 */
  } finally {
    inflight = false;
  }
}

function schedulePush(snapshot: ProgressState): void {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    timer = null;
    void push(snapshot);
  }, 500);
}

/** 登录成功后调用：拉云端、合并、必要时回推。
 *  1.5s 内重复调用直接复用同一个 Promise —— 登录、账号卡挂载、页面切换
 *  会连续触发，没必要打三次后端。 */
let pulling: Promise<boolean> | null = null;
let pulledAt = 0;

export async function pullProgress(): Promise<boolean> {
  const now = Date.now();
  if (pulling) return pulling;
  if (now - pulledAt < 1500) return false;
  pulling = doPull().finally(() => {
    pulling = null;
    pulledAt = Date.now();
  });
  return pulling;
}

async function doPull(): Promise<boolean> {
  if (getSession().status !== 'online') return false;
  if (getAuthBackendId() === 'local') return doPullLocal();
  try {
    const remote = await apiGet<RemoteState>('/api/v1/progress/state');
    // 后端升级后会返回整份快照：走与 auth-server 同逻辑的 mergeRemoteSnapshot
    // （云端当底、本机覆盖，answers/bestiary/chapterRuns 全量恢复），不再丢掌握度。
    if (remote.snapshot) {
      const changedLocally = mergeRemoteSnapshot(remote.snapshot);
      const local = getProgressSnapshot();
      // 稳定序列化比较：只在确实不一致时回推，避免每次登录白传一份快照
      if (stable(local) !== stable(remote.snapshot)) await push(local);
      return changedLocally;
    }
    // 旧后端（无 snapshot）：回退到 5 字段并集合并
    const changedLocally = mergeRemote(remote);
    // 本地有云端没有的东西（例如刚在这台设备通关）就回推一次
    const local = getProgressSnapshot();
    const remoteSet = new Set([...remote.done_chapters, ...remote.done_projects, ...remote.checkins]);
    const hasNew =
      local.doneChapters.some((c) => !remoteSet.has(c)) ||
      local.doneProjects.some((c) => !remoteSet.has(c)) ||
      local.checkins.some((c) => !remoteSet.has(c));
    if (hasNew || !changedLocally) await push(local);
    return changedLocally;
  } catch {
    return false;
  }
}

/**
 * local 后端的一轮同步。
 *
 * 「要不要回推」用整份序列化比较，而不是比计数器：
 *   第一次登录云端为空 → 必然推；
 *   之后两端一致 → 一份 JSON 相等就跳过，登录多少次都不会白传 300KB；
 *   只在本机多了东西（刚通关）时才会多推一次。
 */
/**
 * 稳定序列化（递归按键名排序）。
 *
 * 为什么不能直接 JSON.stringify 比较：
 *   MySQL 的 JSON 列在存储时会把对象键重排（先按长度、再按字典序），
 *   取回来时键序和本地已经不同 —— 逐字节比对结果永远是"不相等"，
 *   于是每次登录都会把一个 300KB 的快照重推一遍，白白浪费流量。
 *   按键名排序后再比，才是在比「内容」。
 */
function stable(v: unknown): string {
  const canon = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(canon);
    if (x && typeof x === 'object') {
      const src = x as Record<string, unknown>;
      const out: Record<string, unknown> = {};
      for (const k of Object.keys(src).sort()) out[k] = canon(src[k]);
      return out;
    }
    return x;
  };
  return JSON.stringify(canon(v));
}

async function doPullLocal(): Promise<boolean> {
  const token = getAccessToken();
  if (!token) return false;
  try {
    const remote = await localGetProgress(token);
    if (!remote.snapshot) {
      await push(getProgressSnapshot());
      return false;
    }
    const changedLocally = mergeRemoteSnapshot(remote.snapshot);
    const local = getProgressSnapshot();
    if (stable(local) !== stable(remote.snapshot)) await push(local);
    return changedLocally;
  } catch {
    return false;
  }
}

/** 应用启动时安装一次；之后所有进度变更都会自动镜像到账号 */
export function installProgressSync(): void {
  if (installed) return;
  installed = true;
  setProgressSyncHook(schedulePush);
}
