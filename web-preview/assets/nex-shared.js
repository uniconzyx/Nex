/**
 * nex-shared.js —— APK 竖屏版 / EXE 桌面版 共用的「数据与业务层」
 * ============================================================================
 * 为什么要有这一层：
 *   两端原本是同源演化的两份 HTML，各写一份 setMood / incAff，各自把
 *   64%、7 天、0/3 硬编码进页面。结果是「同一个凯喵，两副面孔」：
 *   心情靠手动点 chips、进度全是死数、内容和功能互相不一致。
 *
 *   本文件把「事实」收归一处：进度快照、心情判定、好感度公式、小游戏规则、
 *   与后端 /api/v1/progress/state 的读写。两端只保留各自的布局与 DOM，
 *   通过 data-nex 属性声明「这里显示哪个事实」，由本层统一填充。
 *   于是「内容一致」不是靠人工对齐，而是由同一份代码保证。
 *
 * 边界（主人 2026-11-07 定）：
 *   · 布局各守各的：APK 竖屏治愈系 / EXE 桌面端都不推翻、不重写。
 *   · 内容与功能两端一致且完整：同一快照、同一心情、同一套小游戏。
 *
 * 数据源优先级：
 *   服务端快照 > 本地共享镜像 > 真实前端 kaimao.progress.v2 > 首次种子快照
 *   后端不可达 / 未登录 / CORS 被拒时自动回落本地，页面功能不降级、不白屏。
 *   心情与好感度随「整份快照」一起同步，后端零 schema 改动。
 *
 * 依赖：无。只用原生 API，两端用 <script src="assets/nex-shared.js"> 引入。
 * ============================================================================
 */
