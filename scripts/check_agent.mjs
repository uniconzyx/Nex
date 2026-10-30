#!/usr/bin/env node
/**
 * check_agent.mjs —— Agent 全链路离线验收
 * ============================================================================
 * 为什么不用浏览器：agent 的价值主张是「数字可溯源」，那是纯逻辑性质，
 * 用 Playwright 去点按钮验它，等于用显微镜看日历。这个脚本用 esbuild 把
 * TS 打成一个 ESM bundle，在 Node 里直接跑，一次 2 秒，CI 友好。
 *
 * 验的是五件事：
 *   A. 降级路径：planner 崩了，规则序列还能出一份「数字全对」的报告
 *   B. 正常路径：按协议走的 planner，报告里的数字全部能溯源（audit 零 issue）
 *   C. 守门有效：故意编一个数字，audit 必须抓到（证明 B 不是空转）
 *   D. evidence 指错：指向不存在的步骤 / 指错工具，必须是 error 级
 *   E. 导出：.ipynb 结构合法，真实 stdout 落在 code cell 的 outputs 里
 *
 * 用法：
 *   node scripts/check_agent.mjs
 * ============================================================================
 */

import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ENTRY = path.join(ROOT, 'frontend/src/lib/agent/index.ts');
const OUT = path.join(os.tmpdir(), `cppmind_agent_check_${process.pid}.mjs`);

// esbuild 装在 frontend/ 下（根目录没有 node_modules），所以按绝对路径引入
const esb = await import(pathToFileURL(path.join(ROOT, 'frontend/node_modules/esbuild/lib/main.js')).href);
const build = esb.build ?? esb.default.build;

let pass = 0;
let fail = 0;
const failures = [];

function ok(name, cond, detail) {
  if (cond) {
    pass += 1;
    console.log(`  ✓ ${name}`);
  } else {
    fail += 1;
    failures.push(`${name}${detail ? ` —— ${detail}` : ''}`);
    console.log(`  ✗ ${name}${detail ? ` —— ${detail}` : ''}`);
  }
}

function section(t) {
  console.log(`\n${t}`);
}

/* ========================================================================== */
/* 打包                                                                        */
/* ========================================================================== */

console.log('构建 agent bundle…');
await build({
  entryPoints: [ENTRY],
  outfile: OUT,
  bundle: true,
  format: 'esm',
  platform: 'node',
  target: 'node18',
  logLevel: 'error',
  // react 等 UI 依赖不该被扯进来；agent 层只依赖 data + graph + gameTypes
  external: ['react', 'react-dom'],
});

const A = await import(pathToFileURL(OUT).href);
fs.rmSync(OUT, { force: true });

/* ========================================================================== */
/* 夹具                                                                        */
/* ========================================================================== */

/** 造一个 ml 学科的进度：3 章满通关、2 章半通、其余未开始 */
function fakeProgress() {
  const chapterRuns = {};
  const answers = {};
  const done = (id, concept, drill, boss) => ({
    concept,
    drill,
    boss,
    attempts: (concept + drill + boss) * 2,
    lastAt: 0,
  });
  chapterRuns['ml-ch01'] = done('ml-ch01', 1, 1, 1);
  chapterRuns['ml-ch02'] = done('ml-ch02', 1, 1, 1);
  chapterRuns['ml-ch05'] = done('ml-ch05', 1, 1, 1);
  chapterRuns['ml-ch03'] = done('ml-ch03', 1, 0, 0); // 卡在演练
  chapterRuns['ml-ch04'] = done('ml-ch04', 1, 1, 0); // 卡在 BOSS
  // 错题：ml-ch03 三道、ml-ch04 一道
  answers['ml-ch03-x1'] = { chapterId: 'ml-ch03', ok: false, at: 1 };
  answers['ml-ch03-x2'] = { chapterId: 'ml-ch03', ok: false, at: 2 };
  answers['ml-ch03-x3'] = { chapterId: 'ml-ch03', ok: false, at: 3 };
  answers['ml-ch04-x1'] = { chapterId: 'ml-ch04', ok: false, at: 4 };
  answers['ml-ch01-a1'] = { chapterId: 'ml-ch01', ok: true, at: 5 };

  return {
    theme: 'light',
    outfit: 'default',
    doneProjects: [],
    doneChapters: ['ml-ch01', 'ml-ch02', 'ml-ch05'],
    checkins: [],
    coins: 0,
    coinLedger: [],
    bestiary: {},
    chapterRuns,
    answers,
    daily: null,
    shards: 0,
  };
}

