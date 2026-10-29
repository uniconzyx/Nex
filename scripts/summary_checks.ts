// summary_checks.ts —— P2 章节总结表 / 408 专轨 断言入口
// ============================================================================
// 被 scripts/verify_logic_chain.mjs --check-summary 通过 esbuild 打包后由 node 执行。
// 驱动 lib/chapterSummary.ts 与 lib/examTracks.ts，验证：
//
//   1) buildChapterSummary(done)     —— 已通关章返回 7 维非空
//   2) buildChapterSummary(notDone)  —— 未通关章返回 null（不变量）
//   3) buildTrack408Summary(empty)   —— 23 章 / 4 模块 / 0 通关 / 均分 0（数据结构 7 / 计组 7 / OS 5 / 网络 4）
//   4) buildTrack408Summary(done)    —— 标记通关的章进入对应模块 doneCount
//   5) markdown 导出不抛错
//
// 任意断言失败 → process.exit(1)，与 logic_chain_checks 同一套守门哲学。
// ============================================================================
import {
  buildChapterSummary,
  buildAllChapterSummaries,
  summaryToMarkdown,
  type ChapterSummary,
} from '../frontend/src/lib/chapterSummary';
import {
  buildTrack408Summary,
  trackSummaryToMarkdown,
  build408ChapterRow,
} from '../frontend/src/lib/examTracks';
import type { ProgressState } from '../frontend/src/lib/gameTypes';

function emptyState(): ProgressState {
  return {
    theme: 'light',
    outfit: '',
    doneProjects: [],
    doneChapters: [],
    checkins: [],
    coins: 0,
    coinLedger: [],
    bestiary: {},
    chapterRuns: {},
    answers: {},
    daily: null,
    shards: 0,
  } as ProgressState;
}

let fail = 0;
const assert = (cond: boolean, msg: string) => {
  if (!cond) {
    fail++;
    console.error('  ✗ ' + msg);
  } else {
    console.log('  ✓ ' + msg);
  }
};

console.log('[1] buildChapterSummary：已通关章返回 7 维非空');
const st = emptyState();
st.chapterRuns = {
  'fund-ch01': { concept: 1, drill: 1, boss: 1, attempts: 1, lastAt: 0 },
};
const s = buildChapterSummary('fund-ch01', st);
assert(s !== null, 'fund-ch01 通关 → 返回总结（非 null）');
if (s) {
  const dims: [string, ChapterSummary['goals']][] = [
    ['goals', s.goals],
    ['concepts', s.concepts],
    ['pitfalls', s.pitfalls],
    ['exercises', s.exercises],
    ['interview', s.interview],
    ['project', s.project],
  ];
  for (const [name, d] of dims) {
    assert(d.count >= 0 && 'items' in d, `${name} 维度结构完整`);
  }
  assert(s.totalMastery === 100, 'totalMastery === 100');
  assert(s.goals.count >= 1, `goals 带内容（实际 ${s.goals.count} 条）`);
  assert(s.interview.count >= 1, `interview 带内容（实际 ${s.interview.count} 条）`);
}

console.log('[2] buildChapterSummary：未通关章返回 null（不变量）');
const notDone = buildChapterSummary('fund-ch02', st);
assert(notDone === null, 'fund-ch02 未通关 → 返回 null');
const neverTouched = buildChapterSummary('fund-ch99', st);
assert(neverTouched === null, '不存在/未学的章 → 返回 null');

console.log('[3] buildTrack408Summary：空状态 = 23 章 / 4 模块 / 0 通关 / 均分 0');
const t0 = buildTrack408Summary(emptyState());
assert(t0.modules.length === 4, `模块数 = 4（实际 ${t0.modules.length}）`);
const total = t0.modules.reduce((n, m) => n + m.chapterCount, 0);
// 408.json 现状（按王道收口、剔除 STL/Redis/Kafka 后）：
// 数据结构 7 + 计组 7 + OS 5 + 网络 4 = 23
assert(total === 23, `章节总数 = 23（实际 ${total}）`);
assert(t0.totalDone === 0, 'totalDone === 0');
assert(t0.overallAvg === 0, 'overallAvg === 0');
const ds = t0.modules.find((m) => m.module === '数据结构');
assert(!!ds && ds.chapterCount === 7, `数据结构模块 7 章（实际 ${ds?.chapterCount}）`);
const co = t0.modules.find((m) => m.module === '计算机组成原理');
// 王道 7 章：概述/数据表示/存储与CPU/指令/CPU/总线/IO
assert(!!co && co.chapterCount === 7, `计组模块 7 章（实际 ${co?.chapterCount}）`);
const os = t0.modules.find((m) => m.module === '操作系统');
// 概述/进程线程调度/内存管理/文件管理/IO 与磁盘 = 5 章
assert(!!os && os.chapterCount === 5, `操作系统模块 5 章（实际 ${os?.chapterCount}）`);
const net = t0.modules.find((m) => m.module === '计算机网络');
// 体系结构/物理层/数据链路层/应用层 = 4 章
assert(!!net && net.chapterCount === 4, `计算机网络模块 4 章（实际 ${net?.chapterCount}）`);

console.log('[4] buildTrack408Summary：标记通关的章进入对应模块 doneCount');
const t1 = buildTrack408Summary(st);
const ds1 = t1.modules.find((m) => m.module === '数据结构')!;
assert(ds1.doneCount === 1, `数据结构 doneCount = 1（实际 ${ds1.doneCount}）`);
const row = build408ChapterRow('fund-ch01', st);
assert(row !== null && row.done === true, 'build408ChapterRow(fund-ch01) 标记 done');
const offTrack = build408ChapterRow('agent-ch01', st);
assert(offTrack === null, '非 408 章 build408ChapterRow → null');

console.log('[5] markdown 导出不抛错');
try {
  if (s) summaryToMarkdown(s);
  trackSummaryToMarkdown(t1);
  buildAllChapterSummaries(st);
  assert(true, 'summaryToMarkdown / trackSummaryToMarkdown / buildAllChapterSummaries 正常执行');
} catch (e) {
  assert(false, 'markdown 导出抛错：' + String(e));
}

console.log(fail === 0 ? '\nSUMMARY_OK' : `\nSUMMARY_FAIL (${fail})`);
if (fail > 0) process.exit(1);
