/**
 * mood.ts —— 凯喵情绪引擎
 * ============================================================================
 * 【为什么现在才做】
 *   素材里从 P0 起就躺着 7 张 mood-*.png（idle / happy / sleepy / think / shy /
 *   celebrate / aggrieved），但一直只用了 2 张：顶栏品牌图标和登录页。
 *   右栏凯喵卡画的是**装扮立绘**（outfit-*.png），「心情」只改了下面那行文字——
 *   也就是说脸永远是同一张，「凯喵有情绪」这件事玩家根本看不见。
 *
 * 【两层判定，缺一不可】
 *   1) 常态 resolveMood()：从跨日进度里按优先级挑一个，进度变化 / 切页时重算。
 *      没有它，情绪就只是随机表情，和玩家做了什么无关。
 *   2) 瞬时 flashMood()：答题结果推一条带 TTL 的情绪，优先于常态显示，过期回落。
 *      没有它，「刚答错」和「昨天答错过」看起来一模一样，脸就不会当场动。
 *
 * 【依赖方向】
 *   mood ← progress（progress 只 import flashMood 这一个纯函数）
 *   mood 不 import progress，避免成环——MoodCtx 由外壳组装好传进来。
 *   这样情绪引擎可以单独测：给一组 ctx，拿一个确定的 key。
 * ============================================================================
 */
import { useEffect, useState } from 'react';

import { pageLabel } from './nav';
import type { KmPage } from './nav';

/* ---------------------------------------------------------------- 类型 */

export type MoodKey =
  | 'celebrate'
  | 'aggrieved'
  | 'shy'
  | 'happy'
  | 'think'
  | 'idle'
  | 'sleepy';

/** 判定情绪所需的事实，全部由外壳从真实进度里取，不在这里读 store */
export interface MoodCtx {
  /** 今天签到过？ */
  checkedIn: boolean;
  /** 连续打卡天数 */
  streak: number;
  /** 今日试炼进度 */
  dailyDone: number;
  dailyTotal: number;
  /** 图鉴里待收服的野怪（错题）数量 */
  wild: number;
  doneChapters: number;
  doneProjects: number;
  /** 当前所在页面（决定是否「陪你思考」） */
  page: KmPage;
  /** 本地小时，0~23，只用于深夜台词的语气 */
  hour: number;
}

export interface MoodDef {
  key: MoodKey;
  /** 右栏那颗胶囊上显示的 2~3 字 */
  label: string;
  emoji: string;
  /** 光晕色：stage 上那圈径向渐变，让情绪先被余光看见 */
  aura: string;
  /** 凯喵此刻说的话。刻意带真实数字，否则「情绪」和「进度」是两套叙事 */
  say: (c: MoodCtx) => string;
}

/* ---------------------------------------------------------------- 素材 */

const moodImg = (k: MoodKey): string => `/assets/kaimao/mood-${k}.png`;

/**
 * 七种心情。顺序即「强度」参考，不参与判定——判定顺序见 resolveMood。
 * 措辞统一是凯喵第一人称、带一点认真劲，不用「哎呀人家」这类撒娇腔。
 */