/** 假 Python 执行器：确定性输出，顺便模拟一次「报错→改对」的重试 */
function fakeRunner() {
  let call = 0;
  return async (code) => {
    call += 1;
    if (call === 1) {
      return {
        stdout: '',
        stderr: 'NameError: name "np" is not defined',
        interrupted: false,
        durationMs: 12,
        error: { name: 'NameError', message: 'name "np" is not defined' },
        images: [],
      };
    }
    return {
      stdout: 'lr=0.01: 相邻两步损失比 ≈ 0.9604（理论 0.9604）\nlr=0.1: 相邻两步损失比 ≈ 0.6400（理论 0.6400）\n',
      stderr: '',
      interrupted: false,
      durationMs: 34,
      error: null,
      images: [],
    };
  };
}

const progress = fakeProgress();

/* ========================================================================== */
/* A. 降级路径                                                                 */
/* ========================================================================== */

section('A. 降级路径（planner 崩溃 → 规则序列 → 仍有报告）');
{
  const run = await A.runAgent({
    scenario: A.getScenario('diagnose'),
    subject: 'ml',
    progress,
    planner: async () => {
      throw new Error('LLM 超时（模拟）');
    },
    maxSteps: 8,
  });

  ok('stop 原因是 final（规则跑完=正常收尾）', run.stopped === 'final', `实际 ${run.stopped}`);
  ok('规则序列跑完了 5 步', run.steps.length >= 5, `实际 ${run.steps.length} 步`);
  ok('拿到了报告', !!run.report);
  ok('报告有 ≥3 个小节', (run.report?.sections.length ?? 0) >= 3, `实际 ${run.report?.sections.length}`);
  ok(
    '定位到了真正最弱的章（ml-ch03 或 ml-ch04）',
    /ml-ch0[34]/.test(JSON.stringify(run.report?.sections ?? [])),
    JSON.stringify(run.report?.sections?.map((s) => s.heading)),
  );
  const issues = A.auditReport(run);
  const errs = issues.filter((i) => i.level === 'error');
  ok('审计无 error（降级路径的数字也全部可溯源）', errs.length === 0, JSON.stringify(errs));
  ok('降级时有明确的原因记录', typeof run.error === 'string' && run.error.includes('planner'), run.error);
}

/* ========================================================================== */
/* B. 正常路径：按协议走的 planner                                             */
/* ========================================================================== */