(function (global) {
  'use strict';

  /* ------------------------------------------------------------ 常量 */

  var LS_STATE = 'nex.app.state.v1';
  var LS_BASE = 'nex.apiBaseUrl';
  var LS_TOKEN = 'nex.accessToken';
  var LS_PROGRESS_V2 = 'kaimao.progress.v2';
  var DEFAULT_BASE = 'http://127.0.0.1:8000';   // 仅 file:// 打开时的回退
  function defaultBase() {
    // 由 http(s) 提供服务时（本机部署 / 局域网访问），API 与页面同源；
    // 写死 127.0.0.1 会让手机/其它设备把请求发给自己，永远连不上后端。
    try {
      if (global.location && /^https?:$/.test(global.location.protocol)) {
        var host = global.location.hostname || '';
        // Tauri 原生壳（.exe / .apk）用 tauri.localhost 托管内嵌资源，那里没有 API。
        // 此时回落到可配置的本机 / 局域网服务地址：桌面默认 127.0.0.1:8000，
        // 移动端可设 localStorage['nex.apiBaseUrl'] 指向同一 WiFi 下的 PC。
        // 服务不可达时仍自动回落本地快照，功能完整不白屏。
        if (host === 'tauri' || /(^|\.)tauri\.localhost$/i.test(host)) return DEFAULT_BASE;
        return global.location.origin;
      }
    } catch (e) { /* file:// 或受限环境 */ }
    return DEFAULT_BASE;
  }
  var TOTAL_CHAPTERS = 20;   // 章节体系分母（成就/徽章墙都按 20 章）
  var FLASH_TTL = 3400;
  var PREVIEW_TTL = 8000;

  /* ------------------------------------------------------------ 工具 */

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }
  function lsGet(k) { try { return global.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { global.localStorage.setItem(k, v); } catch (e) { /* 隐私模式 */ } }
  function lsDel(k) { try { global.localStorage.removeItem(k); } catch (e) { /* noop */ } }
  function jsonParse(s, fb) { try { var v = JSON.parse(s); return v && typeof v === 'object' ? v : fb; } catch (e) { return fb; } }
  function pad2(n) { return n < 10 ? '0' + n : String(n); }
  function iso(d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
  function todayISO() { return iso(new Date()); }
  function shiftDay(n) { var d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() + n); return iso(d); }
  function hhmm() { var d = new Date(); return pad2(d.getHours()) + ':' + pad2(d.getMinutes()); }

  /* ------------------------------------------------------------ 心情引擎
   * 移植自 frontend/src/lib/mood.ts，规则逐条对齐，保证 Web 预览页与真实
   * 前端算出的是同一个心情。优先级：庆祝 > 委屈 > 害羞 > 开心 > 思考 > 待唤醒 > 发呆
   */

  var MOODS = {
    celebrate: {
      label: '庆祝', emoji: '🎉', aura: '#ffc44d',
      say: function (c) { return '今日试炼 ' + c.dailyDone + '/' + c.dailyTotal + ' 全清！今天手感是真的好，别把这股劲浪费了～'; },
      state: function (c) { return '今日试炼 ' + c.dailyDone + '/' + c.dailyTotal + ' 已清空'; },
      hint: function () { return '趁手感好，再去题库刷一道保持节奏'; }
    },
    aggrieved: {
      label: '委屈', emoji: '🥺', aura: '#93a9cc',
      say: function (c) { return '图鉴里还压着 ' + c.wild + ' 只没打赢的小怪…我有点慌。今天先挑一只收掉，好不好？'; },
      state: function (c) { return '图鉴里压着 ' + c.wild + ' 只野生怪物'; },
      hint: function () { return '去图鉴挑一只收掉，先解决失败次数最多的那只'; }
    },
    shy: {
      label: '害羞', emoji: '😳', aura: '#ff9dbf',
      say: function (c) { return '连签 ' + c.streak + ' 天了…你每天都来，我、我有点不好意思。'; },
      state: function (c) { return '连续签到 ' + c.streak + ' 天，火苗很稳'; },
      hint: function () { return '保持连击，明天同一时间再来'; }
    },
    happy: {
      label: '开心', emoji: '😊', aura: '#ffd05e',
      say: function (c) {
        return c.doneChapters > 0
          ? '今天你来了，签到记上了。已经掌握 ' + c.doneChapters + ' 章，稳步走就好～'
          : '今天你来了，签到记上了。第一关还没开——挑一章，我陪你去打。';
      },
      state: function (c) { return c.doneChapters > 0 ? '今天已签到，已掌握 ' + c.doneChapters + ' 章' : '今天已签到，第一关还没开'; },
      hint: function () { return '去今日试炼做三道新题'; }
    },
    think: {
      label: '陪你思考', emoji: '🤔', aura: '#7cc0ff',
      say: function (c) { return (c.pageLabel || '这一块') + ' 我陪你一起啃，卡住了就把题丢给我。'; },
      state: function (c) { return '在' + (c.pageLabel || '当前页面') + '陪你思考'; },
      hint: function () { return '卡住了就把题丢给我，我陪你看思路'; }
    },
    idle: {
      label: '发呆', emoji: '🐾', aura: '#9ec7f0',
      say: function (c) {
        return c.hour >= 1 && c.hour < 5
          ? '这个点还没打卡…要不今天到这儿，明天我还在。'
          : '我在。今天还没签到，火苗要断了——先去祭坛打个卡？';
      },
      state: function (c) { return c.hour >= 1 && c.hour < 5 ? '深夜档：今天还没打卡' : '今天还没签到，火苗要断了'; },
      hint: function () { return '先去签到祭坛点一下，再回来做题'; }
    },
    sleepy: {
      label: '待唤醒', emoji: '😴', aura: '#8ea6c8',
      say: function (c) {
        return c.hour >= 1 && c.hour < 5
          ? '这个点还没睡啊…随便做一道就收工，好吗？'
          : '今天还没开始呢…随便挑一道题，做一道我就醒了。';
      },
      state: function () { return '今天还没开始'; },
      hint: function () { return '随便做一道题，做一道我就醒了'; }
    }
  };
  var MOOD_ALIAS = { puzzle: 'think', diagnose: 'think', teach: 'think', worry: 'aggrieved' };
  var MOOD_FLOAT = { idle: '💤', think: '🤔', happy: '😊', shy: '😳', celebrate: '🎉', aggrieved: '🥺', sleepy: '😴' };
  var LEARN_PAGES = ['learn', 'projects', 'bestiary', 'lab', 'diagrams', 'track408', 'reexam', 'guides', 'agent', 'employment', 'boss', 'mini'];

  function moodImage(k) { return 'assets/kaimao/mood-' + k + '.png'; }

  function resolveMood(c) {
    if (c.dailyTotal > 0 && c.dailyDone >= c.dailyTotal) return 'celebrate';
    if (c.wild >= 3) return 'aggrieved';
    if (c.checkedIn && c.streak >= 7) return 'shy';
    if (c.checkedIn) return 'happy';
    if (LEARN_PAGES.indexOf(c.page) >= 0) return 'think';
    if (c.doneChapters === 0 && c.doneProjects === 0) return 'sleepy';
    return 'idle';
  }

  /* ------------------------------------------------------------ 快照 */

  /** 首次打开时的本地种子进度。离线可用；连上后端会被服务端真实快照整体覆盖。 */
  function seedState() {
    var checkins = [];
    for (var i = 7; i >= 1; i--) checkins.push(shiftDay(-i));
    var chapters = [];
    for (var j = 1; j <= 16; j++) chapters.push('ch-' + pad2(j));
    return {
      version: 1,
      doneChapters: chapters,
      doneProjects: ['proj-score', 'proj-lib'],
      checkins: checkins,
      answers: {},
      bestiary: {},
      chapterRuns: {},
      weekly: null,
      coins: 1280,
      outfit: 'default',
      theme: 'light',
      affBonus: 0,
      dailyGoal: 3,
      quests: { code: 0, redeem: 0, boss: 0 },
      wild: 3,
      games: { memory: 0, chain: 0, bugs: 0 },
      clientRev: 0,
      updatedAt: null,
      seeded: true
    };
  }

  /** 把真实前端 kaimao.progress.v2 的字段映射进共享快照 */
  function fromProgressV2(p) {
    var s = seedState();
    s.seeded = false;
    if (Array.isArray(p.doneChapters)) s.doneChapters = p.doneChapters.slice();
    if (Array.isArray(p.doneProjects)) s.doneProjects = p.doneProjects.slice();
    if (Array.isArray(p.checkins)) s.checkins = p.checkins.slice();
    if (p.answers && typeof p.answers === 'object') s.answers = p.answers;
    if (p.bestiary && typeof p.bestiary === 'object') s.bestiary = p.bestiary;
    if (p.chapterRuns && typeof p.chapterRuns === 'object') s.chapterRuns = p.chapterRuns;
    if (p.weekly) s.weekly = p.weekly;
    if (typeof p.coins === 'number') s.coins = p.coins;
    if (p.outfit) s.outfit = p.outfit;
    if (p.theme) s.theme = p.theme;
    return s;
  }

  function normalizeState(raw) {
    var s = seedState();
    if (!raw || typeof raw !== 'object') return s;
    Object.keys(s).forEach(function (k) {
      if (raw[k] !== undefined && raw[k] !== null) s[k] = raw[k];
    });
    ['doneChapters', 'doneProjects', 'checkins'].forEach(function (k) {
      if (!Array.isArray(s[k])) s[k] = [];
    });
    if (!s.quests || typeof s.quests !== 'object') s.quests = { code: 0, redeem: 0, boss: 0 };
    if (!s.games || typeof s.games !== 'object') s.games = { memory: 0, chain: 0, bugs: 0 };
    if (typeof s.dailyGoal !== 'number') s.dailyGoal = 3;
    if (typeof s.affBonus !== 'number') s.affBonus = 0;
    return s;
  }

  function loadLocalState() {
    var own = lsGet(LS_STATE);
    if (own) return normalizeState(jsonParse(own, null));
    var v2 = lsGet(LS_PROGRESS_V2);
    if (v2) return fromProgressV2(jsonParse(v2, {}));
    return seedState();
  }

  /* ------------------------------------------------------------ 派生事实 */

  function computeStreak(checkins) {
    var set = {};
    (checkins || []).forEach(function (d) { set[String(d).slice(0, 10)] = true; });
    var n = 0;
    // 今天没签不算断：从昨天开始数，允许「今天待签」的连续态
    var start = set[todayISO()] ? 0 : -1;
    for (var i = start; i > -400; i--) {
      if (set[shiftDay(i)]) n++; else break;
    }
    return n;
  }

  function derive(s, opts) {
    opts = opts || {};
    var checkins = s.checkins || [];
    var streak = computeStreak(checkins);
    var checkedIn = checkins.indexOf(todayISO()) >= 0;
    var q = s.quests || {};
    var dailyDone = (Number(q.code) || 0) + (Number(q.redeem) || 0) + (Number(q.boss) || 0);
    var dailyTotal = s.dailyGoal || 3;
    var doneChapters = (s.doneChapters || []).length;
    var doneProjects = (s.doneProjects || []).length;
    var wild = Number(s.wild) || 0;
    var mastery = clamp(Math.round(doneChapters / TOTAL_CHAPTERS * 100), 0, 100);
    // 与 KaimaoShell.tsx 完全一致：64 + min(章节+项目, 30)，互动另加 affBonus
    var affection = clamp(64 + Math.min(doneChapters + doneProjects, 30) + (s.affBonus || 0), 0, 100);
    var page = opts.page || 'home';
    var hour = new Date().getHours();
    var ctx = {
      checkedIn: checkedIn, streak: streak,
      dailyDone: dailyDone, dailyTotal: dailyTotal,
      wild: wild, doneChapters: doneChapters, doneProjects: doneProjects,
      page: page, pageLabel: opts.pageLabel || '当前页面', hour: hour
    };
    var liveKey = resolveMood(ctx);
    var moodKey = opts.flash || liveKey;
    var mood = MOODS[moodKey] || MOODS.idle;
    var weather = mastery >= 70 ? '晴朗' : (mastery >= 40 ? '多云转晴' : '微雨');
    var weatherTip = mastery >= 70 ? '经验 +15% · 专注极佳'
      : (mastery >= 40 ? '经验 +10% · 状态良好' : '经验 +5% · 慢慢来');
    var weatherIco = mastery >= 70 ? '☀️' : (mastery >= 40 ? '🌤️' : '🌦️');
    return {
      ctx: ctx, liveKey: liveKey, moodKey: moodKey, mood: mood,
      isFlash: !!opts.flash,
      streak: streak, checkedIn: checkedIn,
      dailyDone: dailyDone, dailyTotal: dailyTotal,
      doneChapters: doneChapters, doneProjects: doneProjects,
      mastery: mastery, affection: affection, wild: wild,
      bestiary: 8 + Math.min(doneChapters, 16), bestiaryTotal: 24,
      badges: 6 + Math.floor(doneChapters / 4), badgesTotal: 16,
      chaptersText: Math.min(doneChapters, TOTAL_CHAPTERS) + '/' + TOTAL_CHAPTERS,
      outfits: 2 + Math.floor((s.games.chain + s.games.bugs + s.games.memory) / 2), outfitsTotal: 5,
      coins: s.coins || 0,
      quests: {
        code: Number(q.code) || 0,
        redeem: Number(q.redeem) || 0,
        boss: Number(q.boss) || 0
      },
      weather: weather, weatherTip: weatherTip, weatherIco: weatherIco,
      morning: '🐱 凯喵晨报 · 已掌握 ' + doneChapters + ' 章，连续打卡 ' + streak + ' 天，图鉴还有 ' + wild + ' 只小怪等你收服',
      affLabel: '💞 好感度 · ' + (affection >= 90 ? '羁绊 Max' : affection >= 80 ? '挚友 Max' : '挚友 Lv.4')
    };
  }

  /* ------------------------------------------------------------ API 层 */

  function getBase() {
    var b = lsGet(LS_BASE);
    return (b && b.trim() ? b.trim() : defaultBase()).replace(/\/+$/, '');
  }
  function setBase(b) { if (b && b.trim()) lsSet(LS_BASE, b.trim().replace(/\/+$/, '')); else lsDel(LS_BASE); }
  function getToken() { return lsGet(LS_TOKEN); }

  function request(path, method, body) {
    var url = getBase() + path;
    var headers = { 'Accept': 'application/json' };
    var token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    var ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, 4000) : null;
    return fetch(url, {
      method: method || 'GET',
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctl ? ctl.signal : undefined
    }).then(function (r) {
      if (timer) clearTimeout(timer);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (json) {
      // 后端统一响应包 {code,message,data,traceId}；也兼容裸对象
      if (json && typeof json === 'object' && 'code' in json && 'data' in json) {
        if (json.code !== 0) throw new Error(json.message || ('服务端错误 ' + json.code));
        return json.data;
      }
      return json;
    });
  }

  function health() { return request('/health', 'GET'); }
  function pullRemote() { return request('/api/v1/progress/state', 'GET'); }
  function pushRemote(snapshot) {
    return request('/api/v1/progress/state', 'PUT', { snapshot: snapshot });
  }

  /* ------------------------------------------------------------ Store */

  var state = loadLocalState();
  var mode = 'local';           // local | connecting | synced | offline | need-auth
  var lastSync = '';
  var note = '';
  var listeners = [];
  var flash = null;             // {key, timer}
  var preview = null;
  var currentPage = 'home';
  var currentPageLabel = '主城';
  var pushTimer = null;

  function view() { return derive(state, { page: currentPage, pageLabel: currentPageLabel, flash: flash ? flash.key : null }); }

  function emit() {
    var v = view();
    listeners.forEach(function (fn) { try { fn(v, state); } catch (e) { /* 单个订阅者不拖垮全局 */ } });
    render(v);
  }

  function persist(shouldPush) {
    state.clientRev = (state.clientRev || 0) + 1;
    state.updatedAt = new Date().toISOString();
    lsSet(LS_STATE, JSON.stringify(state));
    if (shouldPush && mode === 'synced') {
      if (pushTimer) clearTimeout(pushTimer);
      pushTimer = setTimeout(function () {
        pushRemote(state).then(function () {
          lastSync = hhmm(); note = '已同步至云端';
          emit();
        }).catch(function (e) {
          mode = 'offline'; note = '同步失败，已存本地：' + e.message;
          emit();
        });
      }, 700);
    }
  }

  /** 局部更新快照；自动持久化 + 按连接状态回写云端 */
  function patch(obj, silent) {
    if (!obj || typeof obj !== 'object') return;
    Object.keys(obj).forEach(function (k) { state[k] = obj[k]; });
    persist(true);
    if (!silent) emit();
  }

  function bumpAff(n) {
    state.affBonus = (state.affBonus || 0) + (Number(n) || 0);
    persist(true);
    emit();
  }

  function flashMood(key, ttl) {
    key = MOOD_ALIAS[key] || key;
    if (!MOODS[key]) return;
    if (flash && flash.timer) clearTimeout(flash.timer);
    var t = setTimeout(function () { flash = null; preview = null; emit(); }, ttl || FLASH_TTL);
    flash = { key: key, timer: t };
    emit();
  }

  function previewMood(key) {
    key = MOOD_ALIAS[key] || key;
    if (!MOODS[key]) return;
    if (key === view().liveKey) { clearOverride(); return; }
    preview = key;
    flashMood(key, PREVIEW_TTL);
  }

  function clearOverride() {
    if (flash && flash.timer) clearTimeout(flash.timer);
    flash = null; preview = null; emit();
  }

  function setPage(page, label) {
    currentPage = page || 'home';
    currentPageLabel = label || '主城';
    if (!flash) emit();
  }

  /** 今日试炼：完成一项 */
  function completeQuest(key) {
    if (!state.quests) state.quests = { code: 0, redeem: 0, boss: 0 };
    if (state.quests[key]) return;
    state.quests[key] = 1;
    state.coins = (state.coins || 0) + 20;
    state.affBonus = (state.affBonus || 0) + 1;
    persist(true);
    emit();
    flashMood('happy', 2200);
    if (typeof global.toast === 'function') global.toast('✅ 试炼完成 · 金币 +20 · 好感 +1');
  }

  /** 签到 */
  function signIn() {
    var t = todayISO();
    if ((state.checkins || []).indexOf(t) >= 0) {
      if (typeof global.toast === 'function') global.toast('今天已经打过卡啦～');
      return false;
    }
    state.checkins = (state.checkins || []).concat([t]);
    state.coins = (state.coins || 0) + 30;
    state.affBonus = (state.affBonus || 0) + 2;
    persist(true);
    emit();
    flashMood('celebrate', 2600);
    if (typeof global.toast === 'function') global.toast('🔥 签到成功 · 连续 ' + view().streak + ' 天 · 金币 +30');
    return true;
  }

  /** 收服一只错题怪 */
  function tameMonster() {
    state.wild = Math.max(0, (Number(state.wild) || 0) - 1);
    state.affBonus = (state.affBonus || 0) + 1;
    persist(true);
    emit();
    flashMood('happy', 2200);
  }

  /** 小游戏通关记分 */
  function recordGame(key, score) {
    if (!state.games) state.games = { memory: 0, chain: 0, bugs: 0 };
    state.games[key] = Math.max(state.games[key] || 0, Number(score) || 0);
    state.coins = (state.coins || 0) + 80;
    state.affBonus = (state.affBonus || 0) + 2;
    persist(true);
    emit();
    flashMood('celebrate', 2600);
  }

  /* ------------------------------------------------------------ 连接 */

  function ensureSession() {
    var canFetch = typeof global.fetch === 'function' && global.location &&
                   /^https?:$/.test(global.location.protocol);
    if (getToken() || !canFetch) { connect(); return; }
    // 本机部署层提供 /api/local/session：自动领取长效本机令牌，无需手动登录。
    // 普通静态托管没有这个端点 -> 静默忽略，照常回落本地快照。
    global.fetch('/api/local/session', { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var d = j && j.data ? j.data : j;
        if (d && d.access_token) lsSet(LS_TOKEN, d.access_token);
      })
      .catch(function () { /* noop */ })
      .then(function () { connect(); });
  }

  function applyRemote(data) {
    var snap = null;
    if (data && typeof data === 'object') {
      if (data.snapshot && typeof data.snapshot === 'object') snap = data.snapshot;
      else if (Array.isArray(data.done_chapters) || Array.isArray(data.checkins)) snap = data;
    }
    if (!snap) return false;
    var merged = normalizeState(snap);
    // 打卡并集（与后端 put_state 的语义一致，避免跨设备丢签到）
    merged.checkins = Array.from(new Set((state.checkins || []).concat(merged.checkins || []))).sort();
    state = merged;
    lsSet(LS_STATE, JSON.stringify(state));
    return true;
  }

  function connect(opts) {
    opts = opts || {};
    mode = 'connecting'; note = '正在连接后端…'; emit();
    return health().then(function () {
      if (!getToken() && !opts.anonymous) {
        mode = 'need-auth'; note = '未登录 · 使用本地快照，登录后自动同步'; emit();
        return false;
      }
      return pullRemote().then(function (data) {
        applyRemote(data);
        mode = 'synced'; lastSync = hhmm(); note = '云端快照已加载';
        emit();
        return true;
      });
    }).catch(function (e) {
      if (/HTTP 401|HTTP 403/.test(e.message)) {
        mode = 'need-auth'; note = '登录状态失效 · 已回落本地快照';
      } else {
        mode = 'offline'; note = '后端不可达 · 本地模式（' + e.message + '）';
      }
      emit();
      return false;
    });
  }

  function promptConnect() {
    // 自绘对话框：window.prompt 在 Tauri / Android WebView 常被静默吞掉，
    // 之前手机上「连接后端」按钮点了没反应。两端共用本层，不改任何 HTML。
    var old = $('nxConnDlg');
    if (old && old.parentNode) { old.parentNode.removeChild(old); return; }
    var ci = connectionInfo();
    var wrap = document.createElement('div');
    wrap.id = 'nxConnDlg';
    wrap.className = 'nx-overlay';
    wrap.innerHTML = '' +
      '<div class="nx-dialog" role="dialog" aria-modal="true" aria-label="连接后端">' +
        '<h3>☁️ 连接后端</h3>' +
        '<p class="nx-sub">当前：' + esc(ci.text) + '<br>' +
          '桌面版默认连本机 <b>127.0.0.1:8000</b>；手机与电脑在同一 WiFi 时，' +
          '请填电脑的局域网地址（如 <b>http://192.168.1.5:8000</b>），留空恢复默认。' +
          '后端不可达会自动回落本地快照，功能不受影响。</p>' +
        '<input id="nxConnInput" type="text" inputmode="url" autocomplete="off" spellcheck="false" ' +
          'placeholder="http://192.168.1.5:8000" value="' + esc(getBase()) + '" ' +
          'class="nx-input" aria-label="后端地址">' +
        '<div class="nx-dlg-actions">' +
          '<button type="button" class="nx-btn ghost" data-act="default">恢复默认</button>' +
          '<button type="button" class="nx-btn ghost" data-act="cancel">取消</button>' +
          '<button type="button" class="nx-btn" data-act="save">保存并重连</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(wrap);
    var input = $('nxConnInput');
    function close() { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }
    function apply(val) {
      setBase(val);
      close();
      connect().then(function (ok) {
        if (typeof global.toast === 'function') {
          global.toast(ok ? '☁️ 已连接后端并同步快照' : '📴 未连上，已保留本地模式（功能不受影响）');
        }
      });
    }
    wrap.addEventListener('click', function (e) {
      if (e.target === wrap) { close(); return; }
      var btn = e.target && e.target.closest ? e.target.closest('[data-act]') : null;
      if (!btn) return;
      var act = btn.getAttribute('data-act');
      if (act === 'cancel') close();
      else if (act === 'default') apply('');
      else if (act === 'save') apply(input ? input.value : '');
    });
    if (input) {
      try { input.focus(); input.select(); } catch (e2) { /* 部分 WebView 禁止自动聚焦 */ }
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') apply(input.value);
        else if (e.key === 'Escape') close();
      });
    }
  }

  function refresh() { return connect(); }

  function connectionInfo() {
    var map = {
      local: { text: '📴 本地模式', cls: 'is-local', desc: '数据存于本机，功能完整可用' },
      connecting: { text: '🔄 连接中…', cls: 'is-busy', desc: '正在探测后端' },
      synced: { text: '☁️ 云端已同步 ' + lastSync, cls: 'is-online', desc: '与服务端快照双向同步' },
      offline: { text: '📴 离线模式', cls: 'is-offline', desc: '后端不可达，已自动回落本地' },
      'need-auth': { text: '🔑 待登录', cls: 'is-offline', desc: '登录后自动同步，当前使用本地快照' }
    };
    return map[mode] || map.local;
  }

  /* ------------------------------------------------------------ 渲染协议
   * 两端 HTML 只声明 data-nex="事实名"，本层统一填值。新增事实只需改这里。
   */

  function bindings(v) {
    return {
      mastery: v.mastery + '%',
      masteryNum: String(v.mastery),
      aff: v.affection + '%',
      affNum: String(v.affection),
      streak: v.streak + ' 天',
      streakNum: String(v.streak),
      dailyDone: String(v.dailyDone),
      dailyTotal: String(v.dailyTotal),
      daily: v.dailyDone + '/' + v.dailyTotal,
      dailyLeft: String(Math.max(0, v.dailyTotal - v.dailyDone)),
      wild: String(v.wild),
      bestiary: v.bestiary + '/' + v.bestiaryTotal,
      badges: v.badges + '/' + v.badgesTotal,
      chapters: v.chaptersText,
      doneChapters: String(v.doneChapters),
      outfits: Math.min(v.outfits, v.outfitsTotal) + '/' + v.outfitsTotal,
      coins: String(v.coins),
      power: (1200 + Math.floor((v.coins || 0) / 50)).toLocaleString('en-US'),
      questCode: v.quests.code + '/3',
      questRedeem: v.quests.redeem + '/2',
      questBoss: v.quests.boss + '/1',
      weather: v.weather,
      weatherTip: v.weatherTip,
      weatherIco: v.weatherIco,
      moodLabel: v.mood.label,
      moodEmoji: v.mood.emoji,
      moodLine: v.mood.state(v.ctx),
      moodHint: v.mood.hint(v.ctx),
      moodSay: v.mood.say(v.ctx),
      moodAura: v.mood.aura,
      morning: v.morning,
      affLabel: v.affLabel,
      connection: connectionInfo().text,
      connectionDesc: note || connectionInfo().desc
    };
  }

  function moodCardHTML(v) {
    var ci = connectionInfo();
    return '' +
      '<div class="nx-mood-card" style="--nx-aura:' + esc(v.mood.aura) + '" data-mood="' + esc(v.moodKey) + '">' +
        '<div class="nx-mood-head">' +
          '<span class="nx-mood-title">凯喵心情</span>' +
          '<span class="nx-mood-chip"><span aria-hidden="true">' + v.mood.emoji + '</span> ' + esc(v.mood.label) + '</span>' +
        '</div>' +
        '<div class="nx-mood-body">' +
          '<img class="nx-mood-face" src="' + esc(moodImage(v.moodKey)) + '" alt="凯喵 · ' + esc(v.mood.label) + '">' +
          '<div class="nx-mood-text">' +
            '<p class="nx-mood-line">' + esc(v.mood.state(v.ctx)) + '</p>' +
            '<p class="nx-mood-hint">' + esc(v.mood.hint(v.ctx)) + '</p>' +
            '<div class="nx-mood-say">' + esc(v.mood.say(v.ctx)) + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="nx-mood-foot">' +
          '<span class="nx-conn ' + ci.cls + '">' + esc(ci.text) + '</span>' +
          '<span class="nx-mood-actions">' +
            (v.isFlash ? '<button type="button" class="nx-mini" onclick="NexApp.clearOverride()">恢复实时</button>' : '') +
            '<button type="button" class="nx-mini" onclick="NexApp.refresh()">同步</button>' +
            '<button type="button" class="nx-mini" onclick="NexApp.promptConnect()">连接后端</button>' +
          '</span>' +
        '</div>' +
        (v.isFlash ? '<div class="nx-flash-tip">表情为临时预览，稍后自动回到实时心情</div>' : '') +
      '</div>';
  }

  function render(v) {
    v = v || view();
    var b = bindings(v);
    var nodes = document.querySelectorAll('[data-nex]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i], key = el.getAttribute('data-nex');
      if (Object.prototype.hasOwnProperty.call(b, key)) el.textContent = b[key];
    }
    var bars = document.querySelectorAll('[data-nex-bar]');
    for (var j = 0; j < bars.length; j++) {
      var bar = bars[j], bk = bar.getAttribute('data-nex-bar');
      var val = bk === 'mastery' ? v.mastery : (bk === 'aff' ? v.affection : Number(b[bk]) || 0);
      bar.style.width = clamp(val, 0, 100) + '%';
    }
    var rings = document.querySelectorAll('[data-nex-ring]');
    for (var k = 0; k < rings.length; k++) {
      var rk = rings[k].getAttribute('data-nex-ring');
      rings[k].style.setProperty('--pct', rk === 'mastery' ? v.mastery : v.affection);
    }
    var dashes = document.querySelectorAll('[data-nex-dash]');
    for (var z = 0; z < dashes.length; z++) {
      var dz = dashes[z].getAttribute('data-nex-dash');
      var pct = dz === 'mastery' ? v.mastery : v.affection;
      var circumference = parseFloat(dashes[z].getAttribute('stroke-dasharray')) || 339.3;
      dashes[z].setAttribute('stroke-dashoffset', (circumference * (1 - clamp(pct, 0, 100) / 100)).toFixed(1));
    }
    var imgs = document.querySelectorAll('[data-nex-img]');
    for (var m = 0; m < imgs.length; m++) {
      if (imgs[m].getAttribute('data-nex-img') === 'mood') imgs[m].src = moodImage(v.moodKey);
    }
    var cards = document.querySelectorAll('[data-nex-card]');
    for (var n = 0; n < cards.length; n++) {
      if (cards[n].getAttribute('data-nex-card') === 'mood') cards[n].innerHTML = moodCardHTML(v);
    }
    var badges = document.querySelectorAll('[data-nex-conn]');
    for (var p = 0; p < badges.length; p++) {
      var ci = connectionInfo();
      badges[p].textContent = ci.text;
      badges[p].className = (badges[p].getAttribute('data-nex-conn') || '') + ' nx-conn ' + ci.cls;
      badges[p].title = note || ci.desc;
    }

    /* 两端同 id 的通用绑定 */
    var stage = $('catStage'); if (stage) stage.dataset.mood = v.moodKey;
    var mlabel = $('moodLabel'); if (mlabel) mlabel.textContent = '· ' + v.mood.label;
    var afp = $('affPct'); if (afp) afp.textContent = v.affection + '%';
    var aff = $('affFill'); if (aff) aff.style.width = v.affection + '%';
    var hafp = $('homeAffPct'); if (hafp) hafp.textContent = v.affection + '%';
    var haff = $('homeAffFill'); if (haff) haff.style.width = v.affection + '%';
    var hal = $('homeAffLbl'); if (hal) hal.textContent = v.affLabel;
    var cf = $('catFloat'); if (cf) cf.textContent = MOOD_FLOAT[v.moodKey] || '💤';
    var fm = $('fabMood'); if (fm) fm.textContent = MOOD_FLOAT[v.moodKey] || '💤';
    var chips = document.querySelectorAll('#moodChips button');
    for (var q = 0; q < chips.length; q++) chips[q].classList.toggle('on', chips[q].dataset.mood === v.moodKey);
  }

  /* ------------------------------------------------------------ 样式注入
   * 只定义共享卡内部样式，颜色全部取两端已有的设计令牌（暗色自动跟随）。
   */
  function injectStyle() {
    if ($('nex-shared-style')) return;
    var css = '' +
    '.nx-mood-card{position:relative;border-radius:var(--r,14px);padding:12px 13px 10px;' +
      'background:var(--surf-1,rgba(255,255,255,.86));border:1px solid var(--line,rgba(91,155,213,.26));' +
      'box-shadow:var(--sh-soft,0 4px 16px rgba(60,95,135,.12));overflow:hidden;color:var(--ink,#26364A)}' +
    '.nx-mood-card::before{content:"";position:absolute;inset:-40% 40% 40% -30%;pointer-events:none;' +
      'background:radial-gradient(circle,var(--nx-aura,#9ec7f0) 0%,transparent 68%);opacity:.16}' +
    '.nx-mood-head{position:relative;display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px}' +
    '.nx-mood-title{font-size:12.5px;font-weight:700;letter-spacing:.02em;color:var(--ink,#26364A)}' +
    '.nx-mood-chip{font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:99px;color:var(--ink,#26364A);' +
      'background:var(--surf-sunk,rgba(91,155,213,.10));border:1px solid var(--line-2,rgba(91,155,213,.14))}' +
    '.nx-mood-body{position:relative;display:flex;gap:11px;align-items:center}' +
    '.nx-mood-face{width:62px;height:62px;flex:0 0 62px;object-fit:contain;border-radius:14px;' +
      'background:var(--surf-2,rgba(255,255,255,.6));border:1px solid var(--line-2,rgba(91,155,213,.14))}' +
    '.nx-mood-text{min-width:0;flex:1}' +
    '.nx-mood-line{margin:0 0 3px;font-size:12.5px;font-weight:700;line-height:1.45;color:var(--ink,#26364A)}' +
    '.nx-mood-hint{margin:0 0 6px;font-size:11.5px;line-height:1.45;color:var(--ink-soft,#54687D)}' +
    '.nx-mood-say{font-size:11.5px;line-height:1.55;padding:6px 9px;border-radius:9px;color:var(--ink-soft,#54687D);' +
      'background:var(--surf-sunk,rgba(91,155,213,.10));border-left:2px solid var(--accent,#5B9BD5)}' +
    '.nx-mood-foot{position:relative;display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;margin-top:9px}' +
    '.nx-conn{font-size:10.5px;padding:2px 8px;border-radius:99px;white-space:nowrap;' +
      'background:var(--surf-sunk,rgba(91,155,213,.10));color:var(--ink-faint,#8496AB);border:1px solid var(--line-2,rgba(91,155,213,.14))}' +
    '.nx-conn.is-online{color:var(--ok,#3B9A6C)}.nx-conn.is-offline,.nx-conn.is-local{color:var(--ink-faint,#8496AB)}' +
    '.nx-conn.is-busy{color:var(--warn,#B57F22)}' +
    '.nx-mood-actions{display:flex;gap:5px;flex-wrap:wrap}' +
    '.nx-mini{font-size:10.5px;padding:3px 8px;border-radius:99px;cursor:pointer;white-space:nowrap;' +
      'color:var(--accent-ink,#2F6494);background:var(--surf-2,rgba(255,255,255,.6));' +
      'border:1px solid var(--line,rgba(91,155,213,.26))}' +
    '.nx-mini:hover{background:var(--accent-soft,#D9EAF7)}' +
    '.nx-flash-tip{position:relative;margin-top:7px;font-size:10.5px;color:var(--ink-faint,#8496AB);text-align:right}' +
    '.nx-compact{padding:10px 11px 9px}' +
    '.nx-compact .nx-mood-face{width:44px;height:44px;flex-basis:44px;border-radius:11px}' +
    '.nx-compact .nx-mood-line{font-size:12px}' +
    '.nx-compact .nx-mood-hint,.nx-compact .nx-mood-say{font-size:11px}' +
    '.nx-compact .nx-mood-foot{gap:4px}' +
    /* 小游戏浮层：两端共用，不依赖各自 openModal 实现 */
    '.nx-overlay{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;padding:18px;' +
      'background:rgba(18,32,48,.46);backdrop-filter:blur(6px)}' +
    '.nx-dialog{width:min(420px,100%);max-height:86vh;overflow:auto;border-radius:18px;padding:16px;' +
      'background:var(--surf-1,rgba(255,255,255,.94));border:1px solid var(--line,rgba(91,155,213,.26));' +
      'box-shadow:var(--sh-pop,0 10px 32px rgba(60,95,135,.20));color:var(--ink,#26364A)}' +
    '.nx-dialog h3{margin:0 0 4px;font-size:16px}.nx-dialog .nx-sub{margin:0 0 12px;font-size:11.5px;color:var(--ink-soft,#54687D);line-height:1.6}' +
    '.nx-q{font-size:13px;font-weight:700;margin:10px 0 8px;line-height:1.6}' +
    '.nx-code{font-family:Consolas,Monaco,monospace;font-size:12.5px;line-height:1.6;padding:9px 11px;border-radius:9px;' +
      'background:var(--surf-sunk,rgba(91,155,213,.10));color:var(--ink,#26364A);white-space:pre-wrap}' +
    '.nx-opt{display:block;width:100%;text-align:left;margin:6px 0;padding:9px 11px;border-radius:10px;cursor:pointer;' +
      'font-family:Consolas,Monaco,monospace;font-size:12.5px;color:var(--ink,#26364A);' +
      'background:var(--surf-2,rgba(255,255,255,.6));border:1px solid var(--line,rgba(91,155,213,.26))}' +
    '.nx-opt:hover{background:var(--accent-soft,#D9EAF7)}' +
    '.nx-opt.ok{background:rgba(59,154,108,.16);border-color:var(--ok,#3B9A6C)}' +
    '.nx-opt.bad{background:rgba(199,91,91,.14);border-color:var(--bad,#C75B5B)}' +
    '.nx-tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}' +
    '.nx-tile{min-height:64px;padding:9px;border-radius:11px;cursor:pointer;text-align:left;font-size:11.5px;line-height:1.5;' +
      'font-family:Consolas,Monaco,monospace;color:var(--ink,#26364A);background:var(--surf-2,rgba(255,255,255,.6));' +
      'border:1px solid var(--line,rgba(91,155,213,.26))}' +
    '.nx-tile.sel{border-color:var(--accent,#5B9BD5);background:var(--accent-soft,#D9EAF7)}' +
    '.nx-tile.gone{opacity:.28;pointer-events:none;text-decoration:line-through}' +
    '.nx-bar{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px;font-size:11.5px;color:var(--ink-soft,#54687D)}' +
    '.nx-btn{padding:7px 14px;border-radius:99px;cursor:pointer;font-size:12px;font-weight:700;' +
      'color:#fff;background:var(--accent,#5B9BD5);border:0}' +
    '.nx-btn.ghost{color:var(--accent-ink,#2F6494);background:var(--surf-2,rgba(255,255,255,.6));border:1px solid var(--line,rgba(91,155,213,.26))}' +
    /* 连接设置对话框：不依赖 window.prompt（原生 WebView 会吞掉 JS 原生对话框） */
    '.nx-input{display:block;width:100%;box-sizing:border-box;margin:4px 0 14px;padding:10px 12px;border-radius:10px;' +
      'font-size:13px;line-height:1.5;color:var(--ink,#26364A);background:var(--surf-2,rgba(255,255,255,.72));' +
      'border:1px solid var(--line,rgba(91,155,213,.26));outline:none}' +
    '.nx-input:focus{border-color:var(--accent,#5B9BD5);box-shadow:0 0 0 3px var(--accent-soft,#D9EAF7)}' +
    '.nx-dlg-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:4px}' +
    '.nx-feedback{margin-top:9px;font-size:12px;line-height:1.6;color:var(--ink-soft,#54687D)}';
    var st = document.createElement('style');
    st.id = 'nex-shared-style';
    st.textContent = css;
    document.head.appendChild(st);
  }

  /* ------------------------------------------------------------ 小游戏
   * 两个原本「开发中~ / 敬请期待」的占位，这里补成两端一致的可玩实现。
   */

  var CHAIN_QUESTIONS = [
    { code: 'int x = 5;', opts: ['x++;', 'x + 1;', 'int = x;', 'x::y;'], ok: 0, why: 'x++ 是合法的自增表达式语句。' },
    { code: 'std::vector<int> v{1,2,3};', opts: ['v.push_back(4);', 'v.push_back<int>(4);', 'v + 4;', 'v.end = 4;'], ok: 0, why: 'push_back 是成员函数，模板参数由 vector 决定，无需再写 <int>。' },
    { code: 'int* p = new int(7);', opts: ['delete p;', 'free p;', 'delete[] p;', 'p.close();'], ok: 0, why: 'new 配 delete；delete[] 只用于 new[] 分配的数组。' },
    { code: 'const int N = 3;', opts: ['int a[N];', 'int a[N+1.5];', 'int a[-N];', 'int a(N);'], ok: 0, why: '编译期常量可作数组长度；函数式 int a(N) 声明的是函数/直接初始化，语义不同。' },
    { code: 'auto f = [] (int a) { return a * 2; };', opts: ['int r = f(3);', 'int r = f<int>(3);', 'int r = f[3];', 'int r = f{3};'], ok: 0, why: 'lambda 的调用运算符直接用 f(3)，不能加模板参数或下标。' }
  ];

  var BUG_PAIRS = [
    { k: 'uninit', text: 'int x;\ncout << x;' },
    { k: 'uninit', text: 'int arr[3];\nreturn arr[0];' },
    { k: 'oob', text: 'int a[3];\na[3] = 1;' },
    { k: 'oob', text: 'v[v.size()] = 9;' },
    { k: 'leak', text: 'int* p = new int[10];\n// 没有 delete[]' },
    { k: 'leak', text: 'malloc(64);\n// 没有 free' },
    { k: 'dangle', text: 'int* p = &local;\nreturn p;' },
    { k: 'dangle', text: 'delete p;\nuse(*p);' }
  ];
  var BUG_LABEL = { uninit: '未初始化', oob: '越界访问', leak: '内存泄漏', dangle: '悬垂指针' };

  var game = { key: null, qi: 0, score: 0, locked: false, sel: null, gone: {}, feedback: '' };
  var chainTimer = null;

  function gameHTML() {
    var head = '<div class="nx-dialog"><h3>' +
      (game.key === 'chain' ? '🔤 语法接龙' : '🐛 Bug 消消乐') + '</h3>' +
      '<p class="nx-sub">' + (game.key === 'chain'
        ? '和凯喵轮流续写：选出能接在下面这句之后、且合法可编译的 C++ 语句。共 ' + CHAIN_QUESTIONS.length + ' 题。'
        : '把「同一类错误」的两张卡配成一对消掉，全部消完即通关。') + '</p>';
    var body = '';
    if (game.key === 'chain') {
      var q = CHAIN_QUESTIONS[game.qi];
      if (q) {
        body += '<div class="nx-q">第 ' + (game.qi + 1) + ' / ' + CHAIN_QUESTIONS.length + ' 题 · 接在：</div>';
        body += '<div class="nx-code">' + esc(q.code) + '</div>';
        q.opts.forEach(function (o, i) {
          var cls = game.locked ? (i === q.ok ? ' ok' : (i === game.sel ? ' bad' : '')) : '';
          body += '<button type="button" class="nx-opt' + cls + '" onclick="NexGame.pick(' + i + ')">' + esc(o) + '</button>';
        });
        body += '<div class="nx-feedback">' + (game.feedback ? esc(game.feedback) : '选一句能合法接续、且能编译通过的 C++ 语句') + '</div>';
      } else {
        body += '<div class="nx-feedback">🎉 全部答完！本次答对 <b>' + game.score + ' / ' + CHAIN_QUESTIONS.length + '</b> 题。</div>';
      }
    } else {
      body += '<div class="nx-tiles">';
      BUG_PAIRS.forEach(function (p, i) {
        var cls = game.gone[i] ? ' gone' : (game.sel === i ? ' sel' : '');
        body += '<button type="button" class="nx-tile' + cls + '" onclick="NexGame.tap(' + i + ')">' + esc(p.text) + '</button>';
      });
      body += '</div>';
      body += '<div class="nx-feedback">已消除 <b>' + Object.keys(game.gone).length + ' / ' + BUG_PAIRS.length + '</b> 张 · ' +
        (game.sel !== null && !game.locked ? '再选一张同类错误' : '训练排错直觉，错误归类比死记语法更重要') + '</div>';
    }
    var foot = '<div class="nx-bar"><span>' + (game.feedback ? esc(game.feedback) : (game.key === 'chain' ? '答对 +1 分 · 通关 +80 EXP' : '配对成功消除 · 通关 +80 EXP')) + '</span>' +
      '<span><button type="button" class="nx-btn ghost" onclick="NexGame.close()">关闭</button> ' +
      '<button type="button" class="nx-btn" onclick="NexGame.reset()">再来一局</button></span></div></div>';
    return '<div class="nx-overlay" id="nxOverlay" onclick="if(event.target===this)NexGame.close()">' + head + body + foot + '</div>';
  }

  function paintGame() {
    var old = $('nxOverlay');
    var wrap = document.createElement('div');
    wrap.innerHTML = gameHTML();
    var node = wrap.firstChild;
    if (old) old.parentNode.replaceChild(node, old);
    else document.body.appendChild(node);
  }

  function openGame(key) {
    if (chainTimer) { clearTimeout(chainTimer); chainTimer = null; }
    game = { key: key, qi: 0, score: 0, locked: false, sel: null, gone: {}, feedback: '' };
    injectStyle();
    paintGame();
  }

  function pick(i) {
    if (game.locked || game.key !== 'chain') return;
    var q = CHAIN_QUESTIONS[game.qi];
    if (!q) return;
    game.sel = i; game.locked = true;
    game.feedback = (i === q.ok ? '✅ 正确：' : '❌ 再想想：') + q.why;
    if (i === q.ok) game.score++;
    paintGame();
    chainTimer = setTimeout(function () {
      chainTimer = null;
      game.qi++; game.locked = false; game.sel = null;
      if (game.qi >= CHAIN_QUESTIONS.length) {
        NexApp.recordGame('chain', game.score);
        game.feedback = '🎉 通关！好感 +2 · 金币 +80';
      } else {
        game.feedback = '';
      }
      paintGame();
    }, 1100);
  }

  function tap(i) {
    if (game.key !== 'bugs' || game.gone[i]) return;
    if (game.sel === null) { game.sel = i; game.feedback = '已选第一张，找同类错误'; paintGame(); return; }
    if (game.sel === i) { game.sel = null; game.feedback = ''; paintGame(); return; }
    var a = BUG_PAIRS[game.sel], b = BUG_PAIRS[i];
    if (a.k === b.k) {
      game.gone[game.sel] = true; game.gone[i] = true;
      game.feedback = '✅ ' + BUG_LABEL[a.k] + ' · 配对成功';
      game.sel = null;
      if (Object.keys(game.gone).length === BUG_PAIRS.length) {
        NexApp.recordGame('bugs', 4);
        game.feedback = '🎉 全部消除！好感 +2 · 金币 +80';
      }
    } else {
      game.feedback = '❌ 这两张不是同一类错误，再试试';
      game.sel = null;
    }
    paintGame();
  }

  function closeGame() { var o = $('nxOverlay'); if (o) o.parentNode.removeChild(o); }
  function resetGame() { var k = game.key; openGame(k); }

  /* ------------------------------------------------------------ 统一动作入口 */

  function action(name, val) {
    switch (name) {
      case 'signin': signIn(); break;
      case 'quest': completeQuest(val); break;
      case 'tame': tameMonster(); break;
      case 'game': openGame(val); break;
      case 'refresh': refresh(); break;
      case 'connect': promptConnect(); break;
      case 'realtime': clearOverride(); break;
      case 'mood': previewMood(val); break;
      default: break;
    }
  }

  /* ------------------------------------------------------------ 启动 */

  function boot() {
    injectStyle();
    emit();                       // 先用本地快照把页面填满，绝不白屏
    document.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('[data-view]') : null;
      if (!t || !t.dataset || !t.dataset.view) return;
      var label = (t.getAttribute('title') || t.textContent || '').trim().slice(0, 8) || '当前页面';
      setPage(t.dataset.view, label);
    }, true);
    ensureSession();              // 本机部署自动领会话后连后端；不可用则回落本地
    // 跨页签同步：另一端改动了快照，这一端跟着更新
    global.addEventListener('storage', function (e) {
      if (e.key === LS_STATE && e.newValue) {
        state = normalizeState(jsonParse(e.newValue, state));
        emit();
      }
      if (e.key === LS_TOKEN) connect();
    });
    // 每分钟重算一次（跨零点 / 深夜台词 / 心情随时段变化）
    setInterval(function () { if (!flash) emit(); }, 60000);
  }

  /* ------------------------------------------------------------ 导出 */

  global.NexApp = {
    version: '1.0.0',
    MOODS: MOODS,
    boot: boot,
    render: render,
    view: view,
    bindings: bindings,
    moodCardHTML: moodCardHTML,
    moodImage: moodImage,
    subscribe: function (fn) { if (typeof fn === 'function') listeners.push(fn); },
    getState: function () { return state; },
    getMode: function () { return mode; },
    connectionInfo: connectionInfo,
    patch: patch,
    bumpAff: bumpAff,
    flashMood: flashMood,
    previewMood: previewMood,
    clearOverride: clearOverride,
    setPage: setPage,
    completeQuest: completeQuest,
    signIn: signIn,
    tameMonster: tameMonster,
    recordGame: recordGame,
    connect: connect,
    refresh: refresh,
    promptConnect: promptConnect,
    getBase: getBase,
    setBase: setBase,
    action: action
  };
  global.NexGame = {
    open: openGame, pick: pick, tap: tap, close: closeGame, reset: resetGame
  };
  global.nexAction = action;
  global.nexGame = openGame;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