export const MOODS: Record<MoodKey, MoodDef> = {
  celebrate: {
    key: 'celebrate',
    label: '庆祝',
    emoji: '🎉',
    aura: '#ffc44d',
    say: (c) =>
      `今日试炼 ${c.dailyDone}/${c.dailyTotal} 全清！今天手感是真的好，别把这股劲浪费了～`,
  },
  aggrieved: {
    key: 'aggrieved',
    label: '委屈',
    emoji: '🥺',
    aura: '#93a9cc',
    say: (c) =>
      `图鉴里还压着 ${c.wild} 只没打赢的小怪…我有点慌。今天先挑一只收掉，好不好？`,
  },
  shy: {
    key: 'shy',
    label: '害羞',
    emoji: '😳',
    aura: '#ff9dbf',
    say: (c) => `连签 ${c.streak} 天了…你每天都来，我、我有点不好意思。`,
  },
  happy: {
    key: 'happy',
    label: '开心',
    emoji: '😊',
    aura: '#ffd05e',
    say: (c) =>
      c.doneChapters > 0
        ? `今天你来了，签到记上了。已经掌握 ${c.doneChapters} 章，稳步走就好～`
        : '今天你来了，签到记上了。第一关还没开——挑一章，我陪你去打。',
  },
  think: {
    key: 'think',
    label: '陪你思考',
    emoji: '🤔',
    aura: '#7cc0ff',
    say: (c) => `${pageLabel(c.page)} 这块我陪你一起啃，卡住了就把题丢给我。`,
  },
  idle: {
    key: 'idle',
    label: '发呆',
    emoji: '🐾',
    aura: '#9ec7f0',
    say: (c) =>
      c.hour >= 1 && c.hour < 5
        ? '这个点还没打卡…要不今天到这儿，明天我还在。'
        : '我在。今天还没签到，火苗要断了——先去祭坛打个卡？',
  },
  sleepy: {
    key: 'sleepy',
    label: '待唤醒',
    emoji: '😴',
    aura: '#8ea6c8',
    say: (c) =>
      c.hour >= 1 && c.hour < 5
        ? '这个点还没睡啊…随便做一道就收工，好吗？'
        : '今天还没开始呢…随便挑一道题，做一道我就醒了。',
  },
};

export const moodImage = moodImg;

/* ---------------------------------------------------------------- 判定 */

/**
 * 这些页面要动脑：进去就切「陪你思考」。
 * 不包含 home / me / rank / bag / dress / checkin 这类管理页——
 * 在排行榜上摆一张思考脸会显得很呆。
 */
const LEARN_PAGES: KmPage[] = [
  'learn',
  'projects',
  'bestiary',
  'lab',
  'diagrams',
  'track408',
  'reexam',
  'guides',
  'agent',
  'employment',
];

/**
 * 常态情绪。优先级从「最该被看见」排到「默认」：
 *   庆祝 > 委屈 > 害羞 > 开心 > 思考 > 待唤醒 > 发呆
 *
 * 为什么委屈排在开心前面：签到只是「你来了」，图鉴里堆着错题才是
 * 「你有事没做」。情绪如果只反映好消息，就失去了催进度的作用。
 */
export function resolveMood(c: MoodCtx): MoodKey {
  if (c.dailyTotal > 0 && c.dailyDone >= c.dailyTotal) return 'celebrate';
  if (c.wild >= 3) return 'aggrieved';
  if (c.checkedIn && c.streak >= 7) return 'shy';
  if (c.checkedIn) return 'happy';
  if (LEARN_PAGES.includes(c.page)) return 'think';
  if (c.doneChapters === 0 && c.doneProjects === 0) return 'sleepy';
  return 'idle';
}

/* -------------------------------------------------------------- 瞬时情绪 */

export interface MoodFlash {
  id: string;
  key: MoodKey;
  /** 毫秒 */
  ttl: number;
}

let seq = 0;
let flash: MoodFlash | null = null;
const listeners = new Set<(v: MoodFlash | null) => void>();
let timer: ReturnType<typeof setTimeout> | null = null;

function emit(): void {
  for (const fn of listeners) fn(flash);
}

/**
 * 推一条瞬时情绪。答题结果、收服怪物这类「刚刚发生」的事用它，
 * 让脸当场变一下再回落——这是「活的宠物」和「一张立绘」的分界。
 */
export function flashMood(key: MoodKey, ttl = 3400): void {
  if (typeof window === 'undefined') return;
  flash = { id: `m${Date.now().toString(36)}${(seq += 1).toString(36)}`, key, ttl };
  emit();
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    flash = null;
    timer = null;
    emit();
  }, ttl);
}

export function clearMoodFlash(): void {
  if (timer) clearTimeout(timer);
  timer = null;
  flash = null;
  emit();
}

/** 页面用：拿到当前瞬时情绪（没有就是 null，由调用方回落到 resolveMood） */
export function useMoodFlash(): MoodFlash | null {
  const [v, setV] = useState<MoodFlash | null>(flash);
  useEffect(() => {
    listeners.add(setV);
    setV(flash);
    return () => {
      listeners.delete(setV);
    };
  }, []);
  return v;
}