section('B. 正常路径（planner 按协议走 → 报告数字可溯源）');
let goodRun;
{
  let n = 0;
  let snapshot = null; // 第 1 步的真实观察，供第 2 步引用
  const planner = async () => {
    n += 1;
    if (n === 1) {
      return { type: 'tool', thought: '先拿整体进度', tool: 'get_progress', args: { subject: 'ml' } };
    }
    if (n === 2) {
      return {
        type: 'tool',
        thought: '看最弱章的易错点',
        tool: 'read_chapter',
        args: { chapter_id: snapshot.weak[0], focus: 'pitfalls' },
      };
    }
    // 用工具给出的汇总数（而不是自己 reduce 一遍）——这正是「数字只由工具算」的做法
    const avg = snapshot.stats.avg_mastery;
    return {
      type: 'final',
      thought: '定位清楚，可以出报告',
      report: {
        title: 'ml 学情诊断',
        scenario: 'diagnose',
        headline: `平均掌握度 ${avg}%，最弱是 ${snapshot.weak[0]}`,
        sections: [
          {
            heading: '整体',
            body: `共 ${snapshot.items.length} 章，平均掌握度 ${avg}%。`,
            evidence: 'get_progress#1',
          },
          {
            heading: '最弱章',
            body: `**${snapshot.weak[0]}** 掌握度最低，先补它的易错点。`,
            evidence: 'get_progress#1',
          },
        ],
      },
    };
  };

  goodRun = await A.runAgent({
    scenario: A.getScenario('diagnose'),
    subject: 'ml',
    progress,
    planner,
    maxSteps: 6,
    onStep: (s) => {
      if (s.tool === 'get_progress' && s.observation?.ok) snapshot = s.observation.data;
    },
  });

  ok('stop=final', goodRun.stopped === 'final', goodRun.stopped);
  ok('走了 3 步（2 次工具 + 1 次 final）', goodRun.steps.length === 3, `实际 ${goodRun.steps.length}`);
  ok('final 步骤没有工具', goodRun.steps[2].tool === undefined);
  const issues = A.auditReport(goodRun);
  ok('审计零 issue（含 warn）', issues.length === 0, JSON.stringify(issues));
  ok('报告里引用了真实章节 id', /ml-ch0\d/.test(JSON.stringify(goodRun.report)), JSON.stringify(goodRun.report?.headline));
}

/* ========================================================================== */
/* C. 守门有效性：故意编数字                                                    */
/* ========================================================================== */

section('C. 守门有效（编数字必须被抓）');
{
  const run = await A.runAgent({
    scenario: A.getScenario('diagnose'),
    subject: 'ml',
    progress,
    maxSteps: 3,
    planner: (() => {
      let n = 0;
      return async () => {
        n += 1;
        if (n === 1) return { type: 'tool', thought: '拿进度', tool: 'get_progress', args: { subject: 'ml' } };
        return {
          type: 'final',
          thought: '出报告',
          report: {
            title: '编的报告',
            scenario: 'diagnose',
            headline: '你的掌握度 97.3%',
            sections: [{ heading: '编的', body: '你已经掌握了 97.3%，错题 999 道。', evidence: 'get_progress#1' }],
          },
        };
      };
    })(),
  });
  const issues = A.auditReport(run);
  const text = JSON.stringify(issues);
  ok('抓到了编造的数字', issues.length > 0, text);
  ok('明确指出 97.3 找不到', text.includes('97.3'), text);
  ok('明确指出 999 找不到', text.includes('999'), text);
}

/* ========================================================================== */
/* D. evidence 指错                                                            */
/* ========================================================================== */

section('D. evidence 指错（必须是 error 级）');
{
  const mk = (evidence) =>
    A.runAgent({
      scenario: A.getScenario('diagnose'),
      subject: 'ml',
      progress,
      maxSteps: 3,
      planner: (() => {
        let n = 0;
        return async () => {
          n += 1;
          if (n === 1) return { type: 'tool', thought: '拿进度', tool: 'get_progress', args: { subject: 'ml' } };
          return {
            type: 'final',
            thought: '出报告',
            report: {
              title: 't',
              scenario: 'diagnose',
              headline: 'h',
              sections: [{ heading: 's', body: '定性结论，无数字。', evidence }],
            },
          };
        };
      })(),
    });

  const r1 = await mk('get_progress#9');
  const e1 = A.auditReport(r1).filter((i) => i.level === 'error');
  ok('指向不存在的步骤 → error', e1.length > 0, JSON.stringify(e1));

  const r2 = await mk('list_chapters#1');
  const e2 = A.auditReport(r2).filter((i) => i.level === 'error');
  ok('指向的工具名与步骤不符 → error', e2.length > 0, JSON.stringify(e2));

  const r3 = await mk('随便写');
  const e3 = A.auditReport(r3).filter((i) => i.level === 'error');
  ok('evidence 格式非法 → error', e3.length > 0, JSON.stringify(e3));
}

/* ========================================================================== */
/* E. .ipynb 导出                                                              */
/* ========================================================================== */

section('E. .ipynb 导出');
{
  let lastStep = null; // 闭包里不能引用尚未赋值的 run（TDZ），用 onStep 捕获
  const run = await A.runAgent({
    scenario: A.getScenario('experiment'),
    subject: 'ml',
    chapterId: 'ml-ch01',
    progress,
    runner: fakeRunner(),
    maxSteps: 6,
    onStep: (s) => {
      lastStep = s;
    },
    planner: (() => {
      let n = 0;
      return async () => {
        n += 1;
        if (n === 1) {
          return { type: 'tool', thought: '读本章概念', tool: 'read_chapter', args: { chapter_id: 'ml-ch01', focus: 'concepts' } };
        }
        if (n === 2) {
          return {
            type: 'tool',
            thought: '跑学习率实验',
            tool: 'run_python',
            args: { code: A.labFor('ml-ch01').template.code },
          };
        }
        if (n === 3) {
          // 第 2 步拿到的是报错观察（ok=true 但 data.ok=false），按协议应当改代码重跑
          return {
            type: 'tool',
            thought: '上次报错 NameError，补上 import numpy 再跑一次',
            tool: 'run_python',
            args: { code: `import numpy as np\n${A.labFor('ml-ch01').template.code}` },
          };
        }
        return {
          type: 'final',
          thought: '实验跑通',
          report: {
            title: 'ml-ch01 学习率实验',
            scenario: 'experiment',
            headline: '学习率 0.1 时收敛最快，1.05 震荡不收敛',
            sections: [{ heading: '实验结论', body: '三次实验的真实输出见下方代码单元。', evidence: `run_python#${lastStep.idx}` }],
            labCode: lastStep.args.code,
            labOutput: lastStep.observation.raw,
          },
        };
      };
    })(),
  });

  ok('实验路径 stop=final', run.stopped === 'final', run.stopped);
  const pySteps = run.steps.filter((s) => s.tool === 'run_python');
  ok('run_python 被真的调用了', pySteps.length >= 1);
  ok('第 1 次调用报错、第 2 次成功（模拟改代码重试）', pySteps.length >= 2, `实际 ${pySteps.length} 次`);
  ok('报错那次也是 ok=true 的观察（错误信息回填给 planner）', pySteps[0]?.observation?.ok === true);

  const issues = A.auditReport(run);
  const errs = issues.filter((i) => i.level === 'error');
  ok('实验报告审计无 error', errs.length === 0, JSON.stringify(errs));

  const nb = A.toIpynb(run.report, { subject: 'ml', generatedAt: '2026-10-30T00:00:00Z' });
  ok('nbformat=4 / minor=5', nb.nbformat === 4 && nb.nbformat_minor === 5);
  ok('有 markdown 单元', nb.cells.some((c) => c.cell_type === 'markdown'));
  const code = nb.cells.find((c) => c.cell_type === 'code');
  ok('有 code 单元', !!code);
  ok('code 单元带真实 stdout', !!code && (code.outputs ?? []).some((o) => o.output_type === 'stream'));
  ok('code 单元源码与最后一次成功运行的代码一致', code?.source.join('') === pySteps[pySteps.length - 1]?.args.code);
  ok('每个 code 单元的 source 是行数组（nbformat 要求）', Array.isArray(code?.source));
  const json = A.ipynbJson(nb);
  ok('JSON 可被解析且含 cells', JSON.parse(json).cells.length === nb.cells.length);
}

/* ========================================================================== */
/* 汇总                                                                        */
/* ========================================================================== */

console.log('\n' + '─'.repeat(66));
if (fail === 0) {
  console.log(`AGENT_OK  ${pass}/${pass} 通过`);
  process.exit(0);
} else {
  console.log(`AGENT_FAIL  ${pass} 通过 / ${fail} 失败`);
  for (const f of failures) console.log('  - ' + f);
  process.exit(1);
}
